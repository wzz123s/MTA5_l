# -*- coding: utf-8 -*-
"""Rerun mapping after filtering duplicate-continuation prototype rows.

This is a non-destructive validation gate. It filters the previously reviewed
duplicate-continuation candidates from the Python-MT5 dynamic trade list,
recalculates the visible balance path, reruns the existing Python-vs-MT5 mapper,
and compares the result with the current stage-state baseline.

It does not rerun the signal engine or recompute dynamic lots from a changed
signal stream. Any merge candidate still needs a later signal-level rerun.
"""
from __future__ import annotations


import shutil
from pathlib import Path

import pandas as pd

import map_python_mt5_ledger_trades as mapper


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

BASE_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
BASE_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"
SUPPRESSION_DIR = VALIDATION_DIR / "stage_state_duplicate_continuation_suppression_prototype_20260716"

OUT_DIR = VALIDATION_DIR / "stage_state_duplicate_suppression_full_chain_20260717"
FILTERED_DYNAMIC_DIR = OUT_DIR / "filtered_dynamic"
FILTERED_MAPPING_DIR = OUT_DIR / "filtered_mapping"

START_BALANCE = 500.0


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index)
    values = frame[column]
    if values.dtype == bool:
        return values.fillna(False)
    return values.astype(str).str.strip().str.lower().isin({"true", "1", "yes", "y"})


