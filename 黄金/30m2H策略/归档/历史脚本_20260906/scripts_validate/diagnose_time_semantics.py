# -*- coding: utf-8 -*-
"""Diagnose raw-data and time-semantics alignment across Python and MT5.

The script is read-only for source data. It writes diagnostic CSV/Markdown
outputs under data/validation so later steps can decide whether Python-MT5
data should be rebuilt or MT5 exports need richer timestamps.
"""
from __future__ import annotations


import hashlib
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = ROOT / "黄金" / "30m2H策略"
DATA_DIR = STRATEGY_DIR / "data"
BASE_DIR = ROOT / "base_data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
VALIDATION_DIR = DATA_DIR / "validation"

OUT_DIR = VALIDATION_DIR
MT5_BAR_EXPORT = VALIDATION_DIR / "mt5_only_bar_export_session5_20260712.csv"


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


def normalized_time(frame: pd.DataFrame) -> tuple[pd.Series | None, str | None]:
    col = first_existing_column(frame, ["date", "bar_time", "time", "datetime", "时间", "时间戳"])
    if col is None and len(frame.columns) > 0:
        sample = frame.iloc[: min(len(frame), 100), 0]
        parsed = parse_datetime_series(sample)
        if parsed.notna().sum() >= max(1, len(sample) // 2):
            col = str(frame.columns[0])
    if col is None:
        return None, None
    return parse_datetime_series(frame[col]), col


def numeric_col(frame: pd.DataFrame, candidates: Iterable[str], fallback_index: int | None = None) -> str | None:
    col = first_existing_column(frame, candidates)
    if col is not None:
        return col
    if fallback_index is not None and fallback_index < len(frame.columns):
        return str(frame.columns[fallback_index])
    return None


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dataset_summary(name: str, path: Path, role: str) -> dict[str, object]:
    out: dict[str, object] = {
        "dataset": name,
        "role": role,
        "path": str(path),
        "exists": path.exists(),
    }
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
            "sha256_12": file_sha256(path)[:12],
        }
    )
    if ts is not None:
        valid = ts.dropna()
        out["parsed_time_rows"] = int(valid.size)
        out["time_start"] = valid.min() if not valid.empty else ""
        out["time_end"] = valid.max() if not valid.empty else ""
        out["duplicate_time_rows"] = int(ts.duplicated().sum())
        if valid.size >= 2:
            deltas = valid.sort_values().diff().dropna().dt.total_seconds() / 60.0
            out["median_step_minutes"] = float(deltas.median()) if not deltas.empty else ""
            out["min_step_minutes"] = float(deltas.min()) if not deltas.empty else ""
            out["max_step_minutes"] = float(deltas.max()) if not deltas.empty else ""
    close_col = numeric_col(df, ["close", "收盘价"], fallback_index=4)
    if close_col is not None:
        close = pd.to_numeric(df[close_col], errors="coerce")
        out["close_column"] = close_col
        out["missing_close_rows"] = int(close.isna().sum())
        out["close_min"] = float(close.min()) if close.notna().any() else ""
        out["close_max"] = float(close.max()) if close.notna().any() else ""
    return out


def load_with_time(path: Path, source: str) -> pd.DataFrame:
    df, _ = read_csv_auto(path)
    ts, time_col = normalized_time(df)
    if ts is None:
        raise RuntimeError(f"No datetime column found in {path}")
    out = df.copy()
    out["date_norm"] = ts
    out["source"] = source
    out["time_col_used"] = time_col
    return out


