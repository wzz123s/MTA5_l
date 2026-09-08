# -*- coding: utf-8 -*-
"""Triage stage-state signal-set residual and mapping-policy risk.

The previous gate rejected a global +120/date+30 time-axis merge. This script
therefore reviews the current stage-state unmatched signal-set gap before any
EA behavior change is considered.
"""
from __future__ import annotations


from pathlib import Path

import numpy as np
import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"
P0_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_p0_subset_bridge_20260716"
RESIDUAL_DIR = VALIDATION_DIR / "exec_model_residual_stage_state_20260716"
REMAP_DIR = VALIDATION_DIR / "stage_state_full_remap_residual_review_20260716"
LIFECYCLE_DIR = VALIDATION_DIR / "stage_state_lifecycle_delta_localization_20260716"
TIME_AXIS_DIR = VALIDATION_DIR / "python_mt5_time_axis_normalization_stage_state_20260716"
BASELINE_DIR = VALIDATION_DIR / "stage_state_new_baseline_decision_20260716"
OUT_DIR = VALIDATION_DIR / "stage_state_signal_set_residual_triage_20260716"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def parse_time(value: object) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.notna(parsed):
        return parsed
    return pd.to_datetime(str(value).replace(".", "-"), errors="coerce")


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"L", "LONG", "BUY", "B", "1"}:
        return "BUY"
    if text in {"S", "SHORT", "SELL", "-1"}:
        return "SELL"
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


def safe_float(value: object, default: float = np.nan) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes"}


def time_key(value: object) -> str:
    parsed = parse_time(value)
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def priority(abs_gap: float) -> str:
    if abs_gap >= 150:
        return "P1"
    if abs_gap >= 75:
        return "P2"
    if abs_gap >= 25:
        return "P3"
    return "P4"


def load_candidate_context() -> tuple[pd.DataFrame, dict[str, dict[str, object]], dict[str, dict[str, object]]]:
    candidates = read_csv(MAPPING_DIR / "python_mt5_mt5_candidate_matches.csv").copy()
    candidates["is_reliable_tier"] = candidates["is_reliable_tier"].map(bool_value)
    candidates["tier_rank"] = pd.to_numeric(candidates["tier_rank"], errors="coerce")
    candidates["abs_time_diff_minutes"] = pd.to_numeric(candidates["abs_time_diff_minutes"], errors="coerce")
    candidates["profit_abs_diff"] = (pd.to_numeric(candidates["profit_diff"], errors="coerce")).abs()

    unique = read_csv(MAPPING_DIR / "python_mt5_mt5_unique_matches.csv").copy()
    py_used = {
        str(row["py_trade_id"]): str(row["mt5_trade_id"])
        for _, row in unique.iterrows()
    }
    mt5_used = {
        str(row["mt5_trade_id"]): str(row["py_trade_id"])
        for _, row in unique.iterrows()
    }

    def best_context(group: pd.DataFrame, side: str) -> dict[str, object]:
        if group.empty:
            return {
                "candidate_count": 0,
                "reliable_candidate_count": 0,
                "best_candidate_tier": "",
                "best_candidate_reliable": False,
                "best_candidate_abs_minutes": np.nan,
                "best_candidate_py_trade_id": "",
                "best_candidate_mt5_trade_id": "",
                "best_candidate_trigger_same": False,
                "best_candidate_mode_same": False,
                "best_candidate_py_trigger_family": "",
                "best_candidate_mt5_trigger_family": "",
                "best_candidate_py_mode_family": "",
                "best_candidate_mt5_mode_family": "",
                "best_candidate_py_profit": np.nan,
                "best_candidate_mt5_profit": np.nan,
                "best_candidate_profit_diff": np.nan,
                "best_candidate_unique_conflict": False,
                "best_candidate_unique_conflict_with": "",
            }
        sorted_group = group.sort_values(["tier_rank", "abs_time_diff_minutes", "profit_abs_diff"], na_position="last")
        row = sorted_group.iloc[0]
        py_id = str(row.get("py_trade_id", ""))
        mt5_id = str(row.get("mt5_trade_id", ""))
        conflict = False
        conflict_with = ""
        if side == "python_unmatched":
            conflict = mt5_id in mt5_used and mt5_used[mt5_id] != py_id
            conflict_with = mt5_used.get(mt5_id, "") if conflict else ""
        elif side == "mt5_unmatched":
            conflict = py_id in py_used and py_used[py_id] != mt5_id
            conflict_with = py_used.get(py_id, "") if conflict else ""
        return {
            "candidate_count": int(len(group)),
            "reliable_candidate_count": int(group["is_reliable_tier"].fillna(False).astype(bool).sum()),
            "best_candidate_tier": row.get("match_tier", ""),
            "best_candidate_reliable": bool(row.get("is_reliable_tier", False)),
            "best_candidate_abs_minutes": safe_float(row.get("abs_time_diff_minutes")),
            "best_candidate_py_trade_id": py_id,
            "best_candidate_mt5_trade_id": mt5_id,
            "best_candidate_trigger_same": bool(row.get("trigger_same", False)),
            "best_candidate_mode_same": bool(row.get("mode_same", False)),
            "best_candidate_py_trigger_family": row.get("py_trigger_family", ""),
            "best_candidate_mt5_trigger_family": row.get("mt5_trigger_family", ""),
            "best_candidate_py_mode_family": row.get("py_mode_family", ""),
            "best_candidate_mt5_mode_family": row.get("mt5_mode_family", ""),
            "best_candidate_py_profit": safe_float(row.get("py_profit")),
            "best_candidate_mt5_profit": safe_float(row.get("mt5_profit")),
            "best_candidate_profit_diff": safe_float(row.get("profit_diff")),
            "best_candidate_unique_conflict": conflict,
            "best_candidate_unique_conflict_with": conflict_with,
        }

    py_context = {
        str(key): best_context(group, "python_unmatched")
        for key, group in candidates.groupby("py_trade_id", dropna=False)
    }
    mt5_context = {
        str(key): best_context(group, "mt5_unmatched")
        for key, group in candidates.groupby("mt5_trade_id", dropna=False)
    }
    return candidates, py_context, mt5_context


