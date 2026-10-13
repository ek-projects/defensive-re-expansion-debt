from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest, rankdata, spearmanr

from defensive_recovery.competition import OFFICIAL_DYNAMIC_EVENT_MATCH_IDS
from validate_epv import load_epv


BASE_CONTROLS = [
    "window_seconds",
    "action_duration",
    "possession_epv_for_start",
    "width_abs_z_at_break",
]
ACTION_CAPS = (0.5, 1.0, 2.0, 3.0, 5.0, 10.0)


def _residual(y: np.ndarray, controls: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    controls = np.asarray(controls, dtype=float)
    if controls.ndim == 1:
        controls = controls[:, None]
    design = np.column_stack([np.ones(len(y)), controls])
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    return y - design @ beta


def _rank_within_match(df: pd.DataFrame, column: str) -> pd.Series:
    return df.groupby("match_id")[column].transform(
        lambda s: pd.Series(rankdata(s), index=s.index)
    )


def partial_rank(
    df: pd.DataFrame,
    metric: str,
    outcome: str,
    controls: list[str],
) -> tuple[float, int]:
    required = [metric, outcome, *controls, "match_id"]
    work = df.dropna(subset=required).copy()
    if len(work) < len(controls) + 4:
        return float("nan"), int(len(work))
    ranked: dict[str, np.ndarray] = {}
    for column in [metric, outcome, *controls]:
        r = _rank_within_match(work, column)
        r = r - r.groupby(work["match_id"]).transform("mean")
        ranked[column] = r.to_numpy(float)
    c = np.column_stack([ranked[column] for column in controls])
    x = _residual(ranked[metric], c)
    y = _residual(ranked[outcome], c)
    denom = np.std(x) * np.std(y)
    corr = float(np.corrcoef(x, y)[0, 1]) if denom > 0 else float("nan")
    return corr, int(len(work))


def per_match_partial(
    df: pd.DataFrame,
    metric: str,
    outcome: str,
    controls: list[str],
) -> pd.DataFrame:
    rows: list[dict] = []
    for match_id, group in df.groupby("match_id"):
        q = group.dropna(subset=[metric, outcome, *controls]).copy()
        if len(q) < len(controls) + 4:
            continue
        ranks = {
            column: rankdata(q[column])
            for column in [metric, outcome, *controls]
        }
        c = np.column_stack([ranks[column] for column in controls])
        x = _residual(ranks[metric], c)
        y = _residual(ranks[outcome], c)
        if np.std(x) == 0 or np.std(y) == 0:
            corr = float("nan")
        else:
            corr = float(np.corrcoef(x, y)[0, 1])
        rows.append(
            {
                "match_id": int(match_id),
                "n": int(len(q)),
                "partial_rank": corr,
            }
        )
    return pd.DataFrame(rows)


def bootstrap_match_median(
    values: np.ndarray,
    *,
    reps: int = 20000,
    seed: int = 2027,
) -> dict:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return {
            "median": None,
            "median_ci95": [None, None],
            "mean": None,
            "positive": 0,
            "total": 0,
            "one_sided_sign_test_p": None,
        }
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(reps, len(values)), replace=True)
    medians = np.median(samples, axis=1)
    positive = int(np.sum(values > 0))
    sign_p = float(binomtest(positive, len(values), 0.5, alternative="greater").pvalue)
    return {
        "median": float(np.median(values)),
        "median_ci95": [float(v) for v in np.quantile(medians, [0.025, 0.975])],
        "mean": float(np.mean(values)),
        "positive": positive,
        "total": int(len(values)),
        "one_sided_sign_test_p": sign_p,
    }


def summarize_association(
    df: pd.DataFrame,
    metric: str,
    outcome: str,
    controls: list[str],
) -> dict:
    q = df.dropna(subset=[metric, outcome, *controls]).copy()
    if len(q) == 0:
        return {"n": 0}
    raw = spearmanr(q[metric], q[outcome])
    adjusted, n = partial_rank(q, metric, outcome, controls)
    pm = per_match_partial(q, metric, outcome, controls)
    finite = pm["partial_rank"].to_numpy(float) if len(pm) else np.asarray([])
    boot = bootstrap_match_median(finite)
    return {
        "n": int(n),
        "matches": int(q["match_id"].nunique()),
        "raw_spearman": float(raw.statistic),
        "adjusted_partial_rank": adjusted,
        "match_level": boot,
        "per_match": pm.to_dict("records"),
    }