def raw_sync_summary() -> pd.DataFrame:
    pairs = [
        ("XAUUSDm30", BASE_DIR / "XAUUSDm30.csv", RAW_DIR / "XAUUSDm30.csv"),
        ("XAUUSDm15", BASE_DIR / "XAUUSDm15.csv", RAW_DIR / "XAUUSDm15.csv"),
        ("H2_XAUUSDm_39col", BASE_DIR / "H2_XAUUSDm_39col.csv", RAW_DIR / "H2_XAUUSDm_39col.csv"),
        ("full_data_30m2h", BASE_DIR / "full_data_30m2h.csv", RAW_DIR / "full_data_30m2h.csv"),
    ]
    rows: list[dict[str, object]] = []
    for name, base_path, raw_path in pairs:
        row: dict[str, object] = {
            "dataset": name,
            "base_exists": base_path.exists(),
            "raw_exists": raw_path.exists(),
        }
        if base_path.exists() and raw_path.exists():
            base = dataset_summary(name, base_path, "base")
            raw = dataset_summary(name, raw_path, "strategy_raw")
            for key in ["rows", "columns", "time_start", "time_end", "sha256_12"]:
                row[f"base_{key}"] = base.get(key, "")
                row[f"raw_{key}"] = raw.get(key, "")
            row["same_sha256_12"] = base.get("sha256_12") == raw.get("sha256_12")
            row["same_rows"] = base.get("rows") == raw.get("rows")
            row["same_time_range"] = base.get("time_start") == raw.get("time_start") and base.get(
                "time_end"
            ) == raw.get("time_end")
        rows.append(row)
    return pd.DataFrame(rows)


def m15_m30_alignment() -> pd.DataFrame:
    m30 = load_with_time(PROCESSED_DIR / "m30_standardized.csv", "m30_processed")
    m15 = load_with_time(PROCESSED_DIR / "m15_context_bars.csv", "m15_processed")
    m30_all = m30["date_norm"].dropna().drop_duplicates().sort_values()
    m15_times = m15["date_norm"].dropna().drop_duplicates().sort_values()
    m15_start = m15_times.min()
    m15_end = m15_times.max()
    scopes = [
        ("all_m30", m30_all),
        (
            "m15_overlap_window",
            m30_all[(m30_all >= m15_start) & (m30_all <= m15_end)],
        ),
    ]
    m15_set = set(m15["date_norm"].dropna())
    rows = []
    for scope, m30_times in scopes:
        for offset in [0, 15, 30, 45, 60, 90]:
            targets = m30_times + pd.Timedelta(minutes=offset)
            hits = targets.isin(m15_set)
            rows.append(
                {
                    "scope": scope,
                    "mapping": f"m30_date_plus_{offset}_min_in_m15",
                    "m30_rows": int(len(m30_times)),
                    "matched_rows": int(hits.sum()),
                    "matched_pct": float(hits.mean() * 100.0) if len(hits) else 0.0,
                    "first_m30": m30_times.min() if len(m30_times) else "",
                    "last_m30": m30_times.max() if len(m30_times) else "",
                    "m15_start": m15_start,
                    "m15_end": m15_end,
                }
            )
    return pd.DataFrame(rows)


def h2_decision_alignment() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    m30 = load_with_time(PROCESSED_DIR / "m30_standardized.csv", "m30_processed")
    h2 = load_with_time(PROCESSED_DIR / "h2_context_bars.csv", "h2_processed")
    rows = []
    if {"source_time", "client_bucket_time", "decision_time"}.issubset(h2.columns):
        source = pd.to_datetime(h2["source_time"], errors="coerce")
        client = pd.to_datetime(h2["client_bucket_time"], errors="coerce")
        decision = pd.to_datetime(h2["decision_time"], errors="coerce")
        rows.append(
            {
                "check": "h2_source_to_client_minutes",
                "min": float(((client - source).dt.total_seconds() / 60.0).min()),
                "median": float(((client - source).dt.total_seconds() / 60.0).median()),
                "max": float(((client - source).dt.total_seconds() / 60.0).max()),
            }
        )
        rows.append(
            {
                "check": "h2_client_to_decision_minutes",
                "min": float(((decision - client).dt.total_seconds() / 60.0).min()),
                "median": float(((decision - client).dt.total_seconds() / 60.0).median()),
                "max": float(((decision - client).dt.total_seconds() / 60.0).max()),
            }
        )
        rows.append(
            {
                "check": "h2_source_to_decision_minutes",
                "min": float(((decision - source).dt.total_seconds() / 60.0).min()),
                "median": float(((decision - source).dt.total_seconds() / 60.0).median()),
                "max": float(((decision - source).dt.total_seconds() / 60.0).max()),
            }
        )

    h2_decision = pd.to_datetime(
        h2["decision_time"] if "decision_time" in h2.columns else h2["date_norm"], errors="coerce"
    ).dropna()
    h2_decision = h2_decision.drop_duplicates().sort_values()
    m30_times = m30["date_norm"].dropna().drop_duplicates().sort_values()
    mapped = pd.merge_asof(
        pd.DataFrame({"m30_time": m30_times}),
        pd.DataFrame({"h2_decision_time": h2_decision}),
        left_on="m30_time",
        right_on="h2_decision_time",
        direction="backward",
    )
    mapped["minutes_since_h2_decision"] = (
        mapped["m30_time"] - mapped["h2_decision_time"]
    ).dt.total_seconds() / 60.0
    bucket_counts = mapped["minutes_since_h2_decision"].value_counts(dropna=False).sort_index()
    for bucket, count in bucket_counts.items():
        rows.append(
            {
                "check": f"m30_to_latest_h2_decision_{bucket}_minutes",
                "min": bucket,
                "median": bucket,
                "max": bucket,
                "rows": int(count),
            }
        )
    anomalies = mapped[mapped["minutes_since_h2_decision"] > 90].copy()
    return pd.DataFrame(rows), mapped.head(2000), anomalies.head(500)


