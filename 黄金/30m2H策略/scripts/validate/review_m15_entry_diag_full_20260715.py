# -*- coding: utf-8 -*-
"""Review full-history EA M15 early-entry diagnostics for top unmatched cases."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

FULL_DIR = VALIDATION_DIR / "ea_m15_entry_diag_full_20260715"
OUT_DIR = VALIDATION_DIR / "ea_m15_entry_diag_full_review_20260715"

M15_DIAG_FILE = FULL_DIR / "30m2H_strategy_m15_entry_diag.csv"
SIGNALS_EXPORT_FILE = FULL_DIR / "30m2H_strategy_signals_export.csv"
LEDGER_FILE = FULL_DIR / "30m2H_strategy_trade_ledger.csv"
DEAL_HISTORY_FILE = FULL_DIR / "30m2H_strategy_deal_history.csv"

START_CAPITAL = 500.0

TARGETS = [
    {
        "stable_case": "far_runtime_rescue_20251021_postn6",
        "original_trade_id": "python_mt5_0079",
        "filtered_trade_id": "python_mt5_0078",
        "python_target_time": "2025-10-21 10:00:00",
        "mt5_raw_anchor_time": "2025-10-21 08:30:00",
        "trigger_family": "M15 SLOT1",
        "mode": "post_n6",
        "dir_norm": "SELL",
    },
    {
        "stable_case": "far_runtime_rescue_20251017_precross",
        "original_trade_id": "python_mt5_0073",
        "filtered_trade_id": "python_mt5_0073",
        "python_target_time": "2025-10-17 11:00:00",
        "mt5_raw_anchor_time": "2025-10-17 09:30:00",
        "trigger_family": "M15 SLOT1",
        "mode": "pre_cross",
        "dir_norm": "SELL",
    },
]

DIAG_DT_COLS = [
    "time",
    "current_m30_bar",
    "completed_m15_open",
    "slot_m30_open",
    "anchor_time",
    "last_signal_anchor",
]

DIAG_NUM_COLS = [
    "m15_shift",
    "m30_shift",
    "slot_in_m30",
    "stage_count",
    "max_pos",
    "post_n_counter",
    "merged_post_n_counter",
    "signal_dir",
    "m15_close",
    "m15_sma13",
    "stop_price",
    "entry_proxy",
    "stop_pts_spec",
]

PRIMARY_COLS = [
    "stable_case",
    "python_target_time",
    "mt5_raw_anchor_time",
    "diag_time",
    "completed_m15_open",
    "anchor_time",
    "slot_in_m30",
    "is_slot1",
    "is_slot2",
    "stage_count",
    "max_pos",
    "same_anchor",
    "pre_cross",
    "is_cross",
    "post_n_counter",
    "merged_post_n_counter",
    "signal_dir",
    "dir",
    "signal_src",
    "layer1_pass",
    "layer3_pass",
    "stop_pts_spec",
    "result",
    "detail",
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def parse_dt_series(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip()
    text = text.mask(text.isin(["", "nan", "NaT", "None"]))
    text = text.str.replace(".", "-", regex=False)
    return pd.to_datetime(text, errors="coerce")


def parse_dt(value: object) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    return pd.to_datetime(str(value).replace(".", "-"), errors="coerce")


def to_bool_text(value: object) -> str:
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return "true"
    if text in {"false", "0", "no"}:
        return "false"
    return text


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    if frame.empty:
        return "_No rows._"
    if columns is not None:
        cols = [col for col in columns if col in frame.columns]
        if not cols:
            return "_No columns._"
        frame = frame[cols]
    return frame.to_markdown(index=False)


def load_diag() -> pd.DataFrame:
    df = read_csv(M15_DIAG_FILE).copy()
    for col in DIAG_DT_COLS:
        if col in df.columns:
            df[f"{col}_dt"] = parse_dt_series(df[col])
    for col in DIAG_NUM_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in ["is_slot1", "is_slot2", "same_anchor", "pre_cross", "is_cross", "layer1_pass", "layer3_pass"]:
        if col in df.columns:
            df[col] = df[col].map(to_bool_text)
    return df


def load_signals_export() -> pd.DataFrame:
    df = read_csv(SIGNALS_EXPORT_FILE).copy()
    dt_col = None
    for candidate in ["bar_time", "time", "current_m30_bar"]:
        if candidate in df.columns:
            dt_col = candidate
            break
    if dt_col is not None:
        df["bar_dt"] = parse_dt_series(df[dt_col])
    return df


def load_ledger() -> pd.DataFrame:
    df = read_csv(LEDGER_FILE).copy()
    for col in ["signal_anchor_time", "open_time", "exit_time"]:
        if col in df.columns:
            df[f"{col}_dt"] = parse_dt_series(df[col])
    if "net_profit" in df.columns:
        df["net_profit_num"] = pd.to_numeric(df["net_profit"], errors="coerce").fillna(0.0)
    return df


def load_deal_history() -> pd.DataFrame:
    if not DEAL_HISTORY_FILE.exists():
        return pd.DataFrame()
    df = read_csv(DEAL_HISTORY_FILE).copy()
    for col in ["time", "open_time", "close_time"]:
        if col in df.columns:
            df[f"{col}_dt"] = parse_dt_series(df[col])
    for col in ["profit", "swap", "commission", "net_profit"]:
        if col in df.columns:
            df[f"{col}_num"] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    return df


def normalize_for_export(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in list(out.columns):
        if col.endswith("_dt"):
            out[col] = out[col].dt.strftime("%Y-%m-%d %H:%M:%S")
    return out


def active_positions_at(ledger: pd.DataFrame, probe_time: pd.Timestamp) -> pd.DataFrame:
    if ledger.empty or pd.isna(probe_time):
        return pd.DataFrame()
    open_col = "open_time_dt"
    exit_col = "exit_time_dt"
    if open_col not in ledger.columns or exit_col not in ledger.columns:
        return pd.DataFrame()
    active = ledger[(ledger[open_col] <= probe_time) & (ledger[exit_col] >= probe_time)].copy()
    active.insert(0, "probe_time", probe_time)
    return active


def target_diag_windows(diag: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    target_rows: list[pd.DataFrame] = []
    window_rows: list[pd.DataFrame] = []

    for target in TARGETS:
        raw_dt = parse_dt(target["mt5_raw_anchor_time"])
        window_start = raw_dt - pd.Timedelta(minutes=120)
        window_end = raw_dt + pd.Timedelta(minutes=120)

        exact = diag[diag["anchor_time_dt"].eq(raw_dt)].copy()
        window_mask = pd.Series(False, index=diag.index)
        for col in ["time_dt", "current_m30_bar_dt", "completed_m15_open_dt", "slot_m30_open_dt", "anchor_time_dt"]:
            if col in diag.columns:
                window_mask |= diag[col].between(window_start, window_end, inclusive="both")
        window = diag[window_mask].copy()

        for frame in [exact, window]:
            frame.insert(0, "stable_case", target["stable_case"])
            frame.insert(1, "python_target_time", target["python_target_time"])
            frame.insert(2, "mt5_raw_anchor_time", target["mt5_raw_anchor_time"])
            frame["minutes_from_raw_anchor"] = (
                frame["time_dt"] - raw_dt
            ).dt.total_seconds() / 60.0
            frame["diag_time"] = frame["time_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")

        target_rows.append(exact)
        window_rows.append(window)

    all_targets = pd.concat(target_rows, ignore_index=True) if target_rows else pd.DataFrame()
    all_windows = pd.concat(window_rows, ignore_index=True) if window_rows else pd.DataFrame()
    return all_targets, all_windows


def summarize_targets(target_diag: pd.DataFrame, ledger: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries: list[dict[str, object]] = []
    active_rows: list[pd.DataFrame] = []

    for target in TARGETS:
        case_rows = target_diag[target_diag["stable_case"].eq(target["stable_case"])].copy()
        slot1_rows = case_rows[case_rows.get("is_slot1", "").eq("true")].copy() if "is_slot1" in case_rows else pd.DataFrame()
        primary = slot1_rows.iloc[0] if not slot1_rows.empty else (case_rows.iloc[0] if not case_rows.empty else None)

        result_counts = case_rows["result"].value_counts(dropna=False).to_dict() if "result" in case_rows else {}
        result_sequence = "; ".join(f"{key}:{value}" for key, value in result_counts.items())
        if primary is None:
            probe_time = pd.NaT
            primary_result = "NO_DIAG_ROW"
            primary_detail = ""
            stage_count = ""
            max_pos = ""
            signal_src = ""
            stop_pts_spec = ""
            signal_dir = ""
        else:
            probe_time = primary.get("time_dt", pd.NaT)
            primary_result = primary.get("result", "")
            primary_detail = primary.get("detail", "")
            stage_count = primary.get("stage_count", "")
            max_pos = primary.get("max_pos", "")
            signal_src = primary.get("signal_src", "")
            stop_pts_spec = primary.get("stop_pts_spec", "")
            signal_dir = primary.get("signal_dir", "")

        active = active_positions_at(ledger, probe_time)
        if not active.empty:
            active.insert(0, "stable_case", target["stable_case"])
            active.insert(1, "python_target_time", target["python_target_time"])
            active.insert(2, "mt5_raw_anchor_time", target["mt5_raw_anchor_time"])
            active_rows.append(active)

        summaries.append(
            {
                "stable_case": target["stable_case"],
                "original_trade_id": target["original_trade_id"],
                "filtered_trade_id": target["filtered_trade_id"],
                "python_target_time": target["python_target_time"],
                "mt5_raw_anchor_time": target["mt5_raw_anchor_time"],
                "expected_trigger_family": target["trigger_family"],
                "expected_mode": target["mode"],
                "expected_dir": target["dir_norm"],
                "anchor_diag_rows": int(len(case_rows)),
                "slot1_diag_rows": int(len(slot1_rows)),
                "primary_diag_time": "" if pd.isna(probe_time) else probe_time.strftime("%Y-%m-%d %H:%M:%S"),
                "primary_result": primary_result,
                "primary_detail": primary_detail,
                "stage_count": stage_count,
                "max_pos": max_pos,
                "signal_dir": signal_dir,
                "signal_src": signal_src,
                "stop_pts_spec": stop_pts_spec,
                "active_ledger_rows_at_primary_time": int(len(active)),
                "result_sequence": result_sequence,
                "classification": classify_result(primary_result, stage_count, max_pos),
                "recommended_next_check": recommended_next_check(primary_result),
            }
        )

    summary = pd.DataFrame(summaries)
    active_all = pd.concat(active_rows, ignore_index=True) if active_rows else pd.DataFrame()
    return summary, active_all


def classify_result(result: object, stage_count: object, max_pos: object) -> str:
    result_text = str(result).strip()
    try:
        stage_value = float(stage_count)
        max_value = float(max_pos)
    except (TypeError, ValueError):
        stage_value = None
        max_value = None

    if result_text == "NO_DIAG_ROW":
        return "diagnostic_missing"
    if result_text == "EXECUTED":
        return "ea_executed"
    if result_text == "SKIP_MAX_POS":
        return "max_position_gate"
    if stage_value is not None and max_value is not None and stage_value < max_value and result_text != "SKIP_MAX_POS":
        max_note = "not_max_pos"
    else:
        max_note = "max_pos_unclear"
    if result_text == "NO_SIGNAL_DIR":
        return f"m15_signal_mode_divergence/{max_note}"
    if result_text in {"LAYER1_FAIL", "LAYER3_FAIL"}:
        return f"layer_gate_divergence/{max_note}"
    if result_text in {"STOP_FAIL", "SPEC_FAIL"}:
        return f"stop_or_symbol_spec_gate/{max_note}"
    if result_text == "SAME_ANCHOR":
        return "same_anchor_lifecycle_gate"
    if result_text in {"NO_SLOT", "NO_SLOT_M30", "SLOT2_DISABLED"}:
        return f"slot_timing_gate/{max_note}"
    return f"other_{result_text}/{max_note}"


def recommended_next_check(result: object) -> str:
    result_text = str(result).strip()
    if result_text == "NO_SIGNAL_DIR":
        return "diff M15 pre_cross/is_cross/post_n counter between Python and EA for the raw anchor"
    if result_text == "SPEC_FAIL":
        return "diff EA stop_pts_spec and Python stop/spec gate for the raw anchor"
    if result_text in {"LAYER1_FAIL", "LAYER3_FAIL"}:
        return "diff layer gate indicator values at M15 completed bar"
    if result_text == "SAME_ANCHOR":
        return "simulate g_signal_anchor_time lifecycle in Python runtime model"
    if result_text == "SKIP_MAX_POS":
        return "simulate OurStageCount lifecycle and max-position gate"
    if result_text == "EXECUTED":
        return "inspect mapping/timing because EA did execute this anchor"
    return "inspect target diag window and signals_export row"


def signals_export_windows(signals_export: pd.DataFrame) -> pd.DataFrame:
    if signals_export.empty or "bar_dt" not in signals_export.columns:
        return pd.DataFrame()
    rows: list[pd.DataFrame] = []
    for target in TARGETS:
        raw_dt = parse_dt(target["mt5_raw_anchor_time"])
        window = signals_export[
            signals_export["bar_dt"].between(raw_dt - pd.Timedelta(minutes=120), raw_dt + pd.Timedelta(minutes=120), inclusive="both")
        ].copy()
        window.insert(0, "stable_case", target["stable_case"])
        window.insert(1, "python_target_time", target["python_target_time"])
        window.insert(2, "mt5_raw_anchor_time", target["mt5_raw_anchor_time"])
        window["minutes_from_raw_anchor"] = (window["bar_dt"] - raw_dt).dt.total_seconds() / 60.0
        rows.append(window)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def summarize_ledger(ledger: pd.DataFrame, deal_history: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    net = float(ledger["net_profit_num"].sum()) if "net_profit_num" in ledger.columns else 0.0
    unique_anchor_count = int(ledger["signal_anchor_time"].nunique()) if "signal_anchor_time" in ledger.columns else 0
    rows.append(
        {
            "source": "trade_ledger",
            "rows": int(len(ledger)),
            "unique_signal_anchors": unique_anchor_count,
            "net_profit": round(net, 6),
            "final_balance_from_net": round(START_CAPITAL + net, 6),
        }
    )
    if not deal_history.empty:
        profit_col = "profit_num" if "profit_num" in deal_history.columns else None
        swap_col = "swap_num" if "swap_num" in deal_history.columns else None
        commission_col = "commission_num" if "commission_num" in deal_history.columns else None
        profit = float(deal_history[profit_col].sum()) if profit_col else 0.0
        swap = float(deal_history[swap_col].sum()) if swap_col else 0.0
        commission = float(deal_history[commission_col].sum()) if commission_col else 0.0
        rows.append(
            {
                "source": "deal_history",
                "rows": int(len(deal_history)),
                "unique_signal_anchors": "",
                "net_profit": round(profit + swap + commission, 6),
                "final_balance_from_net": round(START_CAPITAL + profit + swap + commission, 6),
            }
        )
    return pd.DataFrame(rows)


def result_counts(diag: pd.DataFrame) -> pd.DataFrame:
    counts = diag["result"].value_counts(dropna=False).rename_axis("result").reset_index(name="rows")
    counts["pct"] = (counts["rows"] / len(diag) * 100.0).round(4) if len(diag) else 0.0
    return counts


def build_report(
    summary: pd.DataFrame,
    target_diag: pd.DataFrame,
    target_windows: pd.DataFrame,
    signals_windows: pd.DataFrame,
    ledger_summary: pd.DataFrame,
    counts: pd.DataFrame,
) -> str:
    top_counts = counts.head(12).copy()
    target_view_cols = [
        "stable_case",
        "diag_time",
        "completed_m15_open",
        "anchor_time",
        "slot_in_m30",
        "stage_count",
        "max_pos",
        "pre_cross",
        "is_cross",
        "merged_post_n_counter",
        "signal_dir",
        "signal_src",
        "layer1_pass",
        "layer3_pass",
        "stop_pts_spec",
        "result",
        "detail",
    ]
    signals_cols = [
        "stable_case",
        "bar_time",
        "bar_dt",
        "decision",
        "skip_reason",
        "signal_src",
        "dir",
    ]
    lines = [
        "# EA M15 early-entry full diagnostic review",
        "",
        "## 结论",
        "",
        "- 本报告使用 full-history tester 导出的 `30m2H_strategy_m15_entry_diag.csv`，不是短窗口 smoke。",
        "- 两个重点 Python-unmatched 样本均已定位到 EA `TryM15EarlyEntry()` 的逐 bar 诊断行。",
        "- 若 `stage_count < max_pos` 且结果不是 `SKIP_MAX_POS`，则不能再把原因归为纯持仓占用或 max position。",
        "- 后续修复应按下表的 `classification` 和 `recommended_next_check` 分支推进。",
        "",
        "## Target summary",
        "",
        markdown_table(summary),
        "",
        "## Ledger baseline",
        "",
        markdown_table(ledger_summary),
        "",
        "## Target exact diagnostic rows",
        "",
        markdown_table(target_diag, target_view_cols),
        "",
        "## Overall M15 diagnostic result counts",
        "",
        markdown_table(top_counts),
        "",
        "## Signals export rows around targets",
        "",
        markdown_table(signals_windows, signals_cols),
        "",
        "## Output files",
        "",
        "- `target_m15_entry_diag_rows.csv`: exact `anchor_time == raw_anchor` rows.",
        "- `target_m15_entry_diag_windows.csv`: target +/-120 minute diagnostic windows.",
        "- `target_active_positions_at_diag_time.csv`: ledger positions active at each primary diag time.",
        "- `target_signals_export_windows.csv`: coarse M30 signals export around target anchors.",
        "- `m15_entry_diag_result_counts.csv`: global result counts for the full run.",
        "- `ledger_baseline_summary.csv`: full-run ledger/deal net check.",
    ]
    if len(target_windows) > 0:
        lines.extend(
            [
                "",
                "## Window note",
                "",
                f"- `target_m15_entry_diag_windows.csv` contains {len(target_windows)} rows; use it for detailed row-by-row inspection.",
            ]
        )
    return "\n".join(lines)


def write_readme() -> None:
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# ea_m15_entry_diag_full_review_20260715",
                "",
                "Purpose: parse full-history EA M15 early-entry diagnostics and classify the two remaining high-impact Python-unmatched targets.",
                "",
                "Primary report: `ea_m15_entry_diag_full_review.md`.",
                "",
                "Inputs:",
                "",
                "- `../ea_m15_entry_diag_full_20260715/30m2H_strategy_m15_entry_diag.csv`",
                "- `../ea_m15_entry_diag_full_20260715/30m2H_strategy_signals_export.csv`",
                "- `../ea_m15_entry_diag_full_20260715/30m2H_strategy_trade_ledger.csv`",
                "- `../ea_m15_entry_diag_full_20260715/30m2H_strategy_deal_history.csv`",
            ]
        ),
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    diag = load_diag()
    signals_export = load_signals_export()
    ledger = load_ledger()
    deal_history = load_deal_history()

    target_diag, target_windows = target_diag_windows(diag)
    summary, active_positions = summarize_targets(target_diag, ledger)
    signals_windows = signals_export_windows(signals_export)
    ledger_baseline = summarize_ledger(ledger, deal_history)
    counts = result_counts(diag)

    export_csv(normalize_for_export(target_diag), OUT_DIR / "target_m15_entry_diag_rows.csv")
    export_csv(normalize_for_export(target_windows), OUT_DIR / "target_m15_entry_diag_windows.csv")
    export_csv(normalize_for_export(summary), OUT_DIR / "target_m15_entry_diag_summary.csv")
    export_csv(normalize_for_export(active_positions), OUT_DIR / "target_active_positions_at_diag_time.csv")
    export_csv(normalize_for_export(signals_windows), OUT_DIR / "target_signals_export_windows.csv")
    export_csv(ledger_baseline, OUT_DIR / "ledger_baseline_summary.csv")
    export_csv(counts, OUT_DIR / "m15_entry_diag_result_counts.csv")

    report = build_report(summary, target_diag, target_windows, signals_windows, ledger_baseline, counts)
    write_text(OUT_DIR / "ea_m15_entry_diag_full_review.md", report)
    write_readme()

    print(f"Wrote {OUT_DIR}")
    print(summary.to_string(index=False))
    print(ledger_baseline.to_string(index=False))


if __name__ == "__main__":
    main()
