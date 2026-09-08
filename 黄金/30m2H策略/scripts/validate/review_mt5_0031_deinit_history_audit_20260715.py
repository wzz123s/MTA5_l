# -*- coding: utf-8 -*-
"""Audit mt5_0031 Stage1 deinit_history / missed close anomaly."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = ROOT / "黄金" / "30m2H策略"
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
AUTO_TRADE_DIR = ROOT / "auto_trade"

LEDGER_DIR = VALIDATION_DIR / "mt5_full_close_retry_fix_20260714"
RESIDUAL_DIR = VALIDATION_DIR / "exec_model_residual_pnl_decomposition_20260715"
EXEC_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_metadatafix_20260715"
EXEC_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_metadatafix_20260715"
RAW_M30 = STRATEGY_DIR / "data" / "raw" / "XAUUSDm30.csv"
OUT_DIR = VALIDATION_DIR / "mt5_0031_deinit_history_audit_20260715"

TARGET_PY_ID = "python_mt5_0039"
TARGET_MT5_ID = "mt5_0031"
TARGET_POSITION_IDS = {"182", "183", "184"}
TARGET_ANCHOR = pd.Timestamp("2022-11-08 16:30:00")


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def read_csv_fallback(path: Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "gbk", "gb18030"):
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return pd.read_csv(path, low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def markdown_table(frame: pd.DataFrame, max_rows: int = 30) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def to_dt(value: object) -> pd.Timestamp:
    text = str(value).strip()
    if not text:
        return pd.NaT
    return pd.to_datetime(text.replace(".", "-"), errors="coerce")


def num(value: object, default: float = 0.0) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(out):
        return default
    return float(out)


def load_target_ledger() -> pd.DataFrame:
    ledger = read_csv(LEDGER_DIR / "30m2H_strategy_trade_ledger.csv")
    ledger["_anchor_dt"] = ledger["signal_anchor_time"].map(to_dt)
    out = ledger[(ledger["_anchor_dt"] == TARGET_ANCHOR) & (ledger["signal_src"].astype(str).str.contains("post_n5"))].copy()
    out["stage_num"] = pd.to_numeric(out["stage"], errors="coerce").astype("Int64")
    return out.sort_values("stage_num").reset_index(drop=True)


def load_target_deals() -> pd.DataFrame:
    deals = read_csv(LEDGER_DIR / "30m2H_strategy_deal_history.csv")
    out = deals[deals["position_id"].astype(str).isin(TARGET_POSITION_IDS)].copy()
    out["_time_dt"] = out["time"].map(to_dt)
    return out.sort_values(["_time_dt", "deal_ticket"]).reset_index(drop=True)


def load_python_context() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    mapping = read_csv(EXEC_MAPPING_DIR / "python_mt5_mt5_unique_matches.csv")
    mapping = mapping[(mapping["py_trade_id"] == TARGET_PY_ID) | (mapping["mt5_trade_id"] == TARGET_MT5_ID)].copy()
    dynamic = read_csv(EXEC_DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv")
    py_idx = int(TARGET_PY_ID.rsplit("_", 1)[1]) - 1
    py_row = dynamic.iloc[[py_idx]].copy()
    residual_stage = read_csv(RESIDUAL_DIR / "exec_model_residual_stage_decomposition.csv")
    residual_stage = residual_stage[
        (residual_stage["py_trade_id"] == TARGET_PY_ID) | (residual_stage["mt5_trade_id"] == TARGET_MT5_ID)
    ].copy()
    return mapping, py_row, residual_stage


def load_signal_window(open_time: pd.Timestamp, end_time: pd.Timestamp) -> pd.DataFrame:
    signals = read_csv(LEDGER_DIR / "30m2H_strategy_signals_export.csv")
    signals["_bar_dt"] = signals["bar_time"].map(to_dt)
    window = signals[(signals["_bar_dt"] >= open_time.floor("D")) & (signals["_bar_dt"] <= end_time)].copy()
    keep = [
        "bar_time",
        "close",
        "m30_sma5",
        "m30_sma13",
        "m30_cross",
        "h2_close",
        "h2_sma5",
        "h2_sma13",
        "h2_sma55",
        "h2_dist_pct",
        "h2_dir",
        "h2_cross",
        "decision",
        "skip_reason",
    ]
    return window[[c for c in keep if c in window.columns]].reset_index(drop=True)


def load_raw_m30_touch_matrix(stage1: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = read_csv_fallback(RAW_M30)
    raw = raw.rename(
        columns={
            "交易日期": "time",
            "开盘价": "open",
            "最高价": "high",
            "最低价": "low",
            "收盘价": "close",
            "成交量": "volume",
            "点差": "spread",
            "股票代码": "symbol",
        }
    )
    raw["time"] = pd.to_datetime(raw["time"], errors="coerce")
    for col in ["open", "high", "low", "close"]:
        raw[col] = pd.to_numeric(raw[col], errors="coerce")

    open_time = to_dt(stage1["open_time"])
    exit_time = to_dt(stage1["exit_time"])
    entry = num(stage1["fill_price"])
    stop = num(stage1["actual_stop"])
    direction = str(stage1["dir"]).upper()
    r = abs(entry - stop)
    tp_2r = entry + 2.0 * r if direction == "BUY" else entry - 2.0 * r
    sl_price = stop

    window = raw[(raw["time"] >= open_time.floor("30min")) & (raw["time"] <= min(exit_time, open_time + pd.Timedelta(days=60)))].copy()
    if direction == "BUY":
        window["tp_2r_touched"] = window["high"] >= tp_2r
        window["sl_touched"] = window["low"] <= sl_price
        window["close_beyond_tp_2r"] = window["close"] >= tp_2r
    else:
        window["tp_2r_touched"] = window["low"] <= tp_2r
        window["sl_touched"] = window["high"] >= sl_price
        window["close_beyond_tp_2r"] = window["close"] <= tp_2r

    first_tp = window[window["tp_2r_touched"]].head(1)
    first_sl = window[window["sl_touched"]].head(1)
    first_close_tp = window[window["close_beyond_tp_2r"]].head(1)
    touch_summary = pd.DataFrame(
        [
            {
                "entry": entry,
                "stop": stop,
                "R": r,
                "tp_2r": tp_2r,
                "stage1_open_time": open_time,
                "stage1_deinit_exit_time": exit_time,
                "first_tp_touch_time": first_tp["time"].iloc[0] if not first_tp.empty else pd.NaT,
                "first_tp_touch_high": first_tp["high"].iloc[0] if not first_tp.empty else "",
                "first_sl_touch_time": first_sl["time"].iloc[0] if not first_sl.empty else pd.NaT,
                "first_sl_touch_low": first_sl["low"].iloc[0] if not first_sl.empty else "",
                "first_close_beyond_tp_time": first_close_tp["time"].iloc[0] if not first_close_tp.empty else pd.NaT,
                "bars_to_first_tp_touch": int(window.index.get_loc(first_tp.index[0])) if not first_tp.empty else "",
            }
        ]
    )
    cols = ["time", "open", "high", "low", "close", "tp_2r_touched", "sl_touched", "close_beyond_tp_2r"]
    return touch_summary, window[cols].head(240)


def load_next_stage1_opens(open_time: pd.Timestamp, first_tp_time: pd.Timestamp) -> pd.DataFrame:
    deals = read_csv(LEDGER_DIR / "30m2H_strategy_deal_history.csv")
    deals["_time_dt"] = deals["time"].map(to_dt)
    stage1_ins = deals[
        (pd.to_numeric(deals["stage"], errors="coerce") == 1)
        & (deals["deal_entry"].astype(str) == "IN")
        & (deals["_time_dt"] > open_time)
    ].copy()
    stage1_ins["before_first_tp_touch"] = stage1_ins["_time_dt"] < first_tp_time if pd.notna(first_tp_time) else False
    keep = ["deal_ticket", "position_id", "time", "magic", "stage", "deal_entry", "deal_type", "volume", "price", "comment", "before_first_tp_touch"]
    return stage1_ins[keep].head(20).reset_index(drop=True)


def code_evidence() -> pd.DataFrame:
    path = AUTO_TRADE_DIR / "30m2H_Strategy_EA.mq5"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    ranges = [
        ("single_stage_state_slots", 2148, 2155),
        ("stage_exit_abs_rr", 1828, 1838),
        ("manage_stage_loop", 3169, 3219),
        ("deinit_finalize_from_history", 659, 668),
    ]
    rows = []
    for label, start, end in ranges:
        snippet = "\n".join(f"{i}: {lines[i - 1]}" for i in range(start, min(end, len(lines)) + 1))
        rows.append({"evidence": label, "file": str(path), "start_line": start, "end_line": end, "snippet": snippet})
    return pd.DataFrame(rows)


def build_decision(
    ledger: pd.DataFrame,
    deals: pd.DataFrame,
    touch: pd.DataFrame,
    next_stage1: pd.DataFrame,
    residual_stage: pd.DataFrame,
) -> pd.DataFrame:
    stage1 = ledger[ledger["stage_num"] == 1].iloc[0]
    first_tp_time = touch["first_tp_touch_time"].iloc[0]
    next_before_tp = int(next_stage1["before_first_tp_touch"].astype(str).str.lower().isin(["true", "1"]).sum()) if not next_stage1.empty else 0
    stage1_residual = residual_stage[pd.to_numeric(residual_stage["stage"], errors="coerce") == 1].iloc[0]
    decision = "orphaned_stage1_state_overwrite_or_close_lifecycle_bug"
    if pd.isna(first_tp_time):
        decision = "no_raw_m30_tp_touch_in_60d_but_end_of_test_still_artifact"
    elif next_before_tp > 0:
        decision = "likely_stage1_state_overwritten_before_tp_touch_then_unmanaged_until_deinit"

    return pd.DataFrame(
        [
            {
                "mt5_trade_id": TARGET_MT5_ID,
                "py_trade_id": TARGET_PY_ID,
                "stage1_position_id": stage1["position_id"],
                "stage1_ticket": stage1["ticket"],
                "stage1_local_exit_reason": stage1["local_exit_reason"],
                "stage1_deal_reason": stage1["deal_reason"],
                "stage1_open_time": stage1["open_time"],
                "stage1_exit_time": stage1["exit_time"],
                "stage1_net_profit": num(stage1["net_profit"]),
                "stage1_residual_mt5_minus_py": num(stage1_residual["residual_mt5_minus_py"]),
                "first_tp_touch_time": first_tp_time,
                "next_stage1_opens_before_first_tp_touch": next_before_tp,
                "decision": decision,
                "is_valid_strategy_profit_for_alignment": False,
                "recommended_next_step": "isolate_deinit_history_rows_and_audit_stage_state_overwrite_before_broad_stage_exit_fix",
            }
        ]
    )


def write_report(
    decision: pd.DataFrame,
    ledger: pd.DataFrame,
    deals: pd.DataFrame,
    mapping: pd.DataFrame,
    py_row: pd.DataFrame,
    residual_stage: pd.DataFrame,
    touch: pd.DataFrame,
    next_stage1: pd.DataFrame,
    signals_window: pd.DataFrame,
    code: pd.DataFrame,
) -> None:
    lines = [
        "# mt5_0031 deinit_history / missed Stage1 close audit",
        "",
        "## Decision",
        "",
        markdown_table(decision),
        "",
        "## Target Ledger Rows",
        "",
        markdown_table(ledger),
        "",
        "## Deal History Rows",
        "",
        markdown_table(deals),
        "",
        "## Mapping Row",
        "",
        markdown_table(mapping),
        "",
        "## Python Exec-Model Row",
        "",
        markdown_table(py_row),
        "",
        "## Residual Stage Rows",
        "",
        markdown_table(residual_stage),
        "",
        "## Raw M30 Touch Summary",
        "",
        markdown_table(touch),
        "",
        "## Next Stage1 Opens",
        "",
        markdown_table(next_stage1),
        "",
        "## Signal Export Window",
        "",
        markdown_table(signals_window.head(80)),
        "",
        "## Code Evidence",
        "",
        markdown_table(code),
        "",
        "## Interpretation",
        "",
        "- Stage2 and Stage3 for `mt5_0031` closed through normal EA paths; Stage1 did not.",
        "- Stage1 remained open until tester end and was only recovered by `LedgerFinalizeAllOpenFromHistory(\"deinit_history\")`.",
        "- This row should not be treated as normal strategy PnL in residual alignment until the close lifecycle is fixed or the deinit artifact is isolated.",
        "- The likely repair path is to audit stage state overwrite / position tracking, then rerun full tester; broad Stage exit tuning should wait.",
        "",
        "## Output Files",
        "",
        "- `mt5_0031_decision.csv`",
        "- `mt5_0031_trade_ledger_rows.csv`",
        "- `mt5_0031_deal_history_rows.csv`",
        "- `mt5_0031_mapping_row.csv`",
        "- `mt5_0031_python_exec_model_row.csv`",
        "- `mt5_0031_residual_stage_rows.csv`",
        "- `mt5_0031_raw_m30_touch_summary.csv`",
        "- `mt5_0031_raw_m30_window.csv`",
        "- `mt5_0031_next_stage1_opens.csv`",
        "- `mt5_0031_signal_export_window.csv`",
        "- `mt5_0031_code_evidence.csv`",
    ]
    write_text(OUT_DIR / "mt5_0031_deinit_history_audit_review.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ledger = load_target_ledger()
    if ledger.empty:
        raise RuntimeError("Target ledger rows not found")
    stage1 = ledger[ledger["stage_num"] == 1].iloc[0]
    deals = load_target_deals()
    mapping, py_row, residual_stage = load_python_context()
    touch, raw_window = load_raw_m30_touch_matrix(stage1)
    next_stage1 = load_next_stage1_opens(to_dt(stage1["open_time"]), touch["first_tp_touch_time"].iloc[0])
    signals_window = load_signal_window(to_dt(stage1["open_time"]), to_dt(stage1["open_time"]) + pd.Timedelta(days=7))
    code = code_evidence()
    decision = build_decision(ledger, deals, touch, next_stage1, residual_stage)

    export_csv(decision, OUT_DIR / "mt5_0031_decision.csv")
    export_csv(ledger, OUT_DIR / "mt5_0031_trade_ledger_rows.csv")
    export_csv(deals, OUT_DIR / "mt5_0031_deal_history_rows.csv")
    export_csv(mapping, OUT_DIR / "mt5_0031_mapping_row.csv")
    export_csv(py_row, OUT_DIR / "mt5_0031_python_exec_model_row.csv")
    export_csv(residual_stage, OUT_DIR / "mt5_0031_residual_stage_rows.csv")
    export_csv(touch, OUT_DIR / "mt5_0031_raw_m30_touch_summary.csv")
    export_csv(raw_window, OUT_DIR / "mt5_0031_raw_m30_window.csv")
    export_csv(next_stage1, OUT_DIR / "mt5_0031_next_stage1_opens.csv")
    export_csv(signals_window, OUT_DIR / "mt5_0031_signal_export_window.csv")
    export_csv(code, OUT_DIR / "mt5_0031_code_evidence.csv")
    write_report(decision, ledger, deals, mapping, py_row, residual_stage, touch, next_stage1, signals_window, code)

    print(decision.to_string(index=False))
    print()
    print(touch.to_string(index=False))
    print()
    print(next_stage1.head(5).to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