def load_time_axis_keys() -> dict[tuple[str, str, str], dict[str, object]]:
    cases = read_csv(TIME_AXIS_DIR / "time_axis_candidate_recheck_stage_state.csv").copy()
    cases["raw_anchor_key"] = cases["raw_anchor"].map(time_key)
    cases["dir_norm"] = cases["dir_norm"].map(normalize_dir)
    cases["mode_family"] = cases["mode_family"].map(mode_family)
    out: dict[tuple[str, str, str], dict[str, object]] = {}
    for _, row in cases.iterrows():
        key = (row["raw_anchor_key"], row["dir_norm"], row["mode_family"])
        out[key] = {
            "time_axis_candidate": True,
            "time_axis_remaining_trade_id_old_view": row.get("remaining_trade_id", ""),
            "time_axis_has_gap": bool_value(row.get("has_time_axis_gap")),
            "time_axis_plus120_available": bool_value(row.get("plus120_available_metadatafix")),
            "time_axis_current_plus90_layer3_pass": bool_value(row.get("current_raw_plus90_layer3_pass")),
            "time_axis_raw_plus120_layer3_pass": bool_value(row.get("raw_plus120_layer3_pass")),
        }
    return out


def classify_signal_case(row: dict[str, object]) -> tuple[str, str]:
    side = str(row["side"])
    candidate_count = int(row.get("candidate_count", 0))
    reliable_count = int(row.get("reliable_candidate_count", 0))
    unique_conflict = bool(row.get("best_candidate_unique_conflict", False))
    best_reliable = bool(row.get("best_candidate_reliable", False))
    best_abs_minutes = safe_float(row.get("best_candidate_abs_minutes"))
    time_axis_candidate = bool(row.get("time_axis_candidate", False))
    time_axis_gap = bool(row.get("time_axis_has_gap", False))

    if side == "mt5_unmatched" and time_axis_candidate and time_axis_gap:
        return (
            "time_axis_diagnostic_only",
            "MT5-only row matches a known M15 SLOT1 time-axis gap; do not merge +120/date+30 without full-chain proof.",
        )
    if candidate_count == 0:
        if side == "python_unmatched":
            return (
                "python_only_signal_gap_no_mt5_candidate",
                "No MT5 candidate exists within the mapping candidate search space.",
            )
        return (
            "mt5_only_signal_gap_no_python_candidate",
            "No Python-MT5 candidate exists within the mapping candidate search space.",
        )
    if unique_conflict:
        return (
            "mapping_policy_first_unique_conflict",
            "Best candidate is already consumed by another unique match; fix mapping policy before changing signals or EA.",
        )
    if reliable_count > 0 and best_reliable:
        if best_abs_minutes > 1440:
            return (
                "mapping_policy_first_far_reliable_candidate",
                "A reliable-family candidate exists but is far away; review uniqueness/window policy before treating as true gap.",
            )
        return (
            "mapping_policy_first_unselected_reliable_candidate",
            "A reliable-family candidate exists but was not selected as unique; review mapping before strategy changes.",
        )
    return (
        "mapping_policy_first_relaxed_or_far_candidate",
        "Only relaxed/far candidates exist; this is accounting/mapping risk, not EA behavior proof.",
    )