def load_dynamic_context(raw_root: Path) -> tuple[pd.DataFrame, dict[int, pd.DataFrame]]:
    event_rows: list[pd.DataFrame] = []
    player_possessions: dict[int, pd.DataFrame] = {}
    use = [
        "event_id",
        "event_type",
        "frame_start",
        "frame_end",
        "phase_index",
        "team_id",
        "possession_epv_for_start",
        "possession_epv_for_end",
        "possession_epv_delta_for",
    ]
    for match_id in OFFICIAL_DYNAMIC_EVENT_MATCH_IDS:
        path = raw_root / str(match_id) / f"{match_id}_dynamic_events.csv"
        d = pd.read_csv(path, usecols=use, low_memory=False)
        p = d[d["event_type"] == "player_possession"].copy()
        p["match_id"] = match_id
        player_possessions[int(match_id)] = p
        event_rows.append(
            p[["match_id", "event_id", "frame_end"]]
            .rename(columns={"frame_end": "action_frame_end"})
            .drop_duplicates(["match_id", "event_id"])
        )
    return pd.concat(event_rows, ignore_index=True), player_possessions


def load_samples(
    enriched_path: Path,
    raw_root: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, pd.DataFrame]]:
    episodes = pd.read_csv(enriched_path)
    episodes = episodes[
        episodes["match_id"].astype(int).isin(OFFICIAL_DYNAMIC_EVENT_MATCH_IDS)
    ].copy()
    epv = load_epv(raw_root)
    event_context, player_possessions = load_dynamic_context(raw_root)
    all_epv = (
        episodes.merge(epv, on=["match_id", "event_id"], how="inner")
        .merge(event_context, on=["match_id", "event_id"], how="left")
        .rename(columns={"duration": "action_duration"})
    )
    numeric = [
        "frame_start",
        "phase_index",
        "attack_team_id",
        "defending_team_id",
        "window_seconds",
        "action_duration",
        "action_frame_end",
        "possession_epv_for_start",
        "possession_epv_delta_for",
        "width_abs_z_at_break",
        "width_contract_mean_10s",
        "x_start",
        "y_start",
        "attack_progress_x",
        "n_opponents_bypassed_event",
    ]
    for column in numeric:
        if column in all_epv:
            all_epv[column] = pd.to_numeric(all_epv[column], errors="coerce")
    primary = all_epv[all_epv["furthest_line_break"] == "second_last"].copy()
    required = [
        "frame_start",
        "phase_index",
        "attack_team_id",
        "defending_team_id",
        "window_seconds",
        "action_duration",
        "possession_epv_for_start",
        "possession_epv_delta_for",
        "width_abs_z_at_break",
        "width_contract_mean_10s",
    ]
    primary = primary.dropna(subset=required).reset_index(drop=True)
    return all_epv, primary, player_possessions


def add_frame_based_controls(primary: pd.DataFrame, processed_root: Path) -> pd.DataFrame:
    work = primary.copy()
    columns = [
        "recomputed_contract_mean",
        "expand_mean_10s",
        "absolute_tail_mean_10s",
        "pre_contract_mean_10s",
        "pre_window_seconds",
    ]
    for column in columns:
        work[column] = np.nan
    for cap in ACTION_CAPS:
        key = str(cap).replace(".", "p")
        work[f"actioncap_dred_{key}"] = np.nan
        work[f"actioncap_window_{key}"] = np.nan

    for match_id, indices in work.groupby("match_id").groups.items():
        frame_path = processed_root / f"{int(match_id)}_frame_features.csv"
        frames = pd.read_csv(
            frame_path,
            usecols=["frame", "phase_index", "attack_team_id", "debt", "z_width"],
        )
        by_phase = {
            int(phase): block.sort_values("frame")
            for phase, block in frames.groupby("phase_index")
        }
        for idx in indices:
            event = work.loc[idx]
            block = by_phase.get(int(event["phase_index"]))
            if block is None:
                continue
            block = block[
                (block["attack_team_id"] == int(event["attack_team_id"]))
                & block["debt"].notna()
            ]
            if block.empty:
                continue
            start = int(event["frame_start"])
            post = block[(block["frame"] >= start) & (block["frame"] <= start + 100)]
            if not post.empty:
                z = post["z_width"].to_numpy(float)
                work.loc[idx, "recomputed_contract_mean"] = float(
                    np.maximum(-z - 1.0, 0.0).mean()
                )
                work.loc[idx, "expand_mean_10s"] = float(
                    np.maximum(z - 1.0, 0.0).mean()
                )
                work.loc[idx, "absolute_tail_mean_10s"] = float(
                    np.maximum(np.abs(z) - 1.0, 0.0).mean()
                )

            pre = block[(block["frame"] >= start - 100) & (block["frame"] < start)]
            if not pre.empty:
                z = pre["z_width"].to_numpy(float)
                work.loc[idx, "pre_contract_mean_10s"] = float(
                    np.maximum(-z - 1.0, 0.0).mean()
                )
                work.loc[idx, "pre_window_seconds"] = float(len(pre) / 10.0)

            if pd.isna(event.get("action_frame_end")):
                continue
            action_end = int(event["action_frame_end"])
            for cap in ACTION_CAPS:
                key = str(cap).replace(".", "p")
                cap_end = min(action_end, start + int(round(cap * 10)))
                action_post = block[
                    (block["frame"] >= start) & (block["frame"] <= cap_end)
                ]
                if action_post.empty:
                    continue
                z = action_post["z_width"].to_numpy(float)
                work.loc[idx, f"actioncap_dred_{key}"] = float(
                    np.maximum(-z - 1.0, 0.0).mean()
                )
                work.loc[idx, f"actioncap_window_{key}"] = float(
                    (int(action_post["frame"].max()) - start) / 10.0
                )
    return work