def mt5_export_shift_quality() -> tuple[pd.DataFrame, pd.DataFrame]:
    py = load_with_time(PROCESSED_DIR / "m30_standardized.csv", "python_m30_processed")
    mt5 = load_with_time(MT5_BAR_EXPORT, "mt5_bar_export")
    py_cols = ["date_norm", "close", "SMA_5", "SMA_13"]
    mt5_cols = ["date_norm", "close", "m30_sma5", "m30_sma13", "decision", "skip_reason"]
    py = py[[c for c in py_cols if c in py.columns]].rename(
        columns={"close": "py_close", "SMA_5": "py_sma5", "SMA_13": "py_sma13"}
    )
    mt5 = mt5[[c for c in mt5_cols if c in mt5.columns]].rename(
        columns={"close": "mt5_close", "m30_sma5": "mt5_sma5", "m30_sma13": "mt5_sma13"}
    )
    rows = []
    best_sample = pd.DataFrame()
    best_score: float | None = None
    for offset in [-240, -180, -120, -90, -60, -30, 0, 30, 60, 90, 120, 180, 240]:
        shifted = mt5.copy()
        shifted["date_shifted"] = shifted["date_norm"] + pd.Timedelta(minutes=offset)
        merged = py.merge(shifted, left_on="date_norm", right_on="date_shifted", how="inner")
        for left, right, out_col in [
            ("py_close", "mt5_close", "close_abs_diff"),
            ("py_sma5", "mt5_sma5", "sma5_abs_diff"),
            ("py_sma13", "mt5_sma13", "sma13_abs_diff"),
        ]:
            if left in merged.columns and right in merged.columns:
                merged[out_col] = (
                    pd.to_numeric(merged[left], errors="coerce")
                    - pd.to_numeric(merged[right], errors="coerce")
                ).abs()
        row: dict[str, object] = {
            "mt5_time_plus_offset_minutes": offset,
            "matched_rows": int(len(merged)),
        }
        for col in ["close_abs_diff", "sma5_abs_diff", "sma13_abs_diff"]:
            if col in merged.columns and merged[col].notna().any():
                row[f"{col}_mean"] = float(merged[col].mean())
                row[f"{col}_median"] = float(merged[col].median())
                row[f"{col}_p95"] = float(merged[col].quantile(0.95))
                row[f"{col}_max"] = float(merged[col].max())
                row[f"{col}_gt_1e-6"] = int((merged[col] > 1e-6).sum())
        rows.append(row)
        score = row.get("close_abs_diff_mean")
        if score is not None and (best_score is None or float(score) < best_score):
            best_score = float(score)
            sample_cols = [
                "date_norm_x",
                "date_norm_y",
                "date_shifted",
                "py_close",
                "mt5_close",
                "close_abs_diff",
                "py_sma5",
                "mt5_sma5",
                "sma5_abs_diff",
                "py_sma13",
                "mt5_sma13",
                "sma13_abs_diff",
                "decision",
                "skip_reason",
            ]
            best_sample = merged[[c for c in sample_cols if c in merged.columns]].head(200)
    return pd.DataFrame(rows), best_sample


