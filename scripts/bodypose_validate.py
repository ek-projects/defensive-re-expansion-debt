from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import zipfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, spearmanr

BODYPOSE_MATCHES = (1925299, 1996435)
MIN_SHOULDER_WIDTH_M = 0.15
MAX_SHOULDER_WIDTH_M = 0.60
MAX_ERR_CM = 15.0


def fold_pose_to_tracking(frame: int) -> int:
    return math.floor(frame * 0.4 + 0.5)


def reliable_outward_alignment(player: dict, centroid_y: float) -> float | None:
    joints = player.get("joints")
    if not joints:
        return None
    left, right = joints.get("lShoulder"), joints.get("rShoulder")
    if not left or not right:
        return None
    lx, ly, _ = left["xyz"]
    rx, ry, _ = right["xyz"]
    shoulder_width = math.hypot(rx - lx, ry - ly)
    error = max(left.get("p90_mae_cm") or math.inf, right.get("p90_mae_cm") or math.inf)
    if not (MIN_SHOULDER_WIDTH_M <= shoulder_width <= MAX_SHOULDER_WIDTH_M):
        return None
    if error > MAX_ERR_CM or shoulder_width == 0:
        return None
    # SkillCorner worked example: left→right shoulder axis rotated +90 degrees.
    facing_y = (rx - lx) / shoulder_width
    rel_y = float(player["y"]) - centroid_y
    if abs(rel_y) < 1e-9:
        return None
    outward_sign = 1.0 if rel_y > 0 else -1.0
    return outward_sign * facing_y