def add_aligned_epv_outcomes(
    primary: pd.DataFrame,
    player_possessions: dict[int, pd.DataFrame],
) -> pd.DataFrame:
    work = primary.copy()
    for column in [
        "aligned_epv_net_gain",
        "aligned_epv_peak_gain_strict",
        "aligned_epv_sum_player_deltas",
        "aligned_completed_player_possessions",
    ]:
        work[column] = np.nan

    for match_id, indices in work.groupby("match_id").groups.items():
        d = player_possessions[int(match_id)]
        for idx in indices:
            event = work.loc[idx]
            start = int(event["frame_start"])
            end = start + int(round(float(event["window_seconds"]) * 10.0))
            phase = int(event["phase_index"])
            team = int(event["attack_team_id"])
            window = d[
                (d["team_id"] == team)
                & (d["phase_index"] == phase)
                & (d["frame_start"] >= start)
                & (d["frame_start"] <= end)
            ].sort_values(["frame_start", "frame_end"])
            complete = window[window["frame_end"] <= end].copy()
            start_epv = float(event["possession_epv_for_start"])

            completed_ends = pd.to_numeric(
                complete["possession_epv_for_end"], errors="coerce"
            ).dropna()
            if len(completed_ends):
                work.loc[idx, "aligned_epv_net_gain"] = float(
                    completed_ends.iloc[-1] - start_epv
                )

            start_values = pd.to_numeric(
                window["possession_epv_for_start"], errors="coerce"
            ).dropna()
            completed_end_values = pd.to_numeric(
                complete["possession_epv_for_end"], errors="coerce"
            ).dropna()
            strict_values = pd.concat([start_values, completed_end_values])
            if len(strict_values):
                work.loc[idx, "aligned_epv_peak_gain_strict"] = float(
                    strict_values.max() - start_epv
                )

            deltas = pd.to_numeric(
                complete["possession_epv_delta_for"], errors="coerce"
            ).dropna()
            if len(deltas):
                work.loc[idx, "aligned_epv_sum_player_deltas"] = float(deltas.sum())
            work.loc[idx, "aligned_completed_player_possessions"] = int(len(complete))
    return work


def add_previous_same_defender_placebo(
    all_episodes: pd.DataFrame,
    primary: pd.DataFrame,
) -> pd.DataFrame:
    pool = all_episodes[all_episodes["furthest_line_break"] == "second_last"].copy()
    pool = pool.dropna(
        subset=["match_id", "defending_team_id", "frame_start", "width_contract_mean_10s"]
    )
    pool = pool.sort_values(["match_id", "defending_team_id", "frame_start"])
    pool["previous_same_defender_dred"] = pool.groupby(
        ["match_id", "defending_team_id"]
    )["width_contract_mean_10s"].shift(1)
    prev = pool[["match_id", "event_id", "previous_same_defender_dred"]]
    return primary.merge(prev, on=["match_id", "event_id"], how="left")


