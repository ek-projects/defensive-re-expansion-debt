from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, wilcoxon

from prototype_match import add_debt, build_frame_features, evaluate_line_breaks
from defensive_recovery.competition import OFFICIAL_DYNAMIC_EVENT_MATCH_ID_SET

METRICS = {
    "Recovery Debt": "debt_auc_10s",
    "Width recovery |z|": "width_auc_10s",
    "Width expansion": "width_expand_auc_10s",
    "Width contraction": "width_contract_auc_10s",
    "Static width |z| at break": "width_abs_z_at_break",
    "Max-gap recovery |z|": "max_nearest_neighbor_auc_10s",
    "Max-gap expansion": "max_nearest_neighbor_expand_auc_10s",
    "Static max-gap |z| at break": "max_nearest_neighbor_abs_z_at_break",
    "Length recovery |z|": "length_auc_10s",
    "Area recovery |z|": "area_proxy_auc_10s",
    "Opponents bypassed": "n_opponents_bypassed",
}


def roc_auc(y: pd.Series, score: pd.Series) -> float | None:
    yv = np.asarray(y, dtype=bool)
    xv = pd.to_numeric(score, errors="coerce").to_numpy(float)
    keep = np.isfinite(xv)
    yv, xv = yv[keep], xv[keep]
    n_pos = int(yv.sum())
    n_neg = int((~yv).sum())
    if n_pos == 0 or n_neg == 0:
        return None
    ranks = rankdata(xv, method="average")
    u = float(ranks[yv].sum() - n_pos * (n_pos + 1) / 2.0)
    return u / (n_pos * n_neg)


def safe_float(v):
    if v is None:
        return None
    try:
        f = float(v)
    except Exception:
        return None
    return f if math.isfinite(f) else None


def metric_summary(df: pd.DataFrame, col: str) -> dict:
    x = pd.to_numeric(df[col], errors="coerce")
    y = df["lead_to_shot"].astype(bool)
    good = x.notna()
    x, y = x[good], y[good]
    pos, neg = x[y], x[~y]
    overall_auc = roc_auc(y, x)
    per_match = {}
    for mid, g in df.loc[good].groupby("match_id"):
        auc = roc_auc(g["lead_to_shot"].astype(bool), pd.to_numeric(g[col], errors="coerce"))
        if auc is not None:
            per_match[int(mid)] = auc
    arr = np.asarray(list(per_match.values()), dtype=float)
    return {
        "n": int(len(x)),
        "shot_linked_n": int(y.sum()),
        "non_shot_n": int((~y).sum()),
        "shot_mean": safe_float(pos.mean()),
        "non_shot_mean": safe_float(neg.mean()),
        "shot_median": safe_float(pos.median()),
        "non_shot_median": safe_float(neg.median()),
        "overall_auc": safe_float(overall_auc),
        "rank_biserial": safe_float(None if overall_auc is None else 2 * overall_auc - 1),
        "per_match_auc_n": int(len(arr)),
        "per_match_auc_median": safe_float(np.median(arr) if len(arr) else None),
        "per_match_auc_mean": safe_float(np.mean(arr) if len(arr) else None),
        "matches_auc_gt_half": int(np.sum(arr > 0.5)) if len(arr) else 0,
        "per_match_auc": {str(k): round(v, 6) for k, v in per_match.items()},
    }


def stratified_quartiles(df: pd.DataFrame, col: str) -> dict:
    work = df[["match_id", "lead_to_shot", col]].copy()
    work[col] = pd.to_numeric(work[col], errors="coerce")
    work = work.dropna(subset=[col])
    if work.empty:
        return {}
    work["pct_rank"] = work.groupby("match_id")[col].rank(pct=True, method="average")
    low = work[work["pct_rank"] <= 0.25]
    high = work[work["pct_rank"] >= 0.75]
    low_rate = float(low["lead_to_shot"].mean()) if len(low) else math.nan
    high_rate = float(high["lead_to_shot"].mean()) if len(high) else math.nan
    rr = high_rate / low_rate if low_rate > 0 else math.inf if high_rate > 0 else math.nan
    return {
        "bottom_quartile_n": int(len(low)),
        "bottom_quartile_shot_rate": safe_float(low_rate),
        "top_quartile_n": int(len(high)),
        "top_quartile_shot_rate": safe_float(high_rate),
        "risk_ratio_top_vs_bottom": safe_float(rr),
    }