def process_match(match_id: int, raw_root: Path, processed: Path, bodypose: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    match_dir = raw_root / str(match_id)
    features = pd.read_csv(processed / f"{match_id}_frame_features.csv")
    features = features.set_index("frame")
    episodes = pd.read_csv(processed / f"{match_id}_line_break_recovery.csv")
    episodes = episodes[episodes["furthest_line_break"] == "second_last"].copy()

    members: dict[int, list[int]] = {}
    for idx, event in episodes.iterrows():
        start = int(event["frame_start"])
        end = start + int(round(float(event["window_seconds"]) * 10))
        for frame in range(start, end + 1):
            members.setdefault(frame, []).append(idx)

    meta = json.loads((match_dir / f"{match_id}_match.json").read_text())
    player_team = {
        int(p["id"]): int(p["team_id"])
        for p in meta["players"]
        if p.get("id") is not None and p.get("team_id") is not None
    }
    goalkeepers = {
        int(p["id"])
        for p in meta["players"]
        if (p.get("player_role") or {}).get("position_group", "").lower() == "goalkeeper"
    }

    accum: dict[int, list[tuple[float, int]]] = {}
    archive = bodypose / f"{match_id}.jsonl.zip"
    with zipfile.ZipFile(archive) as zf, zf.open(f"{match_id}.jsonl") as fh:
        for raw in fh:
            record = json.loads(raw)
            tracking_frame = fold_pose_to_tracking(int(record["frame"]))
            if tracking_frame not in members or tracking_frame not in features.index:
                continue
            defending_team = int(features.loc[tracking_frame, "defending_team_id"])
            defenders = []
            for player in record.get("player_data") or []:
                pid = player.get("player_id")
                if pid is None or player_team.get(int(pid)) != defending_team or int(pid) in goalkeepers:
                    continue
                if player.get("x") is None or player.get("y") is None:
                    continue
                defenders.append(player)
            if len(defenders) < 6:
                continue
            centroid_y = float(np.mean([float(p["y"]) for p in defenders]))
            values = [reliable_outward_alignment(p, centroid_y) for p in defenders]
            values = [v for v in values if v is not None]
            if len(values) < 4:
                continue
            accum.setdefault(tracking_frame, []).append((float(np.mean(values)), len(values)))

    frame_rows = []
    for frame, observations in accum.items():
        z_width = float(features.loc[frame, "z_width"])
        frame_rows.append({
            "match_id": match_id,
            "frame": frame,
            "z_width": z_width,
            "contract_excess": max(-z_width - 1.0, 0.0),
            "outward_readiness": float(np.mean([o[0] for o in observations])),
            "reliable_defenders": float(np.mean([o[1] for o in observations])),
        })
    frames = pd.DataFrame(frame_rows).sort_values("frame")

    event_rows = []
    for _, event in episodes.iterrows():
        start = int(event["frame_start"])
        end = start + int(round(float(event["window_seconds"]) * 10))
        q = frames[(frames["frame"] >= start) & (frames["frame"] <= end)]
        if len(q) < 10:
            continue
        event_rows.append({
            "match_id": match_id,
            "event_id": event["event_id"],
            "dred": float(event["width_contract_auc_10s"]),
            "dred_intensity": float(event["width_contract_mean_10s"]),
            "outward_readiness": float(q["outward_readiness"].mean()),
            "pose_tracking_frames": int(len(q)),
        })
    return frames, pd.DataFrame(event_rows)


def analyze(frames: pd.DataFrame, events: pd.DataFrame) -> dict:
    by_match = {}
    for match_id, q in frames.groupby("match_id"):
        contracted = q[q["contract_excess"] > 0]["outward_readiness"]
        normal = q[q["contract_excess"] <= 0]["outward_readiness"]
        rho = spearmanr(q["contract_excess"], q["outward_readiness"])
        by_match[str(match_id)] = {
            "tracking_frames": int(len(q)),
            "mean_reliable_defenders": float(q["reliable_defenders"].mean()),
            "contracted_frames": int(len(contracted)),
            "normal_frames": int(len(normal)),
            "outward_readiness_contracted": float(contracted.mean()),
            "outward_readiness_normal": float(normal.mean()),
            "frame_spearman_rho": float(rho.statistic),
            "frame_spearman_p_naive": float(rho.pvalue),
        }
    event_rho = spearmanr(events["dred_intensity"], events["outward_readiness"])
    positive = events[events["dred_intensity"] > 0]["outward_readiness"]
    zero = events[events["dred_intensity"] <= 0]["outward_readiness"]
    mw = mannwhitneyu(positive, zero, alternative="less")
    return {
        "hypothesis_frozen_before_test": (
            "greater abnormal lateral contraction should coincide with lower outward shoulder-orientation readiness"
        ),
        "matches": by_match,
        "pooled_event_level": {
            "events": int(len(events)),
            "dred_positive_events": int((events["dred_intensity"] > 0).sum()),
            "spearman_rho": float(event_rho.statistic),
            "spearman_p": float(event_rho.pvalue),
            "outward_readiness_dred_positive": float(positive.mean()),
            "outward_readiness_dred_zero": float(zero.mean()),
            "mann_whitney_one_sided_p": float(mw.pvalue),
        },
        "guardrail": (
            "Only two matches contain Body Pose. Frame-level p-values are serially dependent and are descriptive only; "
            "the Body Pose result is exploratory mechanistic support, not primary inferential evidence."
        ),
    }


def write_outputs(summary: dict, frames: pd.DataFrame, events: pd.DataFrame, output_dir: Path, figure_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "bodypose_validation.json").write_text(json.dumps(summary, indent=2) + "\n")
    frames.to_csv(output_dir / "bodypose_frame_metrics.csv", index=False)
    events.to_csv(output_dir / "bodypose_event_metrics.csv", index=False)

    lines = [
        "# DRED — Body Pose mechanism check",
        "",
        "Frozen hypothesis: when a defence is abnormally contracted after a second-last-line break, defenders should be less oriented outward relative to their team centre.",
        "",
        "| Match | Pose-aligned frames | Contracted outward readiness | Normal-width outward readiness |",
        "|---|---:|---:|---:|",
    ]
    for match_id, info in summary["matches"].items():
        lines.append(
            f"| {match_id} | {info['tracking_frames']} | {info['outward_readiness_contracted']:.3f} | {info['outward_readiness_normal']:.3f} |"
        )
    pooled = summary["pooled_event_level"]
    lines += [
        "",
        f"Across {pooled['events']} pose-covered line-break events, event-level DRED intensity has Spearman rho **{pooled['spearman_rho']:.3f}** with outward readiness. DRED-positive events average **{pooled['outward_readiness_dred_positive']:.3f}** versus **{pooled['outward_readiness_dred_zero']:.3f}** for DRED=0.",
        "",
        "This is exploratory mechanistic support only: there are two Body Pose matches and adjacent frames are serially dependent.",
    ]
    (output_dir / "bodypose_validation.md").write_text("\n".join(lines) + "\n")

    labels, contracted, normal = [], [], []
    for match_id, info in summary["matches"].items():
        labels.append(match_id)
        contracted.append(info["outward_readiness_contracted"])
        normal.append(info["outward_readiness_normal"])
    x = np.arange(len(labels)); width = 0.35
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.bar(x - width / 2, normal, width, label="Normal width")
    ax.bar(x + width / 2, contracted, width, label="Abnormally contracted")
    ax.axhline(0, linewidth=1)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Mean outward shoulder-orientation readiness")
    ax.set_title("Body Pose mechanism check")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figure_dir / "dred_bodypose_validation.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--processed", type=Path, default=Path("data/processed"))
    ap.add_argument("--bodypose", type=Path, default=Path("data/bodypose"))
    ap.add_argument("--output-dir", type=Path, default=Path("outputs"))
    ap.add_argument("--figure-dir", type=Path, default=Path("figures"))
    args = ap.parse_args()
    frame_parts, event_parts = [], []
    for match_id in BODYPOSE_MATCHES:
        frames, events = process_match(match_id, args.raw, args.processed, args.bodypose)
        frame_parts.append(frames); event_parts.append(events)
    frames = pd.concat(frame_parts, ignore_index=True)
    events = pd.concat(event_parts, ignore_index=True)
    summary = analyze(frames, events)
    write_outputs(summary, frames, events, args.output_dir, args.figure_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