def rich_context_adjustment(primary: pd.DataFrame) -> dict:
    work = primary.copy()
    work["x_attack_start"] = np.where(
        work["attacking_side"].eq("left_to_right"),
        work["x_start"],
        -work["x_start"],
    )
    work["abs_y_start"] = work["y_start"].abs()
    numeric_controls = [
        *BASE_CONTROLS,
        "attack_progress_x",
        "x_attack_start",
        "abs_y_start",
        "n_opponents_bypassed_event",
    ]
    required = [
        "width_contract_mean_10s",
        "possession_epv_delta_for",
        "match_id",
        *numeric_controls,
    ]
    work = work.dropna(subset=required).copy()

    ranked: dict[str, np.ndarray] = {}
    for column in [
        "width_contract_mean_10s",
        "possession_epv_delta_for",
        *numeric_controls,
    ]:
        r = _rank_within_match(work, column)
        r = r - r.groupby(work["match_id"]).transform("mean")
        ranked[column] = r.to_numpy(float)

    control_arrays = [ranked[column] for column in numeric_controls]
    categories = ["overall_pressure_start", "channel_start", "third_start", "oop_phase"]
    dummies = pd.get_dummies(
        work[categories].fillna("missing").astype(str),
        prefix=categories,
        dtype=float,
    )
    for column in dummies:
        centered = dummies[column] - dummies[column].groupby(work["match_id"]).transform("mean")
        if float(centered.std()) > 0:
            control_arrays.append(centered.to_numpy(float))

    controls = np.column_stack(control_arrays)
    x = _residual(ranked["width_contract_mean_10s"], controls)
    y = _residual(ranked["possession_epv_delta_for"], controls)
    corr = float(np.corrcoef(x, y)[0, 1])
    return {
        "n": int(len(work)),
        "adjusted_partial_rank": corr,
        "numeric_controls": numeric_controls,
        "categorical_controls": categories,
        "design_columns": int(controls.shape[1]),
    }


def line_break_strata(all_epv: pd.DataFrame) -> list[dict]:
    rows = []
    for stratum in ["first", "second_last", "last"]:
        q = all_epv[all_epv["furthest_line_break"] == stratum].copy()
        result = summarize_association(
            q,
            "width_contract_mean_10s",
            "possession_epv_delta_for",
            BASE_CONTROLS,
        )
        rows.append({"furthest_line_break": stratum, **result})
    return rows


def leave_one_defending_team_out(primary: pd.DataFrame) -> list[dict]:
    rows = []
    for team_id in sorted(primary["defending_team_id"].dropna().astype(int).unique()):
        q = primary[primary["defending_team_id"].astype(int) != team_id]
        r, n = partial_rank(
            q,
            "width_contract_mean_10s",
            "possession_epv_delta_for",
            BASE_CONTROLS,
        )
        rows.append(
            {
                "omitted_defending_team_id": int(team_id),
                "n": int(n),
                "adjusted_partial_rank": r,
            }
        )
    return rows


def temporal_split(primary: pd.DataFrame) -> dict:
    work = primary.copy()
    work["within_match_time_rank"] = work.groupby("match_id")["frame_start"].rank(
        method="first", pct=True
    )
    halves = {}
    for label, mask in {
        "early_half": work["within_match_time_rank"] <= 0.5,
        "late_half": work["within_match_time_rank"] > 0.5,
    }.items():
        q = work[mask]
        r, n = partial_rank(
            q,
            "width_contract_mean_10s",
            "possession_epv_delta_for",
            BASE_CONTROLS,
        )
        halves[label] = {"n": int(n), "adjusted_partial_rank": r}
    return halves