def paired_auc_test(debt: dict, baseline: dict) -> dict:
    d = debt["per_match_auc"]
    b = baseline["per_match_auc"]
    common = sorted(set(d) & set(b))
    if not common:
        return {"matches": 0, "median_auc_delta": None, "wilcoxon_p": None}
    delta = np.array([float(d[k]) - float(b[k]) for k in common], dtype=float)
    p = None
    if len(delta) >= 5 and np.any(np.abs(delta) > 1e-12):
        try:
            p = float(wilcoxon(delta, alternative="greater").pvalue)
        except Exception:
            p = None
    return {
        "matches": int(len(common)),
        "median_auc_delta": safe_float(np.median(delta)),
        "mean_auc_delta": safe_float(np.mean(delta)),
        "wins": int(np.sum(delta > 0)),
        "ties": int(np.sum(np.isclose(delta, 0))),
        "losses": int(np.sum(delta < 0)),
        "wilcoxon_one_sided_p": safe_float(p),
    }


def match_meta(match_dir: Path) -> dict:
    mid = match_dir.name
    raw = json.loads((match_dir / f"{mid}_match.json").read_text())
    return {
        "match_id": int(mid),
        "home_team": raw["home_team"]["short_name"],
        "away_team": raw["away_team"]["short_name"],
        "competition": raw["competition_edition"]["competition"]["name"],
        "date_time": raw["date_time"],
    }


def process_all(raw_root: Path, processed: Path, *, official_only: bool = True) -> pd.DataFrame:
    processed.mkdir(parents=True, exist_ok=True)
    all_breaks = []
    match_rows = []
    dirs = sorted([p for p in raw_root.iterdir() if p.is_dir() and p.name.isdigit()], reverse=True)
    if official_only:
        dirs = [p for p in dirs if int(p.name) in OFFICIAL_DYNAMIC_EVENT_MATCH_ID_SET]
    for i, match_dir in enumerate(dirs, 1):
        meta = match_meta(match_dir)
        print(f"[{i}/{len(dirs)}] {meta['match_id']} {meta['home_team']} - {meta['away_team']}", flush=True)
        frames = add_debt(build_frame_features(match_dir))
        breaks = evaluate_line_breaks(match_dir, frames)
        breaks.insert(0, "match_id", meta["match_id"])
        for k in ("home_team", "away_team", "competition", "date_time"):
            breaks[k] = meta[k]
        frames.to_csv(processed / f"{meta['match_id']}_frame_features.csv", index=False)
        breaks.to_csv(processed / f"{meta['match_id']}_line_break_recovery.csv", index=False)
        all_breaks.append(breaks)
        match_rows.append({
            **meta,
            "usable_frames": int(len(frames)),
            "line_breaks": int(len(breaks)),
            "shot_linked": int(breaks["lead_to_shot"].sum()) if len(breaks) else 0,
            "goals_linked": int(breaks["lead_to_goal"].sum()) if len(breaks) else 0,
            "median_frame_debt": safe_float(frames["debt"].median()),
        })
    episodes = pd.concat(all_breaks, ignore_index=True) if all_breaks else pd.DataFrame()
    episodes.to_csv(processed / "all_line_break_recovery.csv", index=False)
    pd.DataFrame(match_rows).to_csv(processed / "match_summary.csv", index=False)
    return episodes


def analyze(episodes: pd.DataFrame) -> dict:
    result = {
        "matches": int(episodes["match_id"].nunique()),
        "episodes": int(len(episodes)),
        "shot_linked": int(episodes["lead_to_shot"].sum()),
        "goal_linked": int(episodes["lead_to_goal"].sum()),
        "shot_rate": safe_float(episodes["lead_to_shot"].mean()),
        "line_break_counts": {str(k): int(v) for k, v in episodes["furthest_line_break"].value_counts().items()},
        "metrics": {},
        "strata": {},
    }
    for name, col in METRICS.items():
        if col in episodes.columns:
            result["metrics"][name] = metric_summary(episodes, col)
            result["metrics"][name]["quartiles"] = stratified_quartiles(episodes, col)
    debt = result["metrics"].get("Recovery Debt")
    if debt:
        result["debt_vs_baselines"] = {}
        for name, stats in result["metrics"].items():
            if name == "Recovery Debt":
                continue
            result["debt_vs_baselines"][name] = paired_auc_test(debt, stats)
    for stratum, g in episodes.groupby("furthest_line_break"):
        if len(g) >= 20:
            result["strata"][str(stratum)] = {
                "episodes": int(len(g)),
                "shot_linked": int(g["lead_to_shot"].sum()),
                "shot_rate": safe_float(g["lead_to_shot"].mean()),
                "recovery_debt": metric_summary(g, "debt_auc_10s"),
                "quartiles": stratified_quartiles(g, "debt_auc_10s"),
            }
    return result