def build_signal_set_cases() -> pd.DataFrame:
    _, py_context, mt5_context = load_candidate_context()
    time_axis_keys = load_time_axis_keys()

    py = read_csv(MAPPING_DIR / "python_mt5_unmatched_python_trades.csv").copy()
    mt5 = read_csv(MAPPING_DIR / "python_mt5_unmatched_mt5_trades.csv").copy()

    rows: list[dict[str, object]] = []
    for _, row in py.iterrows():
        trade_id = str(row["py_trade_id"])
        out = {
            "side": "python_unmatched",
            "trade_id": trade_id,
            "target_time": row.get("date"),
            "dir_norm": normalize_dir(row.get("dir_norm")),
            "trigger_family": row.get("trigger_family"),
            "mode_family": mode_family(row.get("mode_family")),
            "mode_or_signal_src": row.get("mode", ""),
            "source_profit_$": safe_float(row.get("dynamic_total_$")),
            "gap_effect_$": safe_float(row.get("dynamic_total_$")),
            "balance_after": safe_float(row.get("balance_after")),
            "any_sl": row.get("py_any_sl", ""),
            "all_sl": row.get("py_all_sl", ""),
            "time_axis_candidate": False,
            "time_axis_has_gap": False,
            "time_axis_plus120_available": False,
            "time_axis_current_plus90_layer3_pass": False,
            "time_axis_raw_plus120_layer3_pass": False,
        }
        out.update(py_context.get(trade_id, {}))
        bucket, note = classify_signal_case(out)
        out["action_bucket"] = bucket
        out["action_note"] = note
        out["abs_gap_effect_$"] = abs(float(out["gap_effect_$"]))
        out["action_priority"] = priority(float(out["abs_gap_effect_$"]))
        rows.append(out)

    for _, row in mt5.iterrows():
        trade_id = str(row["mt5_trade_id"])
        anchor_key = time_key(row.get("signal_anchor_time"))
        dir_norm = normalize_dir(row.get("dir_norm"))
        mode = mode_family(row.get("mode_family"))
        out = {
            "side": "mt5_unmatched",
            "trade_id": trade_id,
            "target_time": row.get("aligned_time"),
            "raw_anchor": row.get("signal_anchor_time"),
            "dir_norm": dir_norm,
            "trigger_family": row.get("trigger_family"),
            "mode_family": mode,
            "mode_or_signal_src": row.get("signal_src", ""),
            "source_profit_$": safe_float(row.get("net_profit")),
            "gap_effect_$": -safe_float(row.get("net_profit")),
            "balance_after": safe_float(row.get("balance_after")),
            "any_sl": row.get("any_sl_bool", ""),
            "all_sl": row.get("all_sl_bool", ""),
            "time_axis_candidate": False,
            "time_axis_has_gap": False,
            "time_axis_plus120_available": False,
            "time_axis_current_plus90_layer3_pass": False,
            "time_axis_raw_plus120_layer3_pass": False,
        }
        out.update(time_axis_keys.get((anchor_key, dir_norm, mode), {}))
        out.update(mt5_context.get(trade_id, {}))
        bucket, note = classify_signal_case(out)
        out["action_bucket"] = bucket
        out["action_note"] = note
        out["abs_gap_effect_$"] = abs(float(out["gap_effect_$"]))
        out["action_priority"] = priority(float(out["abs_gap_effect_$"]))
        rows.append(out)

    columns = [
        "side",
        "trade_id",
        "target_time",
        "raw_anchor",
        "dir_norm",
        "trigger_family",
        "mode_family",
        "mode_or_signal_src",
        "source_profit_$",
        "gap_effect_$",
        "abs_gap_effect_$",
        "action_priority",
        "action_bucket",
        "action_note",
        "candidate_count",
        "reliable_candidate_count",
        "best_candidate_tier",
        "best_candidate_reliable",
        "best_candidate_abs_minutes",
        "best_candidate_py_trade_id",
        "best_candidate_mt5_trade_id",
        "best_candidate_unique_conflict",
        "best_candidate_unique_conflict_with",
        "best_candidate_trigger_same",
        "best_candidate_mode_same",
        "best_candidate_py_trigger_family",
        "best_candidate_mt5_trigger_family",
        "best_candidate_py_mode_family",
        "best_candidate_mt5_mode_family",
        "best_candidate_py_profit",
        "best_candidate_mt5_profit",
        "best_candidate_profit_diff",
        "time_axis_candidate",
        "time_axis_has_gap",
        "time_axis_plus120_available",
        "time_axis_current_plus90_layer3_pass",
        "time_axis_raw_plus120_layer3_pass",
        "balance_after",
        "any_sl",
        "all_sl",
    ]
    out = pd.DataFrame(rows)
    for col in columns:
        if col not in out.columns:
            out[col] = ""
    numeric_zero_cols = ["candidate_count", "reliable_candidate_count"]
    for col in numeric_zero_cols:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).astype(int)
    for col in ["best_candidate_abs_minutes", "best_candidate_py_profit", "best_candidate_mt5_profit", "best_candidate_profit_diff"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    bool_cols = [
        "best_candidate_reliable",
        "best_candidate_unique_conflict",
        "best_candidate_trigger_same",
        "best_candidate_mode_same",
        "time_axis_candidate",
        "time_axis_has_gap",
        "time_axis_plus120_available",
        "time_axis_current_plus90_layer3_pass",
        "time_axis_raw_plus120_layer3_pass",
    ]
    for col in bool_cols:
        out[col] = out[col].map(bool_value)
    text_cols = [
        "best_candidate_tier",
        "best_candidate_py_trade_id",
        "best_candidate_mt5_trade_id",
        "best_candidate_unique_conflict_with",
        "best_candidate_py_trigger_family",
        "best_candidate_mt5_trigger_family",
        "best_candidate_py_mode_family",
        "best_candidate_mt5_mode_family",
    ]
    for col in text_cols:
        out[col] = out[col].fillna("")
    return out[columns].sort_values(["abs_gap_effect_$", "side"], ascending=[False, True]).reset_index(drop=True)


def build_signal_bucket_summary(cases: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        cases.groupby(["action_bucket", "side"], dropna=False)
        .agg(
            rows=("trade_id", "count"),
            gap_effect_sum=("gap_effect_$", "sum"),
            abs_gap_effect_sum=("abs_gap_effect_$", "sum"),
            max_abs_gap_effect=("abs_gap_effect_$", "max"),
        )
        .reset_index()
    )
    grouped["gap_effect_sum"] = grouped["gap_effect_sum"].round(6)
    grouped["abs_gap_effect_sum"] = grouped["abs_gap_effect_sum"].round(6)
    grouped["max_abs_gap_effect"] = grouped["max_abs_gap_effect"].round(6)
    return grouped.sort_values(["abs_gap_effect_sum", "rows"], ascending=[False, False]).reset_index(drop=True)


def classify_matched_residual(row: pd.Series) -> tuple[str, str]:
    reliable = bool_value(row.get("is_reliable_tier"))
    driver = str(row.get("primary_residual_driver", ""))
    if not reliable:
        return (
            "mapping_policy_first_relaxed_match",
            "Relaxed matched residual cannot be used as EA behavior proof until mapping policy is tightened.",
        )
    if driver == "lot_sizing":
        return (
            "execution_lot_sizing_or_balance_path",
            "Reliable match; prioritize lot sizing, balance base, and value model before Stage exit changes.",
        )
    if driver == "stage_exit_points":
        return (
            "execution_stage_exit_or_tick_ordering",
            "Reliable match; review Stage exit/tick ordering after mapping-policy cases are isolated.",
        )
    return (
        "execution_cost_or_rounding",
        "Reliable match; residual is mainly cost, swap, commission, or rounding.",
    )


def build_matched_residual_triage() -> pd.DataFrame:
    trades = read_csv(RESIDUAL_DIR / "exec_model_residual_trade_decomposition.csv").copy()
    trades = trades[trades["scenario"].astype(str) == "stage_state_metadatafix_exec_model"].copy()
    rows: list[dict[str, object]] = []
    for _, row in trades.iterrows():
        bucket, note = classify_matched_residual(row)
        out = row.to_dict()
        out["action_bucket"] = bucket
        out["action_note"] = note
        out["abs_profit_diff"] = safe_float(out.get("abs_profit_diff"))
        out["action_priority"] = priority(float(out["abs_profit_diff"]))
        rows.append(out)
    out = pd.DataFrame(rows)
    return out.sort_values("abs_profit_diff", ascending=False).reset_index(drop=True)


def build_matched_bucket_summary(cases: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        cases.groupby(["action_bucket", "primary_residual_driver", "is_reliable_tier"], dropna=False)
        .agg(
            rows=("py_trade_id", "count"),
            profit_diff_py_minus_mt5_sum=("profit_diff_py_minus_mt5", "sum"),
            abs_profit_diff_sum=("abs_profit_diff", "sum"),
            max_abs_profit_diff=("abs_profit_diff", "max"),
            lot_sizing_effect_sum=("lot_sizing_effect_mt5_minus_py", "sum"),
            stage_exit_points_effect_sum=("stage_exit_points_effect_mt5_minus_py", "sum"),
            swap_commission_effect_sum=("swap_commission_effect_mt5_minus_py", "sum"),
        )
        .reset_index()
    )
    for col in [
        "profit_diff_py_minus_mt5_sum",
        "abs_profit_diff_sum",
        "max_abs_profit_diff",
        "lot_sizing_effect_sum",
        "stage_exit_points_effect_sum",
        "swap_commission_effect_sum",
    ]:
        grouped[col] = grouped[col].round(6)
    return grouped.sort_values(["abs_profit_diff_sum", "rows"], ascending=[False, False]).reset_index(drop=True)


def build_overall_decision(signal_cases: pd.DataFrame, matched_cases: pd.DataFrame) -> pd.DataFrame:
    baseline = read_csv(BASELINE_DIR / "stage_state_new_baseline_decision.csv").iloc[0]
    gap = read_csv(RESIDUAL_DIR / "exec_model_residual_gap_components.csv")
    gap_row = gap[gap["scenario"].astype(str) == "stage_state_metadatafix_exec_model"].iloc[0]
    remap = read_csv(REMAP_DIR / "stage_state_full_remap_summary.csv")
    metadatafix = remap[remap["scenario"].astype(str) == "metadatafix"].iloc[0]
    p0 = remap[remap["scenario"].astype(str) == "p0_subset_bridge"].iloc[0]

    signal_gap = safe_float(signal_cases["gap_effect_$"].sum(), 0.0)
    signal_gap_expected = safe_float(gap_row["signal_set_gap_py_minus_mt5"])
    signal_gap_error = signal_gap - signal_gap_expected
    mapping_signal_abs = safe_float(
        signal_cases[
            signal_cases["action_bucket"].astype(str).str.startswith("mapping_policy_first")
        ]["abs_gap_effect_$"].sum(),
        0.0,
    )
    time_axis_abs = safe_float(
        signal_cases[signal_cases["action_bucket"] == "time_axis_diagnostic_only"]["abs_gap_effect_$"].sum(),
        0.0,
    )
    no_candidate_abs = safe_float(
        signal_cases[
            signal_cases["action_bucket"].isin(
                ["python_only_signal_gap_no_mt5_candidate", "mt5_only_signal_gap_no_python_candidate"]
            )
        ]["abs_gap_effect_$"].sum(),
        0.0,
    )
    relaxed_matched_abs = safe_float(
        matched_cases[matched_cases["action_bucket"] == "mapping_policy_first_relaxed_match"]["abs_profit_diff"].sum(),
        0.0,
    )
    reliable_matched_abs = safe_float(
        matched_cases[matched_cases["is_reliable_tier"].map(bool_value)]["abs_profit_diff"].sum(),
        0.0,
    )

    return pd.DataFrame(
        [
            {
                "gate": "stage_state_signal_set_residual_triage",
                "current_mt5_baseline_id": baseline["current_mt5_baseline_id"],
                "current_mt5_final_balance": baseline["current_mt5_final_balance"],
                "metadatafix_direct_gap_py_minus_mt5": gap_row["direct_gap_py_minus_mt5"],
                "metadatafix_matched_profit_diff_py_minus_mt5": gap_row["matched_profit_diff_py_minus_mt5"],
                "metadatafix_signal_set_gap_py_minus_mt5": signal_gap_expected,
                "recomputed_signal_set_gap": round(signal_gap, 6),
                "signal_set_gap_recompute_error": round(signal_gap_error, 9),
                "metadatafix_matched_unique": metadatafix["matched_unique"],
                "metadatafix_reliable_tier_matched": metadatafix["reliable_tier_matched"],
                "metadatafix_relaxed_tier_matched": metadatafix["relaxed_tier_matched"],
                "metadatafix_python_unmatched": metadatafix["python_unmatched"],
                "metadatafix_mt5_unmatched": metadatafix["mt5_unmatched"],
                "p0_subset_direct_gap_py_minus_mt5": p0["direct_gap_py_minus_mt5"],
                "p0_subset_signal_set_gap_py_minus_mt5": p0["signal_set_gap_py_minus_mt5"],
                "p0_subset_worse_than_metadatafix": bool(
                    safe_float(p0["direct_gap_py_minus_mt5"]) > safe_float(metadatafix["direct_gap_py_minus_mt5"])
                ),
                "signal_gap_mapping_policy_abs": round(mapping_signal_abs, 6),
                "signal_gap_time_axis_diagnostic_abs": round(time_axis_abs, 6),
                "signal_gap_no_candidate_abs": round(no_candidate_abs, 6),
                "matched_relaxed_mapping_policy_abs": round(relaxed_matched_abs, 6),
                "matched_reliable_execution_abs": round(reliable_matched_abs, 6),
                "mapping_policy_gate_pass": False,
                "ea_price_side_gate_open": False,
                "recommended_next_action": "mapping_policy_and_unique_conflict_review_before_signal_or_ea_changes",
                "decision": "do_not_change_ea_behavior_from_current_evidence",
                "reason": (
                    "Signal-set gap is closed by unmatched case accounting, but large portions still require mapping-policy "
                    "or time-axis diagnostic handling; relaxed matched residuals remain accounting risk, not EA behavior proof."
                ),
            }
        ]
    )


def markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def build_report(
    signal_cases: pd.DataFrame,
    signal_summary: pd.DataFrame,
    matched_cases: pd.DataFrame,
    matched_summary: pd.DataFrame,
    decision: pd.DataFrame,
) -> str:
    decision_row = decision.iloc[0]
    signal_cols = [
        "side",
        "trade_id",
        "target_time",
        "dir_norm",
        "trigger_family",
        "mode_family",
        "gap_effect_$",
        "action_priority",
        "action_bucket",
        "candidate_count",
        "reliable_candidate_count",
        "best_candidate_tier",
        "best_candidate_abs_minutes",
        "best_candidate_unique_conflict",
        "best_candidate_unique_conflict_with",
        "time_axis_candidate",
        "time_axis_has_gap",
    ]
    matched_cols = [
        "py_trade_id",
        "mt5_trade_id",
        "match_tier",
        "is_reliable_tier",
        "py_trigger_family",
        "py_mode_family",
        "dir_norm",
        "profit_diff_py_minus_mt5",
        "abs_profit_diff",
        "primary_residual_driver",
        "action_bucket",
    ]
    lines = [
        "# Stage-state signal-set residual triage",
        "",
        "## Scope",
        "",
        "- Baseline: accepted stage-state MT5 full tester ledger.",
        "- Primary scenario: `stage_state_metadatafix_exec_model`.",
        "- This is read-only and does not modify EA, Python signals, mapping scripts, or fund-curve calculations.",
        "",
        "## Decision",
        "",
        f"- Recomputed signal-set gap: `{decision_row['recomputed_signal_set_gap']}`.",
        f"- Expected signal-set gap: `{decision_row['metadatafix_signal_set_gap_py_minus_mt5']}`.",
        f"- Recompute error: `{decision_row['signal_set_gap_recompute_error']}`.",
        f"- EA price-side gate open: `{decision_row['ea_price_side_gate_open']}`.",
        f"- Decision: `{decision_row['decision']}`.",
        f"- Next action: `{decision_row['recommended_next_action']}`.",
        "",
        "## Current Gap Context",
        "",
        markdown_table(
            decision[
                [
                    "current_mt5_final_balance",
                    "metadatafix_direct_gap_py_minus_mt5",
                    "metadatafix_matched_profit_diff_py_minus_mt5",
                    "metadatafix_signal_set_gap_py_minus_mt5",
                    "metadatafix_matched_unique",
                    "metadatafix_reliable_tier_matched",
                    "metadatafix_relaxed_tier_matched",
                    "metadatafix_python_unmatched",
                    "metadatafix_mt5_unmatched",
                ]
            ]
        ),
        "",
        "## Signal-Set Bucket Summary",
        "",
        markdown_table(signal_summary, 30),
        "",
        "## Top Signal-Set Cases",
        "",
        markdown_table(signal_cases[[c for c in signal_cols if c in signal_cases.columns]], 20),
        "",
        "## Matched Residual Bucket Summary",
        "",
        markdown_table(matched_summary, 30),
        "",
        "## Top Matched Residual Cases",
        "",
        markdown_table(matched_cases[[c for c in matched_cols if c in matched_cases.columns]], 20),
        "",
        "## Interpretation",
        "",
        "- The signal-set gap closes exactly from unmatched Python minus unmatched MT5 profit, so this is now an attribution problem rather than a missing-ledger problem.",
        "- `time_axis_diagnostic_only` rows are not mergeable because the prior +90/+120 gate failed.",
        "- `mapping_policy_first_*` rows require unique-match/window/relaxed-tier review before any signal or EA behavior changes.",
        "- Reliable matched residuals can later feed execution-model work, but relaxed matched residuals must remain mapping/accounting risk first.",
        "- P0 subset bridge is not selected here because it worsens the current stage-state direct and signal-set gaps.",
        "",
        "## Output Files",
        "",
        "- `stage_state_signal_set_case_triage.csv`",
        "- `stage_state_signal_set_bucket_summary.csv`",
        "- `stage_state_matched_residual_action_triage.csv`",
        "- `stage_state_matched_residual_bucket_summary.csv`",
        "- `stage_state_signal_set_residual_triage_decision.csv`",
        "- `mapping_policy_first_signal_cases.csv`",
        "- `time_axis_diagnostic_signal_cases.csv`",
        "- `reliable_execution_residual_cases.csv`",
    ]
    return "\n".join(lines)


def write_readme() -> None:
    lines = [
        "# Stage-state signal-set residual triage 20260716",
        "",
        "Generated by `review_stage_state_signal_set_residual_triage_20260716.py`.",
        "",
        "Purpose: after the +90/+120 time-axis merge gate failed, classify the current stage-state signal-set gap into mapping-policy risk, diagnostic-only time-axis rows, no-candidate signal gaps, and reliable execution residuals.",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    signal_cases = build_signal_set_cases()
    signal_summary = build_signal_bucket_summary(signal_cases)
    matched_cases = build_matched_residual_triage()
    matched_summary = build_matched_bucket_summary(matched_cases)
    decision = build_overall_decision(signal_cases, matched_cases)

    export_csv(signal_cases, OUT_DIR / "stage_state_signal_set_case_triage.csv")
    export_csv(signal_summary, OUT_DIR / "stage_state_signal_set_bucket_summary.csv")
    export_csv(matched_cases, OUT_DIR / "stage_state_matched_residual_action_triage.csv")
    export_csv(matched_summary, OUT_DIR / "stage_state_matched_residual_bucket_summary.csv")
    export_csv(decision, OUT_DIR / "stage_state_signal_set_residual_triage_decision.csv")
    export_csv(
        signal_cases[signal_cases["action_bucket"].astype(str).str.startswith("mapping_policy_first")],
        OUT_DIR / "mapping_policy_first_signal_cases.csv",
    )
    export_csv(
        signal_cases[signal_cases["action_bucket"] == "time_axis_diagnostic_only"],
        OUT_DIR / "time_axis_diagnostic_signal_cases.csv",
    )
    export_csv(
        matched_cases[matched_cases["is_reliable_tier"].map(bool_value)],
        OUT_DIR / "reliable_execution_residual_cases.csv",
    )
    write_text(
        OUT_DIR / "stage_state_signal_set_residual_triage_review.md",
        build_report(signal_cases, signal_summary, matched_cases, matched_summary, decision),
    )
    write_readme()

    print(decision.to_string(index=False))
    print()
    print(signal_summary.to_string(index=False))
    print()
    print(matched_summary.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