def cross_match_cv(primary: pd.DataFrame) -> dict:
    work = primary.dropna(
        subset=[
            "width_contract_mean_10s",
            "possession_epv_delta_for",
            *BASE_CONTROLS,
        ]
    ).copy()
    rank_columns = [
        "width_contract_mean_10s",
        "possession_epv_delta_for",
        *BASE_CONTROLS,
    ]
    for column in rank_columns:
        work[f"r_{column}"] = work.groupby("match_id")[column].transform(
            lambda s: (rankdata(s) - 0.5) / len(s) - 0.5
        )
    base = [f"r_{column}" for column in BASE_CONTROLS]
    augmented = [*base, "r_width_contract_mean_10s"]
    target = "r_possession_epv_delta_for"
    rows = []

    for match_id in sorted(work["match_id"].astype(int).unique()):
        train = work[work["match_id"].astype(int) != match_id]
        test = work[work["match_id"].astype(int) == match_id]

        def predict(features: list[str]) -> np.ndarray:
            x_train = np.column_stack(
                [np.ones(len(train)), *[train[f].to_numpy(float) for f in features]]
            )
            beta = np.linalg.lstsq(x_train, train[target].to_numpy(float), rcond=None)[0]
            x_test = np.column_stack(
                [np.ones(len(test)), *[test[f].to_numpy(float) for f in features]]
            )
            return x_test @ beta

        y = test[target].to_numpy(float)
        p0 = predict(base)
        p1 = predict(augmented)
        mse0 = float(np.mean((y - p0) ** 2))
        mse1 = float(np.mean((y - p1) ** 2))
        rows.append(
            {
                "held_out_match_id": int(match_id),
                "n": int(len(test)),
                "base_mse": mse0,
                "dred_augmented_mse": mse1,
                "mse_improvement": mse0 - mse1,
            }
        )

    n = np.asarray([row["n"] for row in rows], dtype=float)
    base_mse = np.asarray([row["base_mse"] for row in rows], dtype=float)
    aug_mse = np.asarray([row["dred_augmented_mse"] for row in rows], dtype=float)
    delta = base_mse - aug_mse
    weighted_base = float(np.average(base_mse, weights=n))
    weighted_aug = float(np.average(aug_mse, weights=n))
    return {
        "folds": rows,
        "folds_improved": int(np.sum(delta > 0)),
        "total_folds": int(len(rows)),
        "weighted_base_mse": weighted_base,
        "weighted_dred_augmented_mse": weighted_aug,
        "relative_weighted_mse_reduction": float((weighted_base - weighted_aug) / weighted_base),
        "median_fold_mse_improvement": float(np.median(delta)),
    }


def dose_response(primary: pd.DataFrame) -> dict:
    work = primary.copy()
    work["any_dred"] = (work["width_contract_mean_10s"] > 0).astype(float)
    binary_r, binary_n = partial_rank(
        work,
        "any_dred",
        "possession_epv_delta_for",
        BASE_CONTROLS,
    )
    positive = work[work["width_contract_mean_10s"] > 0].copy()
    positive_r, positive_n = partial_rank(
        positive,
        "width_contract_mean_10s",
        "possession_epv_delta_for",
        BASE_CONTROLS,
    )

    q = work.dropna(
        subset=["width_contract_mean_10s", "possession_epv_delta_for", *BASE_CONTROLS]
    ).copy()
    ranked: dict[str, np.ndarray] = {}
    for column in ["possession_epv_delta_for", *BASE_CONTROLS]:
        r = _rank_within_match(q, column)
        r = r - r.groupby(q["match_id"]).transform("mean")
        ranked[column] = r.to_numpy(float)
    c = np.column_stack([ranked[column] for column in BASE_CONTROLS])
    y = _residual(ranked["possession_epv_delta_for"], c)
    y_sd = float(np.std(y, ddof=1))
    q["adjusted_epv_residual_z"] = y / y_sd if y_sd > 0 else y
    q["any_dred_bool"] = q["width_contract_mean_10s"] > 0
    binary_groups = (
        q.groupby("any_dred_bool")
        .agg(
            n=("event_id", "size"),
            mean_adjusted_epv_residual_z=("adjusted_epv_residual_z", "mean"),
            median_adjusted_epv_residual_z=("adjusted_epv_residual_z", "median"),
        )
        .reset_index()
        .to_dict("records")
    )

    p = q[q["width_contract_mean_10s"] > 0].copy()
    p["positive_tertile"] = pd.qcut(
        p["width_contract_mean_10s"],
        3,
        labels=["low", "middle", "high"],
        duplicates="drop",
    )
    tertiles = (
        p.groupby("positive_tertile", observed=True)
        .agg(
            n=("event_id", "size"),
            dred_min=("width_contract_mean_10s", "min"),
            dred_max=("width_contract_mean_10s", "max"),
            mean_adjusted_epv_residual_z=("adjusted_epv_residual_z", "mean"),
        )
        .reset_index()
    )
    tertiles["positive_tertile"] = tertiles["positive_tertile"].astype(str)
    return {
        "zero_dred_events": int((work["width_contract_mean_10s"] == 0).sum()),
        "positive_dred_events": int((work["width_contract_mean_10s"] > 0).sum()),
        "binary_any_dred_adjusted_partial_rank": binary_r,
        "binary_any_dred_n": int(binary_n),
        "positive_only_intensity_adjusted_partial_rank": positive_r,
        "positive_only_n": int(positive_n),
        "binary_adjusted_outcome_groups": binary_groups,
        "positive_intensity_tertiles": tertiles.to_dict("records"),
    }


