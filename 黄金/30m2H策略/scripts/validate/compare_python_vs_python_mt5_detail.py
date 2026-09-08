# -*- coding: utf-8 -*-
"""Detailed comparison between Python-only and legacy Python-MT5 outputs."""
from __future__ import annotations


from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = ROOT / "黄金" / "30m2H策略"
DATA_DIR = STRATEGY_DIR / "data"
OUT_DIR = DATA_DIR / "validation" / "python_only_vs_python_mt5_detail_20260712"


def read_csv_auto(path: Path, **kwargs) -> tuple[pd.DataFrame, str]:
    encodings = ["utf-8-sig", "utf-8", "gbk", "gb18030"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            return pd.read_csv(path, encoding=encoding, **kwargs), encoding
        except Exception as exc:
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


def normalized_time(frame: pd.DataFrame) -> tuple[pd.Series | None, str | None]:
    col = first_existing_column(frame, ["date", "bar_time", "time", "datetime", "时间", "时间戳"])
    if col is None:
        return None, None
    return parse_datetime_series(frame[col]), col


def normalize_mode(value: object) -> str:
    text = str(value)
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return text


def frame_summary(name: str, path: Path, role: str) -> dict[str, object]:
    out: dict[str, object] = {"dataset": name, "role": role, "path": str(path), "exists": path.exists()}
    if not path.exists():
        return out
    df, encoding = read_csv_auto(path)
    ts, time_col = normalized_time(df)
    out.update(
        {
            "encoding": encoding,
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "time_column": time_col or "",
            "column_names_first_20": "; ".join(map(str, df.columns[:20])),
        }
    )
    if ts is not None:
        valid = ts.dropna()
        out["time_start"] = valid.min() if not valid.empty else ""
        out["time_end"] = valid.max() if not valid.empty else ""
        out["duplicate_time_rows"] = int(ts.duplicated().sum())
    return out


def load_signal_frame(path: Path, layer_name: str, source_name: str) -> pd.DataFrame:
    df, _ = read_csv_auto(path)
    out = df.copy()
    out["date"] = parse_datetime_series(out["date"])
    out["mode_norm"] = out["mode"].map(normalize_mode)
    out["signal_key"] = (
        out["date"].dt.strftime("%Y-%m-%d %H:%M:%S")
        + "|"
        + out["dir"].astype(str)
        + "|"
        + out["mode_norm"].astype(str)
    )
    out["source_name"] = source_name
    out["layer_name"] = layer_name
    return out


def compare_signal_layer(layer_name: str, base_path: Path, mt5_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = load_signal_frame(base_path, layer_name, "python_only")
    mt5 = load_signal_frame(mt5_path, layer_name, "python_mt5_legacy")

    base_dedup = base.drop_duplicates(subset=["signal_key"]).copy()
    mt5_dedup = mt5.drop_duplicates(subset=["signal_key"]).copy()

    shared = base_dedup.merge(
        mt5_dedup,
        on="signal_key",
        how="inner",
        suffixes=("_base", "_mt5"),
    )
    base_only = base_dedup[~base_dedup["signal_key"].isin(mt5_dedup["signal_key"])].copy()
    mt5_only = mt5_dedup[~mt5_dedup["signal_key"].isin(base_dedup["signal_key"])].copy()

    summary = pd.DataFrame(
        [
            {
                "layer": layer_name,
                "base_rows": int(len(base_dedup)),
                "mt5_rows": int(len(mt5_dedup)),
                "shared_rows": int(len(shared)),
                "base_only_rows": int(len(base_only)),
                "mt5_only_rows": int(len(mt5_only)),
                "base_mode_counts": "; ".join(
                    f"{k}:{v}" for k, v in base_dedup["mode_norm"].value_counts().sort_index().items()
                ),
                "mt5_mode_counts": "; ".join(
                    f"{k}:{v}" for k, v in mt5_dedup["mode_norm"].value_counts().sort_index().items()
                ),
            }
        ]
    )

    detail_dir = OUT_DIR / layer_name
    export_csv(shared, detail_dir / "shared.csv")
    export_csv(base_only, detail_dir / "python_only.csv")
    export_csv(mt5_only, detail_dir / "python_mt5_only.csv")
    return summary, shared


def compare_processed_m30() -> tuple[pd.DataFrame, pd.DataFrame]:
    base, _ = read_csv_auto(DATA_DIR / "processed" / "m30_standardized.csv")
    mt5, _ = read_csv_auto(DATA_DIR / "processed" / "m30_mt5.csv")
    base["date"] = parse_datetime_series(base["date"])
    mt5["date"] = parse_datetime_series(mt5["date"])
    merged = base.merge(mt5, on="date", how="inner", suffixes=("_base", "_mt5"))

    numeric_pairs = [
        ("close_base", "close_mt5", "close_abs_diff"),
        ("SMA_5_base", "SMA_5_mt5", "sma5_abs_diff"),
        ("SMA_13_base", "SMA_13_mt5", "sma13_abs_diff"),
    ]
    for left, right, out_col in numeric_pairs:
        merged[out_col] = (
            pd.to_numeric(merged[left], errors="coerce") - pd.to_numeric(merged[right], errors="coerce")
        ).abs()

    summary = []
    for _, _, metric in numeric_pairs:
        vals = pd.to_numeric(merged[metric], errors="coerce").dropna()
        summary.append(
            {
                "metric": metric,
                "count": int(len(vals)),
                "mean_abs": float(vals.mean()) if not vals.empty else 0.0,
                "median_abs": float(vals.median()) if not vals.empty else 0.0,
                "p95_abs": float(vals.quantile(0.95)) if not vals.empty else 0.0,
                "max_abs": float(vals.max()) if not vals.empty else 0.0,
            }
        )
    sample = merged[
        [
            "date",
            "close_base",
            "close_mt5",
            "close_abs_diff",
            "SMA_5_base",
            "SMA_5_mt5",
            "sma5_abs_diff",
            "SMA_13_base",
            "SMA_13_mt5",
            "sma13_abs_diff",
        ]
    ].sort_values(["close_abs_diff", "sma5_abs_diff", "sma13_abs_diff"], ascending=False)
    return pd.DataFrame(summary), sample.head(500)


def compare_executed_trade_details(base_path: Path, mt5_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = load_signal_frame(base_path, "executed_stage", "python_only")
    mt5 = load_signal_frame(mt5_path, "executed_stage", "python_mt5_legacy")

    cols = [
        "signal_key",
        "date",
        "mode",
        "mode_norm",
        "dir",
        "stage1_pnl",
        "stage2_pnl",
        "stage3_pnl",
        "total_points",
        "total_$",
        "stage1_exit",
        "stage2_exit",
        "stage3_exit",
        "equity_$",
    ]
    shared = base[cols].merge(mt5[cols], on="signal_key", how="inner", suffixes=("_base", "_mt5"))
    for col in ["stage1_pnl", "stage2_pnl", "stage3_pnl", "total_points", "total_$", "equity_$"]:
        shared[f"{col}_diff"] = (
            pd.to_numeric(shared[f"{col}_base"], errors="coerce")
            - pd.to_numeric(shared[f"{col}_mt5"], errors="coerce")
        )
    for col in ["stage1_exit", "stage2_exit", "stage3_exit"]:
        shared[f"{col}_same"] = shared[f"{col}_base"].astype(str) == shared[f"{col}_mt5"].astype(str)

    stop_summary = pd.DataFrame(
        [
            {
                "source": "python_only",
                "stage1_sl": int(base["stage1_exit"].astype(str).str.contains("SL", regex=False).sum()),
                "stage2_sl": int(base["stage2_exit"].astype(str).str.contains("SL", regex=False).sum()),
                "stage3_sl": int(base["stage3_exit"].astype(str).str.contains("SL", regex=False).sum()),
                "any_sl": int(
                    (
                        base["stage1_exit"].astype(str).str.contains("SL", regex=False)
                        | base["stage2_exit"].astype(str).str.contains("SL", regex=False)
                        | base["stage3_exit"].astype(str).str.contains("SL", regex=False)
                    ).sum()
                ),
            },
            {
                "source": "python_mt5_legacy",
                "stage1_sl": int(mt5["stage1_exit"].astype(str).str.contains("SL", regex=False).sum()),
                "stage2_sl": int(mt5["stage2_exit"].astype(str).str.contains("SL", regex=False).sum()),
                "stage3_sl": int(mt5["stage3_exit"].astype(str).str.contains("SL", regex=False).sum()),
                "any_sl": int(
                    (
                        mt5["stage1_exit"].astype(str).str.contains("SL", regex=False)
                        | mt5["stage2_exit"].astype(str).str.contains("SL", regex=False)
                        | mt5["stage3_exit"].astype(str).str.contains("SL", regex=False)
                    ).sum()
                ),
            },
        ]
    )

    base_curve = base[["date", "equity_$"]].copy().reset_index(drop=True)
    base_curve["trade_index"] = base_curve.index + 1
    mt5_curve = mt5[["date", "equity_$"]].copy().reset_index(drop=True)
    mt5_curve["trade_index"] = mt5_curve.index + 1
    curve = base_curve.merge(mt5_curve, on="trade_index", how="outer", suffixes=("_base", "_mt5"))
    curve["equity_diff"] = pd.to_numeric(curve["equity_$_base"], errors="coerce") - pd.to_numeric(
        curve["equity_$_mt5"], errors="coerce"
    )
    return shared, stop_summary, curve


def build_report(
    data_summary_df: pd.DataFrame,
    calc_summary_df: pd.DataFrame,
    signal_summary_df: pd.DataFrame,
    shared_trade_df: pd.DataFrame,
    stop_summary_df: pd.DataFrame,
) -> str:
    executed_row = signal_summary_df[signal_summary_df["layer"] == "executed_stage"].iloc[0]
    picked_row = signal_summary_df[signal_summary_df["layer"] == "picked_L3"].iloc[0]
    lines = [
        "# Python-only vs Python-MT5 详细对比（2026-07-12）",
        "",
        "## 结论摘要",
        "- 这份对比针对旧版 `data/signals_mt5`，对应当前历史里的 Python 调用 MT5 数据版，不是新的 shift90 诊断分支。",
        "- 两版共享输入并不完全一样：M30/M15 原始行情仍共用 base/raw，但 H2 raw 和 processed M30 已切到不同口径。",
        f"- `picked_L3` 层：Python-only `{int(picked_row['base_rows'])}`，Python-MT5 `{int(picked_row['mt5_rows'])}`，shared `{int(picked_row['shared_rows'])}`。",
        f"- `executed_stage` 层：Python-only `{int(executed_row['base_rows'])}`，Python-MT5 `{int(executed_row['mt5_rows'])}`，shared `{int(executed_row['shared_rows'])}`。",
        "- 交易结果差异不只是信号数不同，shared 交易里的三段 pnl、止损退出类型和 equity 列也会分叉。",
        "",
        "## 输出文件",
        "- `data_source_summary.csv`：原始/processed 输入清单与时间范围。",
        "- `m30_calc_diff_summary.csv`、`m30_calc_diff_sample.csv`：M30 processed close/SMA 差异。",
        "- `accepted_L1_L2/`、`picked_L3/`、`executed_stage/`：每层 shared / python_only / python_mt5_only 清单。",
        "- `shared_executed_trade_diff.csv`：shared executed 交易的逐笔 pnl / exit / equity 差异。",
        "- `stop_exit_summary.csv`：两版止损统计。",
        "- `equity_curve_compare_by_index.csv`：按交易序号对齐的资金曲线差异。",
    ]
    if not shared_trade_df.empty:
        lines.extend(
            [
                "",
                "## Shared 交易差异摘要",
                f"- shared executed 逐笔对比样本数：`{len(shared_trade_df)}`。",
                f"- `total_$` 平均差值：`{shared_trade_df['total_$_diff'].mean():.6f}`。",
                f"- `total_points` 平均差值：`{shared_trade_df['total_points_diff'].mean():.6f}`。",
                f"- `stage1_exit` 完全一致比例：`{shared_trade_df['stage1_exit_same'].mean() * 100.0:.2f}%`。",
                f"- `stage2_exit` 完全一致比例：`{shared_trade_df['stage2_exit_same'].mean() * 100.0:.2f}%`。",
                f"- `stage3_exit` 完全一致比例：`{shared_trade_df['stage3_exit_same'].mean() * 100.0:.2f}%`。",
            ]
        )
    if not stop_summary_df.empty:
        lines.extend(
            [
                "",
                "## 止损统计摘要",
                f"- Python-only 任一阶段 SL：`{int(stop_summary_df.iloc[0]['any_sl'])}`。",
                f"- Python-MT5 任一阶段 SL：`{int(stop_summary_df.iloc[1]['any_sl'])}`。",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    data_sources = [
        ("python_only_raw_m30", DATA_DIR / "raw" / "XAUUSDm30.csv", "python_only_raw"),
        ("python_only_raw_m15", DATA_DIR / "raw" / "XAUUSDm15.csv", "python_only_raw"),
        ("python_only_raw_h2", DATA_DIR / "raw" / "H2_XAUUSDm_39col.csv", "python_only_raw"),
        ("python_only_raw_full_data", DATA_DIR / "raw" / "full_data_30m2h.csv", "python_only_raw"),
        ("python_only_processed_m30", DATA_DIR / "processed" / "m30_standardized.csv", "python_only_processed"),
        ("python_only_processed_h2", DATA_DIR / "processed" / "h2_context_bars.csv", "python_only_processed"),
        ("python_mt5_raw_h2", DATA_DIR / "raw" / "H2_XAUUSDm_mt5.csv", "python_mt5_raw"),
        ("python_mt5_processed_m30", DATA_DIR / "processed" / "m30_mt5.csv", "python_mt5_processed"),
        ("python_mt5_signals_accepted", DATA_DIR / "signals_mt5" / "候选信号_Layer1_Layer2通过.csv", "python_mt5_signal"),
    ]
    data_summary_df = pd.DataFrame([frame_summary(*spec) for spec in data_sources])
    export_csv(data_summary_df, OUT_DIR / "data_source_summary.csv")

    calc_summary_df, calc_sample_df = compare_processed_m30()
    export_csv(calc_summary_df, OUT_DIR / "m30_calc_diff_summary.csv")
    export_csv(calc_sample_df, OUT_DIR / "m30_calc_diff_sample.csv")

    signal_paths = {
        "accepted_L1_L2": (
            DATA_DIR / "signals" / "候选信号_Layer1_Layer2通过.csv",
            DATA_DIR / "signals_mt5" / "候选信号_Layer1_Layer2通过.csv",
        ),
        "picked_L3": (
            DATA_DIR / "signals" / "最终信号_Layer3入选.csv",
            DATA_DIR / "signals_mt5" / "最终信号_Layer3入选.csv",
        ),
        "executed_stage": (
            DATA_DIR / "signals" / "执行交易_Stage结果.csv",
            DATA_DIR / "signals_mt5" / "执行交易_Stage结果.csv",
        ),
    }
    summaries = []
    for layer, (base_path, mt5_path) in signal_paths.items():
        summary_df, _ = compare_signal_layer(layer, base_path, mt5_path)
        summaries.append(summary_df)
    signal_summary_df = pd.concat(summaries, ignore_index=True)
    export_csv(signal_summary_df, OUT_DIR / "signal_layer_diff_summary.csv")

    shared_trade_df, stop_summary_df, curve_df = compare_executed_trade_details(
        signal_paths["executed_stage"][0],
        signal_paths["executed_stage"][1],
    )
    export_csv(shared_trade_df, OUT_DIR / "shared_executed_trade_diff.csv")
    export_csv(stop_summary_df, OUT_DIR / "stop_exit_summary.csv")
    export_csv(curve_df, OUT_DIR / "equity_curve_compare_by_index.csv")

    report = build_report(data_summary_df, calc_summary_df, signal_summary_df, shared_trade_df, stop_summary_df)
    write_text(OUT_DIR / "python_only_vs_python_mt5_detail_report.md", report)
    print(report)


if __name__ == "__main__":
    main()
