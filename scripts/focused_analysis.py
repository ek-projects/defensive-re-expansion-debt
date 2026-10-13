from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import binomtest, rankdata, wilcoxon

from defensive_recovery.competition import OFFICIAL_DYNAMIC_EVENT_MATCH_ID_SET

PRIMARY = "width_contract_auc_10s"
STATIC = "width_abs_z_at_break"


def auc(y, score) -> float | None:
    y = np.asarray(y, dtype=bool)
    x = pd.to_numeric(pd.Series(score), errors="coerce").to_numpy(float)
    keep = np.isfinite(x)
    y, x = y[keep], x[keep]
    n1, n0 = int(y.sum()), int((~y).sum())
    if not n1 or not n0:
        return None
    r = rankdata(x, method="average")
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def safe(v):
    if v is None:
        return None
    f = float(v)
    return f if math.isfinite(f) else None


def enrich(episodes: pd.DataFrame, raw_root: Path) -> pd.DataFrame:
    parts = []
    keep = [
        "event_id", "x_start", "y_start", "x_end", "y_end", "attacking_side",
        "channel_start", "third_start", "penalty_area_start", "organised_defense",
        "defensive_structure", "n_opponents_bypassed", "overall_pressure_start",
    ]
    for mid in sorted(episodes.match_id.unique()):
        ev = pd.read_csv(raw_root / str(mid) / f"{mid}_dynamic_events.csv", low_memory=False)
        cols = [c for c in keep if c in ev.columns]
        sub = ev[cols].copy()
        sub.insert(0, "match_id", int(mid))
        parts.append(sub)
    events = pd.concat(parts, ignore_index=True).drop_duplicates(["match_id", "event_id"])
    out = episodes.merge(events, on=["match_id", "event_id"], how="left", suffixes=("", "_event"))
    side = out["attacking_side"].astype(str)
    x = pd.to_numeric(out["x_start"], errors="coerce")
    out["attack_progress_x"] = np.where(side.eq("right_to_left"), -x, x)
    return out


def conditional_auc_same_duration(df: pd.DataFrame, metric: str, step: float = 0.1) -> float | None:
    work = df[["match_id", "lead_to_shot", "window_seconds", metric]].dropna().copy()
    work["duration_bin"] = np.round(pd.to_numeric(work["window_seconds"], errors="coerce") / step).astype(int)
    u_total = 0.0
    pair_total = 0
    for _, block in work.groupby(["match_id", "duration_bin"]):
        y = block["lead_to_shot"].astype(bool).to_numpy()
        x = pd.to_numeric(block[metric], errors="coerce").to_numpy(float)
        keep = np.isfinite(x); y, x = y[keep], x[keep]
        n1, n0 = int(y.sum()), int((~y).sum())
        if not n1 or not n0:
            continue
        ranks = rankdata(x, method="average")
        u_total += float(ranks[y].sum() - n1 * (n1 + 1) / 2)
        pair_total += n1 * n0
    return None if pair_total == 0 else float(u_total / pair_total)


def per_match_auc(df: pd.DataFrame, metric: str) -> dict[int, float]:
    result = {}
    for mid, g in df.groupby("match_id"):
        a = auc(g["lead_to_shot"], g[metric])
        if a is not None:
            result[int(mid)] = a
    return result


def bootstrap_by_match(df: pd.DataFrame, metric: str, reps: int, rng: np.random.Generator) -> tuple[float, float]:
    ids = np.asarray(sorted(df.match_id.unique()))
    vals = []
    grouped = {mid: df[df.match_id == mid] for mid in ids}
    for _ in range(reps):
        sample = rng.choice(ids, size=len(ids), replace=True)
        g = pd.concat([grouped[mid] for mid in sample], ignore_index=True)
        a = auc(g["lead_to_shot"], g[metric])
        if a is not None:
            vals.append(a)
    return float(np.quantile(vals, 0.025)), float(np.quantile(vals, 0.975))