def analyze(
    all_epv: pd.DataFrame,
    primary: pd.DataFrame,
    *,
    all_episodes: pd.DataFrame,
) -> dict:
    baseline = summarize_association(
        primary,
        "width_contract_mean_10s",
        "possession_epv_delta_for",
        BASE_CONTROLS,
    )

    recompute_diff = np.nanmax(
        np.abs(
            primary["recomputed_contract_mean"].to_numpy(float)
            - primary["width_contract_mean_10s"].to_numpy(float)
        )
    )

    directional = {
        "contraction_primary": baseline,
        "expansion_placebo": summarize_association(
            primary,
            "expand_mean_10s",
            "possession_epv_delta_for",
            BASE_CONTROLS,
        ),
        "absolute_deviation_placebo": summarize_association(
            primary,
            "absolute_tail_mean_10s",
            "possession_epv_delta_for",
            BASE_CONTROLS,
        ),
    }

    pre_controls = [
        "pre_window_seconds",
        "action_duration",
        "possession_epv_for_start",
        "width_abs_z_at_break",
    ]
    placebos = {
        "pre_break_contraction": summarize_association(
            primary,
            "pre_contract_mean_10s",
            "possession_epv_delta_for",
            pre_controls,
        ),
        "previous_same_defender_event": summarize_association(
            primary,
            "previous_same_defender_dred",
            "possession_epv_delta_for",
            BASE_CONTROLS,
        ),
    }

    action_caps = []
    for cap in ACTION_CAPS:
        key = str(cap).replace(".", "p")
        controls = [
            f"actioncap_window_{key}",
            "action_duration",
            "possession_epv_for_start",
            "width_abs_z_at_break",
        ]
        result = summarize_association(
            primary,
            f"actioncap_dred_{key}",
            "possession_epv_delta_for",
            controls,
        )
        action_caps.append({"cap_seconds": cap, **result})

    aligned = {
        "net_epv_gain_over_recovery_window": summarize_association(
            primary,
            "width_contract_mean_10s",
            "aligned_epv_net_gain",
            BASE_CONTROLS,
        ),
        "strict_peak_epv_gain_over_recovery_window": summarize_association(
            primary,
            "width_contract_mean_10s",
            "aligned_epv_peak_gain_strict",
            BASE_CONTROLS,
        ),
        "sum_player_possession_epv_deltas_over_recovery_window": summarize_association(
            primary,
            "width_contract_mean_10s",
            "aligned_epv_sum_player_deltas",
            BASE_CONTROLS,
        ),
    }

    team_lomo = leave_one_defending_team_out(primary)
    team_values = np.asarray([row["adjusted_partial_rank"] for row in team_lomo])

    result = {
        "guardrail": (
            "Post-submission adversarial audit for Pretalx submission 8TTF3B. "
            "These analyses were not pre-specified before the submitted result and must not be represented as such."
        ),
        "sample": {
            "primary_events": int(len(primary)),
            "matches": int(primary["match_id"].nunique()),
        },
        "reproduction": {
            "max_absolute_difference_recomputed_vs_stored_dred": float(recompute_diff),
            "exact_within_1e_12": bool(recompute_diff <= 1e-12),
        },
        "submitted_event_local_epv_result": baseline,
        "direction_specificity": directional,
        "event_locality_placebos": placebos,
        "rich_context_adjustment": rich_context_adjustment(primary),
        "line_break_strata": line_break_strata(all_epv),
        "leave_one_defending_team_out": team_lomo,
        "leave_one_defending_team_out_summary": {
            "all_positive": bool(np.all(team_values > 0)),
            "min": float(np.min(team_values)),
            "max": float(np.max(team_values)),
            "median": float(np.median(team_values)),
        },
        "temporal_split": temporal_split(primary),
        "cross_match_incremental_cv": cross_match_cv(primary),
        "dose_response_characterization": dose_response(primary),
        "trigger_action_temporal_alignment": action_caps,
        "recovery_window_aligned_epv": aligned,
        "interpretation": {
            "supports": [
                "The submitted association reproduces exactly from the stored tracking-derived metric.",
                "The signal is direction-specific: contraction is positive while expansion is negative and absolute width abnormality is approximately null.",
                "Pre-break contraction and the previous same-defender event are much weaker, supporting event locality.",
                "The association survives richer event context, leave-one-defending-team-out checks, and both chronological halves.",
                "A recovery-window-aligned EPV endpoint is stronger than the submitted triggering-action EPV endpoint and is positive in most matches.",
            ],
            "limits": [
                "The effect is not unique to second-last-line breaks: last-line breaks also show a positive adjusted association, while first-line breaks are approximately null.",
                "When DRED is restricted strictly to the triggering player action, the association is materially weaker and near zero in the earliest 0.5-2 seconds.",
                "This reinforces DRED as a recovery diagnostic rather than an instantaneous or pre-break prediction score.",
                "The recovery-window-aligned EPV analysis is post-submission evidence and is contemporaneous association, not causal proof."
            ],
        },
    }
    return result


