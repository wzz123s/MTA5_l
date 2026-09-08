# -*- coding: utf-8 -*-
"""Audit outside-7d mapping/accounting windows for stage-state alignment.

This is a diagnostic-only gate. It reviews no-candidate rows whose nearest
same-direction or same-family counterpart sits outside the current 7-day
candidate window, then runs candidate-window sensitivity for 7/10/14/30 days.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

NO_CANDIDATE_DIR = VALIDATION_DIR / "stage_state_no_candidate_signal_gap_triage_20260717"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"

OUT_DIR = VALIDATION_DIR / "stage_state_outside_7d_mapping_window_audit_20260717"

EA_ALIGN_DELTA_MINUTES = 90
DAY_MINUTES = 24 * 60
WINDOW_DAYS = [7, 10, 14, 30]
WINDOW_POLICIES = ["same_family_extension", "family_plus_relaxed_extension"]

BASE_TIER_ORDER = {
    "exact_align90_all": 1,
    "nearby_60_all": 2,
    "nearby_180_all": 3,
    "nearby_1d_all": 4,
    "nearby_7d_all": 5,
    "nearby_60_trigger_relaxed": 6,
    "nearby_60_mode_relaxed": 7,
    "nearby_7d_trigger_relaxed": 8,
    "nearby_7d_mode_relaxed": 9,
    "outside_window_all": 20,
    "outside_window_trigger_relaxed": 30,
    "outside_window_mode_relaxed": 31,
    "same_dir_window_unclassified": 99,
}

RELIABLE_TIERS = {
    "exact_align90_all",
    "nearby_60_all",
    "nearby_180_all",
    "nearby_1d_all",
    "nearby_7d_all",
}

OUTSIDE_BUCKETS = {
    "outside_7d_same_family_mapping_window_review",
    "outside_7d_same_direction_mapping_window_review",
}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL", "SHORT", "-1"}:
        return "SELL"
    if text in {"L", "B", "BUY", "LONG", "1"}:
        return "BUY"
    return text


def mode_family(value: object) -> str:
    text = str(value).strip()
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return text


def safe_float(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def priority(abs_gap: float) -> str:
    if abs_gap >= 150:
        return "P1"
    if abs_gap >= 75:
        return "P2"
    if abs_gap >= 25:
        return "P3"
    return "P4"


def load_python_trades() -> pd.DataFrame:
    df = read_csv(DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv").copy()
    df["py_trade_id"] = [f"python_mt5_{i + 1:04d}" for i in range(len(df))]
    df["target_time"] = pd.to_datetime(df["date"], errors="coerce")
    df["dir_norm"] = df["dir"].map(normalize_dir)
    df["mode_family"] = df["mode_family"].map(mode_family)
    df["profit"] = pd.to_numeric(df["dynamic_total_$"], errors="coerce")
    df["py_any_sl"] = (
        df["stage1_exit"].astype(str).str.contains("SL", regex=False, na=False)
        | df["stage2_exit"].astype(str).str.contains("SL", regex=False, na=False)
        | df["stage3_exit"].astype(str).str.contains("SL", regex=False, na=False)
    )
    df["py_all_sl"] = (
        df["stage1_exit"].astype(str).str.contains("SL", regex=False, na=False)
        & df["stage2_exit"].astype(str).str.contains("SL", regex=False, na=False)
        & df["stage3_exit"].astype(str).str.contains("SL", regex=False, na=False)
    )
    return df


def load_mt5_trades() -> pd.DataFrame:
    df = read_csv(DYNAMIC_DIR / "mt5_ledger_unique_signals.csv").copy()
    df["mt5_trade_id"] = [f"mt5_{i + 1:04d}" for i in range(len(df))]
    df["signal_anchor_time"] = pd.to_datetime(df["signal_anchor_time"], errors="coerce")
    df["target_time"] = df["signal_anchor_time"] + pd.Timedelta(minutes=EA_ALIGN_DELTA_MINUTES)
    df["dir_norm"] = df["dir"].map(normalize_dir)
    df["mode_family"] = df["mode_family"].map(mode_family)
    df["profit"] = pd.to_numeric(df["net_profit"], errors="coerce")
    df["any_sl_bool"] = df["any_sl"].map(bool_value)
    df["all_sl_bool"] = df["all_sl"].map(bool_value)
    return df


def load_outside_cases() -> pd.DataFrame:
    cases = read_csv(NO_CANDIDATE_DIR / "stage_state_no_candidate_signal_gap_cases.csv").copy()
    cases = cases[cases["no_candidate_action_bucket"].astype(str).isin(OUTSIDE_BUCKETS)].copy()
    cases["target_time"] = pd.to_datetime(cases["target_time"], errors="coerce")
    cases["gap_effect_$"] = pd.to_numeric(cases["gap_effect_$"], errors="coerce").fillna(0.0)
    cases["abs_gap_effect_$"] = cases["gap_effect_$"].abs()
    cases["dir_norm"] = cases["dir_norm"].map(normalize_dir)
    cases["mode_family"] = cases["mode_family"].map(mode_family)
    return cases.sort_values("abs_gap_effect_$", ascending=False).reset_index(drop=True)


def classify_tier(abs_minutes: float, trigger_same: bool, mode_same: bool, window_days: int) -> str:
    if abs_minutes == 0 and trigger_same and mode_same:
        return "exact_align90_all"
    if abs_minutes <= 60 and trigger_same and mode_same:
        return "nearby_60_all"
    if abs_minutes <= 180 and trigger_same and mode_same:
        return "nearby_180_all"
    if abs_minutes <= DAY_MINUTES and trigger_same and mode_same:
        return "nearby_1d_all"
    if abs_minutes <= 7 * DAY_MINUTES and trigger_same and mode_same:
        return "nearby_7d_all"
    if abs_minutes <= 60 and mode_same:
        return "nearby_60_trigger_relaxed"
    if abs_minutes <= 60 and trigger_same:
        return "nearby_60_mode_relaxed"
    if abs_minutes <= 7 * DAY_MINUTES and mode_same:
        return "nearby_7d_trigger_relaxed"
    if abs_minutes <= 7 * DAY_MINUTES and trigger_same:
        return "nearby_7d_mode_relaxed"
    if abs_minutes <= window_days * DAY_MINUTES and trigger_same and mode_same:
        return "outside_window_all"
    if abs_minutes <= window_days * DAY_MINUTES and mode_same:
        return "outside_window_trigger_relaxed"
    if abs_minutes <= window_days * DAY_MINUTES and trigger_same:
        return "outside_window_mode_relaxed"
    return "same_dir_window_unclassified"


def build_candidates(py: pd.DataFrame, mt5: pd.DataFrame, window_days: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    max_minutes = window_days * DAY_MINUTES
    for _, mt5_row in mt5.iterrows():
        same_dir = py[py["dir_norm"] == mt5_row["dir_norm"]].copy()
        if same_dir.empty:
            continue
        same_dir["time_diff_minutes"] = (
            (same_dir["target_time"] - mt5_row["target_time"]).dt.total_seconds() / 60.0
        )
        same_dir["abs_time_diff_minutes"] = same_dir["time_diff_minutes"].abs()
        same_dir = same_dir[same_dir["abs_time_diff_minutes"] <= max_minutes]
        for _, py_row in same_dir.iterrows():
            trigger_same = str(py_row["trigger_family"]) == str(mt5_row["trigger_family"])
            mode_same = str(py_row["mode_family"]) == str(mt5_row["mode_family"])
            tier = classify_tier(float(py_row["abs_time_diff_minutes"]), trigger_same, mode_same, window_days)
            rows.append(
                {
                    "py_trade_id": py_row["py_trade_id"],
                    "mt5_trade_id": mt5_row["mt5_trade_id"],
                    "py_date": py_row["target_time"],
                    "mt5_signal_anchor_time": mt5_row["signal_anchor_time"],
                    "mt5_aligned_time": mt5_row["target_time"],
                    "time_diff_minutes": round(float(py_row["time_diff_minutes"]), 6),
                    "abs_time_diff_minutes": round(float(py_row["abs_time_diff_minutes"]), 6),
                    "window_days": window_days,
                    "match_tier": tier,
                    "tier_rank": BASE_TIER_ORDER[tier],
                    "is_reliable_tier": tier in RELIABLE_TIERS,
                    "is_outside_7d": float(py_row["abs_time_diff_minutes"]) > 7 * DAY_MINUTES,
                    "trigger_same": trigger_same,
                    "mode_same": mode_same,
                    "same_family": trigger_same and mode_same,
                    "dir_norm": py_row["dir_norm"],
                    "py_trigger_family": py_row["trigger_family"],
                    "mt5_trigger_family": mt5_row["trigger_family"],
                    "py_mode_family": py_row["mode_family"],
                    "mt5_mode_family": mt5_row["mode_family"],
                    "py_mode": py_row["mode"],
                    "mt5_signal_src": mt5_row["signal_src"],
                    "py_variant": py_row["variant"],
                    "py_profit": safe_float(py_row["profit"]),
                    "mt5_profit": safe_float(mt5_row["profit"]),
                    "profit_diff": round(float(safe_float(py_row["profit"]) - safe_float(mt5_row["profit"])), 6),
                    "profit_abs_diff": round(abs(float(safe_float(py_row["profit"]) - safe_float(mt5_row["profit"]))), 6),
                    "py_balance_after": safe_float(py_row.get("balance_after")),
                    "mt5_balance_after": safe_float(mt5_row.get("balance_after")),
                    "py_any_sl": bool(py_row.get("py_any_sl", False)),
                    "mt5_any_sl": bool(mt5_row.get("any_sl_bool", False)),
                    "py_all_sl": bool(py_row.get("py_all_sl", False)),
                    "mt5_all_sl": bool(mt5_row.get("all_sl_bool", False)),
                }
            )
    return pd.DataFrame(rows)


def eligible_candidates(candidates: pd.DataFrame, policy: str) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()
    out = candidates[candidates["match_tier"] != "same_dir_window_unclassified"].copy()
    if policy == "same_family_extension":
        outside_relaxed = out["is_outside_7d"] & ~out["same_family"]
        out = out[~outside_relaxed].copy()
    return out


def greedy_unique_matches(candidates: pd.DataFrame, policy: str) -> pd.DataFrame:
    eligible = eligible_candidates(candidates, policy)
    if eligible.empty:
        return pd.DataFrame(columns=candidates.columns)
    eligible = eligible.sort_values(
        ["tier_rank", "abs_time_diff_minutes", "profit_abs_diff", "py_trade_id", "mt5_trade_id"],
        ascending=[True, True, True, True, True],
    )
    used_py: set[str] = set()
    used_mt5: set[str] = set()
    selected_rows: list[pd.Series] = []
    for _, row in eligible.iterrows():
        py_id = str(row["py_trade_id"])
        mt5_id = str(row["mt5_trade_id"])
        if py_id in used_py or mt5_id in used_mt5:
            continue
        selected_rows.append(row)
        used_py.add(py_id)
        used_mt5.add(mt5_id)
    if not selected_rows:
        return pd.DataFrame(columns=eligible.columns)
    return pd.DataFrame(selected_rows).reset_index(drop=True)


def summarize_matches(
    matches: pd.DataFrame,
    py_count: int,
    mt5_count: int,
    window_days: int,
    policy: str,
    current_summary: pd.Series,
    outside_cases: pd.DataFrame,
) -> dict[str, object]:
    if matches.empty:
        matched = 0
        reliable = 0
        matched_diff = 0.0
        outside_matches = pd.DataFrame(columns=matches.columns)
    else:
        matched = int(len(matches))
        reliable = int(matches["is_reliable_tier"].fillna(False).astype(bool).sum())
        matched_diff = float(pd.to_numeric(matches["profit_diff"], errors="coerce").sum())
        outside_matches = matches[matches["is_outside_7d"].fillna(False).astype(bool)].copy()

    current_matched = int(current_summary["matched_unique"])
    current_reliable = int(current_summary["reliable_tier_matched"])
    current_diff = float(current_summary["matched_profit_diff"])

    py_outside_ids = set(outside_cases.loc[outside_cases["side"] == "python_unmatched", "trade_id"].astype(str))
    mt5_outside_ids = set(outside_cases.loc[outside_cases["side"] == "mt5_unmatched", "trade_id"].astype(str))
    resolved_py = set(outside_matches.get("py_trade_id", pd.Series(dtype=str)).astype(str)) & py_outside_ids
    resolved_mt5 = set(outside_matches.get("mt5_trade_id", pd.Series(dtype=str)).astype(str)) & mt5_outside_ids

    outside_same_family = (
        int((outside_matches["same_family"].fillna(False)).sum()) if not outside_matches.empty else 0
    )
    outside_relaxed = int(len(outside_matches) - outside_same_family)
    max_outside_minutes = (
        round(float(outside_matches["abs_time_diff_minutes"].max()), 6) if not outside_matches.empty else ""
    )
    avg_outside_minutes = (
        round(float(outside_matches["abs_time_diff_minutes"].mean()), 6) if not outside_matches.empty else ""
    )
    outside_profit_diff_sum = (
        round(float(pd.to_numeric(outside_matches["profit_diff"], errors="coerce").sum()), 6)
        if not outside_matches.empty
        else 0.0
    )
    return {
        "window_days": window_days,
        "policy": policy,
        "python_trades": py_count,
        "mt5_trades": mt5_count,
        "matched_unique": matched,
        "matched_unique_delta_vs_current": matched - current_matched,
        "reliable_tier_matched": reliable,
        "reliable_delta_vs_current": reliable - current_reliable,
        "relaxed_or_diagnostic_matched": matched - reliable,
        "python_unmatched": py_count - int(matches["py_trade_id"].nunique()) if not matches.empty else py_count,
        "mt5_unmatched": mt5_count - int(matches["mt5_trade_id"].nunique()) if not matches.empty else mt5_count,
        "matched_profit_diff": round(matched_diff, 6),
        "matched_profit_diff_delta_vs_current": round(matched_diff - current_diff, 6),
        "outside_7d_unique_matches": int(len(outside_matches)),
        "outside_7d_same_family_matches": outside_same_family,
        "outside_7d_relaxed_matches": outside_relaxed,
        "outside_7d_profit_diff_sum": outside_profit_diff_sum,
        "outside_7d_max_abs_minutes": max_outside_minutes,
        "outside_7d_avg_abs_minutes": avg_outside_minutes,
        "outside_case_rows_resolved": len(resolved_py) + len(resolved_mt5),
        "outside_python_cases_resolved": len(resolved_py),
        "outside_mt5_cases_resolved": len(resolved_mt5),
        "risk_far_over_14d_matches": int((outside_matches["abs_time_diff_minutes"] > 14 * DAY_MINUTES).sum())
        if not outside_matches.empty
        else 0,
        "risk_relaxed_outside_matches": outside_relaxed,
        "merge_gate_pass": False,
    }


def current_match_maps() -> tuple[pd.DataFrame, dict[str, str], dict[str, str], pd.Series]:
    unique = read_csv(MAPPING_DIR / "python_mt5_mt5_unique_matches.csv").copy()
    py_to_mt5 = {str(row["py_trade_id"]): str(row["mt5_trade_id"]) for _, row in unique.iterrows()}
    mt5_to_py = {str(row["mt5_trade_id"]): str(row["py_trade_id"]) for _, row in unique.iterrows()}
    summary = read_csv(MAPPING_DIR / "unique_match_summary.csv")
    current = summary[summary["source"].astype(str) == "python_mt5"].iloc[0]
    return unique, py_to_mt5, mt5_to_py, current


def nearest_pair(
    case: pd.Series,
    py: pd.DataFrame,
    mt5: pd.DataFrame,
    py_to_mt5: dict[str, str],
    mt5_to_py: dict[str, str],
) -> dict[str, object]:
    side = str(case["side"])
    target_time = pd.to_datetime(case["target_time"], errors="coerce")
    case_dir = str(case["dir_norm"])
    trigger = str(case["trigger_family"])
    mode = str(case["mode_family"])
    if side == "python_unmatched":
        other = mt5[mt5["dir_norm"] == case_dir].copy()
        owner_map = mt5_to_py
        own = py[py["py_trade_id"].astype(str) == str(case["trade_id"])].iloc[0]
    else:
        other = py[py["dir_norm"] == case_dir].copy()
        owner_map = py_to_mt5
        own = mt5[mt5["mt5_trade_id"].astype(str) == str(case["trade_id"])].iloc[0]
    other["time_diff_minutes"] = (other["target_time"] - target_time).dt.total_seconds() / 60.0
    other["abs_time_diff_minutes"] = other["time_diff_minutes"].abs()
    other = other[pd.notna(other["abs_time_diff_minutes"])]
    other_30d = other[other["abs_time_diff_minutes"] <= 30 * DAY_MINUTES].copy()
    same_family = other[
        (other["trigger_family"].astype(str) == trigger)
        & (other["mode_family"].astype(str) == mode)
    ].copy()
    same_family_30d = same_family[same_family["abs_time_diff_minutes"] <= 30 * DAY_MINUTES].copy()
    nearest_same_dir = (
        other_30d.sort_values("abs_time_diff_minutes").iloc[0]
        if not other_30d.empty
        else pd.Series(dtype=object)
    )
    nearest_same_family = (
        same_family_30d.sort_values("abs_time_diff_minutes").iloc[0]
        if not same_family_30d.empty
        else pd.Series(dtype=object)
    )

    chosen = nearest_same_family if not nearest_same_family.empty else nearest_same_dir
    candidate_id_col = "mt5_trade_id" if side == "python_unmatched" else "py_trade_id"
    candidate_id = str(chosen.get(candidate_id_col, "")) if not chosen.empty else ""
    occupied_by = owner_map.get(candidate_id, "")
    occupied = bool(occupied_by)
    trigger_same = str(chosen.get("trigger_family", "")) == trigger if not chosen.empty else False
    mode_same = str(chosen.get("mode_family", "")) == mode if not chosen.empty else False
    abs_minutes = safe_float(chosen.get("abs_time_diff_minutes"), default=10**12) if not chosen.empty else 10**12
    window_needed_days = int((abs_minutes + DAY_MINUTES - 1) // DAY_MINUTES) if abs_minutes < 10**11 else ""

    if side == "python_unmatched":
        py_profit = safe_float(own.get("profit"))
        mt5_profit = safe_float(chosen.get("profit"))
    else:
        py_profit = safe_float(chosen.get("profit"))
        mt5_profit = safe_float(own.get("profit"))
    profit_diff = py_profit - mt5_profit

    if chosen.empty:
        review_bucket = "outside_no_same_direction_candidate_30d"
        note = "No same-direction counterpart found in the audit search frame."
    elif not trigger_same and not mode_same:
        review_bucket = "outside_same_direction_not_same_family_do_not_map"
        note = "Nearest same-direction counterpart does not share trigger or mode; keep as accounting/window diagnostic."
    elif occupied:
        review_bucket = "outside_candidate_already_occupied_accounting_only"
        note = "Nearest outside-window counterpart is already consumed by a current unique match."
    elif trigger_same and mode_same:
        review_bucket = "outside_same_family_window_sensitivity_candidate"
        note = "Same trigger/mode counterpart exists outside 7 days and is not currently occupied; window sensitivity only."
    else:
        review_bucket = "outside_relaxed_family_window_risk"
        note = "Only trigger/mode relaxed counterpart exists outside 7 days; high risk for false mapping."

    return {
        "selected_candidate_trade_id": candidate_id,
        "selected_candidate_side": "mt5" if side == "python_unmatched" else "python",
        "selected_candidate_abs_minutes": round(abs_minutes, 6) if abs_minutes < 10**11 else "",
        "selected_candidate_signed_minutes": round(safe_float(chosen.get("time_diff_minutes")), 6) if not chosen.empty else "",
        "selected_candidate_window_needed_days": window_needed_days,
        "selected_candidate_trigger_same": trigger_same,
        "selected_candidate_mode_same": mode_same,
        "selected_candidate_same_family": trigger_same and mode_same,
        "selected_candidate_trigger_family": chosen.get("trigger_family", "") if not chosen.empty else "",
        "selected_candidate_mode_family": chosen.get("mode_family", "") if not chosen.empty else "",
        "selected_candidate_signal_or_mode": chosen.get("signal_src", chosen.get("mode", "")) if not chosen.empty else "",
        "selected_candidate_profit": round(safe_float(chosen.get("profit")), 6) if not chosen.empty else "",
        "pair_py_profit": round(py_profit, 6),
        "pair_mt5_profit": round(mt5_profit, 6),
        "pair_profit_diff_py_minus_mt5": round(float(profit_diff), 6),
        "selected_candidate_currently_occupied": occupied,
        "selected_candidate_occupied_by": occupied_by,
        "case_review_bucket": review_bucket,
        "case_review_priority": priority(safe_float(case.get("abs_gap_effect_$"))),
        "case_review_note": note,
    }


def build_case_review(
    cases: pd.DataFrame,
    py: pd.DataFrame,
    mt5: pd.DataFrame,
    py_to_mt5: dict[str, str],
    mt5_to_py: dict[str, str],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, case in cases.iterrows():
        row = case.to_dict()
        row.update(nearest_pair(case, py, mt5, py_to_mt5, mt5_to_py))
        rows.append(row)
    out = pd.DataFrame(rows)
    return out.sort_values(["abs_gap_effect_$", "trade_id"], ascending=[False, True]).reset_index(drop=True)


def summarize_case_review(cases: pd.DataFrame) -> pd.DataFrame:
    rows = []
    grouped = cases.groupby(["case_review_bucket", "side"], dropna=False)
    for (bucket, side), grp in grouped:
        rows.append(
            {
                "case_review_bucket": bucket,
                "side": side,
                "rows": int(len(grp)),
                "gap_effect_sum": round(float(grp["gap_effect_$"].sum()), 6),
                "abs_gap_effect_sum": round(float(grp["abs_gap_effect_$"].sum()), 6),
                "p1_rows": int((grp["case_review_priority"] == "P1").sum()),
                "occupied_candidate_rows": int(grp["selected_candidate_currently_occupied"].fillna(False).astype(bool).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("abs_gap_effect_sum", ascending=False)


def build_window_sensitivity(
    py: pd.DataFrame,
    mt5: pd.DataFrame,
    current_summary: pd.Series,
    outside_cases: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    summary_rows: list[dict[str, object]] = []
    candidate_rows: list[pd.DataFrame] = []
    added_rows: list[pd.DataFrame] = []

    for window_days in WINDOW_DAYS:
        candidates = build_candidates(py, mt5, window_days)
        if not candidates.empty:
            tier_counts = (
                candidates.groupby(["window_days", "match_tier", "is_outside_7d", "same_family"], dropna=False)
                .size()
                .reset_index(name="candidate_pairs")
            )
            candidate_rows.append(tier_counts)
        for policy in WINDOW_POLICIES:
            matches = greedy_unique_matches(candidates, policy)
            summary_rows.append(
                summarize_matches(
                    matches,
                    len(py),
                    len(mt5),
                    window_days,
                    policy,
                    current_summary,
                    outside_cases,
                )
            )
            if not matches.empty:
                added = matches[matches["is_outside_7d"].fillna(False).astype(bool)].copy()
                if not added.empty:
                    added["policy"] = policy
                    added["window_days"] = window_days
                    added_rows.append(added)

    summary = pd.DataFrame(summary_rows)
    candidates_summary = (
        pd.concat(candidate_rows, ignore_index=True)
        if candidate_rows
        else pd.DataFrame(columns=["window_days", "match_tier", "is_outside_7d", "same_family", "candidate_pairs"])
    )
    added_matches = pd.concat(added_rows, ignore_index=True) if added_rows else pd.DataFrame()
    return summary, candidates_summary, added_matches


def build_decision(
    case_review: pd.DataFrame,
    case_summary: pd.DataFrame,
    window_summary: pd.DataFrame,
) -> pd.DataFrame:
    outside_gap = float(case_review["gap_effect_$"].sum())
    outside_abs = float(case_review["abs_gap_effect_$"].sum())
    p1_rows = int((case_review["case_review_priority"] == "P1").sum())
    missing_p1_context = int(
        (
            (case_review["case_review_priority"] == "P1")
            & (case_review["selected_candidate_trade_id"].astype(str).str.len() == 0)
        ).sum()
    )
    best_family = window_summary[
        (window_summary["policy"] == "same_family_extension")
        & (window_summary["window_days"] > 7)
    ].sort_values(["outside_case_rows_resolved", "risk_far_over_14d_matches"], ascending=[False, True])
    best_family_row = best_family.iloc[0] if not best_family.empty else pd.Series(dtype=object)
    best_relaxed = window_summary[
        (window_summary["policy"] == "family_plus_relaxed_extension")
        & (window_summary["window_days"] > 7)
    ].sort_values(["outside_case_rows_resolved", "risk_relaxed_outside_matches"], ascending=[False, True])
    best_relaxed_row = best_relaxed.iloc[0] if not best_relaxed.empty else pd.Series(dtype=object)

    family_resolved = int(best_family_row.get("outside_case_rows_resolved", 0)) if not best_family_row.empty else 0
    relaxed_resolved = int(best_relaxed_row.get("outside_case_rows_resolved", 0)) if not best_relaxed_row.empty else 0
    relaxed_risk = int(best_relaxed_row.get("risk_relaxed_outside_matches", 0)) if not best_relaxed_row.empty else 0
    family_far_over_14 = int(best_family_row.get("risk_far_over_14d_matches", 0)) if not best_family_row.empty else 0

    mapping_window_rule_gate_pass = (
        family_resolved > 0
        and family_far_over_14 == 0
        and missing_p1_context == 0
        and int(best_family_row.get("reliable_delta_vs_current", 0)) > 0
    )
    # Outside-window matches are intentionally not counted as reliable, so this
    # gate should normally remain false. Keep the expression explicit for audit.
    mapping_window_rule_gate_pass = False if family_resolved > 0 else mapping_window_rule_gate_pass

    recommended = "keep_outside_7d_accounting_only_then_signal_level_replay"
    if family_resolved > 0 and relaxed_risk > family_resolved:
        recommended = "do_not_expand_window_globally_review_targeted_signal_replay"
    elif family_resolved > 0:
        recommended = "targeted_outside_family_replay_diagnostic_only"

    return pd.DataFrame(
        [
            {
                "gate": "stage_state_outside_7d_mapping_accounting_window_audit",
                "reviewed_rows": int(len(case_review)),
                "outside_gap_effect_sum": round(outside_gap, 6),
                "outside_abs_gap_effect_sum": round(outside_abs, 6),
                "p1_rows": p1_rows,
                "missing_p1_candidate_context": missing_p1_context,
                "best_same_family_window_days": int(best_family_row.get("window_days", 0)) if not best_family_row.empty else "",
                "best_same_family_outside_case_rows_resolved": family_resolved,
                "best_same_family_outside_unique_matches": int(best_family_row.get("outside_7d_unique_matches", 0)) if not best_family_row.empty else 0,
                "best_same_family_matched_delta": int(best_family_row.get("matched_unique_delta_vs_current", 0)) if not best_family_row.empty else 0,
                "best_same_family_profit_diff_delta": round(float(best_family_row.get("matched_profit_diff_delta_vs_current", 0.0)), 6) if not best_family_row.empty else 0.0,
                "best_relaxed_window_days": int(best_relaxed_row.get("window_days", 0)) if not best_relaxed_row.empty else "",
                "best_relaxed_outside_case_rows_resolved": relaxed_resolved,
                "best_relaxed_outside_unique_matches": int(best_relaxed_row.get("outside_7d_unique_matches", 0)) if not best_relaxed_row.empty else 0,
                "best_relaxed_risk_outside_relaxed_matches": relaxed_risk,
                "mapping_window_rule_gate_pass": mapping_window_rule_gate_pass,
                "main_mapping_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "signal_level_replay_required": True,
                "merge_gate_pass": False,
                "recommended_next_action": recommended,
                "decision": "diagnostic_only_keep_7d_mapping_rule",
                "reason": (
                    "Outside-7d candidates explain accounting residual but remain too far to count as reliable/shared. "
                    "Window expansion is diagnostic-only and should be followed by targeted signal-level replay."
                ),
            }
        ]
    )


def simple_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows_"
    return frame.to_markdown(index=False)


def write_report(
    case_review: pd.DataFrame,
    case_summary: pd.DataFrame,
    window_summary: pd.DataFrame,
    candidate_summary: pd.DataFrame,
    added_matches: pd.DataFrame,
    decision: pd.DataFrame,
) -> None:
    d = decision.iloc[0]
    top_cases = case_review.head(8)[
        [
            "side",
            "trade_id",
            "target_time",
            "dir_norm",
            "trigger_family",
            "mode_family",
            "gap_effect_$",
            "selected_candidate_trade_id",
            "selected_candidate_abs_minutes",
            "selected_candidate_same_family",
            "selected_candidate_currently_occupied",
            "case_review_bucket",
        ]
    ]
    key_windows = window_summary[
        (window_summary["window_days"].isin([7, 10, 14, 30]))
        & (window_summary["policy"].isin(WINDOW_POLICIES))
    ]
    top_added = (
        added_matches.sort_values(["window_days", "policy", "abs_time_diff_minutes"]).head(12)
        if not added_matches.empty
        else pd.DataFrame()
    )
    if not top_added.empty:
        top_added = top_added[
            [
                "window_days",
                "policy",
                "py_trade_id",
                "mt5_trade_id",
                "match_tier",
                "abs_time_diff_minutes",
                "same_family",
                "py_profit",
                "mt5_profit",
                "profit_diff",
            ]
        ]

    report = [
        "# Stage-State Outside-7d Mapping/Accounting Window Audit",
        "",
        "## Scope",
        "",
        "- Reviews only outside-7d no-candidate rows from the previous triage.",
        "- Runs 7/10/14/30-day candidate-window sensitivity for diagnostic comparison.",
        "- Does not change the current 7-day mapper, Python signals, dynamic risk, or EA behavior.",
        "",
        "## Closure",
        "",
        f"- Reviewed rows: `{int(d['reviewed_rows'])}`.",
        f"- Outside gap effect sum: `{float(d['outside_gap_effect_sum']):+.6f}`.",
        f"- Outside abs gap effect sum: `{float(d['outside_abs_gap_effect_sum']):.6f}`.",
        f"- P1 rows: `{int(d['p1_rows'])}`.",
        f"- Missing P1 candidate context: `{int(d['missing_p1_candidate_context'])}`.",
        "",
        "## Case Bucket Summary",
        "",
        simple_table(case_summary),
        "",
        "## Window Sensitivity",
        "",
        simple_table(key_windows),
        "",
        "## Top Outside Cases",
        "",
        simple_table(top_cases),
        "",
        "## Added Outside-Window Matches",
        "",
        simple_table(top_added),
        "",
        "## Decision",
        "",
        f"- `mapping_window_rule_gate_pass`: `{bool_value(d['mapping_window_rule_gate_pass'])}`.",
        f"- `main_mapping_change_gate_open`: `{bool_value(d['main_mapping_change_gate_open'])}`.",
        f"- `ea_behavior_gate_open`: `{bool_value(d['ea_behavior_gate_open'])}`.",
        f"- `signal_level_replay_required`: `{bool_value(d['signal_level_replay_required'])}`.",
        f"- `merge_gate_pass`: `{bool_value(d['merge_gate_pass'])}`.",
        f"- Recommended next action: `{d['recommended_next_action']}`.",
        "",
        "The 7-day rule remains the accepted mapping rule. Outside-window pairs are accounting diagnostics until a targeted signal-level replay proves a real construction issue.",
        "",
        "## Output Files",
        "",
        "- `outside_7d_mapping_window_case_review.csv`",
        "- `outside_7d_mapping_window_case_summary.csv`",
        "- `outside_7d_window_candidate_summary.csv`",
        "- `outside_7d_window_sensitivity_summary.csv`",
        "- `outside_7d_window_added_matches.csv`",
        "- `outside_7d_mapping_window_decision.csv`",
    ]
    write_text(OUT_DIR / "outside_7d_mapping_window_audit_review.md", "\n".join(report))

    readme = [
        "# stage_state_outside_7d_mapping_window_audit_20260717",
        "",
        "Diagnostic audit for outside-7d mapping/accounting window cases.",
        "",
        "This output does not change the accepted mapper or strategy logic.",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(readme))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    py = load_python_trades()
    mt5 = load_mt5_trades()
    outside_cases = load_outside_cases()
    _, py_to_mt5, mt5_to_py, current_summary = current_match_maps()

    case_review = build_case_review(outside_cases, py, mt5, py_to_mt5, mt5_to_py)
    case_summary = summarize_case_review(case_review)
    window_summary, candidate_summary, added_matches = build_window_sensitivity(py, mt5, current_summary, outside_cases)
    decision = build_decision(case_review, case_summary, window_summary)

    export_csv(case_review, OUT_DIR / "outside_7d_mapping_window_case_review.csv")
    export_csv(case_summary, OUT_DIR / "outside_7d_mapping_window_case_summary.csv")
    export_csv(candidate_summary, OUT_DIR / "outside_7d_window_candidate_summary.csv")
    export_csv(window_summary, OUT_DIR / "outside_7d_window_sensitivity_summary.csv")
    export_csv(added_matches, OUT_DIR / "outside_7d_window_added_matches.csv")
    export_csv(decision, OUT_DIR / "outside_7d_mapping_window_decision.csv")
    write_report(case_review, case_summary, window_summary, candidate_summary, added_matches, decision)


if __name__ == "__main__":
    main()