def stage_sl_flags(frame: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    stage_cols = [c for c in ["stage1_exit", "stage2_exit", "stage3_exit"] if c in frame.columns]
    if not stage_cols:
        flags = pd.Series(False, index=frame.index)
        return flags, flags
    hits = [frame[col].astype(str).str.contains("SL", regex=False, na=False) for col in stage_cols]
    any_sl = hits[0].copy()
    all_sl = hits[0].copy()
    for hit in hits[1:]:
        any_sl = any_sl | hit
        all_sl = all_sl & hit
    return any_sl, all_sl


def summarize_python(source: str, frame: pd.DataFrame, source_variant: str | None = None) -> dict[str, object]:
    profit = pd.to_numeric(frame["dynamic_total_$"], errors="coerce").fillna(0.0)
    any_sl, all_sl = stage_sl_flags(frame)
    avg_stop = pd.to_numeric(frame.get("stop_pts_spec", pd.Series(dtype=float)), errors="coerce").mean()
    avg_lot = pd.to_numeric(frame.get("dynamic_total_lot", pd.Series(dtype=float)), errors="coerce").mean()
    exec_model = str(frame["exec_model"].dropna().iloc[0]) if "exec_model" in frame.columns and frame["exec_model"].notna().any() else ""
    variant = source_variant
    if variant is None and "source_variant" in frame.columns and frame["source_variant"].notna().any():
        variant = str(frame["source_variant"].dropna().iloc[0])
    return {
        "source": source,
        "trade_count": int(len(frame)),
        "final_balance": round(float(START_BALANCE + profit.sum()), 6),
        "dynamic_total_profit": round(float(profit.sum()), 6),
        "win_count": int((profit > 0).sum()),
        "win_rate_pct": round(float((profit > 0).mean() * 100), 4) if len(frame) else 0.0,
        "any_stage_sl_count": int(any_sl.sum()),
        "all_stage_sl_count": int(all_sl.sum()),
        "avg_stop_pts_spec": round(float(avg_stop), 6) if pd.notna(avg_stop) else "",
        "avg_total_lot": round(float(avg_lot), 6) if pd.notna(avg_lot) else "",
        "exec_model": exec_model,
        "source_variant": variant or "",
    }


def summarize_mt5(frame: pd.DataFrame) -> dict[str, object]:
    profit = pd.to_numeric(frame["net_profit"], errors="coerce").fillna(0.0)
    avg_stop = pd.to_numeric(frame.get("stop_pts_spec", pd.Series(dtype=float)), errors="coerce").mean()
    return {
        "source": "mt5_ledger",
        "trade_count": int(len(frame)),
        "final_balance": round(float(START_BALANCE + profit.sum()), 6),
        "dynamic_total_profit": round(float(profit.sum()), 6),
        "win_count": int((profit > 0).sum()),
        "win_rate_pct": round(float((profit > 0).mean() * 100), 4) if len(frame) else 0.0,
        "any_stage_sl_count": int(bool_series(frame, "any_sl").sum()),
        "all_stage_sl_count": int(bool_series(frame, "all_sl").sum()),
        "avg_stop_pts_spec": round(float(avg_stop), 6) if pd.notna(avg_stop) else "",
        "avg_total_lot": "",
        "exec_model": "mt5_ledger_reference",
        "source_variant": "mt5_stage_state_full_2018_20260707_20260716",
    }


def add_original_ids(frame: pd.DataFrame, source: str) -> pd.DataFrame:
    out = frame.copy()
    out["original_py_trade_id"] = [f"{source}_{i + 1:04d}" for i in range(len(out))]
    out["original_row_number_1based"] = range(1, len(out) + 1)
    return out


def recalc_balance_path(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    profit = pd.to_numeric(out["dynamic_total_$"], errors="coerce").fillna(0.0)
    cumulative_before = profit.cumsum().shift(fill_value=0.0)
    out["balance_before_original"] = out["balance_before"]
    out["balance_after_original"] = out["balance_after"]
    out["balance_before"] = (START_BALANCE + cumulative_before).round(6)
    out["balance_after"] = (START_BALANCE + profit.cumsum()).round(6)
    out["filtered_balance_path_note"] = "trade_list_filtered_balance_recalc_only"
    return out


def prepare_filtered_dynamic_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    FILTERED_DYNAMIC_DIR.mkdir(parents=True, exist_ok=True)

    suppression = read_csv(SUPPRESSION_DIR / "duplicate_suppression_candidates.csv")
    remove_ids = set(suppression["py_trade_id"].astype(str))

    python_mt5 = add_original_ids(read_csv(BASE_DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"), "python_mt5")
    python_mt5["suppression_filter_removed"] = python_mt5["original_py_trade_id"].isin(remove_ids)

    removed = python_mt5[python_mt5["suppression_filter_removed"]].copy()
    filtered = python_mt5[~python_mt5["suppression_filter_removed"]].copy()
    filtered = recalc_balance_path(filtered)

    removed = removed.merge(
        suppression,
        left_on="original_py_trade_id",
        right_on="py_trade_id",
        how="left",
        suffixes=("", "_suppression_review"),
    )

    python_only = read_csv(BASE_DYNAMIC_DIR / "python_only_dynamic_risk_trades.csv")
    mt5 = read_csv(BASE_DYNAMIC_DIR / "mt5_ledger_unique_signals.csv")

    export_csv(filtered, FILTERED_DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv")
    export_csv(python_only, FILTERED_DYNAMIC_DIR / "python_only_dynamic_risk_trades.csv")
    export_csv(mt5, FILTERED_DYNAMIC_DIR / "mt5_ledger_unique_signals.csv")
    export_csv(removed, OUT_DIR / "filtered_duplicate_suppression_removed_rows.csv")

    summary = pd.DataFrame(
        [
            summarize_python("python_only", python_only),
            summarize_python(
                "python_mt5",
                filtered,
                "stage_state_duplicate_suppression_filtered_trade_list_20260717",
            ),
            summarize_mt5(mt5),
        ]
    )
    export_csv(summary, FILTERED_DYNAMIC_DIR / "dynamic_risk_compare_summary.csv")

    overlap = pd.DataFrame(
        [
            {"source": "python_only", "shared": 0, "python_only": int(len(python_only)), "mt5_only": int(len(mt5))},
            {"source": "python_mt5", "shared": 0, "python_only": int(len(filtered)), "mt5_only": int(len(mt5))},
        ]
    )
    export_csv(overlap, FILTERED_DYNAMIC_DIR / "dynamic_risk_key_overlap_summary.csv")

    return filtered, removed, summary


def run_filtered_mapping() -> None:
    FILTERED_MAPPING_DIR.mkdir(parents=True, exist_ok=True)
    original_input_dir = mapper.INPUT_DIR
    original_out_dir = mapper.OUT_DIR
    original_load_python_trades = mapper.load_python_trades

    def load_python_trades_preserve_original_id(path: Path, source: str) -> pd.DataFrame:
        loaded = original_load_python_trades(path, source)
        if "original_py_trade_id" in loaded.columns:
            original_ids = loaded["original_py_trade_id"].astype(str)
            loaded.loc[original_ids.str.len() > 0, "py_trade_id"] = original_ids
        return loaded

    try:
        mapper.INPUT_DIR = FILTERED_DYNAMIC_DIR
        mapper.OUT_DIR = FILTERED_MAPPING_DIR
        mapper.load_python_trades = load_python_trades_preserve_original_id
        mapper.main()
    finally:
        mapper.INPUT_DIR = original_input_dir
        mapper.OUT_DIR = original_out_dir
        mapper.load_python_trades = original_load_python_trades


def source_row(frame: pd.DataFrame, source: str) -> pd.Series:
    key_col = "source" if "source" in frame.columns else "scenario"
    rows = frame[frame[key_col].astype(str) == source]
    if rows.empty:
        raise ValueError(f"missing source row: {source}")
    return rows.iloc[0]


def build_before_after_summary(filtered_dynamic_summary: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    base_dynamic = read_csv(BASE_DYNAMIC_DIR / "dynamic_risk_compare_summary.csv")
    base_mapping = read_csv(BASE_MAPPING_DIR / "unique_match_summary.csv")
    filtered_mapping = read_csv(FILTERED_MAPPING_DIR / "unique_match_summary.csv")
    first_order = read_csv(SUPPRESSION_DIR / "duplicate_suppression_before_after_summary.csv")

    current_dyn = source_row(base_dynamic, "python_mt5")
    current_mt5 = source_row(base_dynamic, "mt5_ledger")
    current_map = source_row(base_mapping, "python_mt5")
    filtered_dyn = source_row(filtered_dynamic_summary, "python_mt5")
    filtered_map = source_row(filtered_mapping, "python_mt5")
    first_order_after = source_row(first_order, "first_order_duplicate_suppression_estimate")

    def scenario_row(name: str, dyn: pd.Series, map_row: pd.Series, note: str) -> dict[str, object]:
        direct_gap = float(dyn["final_balance"]) - float(current_mt5["final_balance"])
        matched_diff = float(map_row["matched_profit_diff"])
        signal_set_gap = direct_gap - matched_diff
        return {
            "scenario": name,
            "python_trade_count": int(dyn["trade_count"] if "trade_count" in dyn else map_row["python_trades"]),
            "mt5_trade_count": int(current_mt5["trade_count"]),
            "python_final_balance": round(float(dyn["final_balance"]), 6),
            "mt5_final_balance": round(float(current_mt5["final_balance"]), 6),
            "direct_gap_py_minus_mt5": round(float(direct_gap), 6),
            "matched_unique": int(map_row["matched_unique"]),
            "reliable_tier_matched": int(map_row["reliable_tier_matched"]),
            "relaxed_tier_matched": int(map_row["relaxed_tier_matched"]),
            "python_unmatched": int(map_row["python_unmatched"]),
            "mt5_unmatched": int(map_row["mt5_unmatched"]),
            "matched_profit_diff_py_minus_mt5": round(float(matched_diff), 6),
            "signal_set_gap_py_minus_mt5": round(float(signal_set_gap), 6),
            "note": note,
        }

    rows = [
        scenario_row("current_stage_state_metadatafix", current_dyn, current_map, "current accepted stage-state metadatafix comparison"),
        {
            "scenario": "first_order_duplicate_suppression_estimate",
            "python_trade_count": int(first_order_after["python_trade_count"]),
            "mt5_trade_count": int(current_mt5["trade_count"]),
            "python_final_balance": round(float(first_order_after["python_final_balance"]), 6),
            "mt5_final_balance": round(float(first_order_after["mt5_final_balance"]), 6),
            "direct_gap_py_minus_mt5": round(float(first_order_after["direct_gap_py_minus_mt5"]), 6),
            "matched_unique": int(current_map["matched_unique"]),
            "reliable_tier_matched": int(current_map["reliable_tier_matched"]),
            "relaxed_tier_matched": int(current_map["relaxed_tier_matched"]),
            "python_unmatched": "",
            "mt5_unmatched": "",
            "matched_profit_diff_py_minus_mt5": round(float(first_order_after["matched_profit_diff_py_minus_mt5"]), 6),
            "signal_set_gap_py_minus_mt5": round(float(first_order_after["signal_set_gap_py_minus_mt5"]), 6),
            "note": "previous first-order estimate; mapping not rerun",
        },
        scenario_row(
            "filtered_trade_list_mapping_rerun",
            filtered_dyn,
            filtered_map,
            "filtered dynamic trade list plus existing unique mapper rerun; dynamic lots not signal-level recalculated",
        ),
    ]
    before_after = pd.DataFrame(rows)

    current_direct_gap = float(rows[0]["direct_gap_py_minus_mt5"])
    filtered_direct_gap = float(rows[2]["direct_gap_py_minus_mt5"])
    current_signal_gap = float(rows[0]["signal_set_gap_py_minus_mt5"])
    filtered_signal_gap = float(rows[2]["signal_set_gap_py_minus_mt5"])
    current_reliable = int(rows[0]["reliable_tier_matched"])
    filtered_reliable = int(rows[2]["reliable_tier_matched"])
    current_matched = int(rows[0]["matched_unique"])
    filtered_matched = int(rows[2]["matched_unique"])

    direct_gap_improved = abs(filtered_direct_gap) < abs(current_direct_gap)
    signal_gap_improved = abs(filtered_signal_gap) < abs(current_signal_gap)
    reliable_not_worse = filtered_reliable >= current_reliable
    matched_not_worse = filtered_matched >= current_matched
    unmatched_count_reduced = int(rows[2]["python_unmatched"]) < int(rows[0]["python_unmatched"])
    mapping_quality_improved = filtered_matched > current_matched or filtered_reliable > current_reliable

    decision = pd.DataFrame(
        [
            {
                "gate": "stage_state_duplicate_suppression_filtered_mapping_rerun",
                "removed_rows": int(rows[0]["python_trade_count"]) - int(rows[2]["python_trade_count"]),
                "current_direct_gap": round(current_direct_gap, 6),
                "filtered_direct_gap": round(filtered_direct_gap, 6),
                "direct_gap_improvement": round(current_direct_gap - filtered_direct_gap, 6),
                "current_signal_set_gap": round(current_signal_gap, 6),
                "filtered_signal_set_gap": round(filtered_signal_gap, 6),
                "signal_set_gap_improvement": round(current_signal_gap - filtered_signal_gap, 6),
                "current_matched_unique": current_matched,
                "filtered_matched_unique": filtered_matched,
                "current_reliable_tier_matched": current_reliable,
                "filtered_reliable_tier_matched": filtered_reliable,
                "direct_gap_improved": direct_gap_improved,
                "signal_set_gap_improved": signal_gap_improved,
                "reliable_not_worse": reliable_not_worse,
                "matched_not_worse": matched_not_worse,
                "unmatched_count_reduced": unmatched_count_reduced,
                "mapping_quality_improved": mapping_quality_improved,
                "signal_level_rerun_required": True,
                "merge_gate_pass": False,
                "recommended_next_action": "triage_true_no_candidate_signal_gap_before_main_signal_change",
                "decision": "diagnostic_improvement_only",
                "reason": (
                    "The filtered mapping rerun reduces the accounting gap by deleting already-sized unmatched "
                    "Python rows. Matched/reliable counts do not improve, so this is not yet proof that the "
                    "signal engine should suppress those rows."
                ),
            }
        ]
    )
    return before_after, decision


def write_report(
    filtered: pd.DataFrame,
    removed: pd.DataFrame,
    before_after: pd.DataFrame,
    decision: pd.DataFrame,
) -> None:
    current = source_row(before_after, "current_stage_state_metadatafix")
    first_order = source_row(before_after, "first_order_duplicate_suppression_estimate")
    filtered_row = source_row(before_after, "filtered_trade_list_mapping_rerun")
    decision_row = decision.iloc[0]

    report = [
        "# Stage-State Duplicate Suppression Filtered Mapping Rerun",
        "",
        "## Scope",
        "",
        "- Non-destructive validation only.",
        "- Filters the 8 duplicate-continuation candidates from the Python-MT5 dynamic trade list.",
        "- Recalculates the visible balance path and reruns the existing unique mapper.",
        "- Does not rerun signal generation or dynamic lot sizing from a changed signal stream.",
        "",
        "## Key Numbers",
        "",
        f"- Removed rows: `{int(len(removed))}`.",
        f"- Filtered Python-MT5 rows: `{int(len(filtered))}`.",
        f"- Current direct gap: `{float(current['direct_gap_py_minus_mt5']):+.6f}`.",
        f"- First-order direct gap: `{float(first_order['direct_gap_py_minus_mt5']):+.6f}`.",
        f"- Filtered mapping rerun direct gap: `{float(filtered_row['direct_gap_py_minus_mt5']):+.6f}`.",
        f"- Current signal-set gap: `{float(current['signal_set_gap_py_minus_mt5']):+.6f}`.",
        f"- Filtered mapping rerun signal-set gap: `{float(filtered_row['signal_set_gap_py_minus_mt5']):+.6f}`.",
        f"- Matched unique: `{int(current['matched_unique'])} -> {int(filtered_row['matched_unique'])}`.",
        f"- Reliable tier matched: `{int(current['reliable_tier_matched'])} -> {int(filtered_row['reliable_tier_matched'])}`.",
        f"- Python unmatched: `{int(current['python_unmatched'])} -> {int(filtered_row['python_unmatched'])}`.",
        f"- MT5 unmatched: `{int(current['mt5_unmatched'])} -> {int(filtered_row['mt5_unmatched'])}`.",
        "",
        "## Decision",
        "",
        f"- `direct_gap_improved`: `{bool(decision_row['direct_gap_improved'])}`.",
        f"- `signal_set_gap_improved`: `{bool(decision_row['signal_set_gap_improved'])}`.",
        f"- `unmatched_count_reduced`: `{bool(decision_row['unmatched_count_reduced'])}`.",
        f"- `mapping_quality_improved`: `{bool(decision_row['mapping_quality_improved'])}`.",
        f"- `merge_gate_pass`: `{bool(decision_row['merge_gate_pass'])}`.",
        f"- Decision: `{decision_row['decision']}`.",
        "",
        "The result remains diagnostic. A main signal change still requires a signal-level suppression prototype, not only a filtered trade-list rerun.",
        "",
        "## Output Files",
        "",
        "- `filtered_dynamic/python_mt5_dynamic_risk_trades.csv`",
        "- `filtered_mapping/unique_match_summary.csv`",
        "- `filtered_duplicate_suppression_removed_rows.csv`",
        "- `stage_state_duplicate_suppression_full_chain_before_after.csv`",
        "- `stage_state_duplicate_suppression_full_chain_decision.csv`",
    ]
    write_text(OUT_DIR / "stage_state_duplicate_suppression_full_chain_review.md", "\n".join(report))

    readme = [
        "# stage_state_duplicate_suppression_full_chain_20260717",
        "",
        "Filtered trade-list mapping rerun for the duplicate-continuation suppression prototype.",
        "",
        "This directory is diagnostic-only. It must not be treated as a final strategy version because dynamic lots and signal generation were not rerun from a changed signal stream.",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(readme))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    filtered, removed, filtered_dynamic_summary = prepare_filtered_dynamic_inputs()
    run_filtered_mapping()

    # Keep a copy of the mapping summary at the root for quick review.
    shutil.copyfile(
        FILTERED_MAPPING_DIR / "unique_match_summary.csv",
        OUT_DIR / "filtered_mapping_unique_match_summary.csv",
    )

    before_after, decision = build_before_after_summary(filtered_dynamic_summary)
    export_csv(before_after, OUT_DIR / "stage_state_duplicate_suppression_full_chain_before_after.csv")
    export_csv(decision, OUT_DIR / "stage_state_duplicate_suppression_full_chain_decision.csv")
    write_report(filtered, removed, before_after, decision)


if __name__ == "__main__":
    main()