def _fmt(value: float | None, digits: int = 3) -> str:
    if value is None or not np.isfinite(value):
        return "NA"
    return f"{value:.{digits}f}"


def report_md(result: dict) -> str:
    baseline = result["submitted_event_local_epv_result"]
    direction = result["direction_specificity"]
    placebos = result["event_locality_placebos"]
    rich = result["rich_context_adjustment"]
    aligned = result["recovery_window_aligned_epv"]
    cv = result["cross_match_incremental_cv"]
    dose = result["dose_response_characterization"]

    net = aligned["net_epv_gain_over_recovery_window"]
    peak = aligned["strict_peak_epv_gain_over_recovery_window"]
    lines = [
        "# DRED post-submission adversarial EPV audit",
        "",
        result["guardrail"],
        "",
        "## Executive result",
        "",
        f"- submitted event-local EPV adjusted partial-rank: **{_fmt(baseline['adjusted_partial_rank'])}** on **{baseline['n']}** events",
        f"- richer-context adjusted result: **{_fmt(rich['adjusted_partial_rank'])}** on **{rich['n']}** events",
        f"- recovery-window-aligned net EPV gain: adjusted **{_fmt(net['adjusted_partial_rank'])}**, median match **{_fmt(net['match_level']['median'])}**, positive **{net['match_level']['positive']}/{net['match_level']['total']}** matches",
        f"- aligned net-EPV match-bootstrap 95% interval: **{_fmt(net['match_level']['median_ci95'][0])} to {_fmt(net['match_level']['median_ci95'][1])}**",
        "",
        "The central interpretation changes slightly after the adversarial checks: DRED is best supported as a contemporaneous recovery diagnostic over the recovery window, not as an instantaneous player-action predictor.",
        "",
        "## Direction specificity",
        "",
        "| metric | n | raw rho | adjusted r |",
        "|---|---:|---:|---:|",
    ]
    for label, key in [
        ("DRED contraction", "contraction_primary"),
        ("width expansion placebo", "expansion_placebo"),
        ("absolute width-tail placebo", "absolute_deviation_placebo"),
    ]:
        row = direction[key]
        lines.append(
            f"| {label} | {row['n']} | {_fmt(row['raw_spearman'])} | {_fmt(row['adjusted_partial_rank'])} |"
        )

    lines += [
        "",
        "## Event-locality placebos",
        "",
        "| placebo | n | adjusted r |",
        "|---|---:|---:|",
    ]
    for label, key in [
        ("pre-break contraction", "pre_break_contraction"),
        ("previous second-last break by the same defending team", "previous_same_defender_event"),
    ]:
        row = placebos[key]
        lines.append(f"| {label} | {row['n']} | {_fmt(row['adjusted_partial_rank'])} |")

    lines += [
        "",
        "## Triggering-action temporal alignment",
        "",
        "DRED was recomputed using only reliable tracking frames that occur before the triggering player possession ends. The effect is weak in the first seconds and increases only for longer actions, which is consistent with DRED being a recovery-process metric.",
        "",
        "| action cap | n | adjusted r | median match r | positive matches |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in result["trigger_action_temporal_alignment"]:
        ml = row["match_level"]
        lines.append(
            f"| {row['cap_seconds']:.1f}s | {row['n']} | {_fmt(row['adjusted_partial_rank'])} | {_fmt(ml['median'])} | {ml['positive']}/{ml['total']} |"
        )

    lines += [
        "",
        "## EPV aligned to the same recovery window",
        "",
        "The alternative outcome uses only player-possession EPV states from the same attacking team, same phase and same DRED recovery window. Completed-possession end values are required for the net endpoint; the strict peak endpoint never uses an event end beyond the recovery-window boundary.",
        "",
        "| outcome | n | raw rho | adjusted r | median match r | positive matches | 95% median CI |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for label, row in [
        ("net EPV gain", net),
        ("strict peak EPV gain", peak),
        ("sum of player-possession EPV deltas", aligned["sum_player_possession_epv_deltas_over_recovery_window"]),
    ]:
        ml = row["match_level"]
        ci = ml.get("median_ci95", [None, None])
        lines.append(
            f"| {label} | {row['n']} | {_fmt(row['raw_spearman'])} | {_fmt(row['adjusted_partial_rank'])} | {_fmt(ml['median'])} | {ml['positive']}/{ml['total']} | {_fmt(ci[0])} to {_fmt(ci[1])} |"
        )

    lines += [
        "",
        "## Specificity across line-break depth",
        "",
        "| furthest line broken | n | adjusted r | median match r | positive matches |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in result["line_break_strata"]:
        ml = row["match_level"]
        lines.append(
            f"| {row['furthest_line_break']} | {row['n']} | {_fmt(row['adjusted_partial_rank'])} | {_fmt(ml['median'])} | {ml['positive']}/{ml['total']} |"
        )

    team = result["leave_one_defending_team_out_summary"]
    temp = result["temporal_split"]
    lines += [
        "",
        "## Stability checks",
        "",
        f"- leave-one-defending-team-out: all positive **{team['all_positive']}**, range **{_fmt(team['min'])} to {_fmt(team['max'])}**, median **{_fmt(team['median'])}**",
        f"- chronological early half: **{_fmt(temp['early_half']['adjusted_partial_rank'])}** ({temp['early_half']['n']} events)",
        f"- chronological late half: **{_fmt(temp['late_half']['adjusted_partial_rank'])}** ({temp['late_half']['n']} events)",
        f"- leave-one-match-out cross-match regression: adding DRED lowers held-out MSE in **{cv['folds_improved']}/{cv['total_folds']}** matches; weighted MSE reduction **{100*cv['relative_weighted_mse_reduction']:.2f}%**",
        "",
        "## Exposure shape",
        "",
        f"- zero DRED: **{dose['zero_dred_events']}** events; positive DRED: **{dose['positive_dred_events']}**",
        f"- any-DRED indicator adjusted association: **{_fmt(dose['binary_any_dred_adjusted_partial_rank'])}**",
        f"- among positive-DRED events only, continuous intensity adjusted association: **{_fmt(dose['positive_only_intensity_adjusted_partial_rank'])}**",
        "",
        "Positive-DRED tertiles (adjusted EPV outcome residual, standardised after the submitted controls):",
        "",
        "| tertile | n | DRED range | mean adjusted EPV residual (SD) |",
        "|---|---:|---:|---:|",
    ]
    for row in dose["positive_intensity_tertiles"]:
        lines.append(
            f"| {row['positive_tertile']} | {row['n']} | {_fmt(row['dred_min'], 4)}–{_fmt(row['dred_max'], 4)} | {_fmt(row['mean_adjusted_epv_residual_z'])} |"
        )

    lines += [
        "",
        "## What survived and what did not",
        "",
    ]
    for item in result["interpretation"]["supports"]:
        lines.append(f"- SUPPORT: {item}")
    for item in result["interpretation"]["limits"]:
        lines.append(f"- LIMIT: {item}")
    lines += ["", "No causal or pre-break prediction claim is supported by this audit.", ""]
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--enriched", type=Path, default=Path("outputs/episodes_enriched.csv"))
    ap.add_argument("--processed", type=Path, default=Path("data/processed"))
    ap.add_argument("--raw", type=Path, default=Path("data/raw"))
    ap.add_argument("--outputs", type=Path, default=Path("outputs"))
    ap.add_argument("--report", type=Path, default=Path("docs/POST_SUBMISSION_ADVERSARIAL_AUDIT.md"))
    args = ap.parse_args()

    all_epv, primary, player_possessions = load_samples(args.enriched, args.raw)
    all_episodes = pd.read_csv(args.enriched)
    primary = add_previous_same_defender_placebo(all_episodes, primary)
    primary = add_frame_based_controls(primary, args.processed)
    primary = add_aligned_epv_outcomes(primary, player_possessions)

    result = analyze(all_epv, primary, all_episodes=all_episodes)
    args.outputs.mkdir(parents=True, exist_ok=True)
    json_path = args.outputs / "epv_adversarial_post_submission.json"
    md_path = args.outputs / "epv_adversarial_post_submission.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n")
    rendered = report_md(result)
    md_path.write_text(rendered)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(rendered)
    print(rendered)


if __name__ == "__main__":
    main()
