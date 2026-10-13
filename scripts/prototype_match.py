from __future__ import annotations

import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

from defensive_recovery.dred import compute_dred, contraction_excess
from defensive_recovery.geometry import compute_shape_metrics
from defensive_recovery.skillcorner import load_match_context, team_positions

FEATURES = ["width", "length", "area_proxy", "mean_nearest_neighbor", "max_nearest_neighbor"]
DEBT_FEATURES = ["width", "length", "mean_nearest_neighbor", "max_nearest_neighbor"]


def build_frame_features(match_dir: Path) -> pd.DataFrame:
    match_id = int(match_dir.name)
    ctx = load_match_context(match_dir / f"{match_id}_match.json")
    phases = pd.read_csv(match_dir / f"{match_id}_phases_of_play.csv").sort_values("frame_start")
    phase_rows = phases.to_dict("records")
    pi = 0
    out = []

    track_path = match_dir / f"{match_id}_tracking_extrapolated.jsonl"
    with track_path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            frame = json.loads(raw)
            f = int(frame["frame"])
            while pi < len(phase_rows) and f > int(phase_rows[pi]["frame_end"]):
                pi += 1
            if pi >= len(phase_rows):
                break
            phase = phase_rows[pi]
            if f < int(phase["frame_start"]):
                continue
            attack_id = int(phase["team_in_possession_id"])
            defend_id = ctx.away_team_id if attack_id == ctx.home_team_id else ctx.home_team_id
            xy = team_positions(frame, ctx, defend_id, include_goalkeeper=False)
            if len(xy) < 6:
                continue
            m = compute_shape_metrics(xy)
            ball = frame.get("ball_data") or {}
            out.append({
                "frame": f,
                "timestamp": frame.get("timestamp"),
                "period": frame.get("period"),
                "phase_index": int(phase["index"]),
                "attack_team_id": attack_id,
                "defending_team_id": defend_id,
                "oop_phase": str(phase["team_out_of_possession_phase_type"]),
                "ball_x": ball.get("x"),
                "ball_y": ball.get("y"),
                "n_outfield": len(xy),
                **m.__dict__,
            })
    return pd.DataFrame(out)


