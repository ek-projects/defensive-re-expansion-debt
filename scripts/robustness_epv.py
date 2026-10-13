from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, rankdata, spearmanr

from defensive_recovery.competition import OFFICIAL_DYNAMIC_EVENT_MATCH_IDS
from validate_epv import load_epv


THRESHOLDS = (0.5, 0.75, 1.0, 1.25, 1.5)
HORIZONS = (3, 5, 8, 10)


def _rank_within_match(df: pd.DataFrame, column: str) -> pd.Series:
    return df.groupby("match_id")[column].transform(
        lambda s: pd.Series(rankdata(s), index=s.index)
    )


def _residual(y: np.ndarray, controls: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(y)), controls])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    return y - design @ beta


def _rank_residuals(
    df: pd.DataFrame,
    metric: str,
    *,
    window_col: str = "window_seconds",
) -> tuple[np.ndarray, np.ndarray]:
    cols = {
        metric: "rx",
        "possession_epv_delta_for": "ry",
        window_col: "rw",
        "action_duration": "ra",
        "possession_epv_for_start": "rs",
        "width_abs_z_at_break": "rz",
    }
    work = df.copy()
    for source, target in cols.items():
        work[target] = _rank_within_match(work, source)
        work[target] -= work.groupby("match_id")[target].transform("mean")
    controls = work[["rw", "ra", "rs", "rz"]].to_numpy(float)
    x = _residual(work["rx"].to_numpy(float), controls)
    y = _residual(work["ry"].to_numpy(float), controls)
    return x, y


def partial_rank(
    df: pd.DataFrame,
    metric: str,
    *,
    window_col: str = "window_seconds",
) -> tuple[float, float]:
    x, y = _rank_residuals(df, metric, window_col=window_col)
    result = pearsonr(x, y)
    return float(result.statistic), float(result.pvalue)


def per_match_partial(
    df: pd.DataFrame,
    metric: str,
    *,
    window_col: str = "window_seconds",
) -> pd.DataFrame:
    rows = []
    for match_id, q in df.groupby("match_id"):
        ranks = {
            "x": rankdata(q[metric]),
            "y": rankdata(q["possession_epv_delta_for"]),
            "w": rankdata(q[window_col]),
            "a": rankdata(q["action_duration"]),
            "s": rankdata(q["possession_epv_for_start"]),
            "z": rankdata(q["width_abs_z_at_break"]),
        }
        controls = np.column_stack([ranks[k] for k in ("w", "a", "s", "z")])
        xr = _residual(ranks["x"], controls)
        yr = _residual(ranks["y"], controls)
        corr = float(np.corrcoef(xr, yr)[0, 1])
        rows.append({"match_id": int(match_id), "n": int(len(q)), "partial_rank": corr})
    return pd.DataFrame(rows)


def load_sample(episodes_path: Path, raw_root: Path) -> pd.DataFrame:
    episodes = pd.read_csv(episodes_path)
    episodes = episodes[
        episodes["match_id"].astype(int).isin(OFFICIAL_DYNAMIC_EVENT_MATCH_IDS)
        & (episodes["furthest_line_break"] == "second_last")
    ].copy()
    q = episodes.merge(load_epv(raw_root), on=["match_id", "event_id"], how="inner")
    q = q.rename(columns={"duration": "action_duration"})
    numeric = [
        "frame_start",
        "phase_index",
        "attack_team_id",
        "width_contract_mean_10s",
        "width_abs_z_at_break",
        "window_seconds",
        "action_duration",
        "possession_epv_for_start",
        "possession_epv_delta_for",
    ]
    for col in numeric:
        q[col] = pd.to_numeric(q[col], errors="coerce")
    return q.dropna(subset=numeric).copy()


def _metric_name(threshold: float, horizon: int) -> str:
    threshold_text = str(threshold).replace(".", "p")
    return f"dred_t{threshold_text}_h{horizon}s"


