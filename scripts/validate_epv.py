from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import binomtest, pearsonr, rankdata, spearmanr

from defensive_recovery.competition import OFFICIAL_DYNAMIC_EVENT_MATCH_IDS


def _rank_within_match(df: pd.DataFrame, column: str) -> pd.Series:
    return df.groupby("match_id")[column].transform(
        lambda s: pd.Series(rankdata(s), index=s.index)
    )


def _residual(y: np.ndarray, controls: np.ndarray) -> np.ndarray:
    design = np.column_stack([np.ones(len(y)), controls])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    return y - design @ beta


def _partial_rank(df: pd.DataFrame) -> tuple[float, float]:
    cols = {
        "width_contract_mean_10s": "rx",
        "possession_epv_delta_for": "ry",
        "window_seconds": "rw",
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
    result = pearsonr(x, y)
    return float(result.statistic), float(result.pvalue)


def _per_match_partial(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for match_id, q in df.groupby("match_id"):
        ranks = {
            "x": rankdata(q["width_contract_mean_10s"]),
            "y": rankdata(q["possession_epv_delta_for"]),
            "w": rankdata(q["window_seconds"]),
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


def _match_bootstrap(values: np.ndarray, *, reps: int = 20000, seed: int = 2027) -> dict:
    rng = np.random.default_rng(seed)
    medians = np.empty(reps)
    means = np.empty(reps)
    for i in range(reps):
        sample = rng.choice(values, size=len(values), replace=True)
        medians[i] = np.median(sample)
        means[i] = np.mean(sample)
    return {
        "median": float(np.median(values)),
        "median_ci95": [float(v) for v in np.quantile(medians, [0.025, 0.975])],
        "mean": float(np.mean(values)),
        "mean_ci95": [float(v) for v in np.quantile(means, [0.025, 0.975])],
    }


def load_epv(raw_root: Path) -> pd.DataFrame:
    parts = []
    use = [
        "event_id", "event_type", "duration",
        "possession_epv_for_start", "possession_epv_delta_for",
    ]
    for match_id in OFFICIAL_DYNAMIC_EVENT_MATCH_IDS:
        path = raw_root / str(match_id) / f"{match_id}_dynamic_events.csv"
        frame = pd.read_csv(path, usecols=use, low_memory=False)
        frame = frame[frame["event_type"] == "player_possession"][use[0:1] + use[2:]].copy()
        frame["match_id"] = match_id
        parts.append(frame)
    return pd.concat(parts, ignore_index=True).drop_duplicates(["match_id", "event_id"])


def analyze(episodes: pd.DataFrame, epv: pd.DataFrame, matches: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    q = episodes[episodes["furthest_line_break"] == "second_last"].copy()
    q = q.merge(epv, on=["match_id", "event_id"], how="inner")
    q = q.rename(columns={"duration": "action_duration"})
    numeric = [
        "width_contract_mean_10s", "width_abs_z_at_break", "window_seconds",
        "action_duration", "possession_epv_for_start", "possession_epv_delta_for",
    ]
    for col in numeric:
        q[col] = pd.to_numeric(q[col], errors="coerce")
    q = q.dropna(subset=numeric).copy()

    raw = spearmanr(q["width_contract_mean_10s"], q["possession_epv_delta_for"])
    duration = spearmanr(q["window_seconds"], q["possession_epv_delta_for"])
    action_duration = spearmanr(q["action_duration"], q["possession_epv_delta_for"])
    pooled_r, pooled_p = _partial_rank(q)
    pm = _per_match_partial(q)
    match_info = matches[["match_id", "home_team", "away_team"]].drop_duplicates("match_id")
    pm = pm.merge(match_info, on="match_id", how="left")
    pm["fixture"] = pm["home_team"].fillna(pm["match_id"].astype(str)) + " – " + pm["away_team"].fillna("")
    boot = _match_bootstrap(pm["partial_rank"].to_numpy(float))
    positives = int((pm["partial_rank"] > 0).sum())
    sign_p = float(binomtest(positives, len(pm), 0.5, alternative="greater").pvalue)

    summary = {
        "sample": {
            "events": int(len(q)),
            "matches": int(q["match_id"].nunique()),
            "context": "second_last line breaks with non-null player-possession EPV",
        },
        "metric": "width_contract_mean_10s",
        "outcome": "possession_epv_delta_for",
        "raw_spearman": {"rho": float(raw.statistic), "p": float(raw.pvalue)},
        "confound_checks": {
            "recovery_window_vs_epv": {"rho": float(duration.statistic), "p": float(duration.pvalue)},
            "action_duration_vs_epv": {"rho": float(action_duration.statistic), "p": float(action_duration.pvalue)},
        },
        "duration_context_adjusted_partial_rank": {
            "r": pooled_r,
            "naive_event_level_p": pooled_p,
            "controls": [
                "match fixed effects via within-match ranks",
                "recovery window duration",
                "player-possession duration",
                "EPV at possession start",
                "static absolute width deviation at the break",
            ],
        },
        "match_level": {
            **boot,
            "positive_matches": positives,
            "total_matches": int(len(pm)),
            "one_sided_sign_test_p": sign_p,
        },
        "interpretation": (
            "DRED intensity has a small positive association with event-local EPV gain after adjustment. "
            "The match-level bootstrap is the preferred uncertainty summary; the pooled event p-value is not "
            "treated as if all events were independent matches."
        ),
    }
    return summary, pm


def write_outputs(summary: dict, pm: pd.DataFrame, output_dir: Path, figure_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "epv_validation.json").write_text(json.dumps(summary, indent=2) + "\n")

    ml = summary["match_level"]
    adj = summary["duration_context_adjusted_partial_rank"]
    raw = summary["raw_spearman"]
    lines = [
        "# DRED intensity — external EPV validation",
        "",
        f"Sample: **{summary['sample']['events']}** second-last-line-break player possessions across **{summary['sample']['matches']}** official Dynamic Events matches.",
        "",
        "SkillCorner EPV delta measures the change in attacking possession value during the individual player possession. DRED intensity is the mean abnormal width-contraction excess during the subsequent recovery window.",
        "",
        "## Result",
        "",
        f"- raw Spearman DRED-intensity vs EPV gain: **rho={raw['rho']:.3f}**",
        f"- within-match partial-rank association after controlling both durations, EPV at action start and static width at the break: **r={adj['r']:.3f}**",
        f"- median per-match partial association: **{ml['median']:.3f}** (match-bootstrap 95% CI **{ml['median_ci95'][0]:.3f} to {ml['median_ci95'][1]:.3f}**)",
        f"- positive association in **{ml['positive_matches']}/{ml['total_matches']}** matches (one-sided sign test p={ml['one_sided_sign_test_p']:.4f})",
        "",
        "The pooled event-level p-value is deliberately not the headline uncertainty measure because events within a match are not equivalent to independent matches.",
        "",
        "## Per match",
        "",
        "| Match | n | Partial rank |",
        "|---|---:|---:|",
    ]
    for _, row in pm.sort_values("partial_rank", ascending=False).iterrows():
        lines.append(f"| {row['fixture']} | {int(row['n'])} | {row['partial_rank']:.3f} |")
    (output_dir / "epv_validation.md").write_text("\n".join(lines) + "\n")

    plot = pm.sort_values("partial_rank")
    fig, ax = plt.subplots(figsize=(8, 5.5))
    ax.barh(plot["fixture"], plot["partial_rank"])
    ax.axvline(0, linewidth=1)
    ax.set_xlabel("Partial rank correlation: DRED intensity vs EPV gain")
    ax.set_title("External validity across the 10 official Dynamic Events matches")
    fig.tight_layout()
    fig.savefig(figure_dir / "dred_epv_validation.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=Path, default=Path("data/processed/all_line_break_recovery.csv"))
    ap.add_argument("--matches", type=Path, default=Path("data/processed/match_summary.csv"))
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--output-dir", type=Path, default=Path("outputs"))
    ap.add_argument("--figure-dir", type=Path, default=Path("figures"))
    args = ap.parse_args()
    episodes = pd.read_csv(args.episodes)
    matches = pd.read_csv(args.matches)
    summary, pm = analyze(episodes, load_epv(args.raw), matches)
    write_outputs(summary, pm, args.output_dir, args.figure_dir)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