def within_match_permutation_p(df: pd.DataFrame, metric: str, reps: int, rng: np.random.Generator) -> float:
    x = pd.to_numeric(df[metric], errors="coerce").to_numpy(float)
    y = df["lead_to_shot"].astype(bool).to_numpy()
    keep = np.isfinite(x)
    x, y = x[keep], y[keep]
    mids = df.loc[keep, "match_id"].to_numpy()
    ranks = rankdata(x, method="average")
    n1, n0 = int(y.sum()), int((~y).sum())
    obs = (ranks[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
    groups = [np.flatnonzero(mids == mid) for mid in np.unique(mids)]
    ge = 0
    for _ in range(reps):
        yp = y.copy()
        for idx in groups:
            yp[idx] = rng.permutation(yp[idx])
        a = (ranks[yp].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)
        ge += a >= obs
    return float((ge + 1) / (reps + 1))


def exposure_table(df: pd.DataFrame, metric: str, positive_cut: float | None = None) -> tuple[pd.DataFrame, float | None]:
    q = df[["lead_to_shot", metric]].dropna().copy()
    score = pd.to_numeric(q[metric], errors="coerce").fillna(0.0)
    positive = score[score > 0]
    if positive_cut is None:
        positive_cut = float(positive.median()) if len(positive) else None
    if positive_cut is None:
        q["exposure"] = "none"
    else:
        q["exposure"] = np.select(
            [score <= 0, (score > 0) & (score <= positive_cut), score > positive_cut],
            ["none", "low", "high"],
            default="none",
        )
    order = ["none", "low", "high"]
    table = q.groupby("exposure")["lead_to_shot"].agg(["count", "sum", "mean"]).reindex(order).dropna(how="all").reset_index()
    return table, positive_cut


def split_ids(match_summary: pd.DataFrame) -> tuple[set[int], set[int]]:
    m = match_summary.sort_values("date_time")
    half = len(m) // 2
    return set(m.iloc[:half].match_id.astype(int)), set(m.iloc[half:].match_id.astype(int))


def analyze(df: pd.DataFrame, match_summary: pd.DataFrame, reps: int = 5000) -> dict:
    g = df[df["furthest_line_break"] == "second_last"].copy()
    dev_ids, hold_ids = split_ids(match_summary)
    dev, hold = g[g.match_id.isin(dev_ids)], g[g.match_id.isin(hold_ids)]
    rng = np.random.default_rng(2027)

    pm = per_match_auc(g, PRIMARY)
    static_pm = per_match_auc(g, STATIC)
    common = sorted(set(pm) & set(static_pm))
    delta = np.asarray([pm[k] - static_pm[k] for k in common], dtype=float)
    wilcox = None
    if len(delta) >= 5 and np.any(np.abs(delta) > 1e-12):
        wilcox = float(wilcoxon(delta, alternative="greater").pvalue)
    wins = sum(v > 0.5 for v in pm.values())
    match_win_p = float(binomtest(wins, len(pm), 0.5, alternative="greater").pvalue) if pm else None

    exposure, positive_cut = exposure_table(g, PRIMARY)
    hold_exposure, _ = exposure_table(hold, PRIMARY, positive_cut=positive_cut)
    emap = {str(r.exposure): r for r in exposure.itertuples()}
    hmap = {str(r.exposure): r for r in hold_exposure.itertuples()}
    any_rate = float(g.loc[g[PRIMARY] > 0, "lead_to_shot"].mean())
    none_rate = float(g.loc[g[PRIMARY] <= 0, "lead_to_shot"].mean())
    rr_any = any_rate / none_rate if none_rate > 0 else None
    hold_any_rate = float(hold.loc[hold[PRIMARY] > 0, "lead_to_shot"].mean())
    hold_none_rate = float(hold.loc[hold[PRIMARY] <= 0, "lead_to_shot"].mean())
    rr_hold_any = hold_any_rate / hold_none_rate if hold_none_rate > 0 else None
    rr_high = float(emap["high"].mean / emap["none"].mean) if "high" in emap and emap["none"].mean > 0 else None
    rr_hold_high = float(hmap["high"].mean / hmap["none"].mean) if "high" in hmap and hmap["none"].mean > 0 else None

    horizon_sensitivity = {}
    for horizon_s in (3, 5, 8, 10):
        col = f"width_contract_auc_{horizon_s}s"
        horizon_sensitivity[str(horizon_s)] = {
            "all_auc": safe(auc(g["lead_to_shot"], g[col])),
            "development_auc": safe(auc(dev["lead_to_shot"], dev[col])),
            "temporal_holdout_check_auc": safe(auc(hold["lead_to_shot"], hold[col])),
            "median_match_auc": safe(np.median(list(per_match_auc(g, col).values()))),
        }

    controls = {}
    for col in ["third_start", "channel_start"]:
        controls[col] = {}
        for key, block in g.groupby(col, dropna=False):
            if len(block) >= 40 and int(block.lead_to_shot.sum()) >= 5:
                controls[col][str(key)] = {
                    "n": int(len(block)),
                    "shots": int(block.lead_to_shot.sum()),
                    "auc": safe(auc(block.lead_to_shot, block[PRIMARY])),
                }

    duration_auc = auc(g["lead_to_shot"], g["window_seconds"])
    duration_matched_auc = conditional_auc_same_duration(g, PRIMARY, step=0.1)

    return {
        "duration_confound_audit": {
            "window_seconds_auc": safe(duration_auc),
            "dred_exact_0_1s_duration_matched_auc": safe(duration_matched_auc),
            "conclusion": "lead_to_shot is duration-confounded and is secondary descriptive evidence only",
        },
        "definition": {
            "name": "Defensive Re-Expansion Debt",
            "abbreviation": "DRED",
            "target_context": "second-last defensive line break",
            "formula": "integral_0^10s max(-z_width(t) - 1, 0) dt",
            "z_width": "robust within-match, defending-team, OOP-phase width deviation",
        },
        "sample": {
            "matches": int(g.match_id.nunique()),
            "episodes": int(len(g)),
            "shot_linked": int(g.lead_to_shot.sum()),
            "shot_rate": float(g.lead_to_shot.mean()),
        },
        "auc": {
            "dred_all": safe(auc(g.lead_to_shot, g[PRIMARY])),
            "dred_temporal_dev": safe(auc(dev.lead_to_shot, dev[PRIMARY])),
            "dred_temporal_holdout_check": safe(auc(hold.lead_to_shot, hold[PRIMARY])),
            "static_width_at_break": safe(auc(g.lead_to_shot, g[STATIC])),
            "width_abs_recovery": safe(auc(g.lead_to_shot, g["width_auc_10s"])),
            "max_gap_recovery": safe(auc(g.lead_to_shot, g["max_nearest_neighbor_auc_10s"])),
            "opponents_bypassed": safe(auc(g.lead_to_shot, g["n_opponents_bypassed"])),
        },
        "robustness": {
            "match_auc_median": safe(np.median(list(pm.values()))),
            "match_auc_mean": safe(np.mean(list(pm.values()))),
            "match_auc_gt_half": int(wins),
            "match_auc_n": int(len(pm)),
            "match_win_binomial_p": safe(match_win_p),
            "match_bootstrap_auc_95ci": list(bootstrap_by_match(g, PRIMARY, 2000, rng)),
            "within_match_permutation_p": within_match_permutation_p(g, PRIMARY, reps, rng),
            "dynamic_minus_static_median_auc": safe(np.median(delta)),
            "dynamic_minus_static_mean_auc": safe(np.mean(delta)),
            "dynamic_beats_static_matches": int(np.sum(delta > 0)),
            "dynamic_loses_static_matches": int(np.sum(delta < 0)),
            "dynamic_vs_static_wilcoxon_p": safe(wilcox),
        },
        "exposure": {
            "positive_median_cut": safe(positive_cut),
            "all": exposure.to_dict("records"),
            "temporal_holdout_check": hold_exposure.to_dict("records"),
            "any_vs_none_risk_ratio": safe(rr_any),
            "high_vs_none_risk_ratio": safe(rr_high),
            "holdout_any_vs_none_risk_ratio": safe(rr_hold_any),
            "holdout_high_vs_none_risk_ratio": safe(rr_hold_high),
        },
        "horizon_sensitivity": horizon_sensitivity,
        "controls": controls,
        "temporal_split": {
            "development_match_ids": sorted(dev_ids),
            "holdout_check_match_ids": sorted(hold_ids),
            "note": "Exploratory temporal stress test; not claimed as a pristine confirmatory holdout because the full dataset was inspected during metric development.",
        },
        "per_match_auc": {str(k): float(v) for k, v in sorted(pm.items())},
    }


def report(result: dict) -> str:
    a, r, s, q = result["auc"], result["robustness"], result["sample"], result["exposure"]
    audit = result["duration_confound_audit"]
    lines = [
        "# Defensive Re-Expansion Debt — shot-link audit (secondary)",
        "",
        "**Important:** this is not the primary validation. Remaining possession-window duration is itself strongly associated with `lead_to_shot`.",
        "",
        f"- DRED AUC: **{a['dred_all']:.3f}**",
        f"- recovery-window duration AUC: **{audit['window_seconds_auc']:.3f}**",
        f"- DRED conditional AUC within the same match and ~0.1 s recovery-duration strata: **{audit['dred_exact_0_1s_duration_matched_auc']:.3f}**",
        "",
        "The shot-linked result is retained as a confounding audit and descriptive observation, not as evidence that DRED independently predicts shots.",
        "",
        "**Original question:** after the second-last defensive line is broken, is sustained lateral contraction associated with a shot-linked possession?",
        "",
        f"Sample: **{s['episodes']}** second-last-line breaks across **{s['matches']}** matches; **{s['shot_linked']}** are shot-linked ({100*s['shot_rate']:.1f}%).",
        "",
        "## Main finding",
        "",
        f"- DRED AUC: **{a['dred_all']:.3f}**",
        f"- static width at the instant of the break: **{a['static_width_at_break']:.3f}**",
        f"- temporal development half: **{a['dred_temporal_dev']:.3f}**",
        f"- later-match temporal stress test: **{a['dred_temporal_holdout_check']:.3f}**",
        f"- median per-match AUC: **{r['match_auc_median']:.3f}**",
        f"- AUC > 0.5 in **{r['match_auc_gt_half']}/{r['match_auc_n']}** evaluable matches (one-sided binomial p={r['match_win_binomial_p']:.4g})",
        f"- match-bootstrap 95% CI for AUC: **{r['match_bootstrap_auc_95ci'][0]:.3f}–{r['match_bootstrap_auc_95ci'][1]:.3f}**",
        f"- within-match permutation p: **{r['within_match_permutation_p']:.4g}**",
        "",
        "## Dynamic recovery versus snapshot",
        "",
        f"The per-match AUC gain of DRED over static width is median **+{r['dynamic_minus_static_median_auc']:.3f}**; DRED wins in **{r['dynamic_beats_static_matches']}** matches and loses in **{r['dynamic_loses_static_matches']}** (one-sided Wilcoxon p={r['dynamic_vs_static_wilcoxon_p']:.4g}).",
        "",
        "## Exposure gradient",
        "",
        "| DRED exposure | n | shot-linked | rate |",
        "|---|---:|---:|---:|",
    ]
    for row in q["all"]:
        lines.append(f"| {row['exposure']} | {int(row['count'])} | {int(row['sum'])} | {100*row['mean']:.1f}% |")
    lines += [
        "",
        f"Any measurable DRED vs none: **{q['any_vs_none_risk_ratio']:.2f}x** shot-linked rate. High DRED vs none: **{q['high_vs_none_risk_ratio']:.2f}x**. Later-match temporal check (any vs none): **{q['holdout_any_vs_none_risk_ratio']:.2f}x**.",
        "",
        "## Time-horizon sensitivity",
        "",
        "| Window | All AUC | Later-match check | Median match AUC |",
        "|---|---:|---:|---:|",
    ]
    for horizon, hs in result["horizon_sensitivity"].items():
        lines.append(f"| {horizon}s | {hs['all_auc']:.3f} | {hs['temporal_holdout_check_auc']:.3f} | {hs['median_match_auc']:.3f} |")
    lines += [
        "",
        "The signal strengthens from 3–5 seconds to 8–10 seconds, consistent with a recovery process rather than an instantaneous shape snapshot.",
        "",
        "## Controls",
        "",
        "The association is not confined to a single starting channel or field third. These are descriptive subgroup checks, not independent hypothesis tests.",
        "",
        "## Interpretation",
        "",
        "The snapshot at the moment of the line break contains almost no width signal. The useful information appears *after* the break: shot-linked possessions are more often followed by a sustained lateral collapse relative to that team's normal out-of-possession width. DRED therefore measures recovery dynamics rather than static compactness.",
        "",
        "This is diagnostic association, not causal proof. `lead_to_shot` is supplied by SkillCorner and DRED is measured after the break.",
    ]
    return "\n".join(lines) + "\n"


def make_figures(df: pd.DataFrame, result: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    a = result["auc"]
    labels = ["Static width\nat break", "Width |z|\nrecovery", "DRED\n(contraction)"]
    values = [a["static_width_at_break"], a["width_abs_recovery"], a["dred_all"]]
    fig, ax = plt.subplots(figsize=(7, 4.2))
    bars = ax.bar(labels, values)
    ax.axhline(0.5, linestyle="--", linewidth=1)
    ax.set_ylim(0.4, 0.72)
    ax.set_ylabel("ROC AUC for shot-linked possession")
    ax.set_title("Dynamic recovery contains signal missing from the snapshot")
    for b, v in zip(bars, values):
        ax.text(b.get_x()+b.get_width()/2, v+0.008, f"{v:.3f}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(out / "dred_static_vs_dynamic.png", dpi=180)
    plt.close(fig)

    q = pd.DataFrame(result["exposure"]["all"])
    fig, ax = plt.subplots(figsize=(7, 4.2))
    bars = ax.bar(q["exposure"].astype(str), 100*q["mean"])
    ax.set_ylabel("Shot-linked possessions (%)")
    ax.set_xlabel("Defensive Re-Expansion Debt")
    ax.set_title("Shot-linked rate rises when lateral collapse persists")
    for b, v in zip(bars, 100*q["mean"]):
        ax.text(b.get_x()+b.get_width()/2, v+0.2, f"{v:.1f}%", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(out / "dred_exposure_risk.png", dpi=180)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=Path, default=Path("data/processed/all_line_break_recovery.csv"))
    ap.add_argument("--matches", type=Path, default=Path("data/processed/match_summary.csv"))
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--outputs", type=Path, default=Path("outputs"))
    ap.add_argument("--figures", type=Path, default=Path("figures"))
    ap.add_argument(
        "--all-public-matches",
        action="store_true",
        help="research extension only; primary submission analysis uses the 10 official Dynamic Events matches",
    )
    args = ap.parse_args()
    args.outputs.mkdir(parents=True, exist_ok=True)
    episodes = pd.read_csv(args.episodes)
    if not args.all_public_matches:
        episodes = episodes[episodes["match_id"].astype(int).isin(OFFICIAL_DYNAMIC_EVENT_MATCH_ID_SET)].copy()
    for c in ["lead_to_shot", "lead_to_goal"]:
        episodes[c] = episodes[c].astype(str).str.lower().isin(["true", "1", "yes"])
    enriched = enrich(episodes, args.raw)
    enriched.to_csv(args.outputs / "episodes_enriched.csv", index=False)
    matches = pd.read_csv(args.matches)
    if not args.all_public_matches:
        matches = matches[matches["match_id"].astype(int).isin(OFFICIAL_DYNAMIC_EVENT_MATCH_ID_SET)].copy()
    result = analyze(enriched, matches)
    (args.outputs / "dred_validation.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    text = report(result)
    (args.outputs / "dred_validation.md").write_text(text)
    make_figures(enriched, result, args.figures)
    print(text)


if __name__ == "__main__":
    main()