def recompute_dred_grid(sample: pd.DataFrame, processed_root: Path) -> pd.DataFrame:
    work = sample.copy()
    metric_values = {
        _metric_name(threshold, horizon): pd.Series(index=work.index, dtype=float)
        for threshold in THRESHOLDS
        for horizon in HORIZONS
    }

    for match_id, q in work.groupby("match_id"):
        frame_path = processed_root / f"{int(match_id)}_frame_features.csv"
        frames = pd.read_csv(
            frame_path,
            usecols=["frame", "phase_index", "attack_team_id", "debt", "z_width"],
        )
        by_phase = {
            int(phase): block.sort_values("frame")
            for phase, block in frames.groupby("phase_index")
        }
        for idx, event in q.iterrows():
            phase = by_phase.get(int(event["phase_index"]))
            if phase is None:
                continue
            block = phase[phase["attack_team_id"] == int(event["attack_team_id"])]
            start = int(event["frame_start"])
            post = block[(block["frame"] >= start) & (block["frame"] <= start + 100)].copy()
            post = post[post["debt"].notna()]
            if post.empty:
                continue
            for horizon in HORIZONS:
                hpost = post[post["frame"] <= start + horizon * 10]
                signed = hpost["z_width"].to_numpy(float)
                if len(signed) == 0:
                    continue
                for threshold in THRESHOLDS:
                    metric_values[_metric_name(threshold, horizon)].loc[idx] = float(
                        np.maximum(-signed - threshold, 0.0).mean()
                    )

    for name, values in metric_values.items():
        work[name] = values
    for horizon in HORIZONS:
        work[f"window_seconds_h{horizon}s"] = np.minimum(
            work["window_seconds"].to_numpy(float), float(horizon)
        )
    return work


def sensitivity_grid(work: pd.DataFrame) -> list[dict]:
    rows = []
    for threshold in THRESHOLDS:
        for horizon in HORIZONS:
            metric = _metric_name(threshold, horizon)
            window_col = f"window_seconds_h{horizon}s"
            q = work.dropna(subset=[metric]).copy()
            raw = spearmanr(q[metric], q["possession_epv_delta_for"])
            adjusted, _ = partial_rank(q, metric, window_col=window_col)
            pm = per_match_partial(q, metric, window_col=window_col)
            rows.append(
                {
                    "threshold": threshold,
                    "horizon_seconds": horizon,
                    "events": int(len(q)),
                    "raw_spearman": float(raw.statistic),
                    "adjusted_partial_rank": adjusted,
                    "median_match_partial_rank": float(pm["partial_rank"].median()),
                    "positive_matches": int((pm["partial_rank"] > 0).sum()),
                    "total_matches": int(len(pm)),
                }
            )
    return rows


def leave_one_match_out(work: pd.DataFrame, metric: str) -> list[dict]:
    rows = []
    for omitted in sorted(work["match_id"].astype(int).unique()):
        q = work[work["match_id"].astype(int) != omitted]
        r, _ = partial_rank(q, metric)
        rows.append(
            {
                "omitted_match_id": int(omitted),
                "events": int(len(q)),
                "adjusted_partial_rank": r,
            }
        )
    return rows


def permutation_negative_control(
    work: pd.DataFrame,
    metric: str,
    *,
    reps: int = 10000,
    seed: int = 2027,
) -> dict:
    x, y = _rank_residuals(work, metric)
    observed = float(np.corrcoef(x, y)[0, 1])
    groups = [np.asarray(idx, dtype=int) for idx in work.groupby("match_id", sort=True).indices.values()]
    rng = np.random.default_rng(seed)
    null = np.empty(reps, dtype=float)
    y_centered = y - y.mean()
    y_norm = np.sqrt(np.sum(y_centered * y_centered))
    for i in range(reps):
        xp = x.copy()
        for idx in groups:
            xp[idx] = rng.permutation(xp[idx])
        xp -= xp.mean()
        denom = np.sqrt(np.sum(xp * xp)) * y_norm
        null[i] = float(np.sum(xp * y_centered) / denom) if denom > 0 else np.nan
    null = null[np.isfinite(null)]
    return {
        "method": "permute adjusted DRED residuals within match",
        "reps": int(len(null)),
        "seed": seed,
        "observed": observed,
        "null_mean": float(np.mean(null)),
        "null_sd": float(np.std(null, ddof=1)),
        "one_sided_p": float((1 + np.sum(null >= observed)) / (len(null) + 1)),
        "two_sided_p": float((1 + np.sum(np.abs(null) >= abs(observed))) / (len(null) + 1)),
        "null_ci95": [float(v) for v in np.quantile(null, [0.025, 0.975])],
    }