def report_md(result: dict) -> str:
    m = result["metrics"]
    debt = m["Recovery Debt"]
    lines = [
        "# Feature-generation and development audit",
        "",
        f"Matches: **{result['matches']}**  ",
        f"Line-break episodes: **{result['episodes']}**  ",
        f"Shot-linked episodes: **{result['shot_linked']}** ({100*result['shot_rate']:.1f}%)  ",
        f"Goal-linked episodes: **{result['goal_linked']}**",
        "",
        "## Legacy multivariate baseline",
        "",
        "This report is a development audit, not the submission primary validation. The submission uses DRED intensity with EPV validation; shot linkage is retained only as a confounding audit.",
        "",
        f"Recovery Debt overall ROC AUC for distinguishing shot-linked line breaks: **{debt['overall_auc']:.3f}**.",
        f"Median per-match AUC: **{debt['per_match_auc_median']:.3f}** across **{debt['per_match_auc_n']}** matches with both classes.",
        f"Mean Debt AUC10s: shot-linked **{debt['shot_mean']:.3f}**, non-shot **{debt['non_shot_mean']:.3f}**.",
        "",
        "## Baseline comparison",
        "",
        "| Metric | Overall AUC | Median match AUC | Matches > 0.5 | Top-v-bottom quartile RR |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, st in m.items():
        q = st.get("quartiles", {})
        rr = q.get("risk_ratio_top_vs_bottom")
        lines.append(
            f"| {name} | {st['overall_auc']:.3f} | {st['per_match_auc_median']:.3f} | {st['matches_auc_gt_half']}/{st['per_match_auc_n']} | "
            + (f"{rr:.2f}x |" if rr is not None else "n/a |")
        )
    lines += ["", "## Recovery Debt versus each baseline (paired per-match AUC)", "", "| Baseline | Median ΔAUC | W/T/L | one-sided Wilcoxon p |", "|---|---:|---:|---:|"]
    for name, st in result.get("debt_vs_baselines", {}).items():
        p = st.get("wilcoxon_one_sided_p")
        lines.append(f"| {name} | {st['median_auc_delta']:.3f} | {st['wins']}/{st['ties']}/{st['losses']} | " + (f"{p:.4f} |" if p is not None else "n/a |"))
    lines += ["", "## Line-break strata", ""]
    for name, st in result["strata"].items():
        r = st["recovery_debt"]
        lines.append(f"- **{name}**: n={st['episodes']}, shot-linked={st['shot_linked']}, Debt AUC={r['overall_auc']:.3f}, median match AUC={r['per_match_auc_median']:.3f}.")
    lines += [
        "",
        "## Interpretation guardrails",
        "",
        "- `lead_to_shot` is a SkillCorner event label; this analysis is diagnostic, not a causal claim.",
        "- Recovery Debt is measured after a line break, so it describes the quality of defensive recovery rather than predicting the break before it occurs.",
        "- Baselines are fitted within each match, defending team and out-of-possession phase using robust medians/IQRs.",
        "- Possession termination truncates the 10-second debt window; remaining time contributes no additional debt.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--processed", type=Path, default=Path("data/processed"))
    ap.add_argument("--outputs", type=Path, default=Path("outputs"))
    ap.add_argument("--analyze-only", action="store_true")
    ap.add_argument(
        "--all-public-matches",
        action="store_true",
        help="research extension only: process every locally available public match instead of the 10 official Dynamic Events matches",
    )
    args = ap.parse_args()
    args.outputs.mkdir(parents=True, exist_ok=True)
    if args.analyze_only:
        episodes = pd.read_csv(args.processed / "all_line_break_recovery.csv")
        for c in ("lead_to_shot", "lead_to_goal"):
            episodes[c] = episodes[c].astype(str).str.lower().isin(["true", "1", "yes"])
    else:
        episodes = process_all(args.raw, args.processed, official_only=not args.all_public_matches)
    result = analyze(episodes)
    (args.outputs / "validation_summary.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    (args.outputs / "validation_report.md").write_text(report_md(result))
    print(report_md(result))


if __name__ == "__main__":
    main()
