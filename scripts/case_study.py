from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from prototype_match import add_debt, build_frame_features


def event_row(path: Path, event_id: str) -> pd.Series:
    df = pd.read_csv(path, low_memory=False)
    hit = df[df["event_id"].astype(str) == str(event_id)]
    if len(hit) != 1:
        raise RuntimeError(f"expected one event {event_id}, found {len(hit)}")
    return hit.iloc[0]


def trajectory(frames: pd.DataFrame, event: pd.Series, horizon_s: int = 10) -> pd.DataFrame:
    start = int(event["frame_start"])
    phase = int(event["phase_index"])
    attack = int(event["team_id"])
    block = frames[
        (frames["phase_index"] == phase)
        & (frames["attack_team_id"] == attack)
        & (frames["frame"] >= start)
        & (frames["frame"] <= start + 10 * horizon_s)
    ].copy()
    block["seconds"] = (block["frame"] - start) / 10.0
    block["contraction_excess"] = (-block["z_width"] - 1.0).clip(lower=0.0)
    return block


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--match-id", default="1925299")
    ap.add_argument("--shot-event", default="8_774")
    ap.add_argument("--control-event", default="8_595")
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--out", type=Path, default=Path("figures/dred_case_study.png"))
    ap.add_argument("--summary", type=Path, default=Path("outputs/case_study_summary.json"))
    args = ap.parse_args()

    match_dir = args.raw / str(args.match_id)
    events_path = match_dir / f"{args.match_id}_dynamic_events.csv"
    shot = event_row(events_path, args.shot_event)
    control = event_row(events_path, args.control_event)

    frames = add_debt(build_frame_features(match_dir))
    shot_t = trajectory(frames, shot)
    control_t = trajectory(frames, control)

    meta = json.loads((match_dir / f"{args.match_id}_match.json").read_text())
    title = f"{meta['home_team']['short_name']} vs {meta['away_team']['short_name']}"

    fig, axes = plt.subplots(2, 1, figsize=(8, 6), sharex=True, sharey=True)
    examples = [
        (axes[0], shot_t, "High DRED — sustained contraction", args.shot_event),
        (axes[1], control_t, "DRED = 0 — lateral shape restored", args.control_event),
    ]
    for ax, block, label, eid in examples:
        ax.plot(block["seconds"], block["z_width"], linewidth=2)
        ax.axhline(-1.0, linestyle="--", linewidth=1)
        ax.axhline(0.0, linewidth=0.8)
        ax.fill_between(
            block["seconds"],
            block["z_width"],
            -1.0,
            where=block["z_width"] < -1.0,
            alpha=0.2,
        )
        ax.set_ylabel("Robust width deviation (z)")
        ax.set_title(f"{label} · event {eid}")
        ax.grid(alpha=0.2)
    axes[1].set_xlabel("Seconds after second-last-line break")
    fig.suptitle(f"Same tactical context, different recovery — {title}")
    fig.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=180)
    plt.close(fig)

    summary = {
        "match_id": int(args.match_id),
        "fixture": title,
        "high_dred_event": args.shot_event,
        "high_dred": float(shot_t["contraction_excess"].sum() / 10.0),
        "control_event": args.control_event,
        "control_dred": float(control_t["contraction_excess"].sum() / 10.0),
        "same_attack_team": int(shot["team_id"]) == int(control["team_id"]),
        "same_phase_type": str(shot["team_out_of_possession_phase_type"]) == str(control["team_out_of_possession_phase_type"]),
        "same_channel": str(shot["channel_start"]) == str(control["channel_start"]),
        "same_third": str(shot["third_start"]) == str(control["third_start"]),
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
