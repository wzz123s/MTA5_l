# -*- coding: utf-8 -*-
"""Prepare runtime-style Python Stage exit prototype input cases."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
STAGE_DIR = DATA_DIR / "validation" / "stage_exit_rule_alignment_shift90_close_retry_20260714"
LEDGER_DIR = DATA_DIR / "validation" / "mt5_full_close_retry_fix_20260714"
OUT_DIR = DATA_DIR / "validation" / "python_runtime_stage_exit_prototype_20260714"


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def priority(row: pd.Series) -> int:
    relation = str(row.get("exit_relation", ""))
    sign_pair = str(row.get("sign_pair", ""))
    if relation in {"py_tp_mt5_sl", "py_forced_mt5_sl", "py_cross_mt5_sl"}:
        return 1
    if sign_pair == "win->loss":
        return 1
    if relation in {"mt5_expert_close_other", "both_cross_but_price_time_may_diff"}:
        return 2
    return 3


def priority_reason(row: pd.Series) -> str:
    relation = str(row.get("exit_relation", ""))
    sign_pair = str(row.get("sign_pair", ""))
    if relation == "py_tp_mt5_sl":
        return "Python Stage1 TP but MT5 broker SL"
    if relation == "py_forced_mt5_sl":
        return "Python Stage2 forced exit but MT5 broker SL"
    if relation == "py_cross_mt5_sl":
        return "Python merged cross exit but MT5 broker SL"
    if sign_pair == "win->loss":
        return "Python win becomes MT5 loss"
    if relation == "mt5_expert_close_other":
        return "MT5 expert close where Python did not model same exit"
    if relation == "both_cross_but_price_time_may_diff":
        return "Both cross-like but price/time may differ"
    return "lower priority control case"


def required_granularity(row: pd.Series) -> str:
    stage = int(row["stage"])
    relation = str(row.get("exit_relation", ""))
    if stage in {1, 2}:
        return "MT5 tick preferred; M15/M30 approximation acceptable only as first prototype"
    if "cross" in relation:
        return "M30 cross chronology plus broker deal/SL history"
    return "M30/M15 bars plus broker deal history"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    stage_rows = pd.read_csv(STAGE_DIR / "stage_exit_rule_alignment_stage_rows.csv", encoding="utf-8-sig")
    ledger = pd.read_csv(LEDGER_DIR / "30m2H_strategy_trade_ledger.csv", encoding="utf-8-sig")

    for col in ["deal_ticket", "stage"]:
        stage_rows[col] = pd.to_numeric(stage_rows[col], errors="coerce")
        ledger[col] = pd.to_numeric(ledger[col], errors="coerce")

    ledger_keep = [
        "deal_ticket",
        "signal_anchor_time",
        "trigger_tag",
        "signal_src",
        "dir",
        "stage",
        "ticket",
        "position_id",
        "open_time",
        "signal_entry",
        "signal_stop",
        "fill_price",
        "actual_stop",
        "lots",
        "stop_pts",
        "local_exit_reason",
        "deal_reason",
        "exit_time",
        "exit_price",
        "net_profit",
        "deal_comment",
    ]
    merged = stage_rows.merge(
        ledger[[c for c in ledger_keep if c in ledger.columns]],
        on=["deal_ticket", "stage"],
        how="left",
        suffixes=("", "_ledger"),
    )

    merged["runtime_priority"] = merged.apply(priority, axis=1)
    merged["runtime_priority_reason"] = merged.apply(priority_reason, axis=1)
    merged["required_data_granularity"] = merged.apply(required_granularity, axis=1)
    merged["case_id"] = [
        f"runtime_stage_case_{i + 1:03d}" for i in range(len(merged.sort_values(["runtime_priority", "py_date", "stage"])))
    ]
    merged = merged.sort_values(["runtime_priority", "py_date", "stage"]).reset_index(drop=True)
    merged["case_id"] = [f"runtime_stage_case_{i + 1:03d}" for i in range(len(merged))]

    columns = [
        "case_id",
        "runtime_priority",
        "runtime_priority_reason",
        "required_data_granularity",
        "py_trade_id",
        "mt5_trade_id",
        "py_date",
        "signal_anchor_time",
        "mt5_aligned_time",
        "dir_norm",
        "trigger_tag",
        "signal_src",
        "py_trigger_family",
        "mt5_trigger_family",
        "py_mode_family",
        "mt5_mode_family",
        "py_variant",
        "stage",
        "ticket",
        "position_id",
        "open_time",
        "signal_entry",
        "signal_stop",
        "fill_price",
        "actual_stop",
        "stop_pts",
        "py_exit",
        "mt5_local_exit_reason",
        "mt5_deal_reason",
        "exit_time",
        "exit_price",
        "deal_comment",
        "py_stage_profit",
        "mt5_stage_profit",
        "stage_profit_diff",
        "py_stage_lot",
        "mt5_stage_lot",
        "stage_lot_ratio_py_over_mt5",
        "sign_pair",
        "exit_relation",
        "trade_profit_abs_diff",
    ]
    out = merged[[c for c in columns if c in merged.columns]].copy()

    summary = (
        out.groupby(["runtime_priority", "runtime_priority_reason", "stage", "exit_relation"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["runtime_priority", "stage", "rows"], ascending=[True, True, False])
    )

    export_csv(out, OUT_DIR / "runtime_stage_input_cases.csv")
    export_csv(summary, OUT_DIR / "runtime_stage_input_case_summary.csv")

    report = [
        "# Python Runtime-Style Stage Exit Prototype Inputs",
        "",
        "## Scope",
        "",
        "- Source: `stage_exit_rule_alignment_shift90_close_retry_20260714/stage_exit_rule_alignment_stage_rows.csv`.",
        "- MT5 ledger enrichment: `mt5_full_close_retry_fix_20260714/30m2H_strategy_trade_ledger.csv`.",
        "- Rows: one case per matched trade stage.",
        "",
        "## Summary",
        "",
        summary.to_markdown(index=False),
        "",
        "## Priority Rules",
        "",
        "- Priority 1: Python win/TP/forced/cross becomes MT5 broker SL, or sign changes from win to loss.",
        "- Priority 2: MT5 expert close or both cross-like exits with possible price/time mismatch.",
        "- Priority 3: lower-risk control cases.",
        "",
        "## Output Files",
        "",
        "- `runtime_stage_input_cases.csv`",
        "- `runtime_stage_input_case_summary.csv`",
    ]
    write_text(OUT_DIR / "runtime_stage_input_cases_report.md", "\n".join(report))

    print(summary.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