def add_debt(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["debt"] = np.nan
    group_cols = ["defending_team_id", "oop_phase"]
    for _, idx in df.groupby(group_cols).groups.items():
        block = df.loc[idx, FEATURES].astype(float)
        if len(block) < 50:
            continue
        med = block.median()
        q1 = block.quantile(0.25)
        q3 = block.quantile(0.75)
        scale = (q3 - q1) / 1.349
        floors = pd.Series({
            "width": 0.75,
            "length": 0.75,
            "area_proxy": 35.0,
            "mean_nearest_neighbor": 0.35,
            "max_nearest_neighbor": 0.5,
        })
        scale = pd.concat([scale, floors], axis=1).max(axis=1)
        z = (block - med) / scale
        df.loc[idx, "debt"] = np.sqrt((z[DEBT_FEATURES] * z[DEBT_FEATURES]).mean(axis=1)).to_numpy()
        for col in FEATURES:
            df.loc[idx, f"z_{col}"] = z[col].to_numpy()
    return df


def _boolish(v) -> bool:
    if pd.isna(v):
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes"}


def evaluate_line_breaks(match_dir: Path, frames: pd.DataFrame) -> pd.DataFrame:
    match_id = int(match_dir.name)
    events = pd.read_csv(match_dir / f"{match_id}_dynamic_events.csv", low_memory=False)
    lb = events[(events["event_type"] == "player_possession") & events["furthest_line_break"].notna()].copy()
    rows = []
    frame_by_phase = {int(k): v.sort_values("frame") for k, v in frames.groupby("phase_index")}

    for _, ev in lb.iterrows():
        phase_idx = int(ev["phase_index"])
        block = frame_by_phase.get(phase_idx)
        if block is None or block.empty:
            continue
        attack_id = int(ev["team_id"])
        block = block[block["attack_team_id"] == attack_id]
        if block.empty:
            continue
        defending_id = int(block["defending_team_id"].iloc[0])
        oop_phase = str(block["oop_phase"].iloc[0])
        start = int(ev["frame_start"])
        post = block[(block["frame"] >= start) & (block["frame"] <= start + 100)].copy()
        post = post[post["debt"].notna()]
        if post.empty:
            continue
        d = post["debt"].to_numpy(float)
        frames_arr = post["frame"].to_numpy(int)
        excess = np.maximum(d - 1.0, 0.0)
        auc = float(excess.sum() / 10.0)
        baseline_aucs = {}
        for col in FEATURES:
            signed = post[f"z_{col}"].to_numpy(float)
            vals = np.abs(signed)
            baseline_aucs[f"{col}_z_at_break"] = float(signed[0])
            baseline_aucs[f"{col}_abs_z_at_break"] = float(vals[0])
            baseline_aucs[f"{col}_auc_10s"] = float(np.maximum(vals - 1.0, 0.0).sum() / 10.0)
            baseline_aucs[f"{col}_expand_auc_10s"] = float(np.maximum(signed - 1.0, 0.0).sum() / 10.0)
            contract_excess = contraction_excess(signed)
            baseline_aucs[f"{col}_contract_auc_10s"] = float(contract_excess.sum() / 10.0)
            baseline_aucs[f"{col}_contract_mean_10s"] = float(contract_excess.mean())
            baseline_aucs[f"{col}_contract_peak_10s"] = float(contract_excess.max())
            baseline_aucs[f"{col}_contract_fraction_10s"] = float(np.mean(contract_excess > 0.0))
            baseline_aucs[f"{col}_peak_10s"] = float(np.max(vals))
        # Pre-specified time-horizon sensitivity for the primary width-contraction signal.
        for horizon_s in (3, 5, 8, 10):
            hpost = post[post["frame"] <= start + horizon_s * 10]
            signed_w = hpost["z_width"].to_numpy(float)
            baseline_aucs[f"width_contract_auc_{horizon_s}s"] = (
                compute_dred(signed_w, fps=10.0).integral if len(signed_w) else 0.0
            )
        recovered_sec = np.nan
        hold = 10
        for i in range(len(d)):
            if d[i] <= 1.0 and i + hold <= len(d) and np.all(d[i:i+hold] <= 1.0):
                recovered_sec = float((frames_arr[i] - start) / 10.0)
                break
        rows.append({
            "event_id": ev["event_id"],
            "frame_start": start,
            "phase_index": phase_idx,
            "attack_team_id": attack_id,
            "defending_team_id": defending_id,
            "oop_phase": oop_phase,
            "furthest_line_break": ev["furthest_line_break"],
            "n_opponents_bypassed": ev.get("n_opponents_bypassed"),
            "dangerous": _boolish(ev.get("dangerous")),
            "lead_to_shot": _boolish(ev.get("lead_to_shot")),
            "lead_to_goal": _boolish(ev.get("lead_to_goal")),
            "xthreat": ev.get("xthreat"),
            "debt_at_break": float(d[0]),
            "peak_debt_10s": float(np.max(d)),
            "debt_auc_10s": auc,
            "recovery_seconds": recovered_sec,
            "window_seconds": float((frames_arr[-1] - start) / 10.0),
            **baseline_aucs,
        })
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("match_dir", type=Path)
    ap.add_argument("--output-dir", type=Path, default=Path("data/processed"))
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    mid = args.match_dir.name

    frames = add_debt(build_frame_features(args.match_dir))
    breaks = evaluate_line_breaks(args.match_dir, frames)
    frames.to_csv(args.output_dir / f"{mid}_frame_features.csv", index=False)
    breaks.to_csv(args.output_dir / f"{mid}_line_break_recovery.csv", index=False)

    summary = {
        "match_id": int(mid),
        "usable_frames": int(len(frames)),
        "line_break_player_possessions": int(len(breaks)),
        "debt_median": float(frames["debt"].median()),
        "debt_p90": float(frames["debt"].quantile(0.9)),
    }
    if len(breaks):
        summary["by_line_break"] = (
            breaks.groupby("furthest_line_break")["debt_auc_10s"]
            .agg(["count", "mean", "median"])
            .round(3).to_dict("index")
        )
        danger = breaks.groupby("dangerous")["debt_auc_10s"].agg(["count", "mean", "median"])
        summary["by_dangerous"] = danger.round(3).to_dict("index")
        summary["top_events"] = breaks.nlargest(5, "debt_auc_10s")[[
            "event_id","frame_start","furthest_line_break","dangerous","lead_to_shot","debt_auc_10s","peak_debt_10s","recovery_seconds"
        ]].to_dict("records")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