def build_report(
    dataset_summary_df: pd.DataFrame,
    raw_sync_df: pd.DataFrame,
    timeframe_df: pd.DataFrame,
    h2_df: pd.DataFrame,
    shift_df: pd.DataFrame,
) -> str:
    def fmt(value: object) -> str:
        if pd.isna(value):
            return ""
        return str(value)

    best_close = shift_df.sort_values("close_abs_diff_mean", na_position="last").head(1)
    best_sma5 = shift_df.sort_values("sma5_abs_diff_mean", na_position="last").head(1)
    best_sma13 = shift_df.sort_values("sma13_abs_diff_mean", na_position="last").head(1)

    raw_same = int(raw_sync_df.get("same_sha256_12", pd.Series(dtype=bool)).fillna(False).sum())
    raw_total = int(len(raw_sync_df))
    m15_rows = timeframe_df[timeframe_df.get("scope", "").eq("m15_overlap_window")]
    m15_best = m15_rows.sort_values("matched_pct", ascending=False).head(1)
    h2_anomaly_rows = 0
    h2_rows = timeframe_df[timeframe_df["check"].astype(str).str.startswith("m30_to_latest_h2_decision_")]
    if not h2_rows.empty and "min" in h2_rows.columns and "rows" in h2_rows.columns:
        mins = pd.to_numeric(h2_rows["min"], errors="coerce")
        counts = pd.to_numeric(h2_rows["rows"], errors="coerce").fillna(0)
        h2_anomaly_rows = int(counts[mins > 90].sum())

    lines = [
        "# 时间语义与原始数据诊断（2026-07-12）",
        "",
        "## 结论摘要",
        f"- base/raw 文件同步：`{raw_same}/{raw_total}` 个核心文件的前 12 位 SHA256 一致；不一致项需要看是否只是 BOM/编码/截断差异。",
    ]
    if not best_close.empty:
        row = best_close.iloc[0]
        lines.append(
            "- MT5 bar export 与 Python M30 processed 的 close 最佳时间偏移："
            f"`MT5 bar_time + {fmt(row['mt5_time_plus_offset_minutes'])} min`，"
            f"匹配 `{fmt(row['matched_rows'])}` 行，close mean abs diff `{float(row['close_abs_diff_mean']):.6f}`。"
        )
    if not best_sma5.empty and not best_sma13.empty:
        row5 = best_sma5.iloc[0]
        row13 = best_sma13.iloc[0]
        lines.append(
            "- SMA 最佳偏移并不自动证明语义已对齐："
            f"SMA5 最佳 `{fmt(row5['mt5_time_plus_offset_minutes'])} min`，mean abs diff `{float(row5['sma5_abs_diff_mean']):.6f}`；"
            f"SMA13 最佳 `{fmt(row13['mt5_time_plus_offset_minutes'])} min`，mean abs diff `{float(row13['sma13_abs_diff_mean']):.6f}`。"
        )
    if not m15_best.empty:
        row = m15_best.iloc[0]
        lines.append(
            "- M15/M30 覆盖关系最佳映射："
            f"`{fmt(row['mapping'])}`，覆盖 `{float(row['matched_pct']):.2f}%`。"
        )
    source_to_decision = h2_df[h2_df["check"].eq("h2_source_to_decision_minutes")]
    if not source_to_decision.empty:
        row = source_to_decision.iloc[0]
        lines.append(
            "- H2 context 当前保留三种时间："
            f"`source_time -> decision_time` 中位偏移 `{float(row['median']):.0f} min`，这确认 H2 不是单一 date 口径。"
        )
    lines.append(f"- M30 映射到最近 H2 decision 后仍有 `{h2_anomaly_rows}` 行超过常规 `0/30/60/90 min` 桶，需要作为数据缺口/休市窗口处理。")
    lines.extend(
        [
            "- 当前仍不能把 MT5-only bar export 直接当成完整信号源：它只覆盖 bar 级 M30 导出，M15 SLOT1 仍要依赖 tester log 或后续 trade ledger。",
            "",
            "## 输出文件",
            "- `time_semantics_dataset_summary_20260712.csv`：核心输入文件的行数、时间范围、重复时间、close 摘要。",
            "- `raw_sync_consistency_20260712.csv`：base_data 与策略 raw 的同步对比。",
            "- `timeframe_alignment_20260712.csv`：M15/M30 与 H2 decision bucket 映射检查。",
            "- `mt5_export_shift_quality_20260712.csv`：不同时间偏移下 MT5 export 与 Python M30 processed 的 close/SMA 匹配质量。",
            "- `mt5_export_best_shift_sample_20260712.csv`：close 最佳偏移下的前 200 行样本。",
            "",
            "## 后续动作",
            "1. 先解释 raw/full_data 不一致项是编码/BOM 还是真实数据差异。",
            "2. 用当前最佳偏移结果复核 `bar_time` 是否代表 MT5 completed bar、EA aligned anchor，还是 tester 新 bar 时间。",
            "3. 在重建 Python-MT5 数据版前，先固定 H2 的 `source_time/client_bucket_time/decision_time` 使用规则。",
            "4. MT5 侧下一步必须补 `trade ledger` 或更完整的 M15 SLOT1 bar-level export，否则胜率、止损次数和资金曲线仍不能可靠并表。",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    dataset_specs = [
        ("base_XAUUSDm30", BASE_DIR / "XAUUSDm30.csv", "base_data"),
        ("base_XAUUSDm15", BASE_DIR / "XAUUSDm15.csv", "base_data"),
        ("base_H2_XAUUSDm_39col", BASE_DIR / "H2_XAUUSDm_39col.csv", "base_data"),
        ("base_full_data_30m2h", BASE_DIR / "full_data_30m2h.csv", "base_data"),
        ("raw_XAUUSDm30", RAW_DIR / "XAUUSDm30.csv", "strategy_raw"),
        ("raw_XAUUSDm15", RAW_DIR / "XAUUSDm15.csv", "strategy_raw"),
        ("raw_H2_XAUUSDm_39col", RAW_DIR / "H2_XAUUSDm_39col.csv", "strategy_raw"),
        ("raw_full_data_30m2h", RAW_DIR / "full_data_30m2h.csv", "strategy_raw"),
        ("processed_m30_standardized", PROCESSED_DIR / "m30_standardized.csv", "strategy_processed"),
        ("processed_m30_mt5", PROCESSED_DIR / "m30_mt5.csv", "strategy_processed"),
        ("processed_m15_context", PROCESSED_DIR / "m15_context_bars.csv", "strategy_processed"),
        ("processed_h2_context", PROCESSED_DIR / "h2_context_bars.csv", "strategy_processed"),
        ("mt5_only_bar_export", MT5_BAR_EXPORT, "mt5_export"),
    ]
    dataset_summary_df = pd.DataFrame([dataset_summary(*spec) for spec in dataset_specs])
    raw_sync_df = raw_sync_summary()
    m15_m30_df = m15_m30_alignment()
    h2_df, h2_sample_df, h2_anomaly_df = h2_decision_alignment()
    timeframe_df = pd.concat([m15_m30_df, h2_df], ignore_index=True, sort=False)
    shift_df, best_shift_sample = mt5_export_shift_quality()

    export_csv(dataset_summary_df, OUT_DIR / "time_semantics_dataset_summary_20260712.csv")
    export_csv(raw_sync_df, OUT_DIR / "raw_sync_consistency_20260712.csv")
    export_csv(timeframe_df, OUT_DIR / "timeframe_alignment_20260712.csv")
    export_csv(h2_sample_df, OUT_DIR / "h2_decision_mapping_sample_20260712.csv")
    export_csv(h2_anomaly_df, OUT_DIR / "h2_decision_anomaly_sample_20260712.csv")
    export_csv(shift_df, OUT_DIR / "mt5_export_shift_quality_20260712.csv")
    export_csv(best_shift_sample, OUT_DIR / "mt5_export_best_shift_sample_20260712.csv")
    report = build_report(dataset_summary_df, raw_sync_df, timeframe_df, h2_df, shift_df)
    write_text(OUT_DIR / "time_semantics_diagnosis_20260712.md", report)
    print(report)


if __name__ == "__main__":
    main()
