# -*- coding: utf-8 -*-
"""Compare Python, Python-with-MT5-data, and MT5-only layers.

This script is intentionally diagnostic-only. It does not regenerate signals or
modify EA outputs; it compares the currently available artifacts layer by layer.
"""
from __future__ import annotations


import math
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = ROOT / "黄金" / "30m2H策略"
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"
OUT_DIR = VALIDATION_DIR / "three_sources_layer_compare_20260712"

MT5_BAR_EXPORT = VALIDATION_DIR / "mt5_only_bar_export_session5_20260712.csv"
MT5_COMPARE_DIR = (
    VALIDATION_DIR
    / "mt5_log_session_compare_v326_full_20260712_restore_m30postn_strict_veto_ea_diag"
)
MT5_DIFF_DIR = (
    VALIDATION_DIR
    / "mt5_log_session_diff_v326_full_20260712_m30postn_strict_veto_initfix_ea_diag"
    / "session_03"
)


def read_csv_auto(path: Path, **kwargs) -> tuple[pd.DataFrame, str]:
    encodings = ["utf-8-sig", "utf-8", "gbk", "gb18030"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs), encoding
        except Exception as exc:  # pragma: no cover - diagnostic fallback
            last_error = exc
    raise RuntimeError(f"Unable to read {path}") from last_error


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def first_existing_column(frame: pd.DataFrame, candidates: Iterable[str]) -> str | None:
    for col in candidates:
        if col in frame.columns:
            return col
    return None