def analyze(work: pd.DataFrame, *, permutation_reps: int) -> dict:
    primary = _metric_name(1.0, 10)
    max_abs_diff = float(
        np.nanmax(np.abs(work[primary].to_numpy(float) - work["width_contract_mean_10s"].to_numpy(float)))
    )
    primary_r, _ = partial_rank(work, primary)
    grid = sensitivity_grid(work)
    lomo = leave_one_match_out(work, primary)
    permutation = permutation_negative_control(work, primary, reps=permutation_reps)

    adjusted_values = np.asarray([row["adjusted_partial_rank"] for row in grid], dtype=float)
    lomo_values = np.asarray([row["adjusted_partial_rank"] for row in lomo], dtype=float)
    return {
        "sample": {
            "events": int(len(work)),
            "matches": int(work["match_id"].nunique()),
        },
        "reproducibility_check": {
            "recomputed_primary_metric": primary,
            "stored_metric": "width_contract_mean_10s",
            "max_absolute_difference": max_abs_diff,
            "exact_within_1e_12": bool(max_abs_diff <= 1e-12),
        },
        "primary_adjusted_partial_rank": primary_r,
        "threshold_horizon_sensitivity": grid,
        "sensitivity_summary": {
            "combinations": int(len(grid)),
            "positive_adjusted_combinations": int(np.sum(adjusted_values > 0)),
            "min_adjusted_partial_rank": float(adjusted_values.min()),
            "max_adjusted_partial_rank": float(adjusted_values.max()),
            "median_adjusted_partial_rank": float(np.median(adjusted_values)),
        },
        "leave_one_match_out": lomo,
        "leave_one_match_out_summary": {
            "all_positive": bool(np.all(lomo_values > 0)),
            "min_adjusted_partial_rank": float(lomo_values.min()),
            "max_adjusted_partial_rank": float(lomo_values.max()),
            "median_adjusted_partial_rank": float(np.median(lomo_values)),
        },
        "permutation_negative_control": permutation,
        "guardrail": (
            "Post-submission robustness analysis. It is not part of the frozen 8TTF3B submission and must not be "
            "retroactively described as pre-specified confirmatory evidence."
        ),
    }


def report_md(result: dict) -> str:
    rep = result["reproducibility_check"]
    sens = result["sensitivity_summary"]
    lomo = result["leave_one_match_out_summary"]
    perm = result["permutation_negative_control"]
    lines = [
        "# DRED post-submission EPV robustness audit",
        "",
        "This audit was run after submission `8TTF3B`; it is robustness evidence, not pre-specified confirmatory evidence.",
        "",
        "## Reproduction check",
        "",
        f"- events: **{result['sample']['events']}** across **{result['sample']['matches']}** matches",
        f"- recomputed 10 s / 1.0-threshold DRED intensity vs stored metric max absolute difference: **{rep['max_absolute_difference']:.3g}**",
        f"- exact within 1e-12: **{rep['exact_within_1e_12']}**",
        f"- primary adjusted partial-rank association: **{result['primary_adjusted_partial_rank']:.3f}**",
        "",
        "## Threshold × horizon sensitivity",
        "",
        f"Positive adjusted association in **{sens['positive_adjusted_combinations']}/{sens['combinations']}** combinations; range **{sens['min_adjusted_partial_rank']:.3f} to {sens['max_adjusted_partial_rank']:.3f}**, median **{sens['median_adjusted_partial_rank']:.3f}**.",
        "",
        "| threshold | horizon | adjusted r | median match r | positive matches |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in result["threshold_horizon_sensitivity"]:
        lines.append(
            f"| {row['threshold']:.2f} | {row['horizon_seconds']}s | {row['adjusted_partial_rank']:.3f} | "
            f"{row['median_match_partial_rank']:.3f} | {row['positive_matches']}/{row['total_matches']} |"
        )
    lines += [
        "",
        "## Leave-one-match-out",
        "",
        f"All ten leave-one-match-out estimates positive: **{lomo['all_positive']}**; range **{lomo['min_adjusted_partial_rank']:.3f} to {lomo['max_adjusted_partial_rank']:.3f}**.",
        "",
        "| omitted match | adjusted r |",
        "|---:|---:|",
    ]
    for row in result["leave_one_match_out"]:
        lines.append(f"| {row['omitted_match_id']} | {row['adjusted_partial_rank']:.3f} |")
    lines += [
        "",
        "## Within-match permutation negative control",
        "",
        f"Observed adjusted association **{perm['observed']:.3f}**; null mean **{perm['null_mean']:.3f}**, 95% null interval **{perm['null_ci95'][0]:.3f} to {perm['null_ci95'][1]:.3f}**; one-sided empirical p **{perm['one_sided_p']:.4f}**.",
        "",
        "## Guardrail",
        "",
        result["guardrail"],
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=Path, default=Path("data/processed/all_line_break_recovery.csv"))
    ap.add_argument("--processed", type=Path, default=Path("data/processed"))
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--outputs", type=Path, default=Path("outputs"))
    ap.add_argument("--permutation-reps", type=int, default=10000)
    args = ap.parse_args()

    sample = load_sample(args.episodes, args.raw)
    work = recompute_dred_grid(sample, args.processed)
    result = analyze(work, permutation_reps=args.permutation_reps)
    args.outputs.mkdir(parents=True, exist_ok=True)
    (args.outputs / "epv_robustness_post_submission.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.outputs / "epv_robustness_post_submission.md").write_text(report_md(result))
    print(report_md(result))


if __name__ == "__main__":
    main()