def parse_datetime_series(values: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(values, errors="coerce")
    if parsed.notna().sum() == 0:
        parsed = pd.to_datetime(values, errors="coerce", format="%Y.%m.%d %H:%M")
    return parsed


def normalized_time(frame: pd.DataFrame) -> pd.Series | None:
    col = first_existing_column(frame, ["date", "bar_time", "time", "datetime", "时间", "时间戳"])
    if col is None and len(frame.columns) > 0:
        sample = frame.iloc[: min(len(frame), 100), 0]
        parsed = parse_datetime_series(sample)
        if parsed.notna().sum() >= max(1, len(sample) // 2):
            col = str(frame.columns[0])
    if col is None:
        return None
    return parse_datetime_series(frame[col])


def numeric_summary(frame: pd.DataFrame, column: str) -> dict[str, float | int | None]:
    if column not in frame.columns:
        return {"count": 0, "min": None, "max": None, "mean": None}
    values = pd.to_numeric(frame[column], errors="coerce")
    valid = values.dropna()
    if valid.empty:
        return {"count": 0, "min": None, "max": None, "mean": None}
    return {
        "count": int(valid.size),
        "min": float(valid.min()),
        "max": float(valid.max()),
        "mean": float(valid.mean()),
    }


def frame_summary(name: str, path: Path, role: str) -> dict[str, object]:
    if not path.exists():
        return {
            "dataset": name,
            "role": role,
            "path": str(path),
            "exists": False,
        }
    df, encoding = read_csv_auto(path)
    ts = normalized_time(df)
    start = end = ""
    duplicate_times = ""
    if ts is not None:
        valid = ts.dropna()
        if not valid.empty:
            start = valid.min()
            end = valid.max()
            duplicate_times = int(ts.duplicated().sum())
    close_col = first_existing_column(df, ["close", "收盘价", "���̼�"])
    missing_close = ""
    if close_col is not None:
        missing_close = int(pd.to_numeric(df[close_col], errors="coerce").isna().sum())
    return {
        "dataset": name,
        "role": role,
        "path": str(path),
        "exists": True,
        "encoding": encoding,
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "time_start": start,
        "time_end": end,
        "duplicate_time_rows": duplicate_times,
        "missing_close_rows": missing_close,
        "column_names": "; ".join(map(str, df.columns[:30])),
    }


def load_with_date(path: Path, source: str) -> pd.DataFrame:
    df, _ = read_csv_auto(path)
    ts = normalized_time(df)
    if ts is None:
        raise RuntimeError(f"No datetime column found for {path}")
    df = df.copy()
    df["date_norm"] = ts
    df["source"] = source
    return df


def compare_m30_calculation() -> pd.DataFrame:
    py = load_with_date(DATA_DIR / "processed" / "m30_standardized.csv", "python_base_processed")
    py_mt5 = load_with_date(DATA_DIR / "processed" / "m30_mt5.csv", "python_mt5_processed")
    mt5 = load_with_date(MT5_BAR_EXPORT, "mt5_only_bar_export")

    cols_py = ["date_norm", "close", "SMA_5", "SMA_13", "pre_cross", "merged_post_cross_n"]
    cols_mt5 = ["date_norm", "close", "m30_sma5", "m30_sma13", "m30_cross", "decision", "skip_reason"]
    py = py[[c for c in cols_py if c in py.columns]].rename(
        columns={"close": "py_close", "SMA_5": "py_sma5", "SMA_13": "py_sma13"}
    )
    py_mt5 = py_mt5[[c for c in cols_py if c in py_mt5.columns]].rename(
        columns={"close": "py_mt5_close", "SMA_5": "py_mt5_sma5", "SMA_13": "py_mt5_sma13"}
    )
    mt5 = mt5[[c for c in cols_mt5 if c in mt5.columns]].rename(
        columns={"close": "mt5_close", "m30_sma5": "mt5_sma5", "m30_sma13": "mt5_sma13"}
    )

    merged = py.merge(py_mt5, on="date_norm", how="inner").merge(mt5, on="date_norm", how="inner")
    for left, right, out_col in [
        ("py_close", "py_mt5_close", "py_vs_py_mt5_close_diff"),
        ("py_close", "mt5_close", "py_vs_mt5_close_diff"),
        ("py_sma5", "py_mt5_sma5", "py_vs_py_mt5_sma5_diff"),
        ("py_sma13", "py_mt5_sma13", "py_vs_py_mt5_sma13_diff"),
        ("py_mt5_close", "mt5_close", "py_mt5_vs_mt5_close_diff"),
        ("py_mt5_sma5", "mt5_sma5", "py_mt5_vs_mt5_sma5_diff"),
        ("py_mt5_sma13", "mt5_sma13", "py_mt5_vs_mt5_sma13_diff"),
        ("py_sma5", "mt5_sma5", "py_vs_mt5_sma5_diff"),
        ("py_sma13", "mt5_sma13", "py_vs_mt5_sma13_diff"),
    ]:
        if left in merged.columns and right in merged.columns:
            merged[out_col] = pd.to_numeric(merged[left], errors="coerce") - pd.to_numeric(
                merged[right], errors="coerce"
            )
    return merged


def diff_metric(frame: pd.DataFrame, column: str) -> dict[str, object]:
    if column not in frame.columns:
        return {"metric": column, "count": 0}
    values = pd.to_numeric(frame[column], errors="coerce").dropna().abs()
    if values.empty:
        return {"metric": column, "count": 0}
    return {
        "metric": column,
        "count": int(values.size),
        "max_abs": float(values.max()),
        "mean_abs": float(values.mean()),
        "p95_abs": float(values.quantile(0.95)),
        "nonzero_gt_1e-6": int((values > 1e-6).sum()),
    }


def normalize_mode(value: object) -> str:
    text = str(value)
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return text


def summarize_signal_file(source: str, layer: str, path: Path) -> dict[str, object]:
    if not path.exists():
        return {"source": source, "layer": layer, "exists": False, "path": str(path)}
    df, encoding = read_csv_auto(path)
    out: dict[str, object] = {
        "source": source,
        "layer": layer,
        "exists": True,
        "path": str(path),
        "encoding": encoding,
        "rows": int(len(df)),
    }
    if "date" in df.columns:
        ts = parse_datetime_series(df["date"])
        out["start"] = ts.min() if ts.notna().any() else ""
        out["end"] = ts.max() if ts.notna().any() else ""
        out["unique_time_dir"] = int(
            (ts.dt.strftime("%Y-%m-%d %H:%M:%S").fillna("") + "|" + df.get("dir", "").astype(str)).nunique()
        )
    mode_col = first_existing_column(df, ["mode", "mode_norm", "mode_raw"])
    if mode_col is not None:
        out["mode_counts"] = "; ".join(
            f"{k}:{v}" for k, v in df[mode_col].map(normalize_mode).value_counts().sort_index().items()
        )
    if "dir" in df.columns:
        out["dir_counts"] = "; ".join(f"{k}:{v}" for k, v in df["dir"].value_counts().sort_index().items())
    if "sd" in df.columns:
        sd = pd.to_numeric(df["sd"], errors="coerce")
        out["sd_min"] = float(sd.min()) if sd.notna().any() else ""
        out["sd_max"] = float(sd.max()) if sd.notna().any() else ""
        out["sd_mean"] = float(sd.mean()) if sd.notna().any() else ""
    return out


def stage_stop_summary(source: str, path: Path) -> dict[str, object]:
    df, _ = read_csv_auto(path)
    out: dict[str, object] = {"source": source, "path": str(path), "trade_rows": int(len(df))}
    for col in ["stage1_exit", "stage2_exit", "stage3_exit"]:
        if col in df.columns:
            out[f"{col}_sl_count"] = int(df[col].astype(str).str.contains("SL", regex=False).sum())
    if {"stage1_exit", "stage2_exit", "stage3_exit"}.issubset(df.columns):
        s1 = df["stage1_exit"].astype(str).str.contains("SL", regex=False)
        s2 = df["stage2_exit"].astype(str).str.contains("SL", regex=False)
        s3 = df["stage3_exit"].astype(str).str.contains("SL", regex=False)
        out["any_stage_sl_count"] = int((s1 | s2 | s3).sum())
        out["all_stage_sl_count"] = int((s1 & s2 & s3).sum())
    if "total_points" in df.columns:
        points = pd.to_numeric(df["total_points"], errors="coerce")
        out["wins"] = int((points > 0).sum())
        out["losses"] = int((points <= 0).sum())
        out["win_rate_pct"] = float((points > 0).mean() * 100.0) if len(points) else 0.0
    if "total_$" in df.columns:
        total = pd.to_numeric(df["total_$"], errors="coerce").sum()
        out["base_profit"] = float(total)
        out["profit_times_5"] = float(total * 5.0)
        out["final_times_5"] = float(500.0 + total * 5.0)
    if "equity_$" in df.columns:
        equity = pd.to_numeric(df["equity_$"], errors="coerce").dropna()
        if not equity.empty:
            out["last_equity_column"] = float(equity.iloc[-1])
            out["max_equity_column"] = float(equity.max())
            out["min_equity_column"] = float(equity.min())
    return out


def load_mt5_session_summary() -> dict[str, object]:
    path = MT5_COMPARE_DIR / "sessions_summary.csv"
    df, _ = read_csv_auto(path)
    if "会话编号" in df.columns:
        row = df[df["会话编号"].astype(str) == "5"]
        if row.empty:
            row = df.tail(1)
    else:
        row = df.tail(1)
    r = row.iloc[0].to_dict()
    return {
        "source": "MT5-only EA session 5",
        "trade_rows": r.get("MT5信号数", ""),
        "initial_balance": r.get("MT5初始资金", ""),
        "final_balance": r.get("MT5最终资金", ""),
        "python_same_window_trades": r.get("Python同窗交易数", ""),
        "python_same_window_final": r.get("Python同窗最终资金", ""),
        "note": "MT5 win/stop/equity curve require trade ledger; only final balance and signal count are available now.",
    }


def summarize_mt5_bar_export() -> tuple[pd.DataFrame, pd.DataFrame]:
    mt5, _ = read_csv_auto(MT5_BAR_EXPORT)
    decision = (
        mt5["decision"].value_counts(dropna=False).rename_axis("decision").reset_index(name="rows")
        if "decision" in mt5.columns
        else pd.DataFrame()
    )
    skip = (
        mt5["skip_reason"].value_counts(dropna=False).rename_axis("skip_reason").reset_index(name="rows")
        if "skip_reason" in mt5.columns
        else pd.DataFrame()
    )
    return decision, skip


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    data_sources = [
        ("Python base raw M30", DATA_DIR / "raw" / "XAUUSDm30.csv", "python_base_raw"),
        ("Python base raw M15", DATA_DIR / "raw" / "XAUUSDm15.csv", "python_base_raw"),
        ("Python base raw H2", DATA_DIR / "raw" / "H2_XAUUSDm_39col.csv", "python_base_raw"),
        ("Python base processed M30", DATA_DIR / "processed" / "m30_standardized.csv", "python_base_calc"),
        ("Python base processed M15", DATA_DIR / "processed" / "m15_context_bars.csv", "python_base_calc"),
        ("Python base processed H2", DATA_DIR / "processed" / "h2_context_bars.csv", "python_base_calc"),
        ("Python MT5 raw H2", DATA_DIR / "raw" / "H2_XAUUSDm_mt5.csv", "python_mt5_raw"),
        ("Python MT5 processed M30", DATA_DIR / "processed" / "m30_mt5.csv", "python_mt5_calc"),
        ("MT5-only bar export", MT5_BAR_EXPORT, "mt5_only_calc"),
    ]
    data_summary = pd.DataFrame([frame_summary(name, path, role) for name, path, role in data_sources])
    export_csv(data_summary, OUT_DIR / "data_layer_summary.csv")

    m30_compare = compare_m30_calculation()
    export_csv(m30_compare.head(5000), OUT_DIR / "m30_calculation_compare_sample.csv")
    diff_cols = [c for c in m30_compare.columns if c.endswith("_diff")]
    diff_summary = pd.DataFrame([diff_metric(m30_compare, col) for col in diff_cols])
    diff_summary.insert(0, "common_bars", len(m30_compare))
    export_csv(diff_summary, OUT_DIR / "m30_calculation_diff_summary.csv")

    signal_files = [
        ("Python base", "accepted_L1_L2", DATA_DIR / "signals" / "候选信号_Layer1_Layer2通过.csv"),
        ("Python base", "picked_L3", DATA_DIR / "signals" / "最终信号_Layer3入选.csv"),
        ("Python base", "executed_stage", DATA_DIR / "signals" / "执行交易_Stage结果.csv"),
        ("Python MT5 data", "accepted_L1_L2", DATA_DIR / "signals_mt5" / "候选信号_Layer1_Layer2通过.csv"),
        ("Python MT5 data", "picked_L3", DATA_DIR / "signals_mt5" / "最终信号_Layer3入选.csv"),
        ("Python MT5 data", "executed_stage", DATA_DIR / "signals_mt5" / "执行交易_Stage结果.csv"),
        ("MT5-only EA", "executed_log_signals", MT5_DIFF_DIR / "mt5_signals.csv"),
        ("MT5-only EA", "shared_with_python", MT5_DIFF_DIR / "shared_signals.csv"),
        ("MT5-only EA", "mt5_only", MT5_DIFF_DIR / "mt5_only_signals.csv"),
        ("Python EA-window", "python_only", MT5_DIFF_DIR / "python_only_signals.csv"),
    ]
    signal_summary = pd.DataFrame([summarize_signal_file(*item) for item in signal_files])
    export_csv(signal_summary, OUT_DIR / "signal_layer_summary.csv")

    stop_rows = [
        stage_stop_summary("Python base", DATA_DIR / "signals" / "执行交易_Stage结果.csv"),
        stage_stop_summary("Python MT5 data", DATA_DIR / "signals_mt5" / "执行交易_Stage结果.csv"),
        load_mt5_session_summary(),
    ]
    export_csv(pd.DataFrame(stop_rows), OUT_DIR / "trade_stop_equity_summary.csv")

    decision_counts, skip_counts = summarize_mt5_bar_export()
    export_csv(decision_counts, OUT_DIR / "mt5_bar_decision_counts.csv")
    export_csv(skip_counts, OUT_DIR / "mt5_bar_skip_reason_counts.csv")

    if (MT5_DIFF_DIR / "mt5_signals.csv").exists():
        mt5_signals, _ = read_csv_auto(MT5_DIFF_DIR / "mt5_signals.csv")
        export_csv(mt5_signals, OUT_DIR / "mt5_only_trade_signals.csv")
    if (MT5_DIFF_DIR / "python_executed_signals.csv").exists():
        py_exec, _ = read_csv_auto(MT5_DIFF_DIR / "python_executed_signals.csv")
        export_csv(py_exec, OUT_DIR / "python_ea_window_executed_signals.csv")

    report_lines = [
        "# 三来源分层对比报告",
        "",
        "## 输入范围",
        "",
        "- Python基础版：`data/raw`、`data/processed/m30_standardized.csv`、`data/signals`",
        "- Python调用MT5数据版：`data/raw/H2_XAUUSDm_mt5.csv`、`data/processed/m30_mt5.csv`、`data/signals_mt5`",
        "- MT5-only：`mt5_only_bar_export_session5_20260712.csv` + 当前 M30-only strict-veto diff session_03",
        "",
        "## 先看原始/计算数据",
        "",
        data_summary[["dataset", "role", "rows", "time_start", "time_end", "duplicate_time_rows"]]
        .to_markdown(index=False),
        "",
        "## M30计算差异摘要",
        "",
        diff_summary.to_markdown(index=False),
        "",
        "## 信号层摘要",
        "",
        signal_summary[["source", "layer", "rows", "mode_counts", "dir_counts"]]
        .fillna("")
        .to_markdown(index=False),
        "",
        "## 交易/止损/资金摘要",
        "",
        pd.DataFrame(stop_rows).fillna("").to_markdown(index=False),
        "",
        "## MT5 bar级决策分布",
        "",
        decision_counts.to_markdown(index=False) if not decision_counts.empty else "无 decision 列",
        "",
        "## MT5 bar级跳过原因",
        "",
        skip_counts.head(20).to_markdown(index=False) if not skip_counts.empty else "无 skip_reason 列",
        "",
        "## 当前限制",
        "",
        "- MT5-only 现在有 bar级计算导出和日志信号，但还没有交易级 ledger，因此 MT5 胜率、止损次数、逐笔资金曲线仍不能可靠对齐。",
        "- `signals_mt5` 当前文件时间仍是 2026-07-10，且 `export_with_mt5_data.py` 之前指向旧 terminal；本报告先按现有文件比较，后续仍需重建。",
        "- MT5 bar export 的 `SIGNAL` 只有 M30 close 路径，M15 SLOT1 信号主要来自 tester log；因此 MT5-only 信号计算和交易信号需要分开看。",
    ]
    write_text(OUT_DIR / "three_sources_layer_compare_report.md", "\n".join(report_lines))
    print(f"Wrote comparison outputs to {OUT_DIR}")


if __name__ == "__main__":
    main()
