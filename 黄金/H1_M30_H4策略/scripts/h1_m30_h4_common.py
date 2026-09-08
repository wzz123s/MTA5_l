# -*- coding: utf-8 -*-
"""Shared helpers for the H1_M30_H4 strategy workspace."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
STRATEGY_DIR = ROOT / "H1_M30_H4策略"
SCRIPTS_DIR = STRATEGY_DIR / "scripts"
DATA_DIR = STRATEGY_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SIGNALS_DIR = DATA_DIR / "signals"
VALIDATION_DIR = DATA_DIR / "validation"
GLOBAL_VALIDATION_DIR = ROOT / "shadow_tests" / "multi_tf_matrix" / "data" / "validation_20260701"
COMBO = "H1_M30_H4"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "shadow_tests" / "multi_tf_matrix" / "scripts"))

from _multi_tf_matrix_common import TIMEFRAME_MATRIX  # type: ignore  # noqa: E402


FINAL_SUMMARY_COLS = [
    "combo",
    "picked_variant",
    "picked_desc",
    "picked_n",
    "picked_pf",
    "picked_ev",
    "picked_test_pf",
    "picked_test_ev",
    "stage1_r",
    "stage2_trail_r",
    "stage2_force_r",
    "stage_pf",
    "stage_ev",
    "stage_test_pf",
    "stage_test_ev",
    "units",
    "lots",
    "final_pf",
    "final_ev",
    "final_pnl_$",
    "final_test_pf",
    "final_test_ev",
]

COMBINED_SUMMARY_COLS = [
    "combo",
    "current_variant",
    "variant_desc",
    "gate_range",
    "stage_params",
    "units",
    "lots",
    "focus_tf",
    "stop_main",
    "stop_second",
    "stop_ok",
    "stop_grid_lo",
    "stop_grid_hi",
    "stop_desc",
    "stop_pf",
    "stop_test_pf",
    "stop_ev",
    "stop_profit",
]

CAPITAL_BASE_COLS = [
    "combo",
    "final_variant",
    "variant_desc",
    "stage_params",
    "units",
    "lots",
    "start_capital",
    "total_trades",
    "final_capital",
    "total_profit",
    "avg_stop_pt",
    "median_stop_pt",
    "max_r",
    "min_r",
    "avg_r",
    "median_r",
    "stop_count",
    "stop_ratio",
]

STOP_SCAN_COLS = [
    "combo",
    "current_variant",
    "focus_tf",
    "stop_range",
    "stop_lo",
    "stop_hi",
    "grid_lo",
    "grid_hi",
    "trades",
    "wr",
    "pf",
    "ev",
    "profit",
    "test_pf",
    "test_ev",
    "avg_stop",
    "median_stop",
    "sample_ok",
    "score",
]

GATE_SCAN_COLS = [
    "combo",
    "current_variant",
    "focus_tf",
    "gate_family",
    "gate_param",
    "desc",
    "trades",
    "wr",
    "pf",
    "ev",
    "test_pf",
    "test_ev",
]


def ensure_dirs() -> None:
    for path in [
        RAW_DIR,
        PROCESSED_DIR,
        SIGNALS_DIR,
        VALIDATION_DIR,
        SCRIPTS_DIR / "data_source",
        SCRIPTS_DIR / "prepare",
        SCRIPTS_DIR / "signals",
        SCRIPTS_DIR / "validate",
        SCRIPTS_DIR / "bundle",
    ]:
        path.mkdir(parents=True, exist_ok=True)


def strategy_spec() -> dict:
    for item in TIMEFRAME_MATRIX:
        if item["name"] == COMBO:
            return item
    raise KeyError(f"Strategy combo not found: {COMBO}")


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def read_csv_with_fallback(path: Path, encodings: list[str] | None = None) -> pd.DataFrame:
    attempts = encodings or ["utf-8-sig", "utf-8", "gbk"]
    last_error: Exception | None = None
    for encoding in attempts:
        try:
            return pd.read_csv(path, encoding=encoding)
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc
    raise RuntimeError(f"Unable to read CSV: {path}") from last_error


def rename_by_position(frame: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    out = frame.copy()
    out.columns = names + list(out.columns[len(names):])
    return out


def filter_combo(frame: pd.DataFrame, combo_col: str = "combo") -> pd.DataFrame:
    return frame.loc[frame[combo_col] == COMBO].copy().reset_index(drop=True)


def load_final_summary(local_first: bool = True) -> pd.Series:
    path = VALIDATION_DIR / "combo_final_best_summary.csv" if local_first else GLOBAL_VALIDATION_DIR / "combo_final_best_summary.csv"
    if not path.exists():
        path = GLOBAL_VALIDATION_DIR / "combo_final_best_summary.csv"
    df = read_csv_with_fallback(path)
    df = rename_by_position(df, FINAL_SUMMARY_COLS)
    return filter_combo(df).iloc[0]


def load_combined_summary(local_first: bool = True) -> pd.Series:
    path = VALIDATION_DIR / "combo_combined_summary.csv" if local_first else GLOBAL_VALIDATION_DIR / "组合参数总表_门区间_止损区间_中文.csv"
    if not path.exists():
        path = GLOBAL_VALIDATION_DIR / "组合参数总表_门区间_止损区间_中文.csv"
    df = read_csv_with_fallback(path)
    df = rename_by_position(df, COMBINED_SUMMARY_COLS)
    return filter_combo(df).iloc[0]


def load_capital_metrics(local_first: bool = True) -> pd.Series:
    path = VALIDATION_DIR / "combo_final_capital_metrics.csv" if local_first else GLOBAL_VALIDATION_DIR / "组合最终资金指标_中文_utf8.csv"
    if not path.exists():
        path = GLOBAL_VALIDATION_DIR / "组合最终资金指标_中文_utf8.csv"
    df = read_csv_with_fallback(path)
    year_cols: list[str] = []
    for year in range(2020, 2027):
        year_cols.extend([f"y{year}_trades", f"y{year}_profit", f"y{year}_stops"])
    df = rename_by_position(df, CAPITAL_BASE_COLS + year_cols)
    return filter_combo(df).iloc[0]


def load_stop_scan(local_first: bool = True) -> pd.DataFrame:
    path = VALIDATION_DIR / "combo_stop_range_scan.csv" if local_first else GLOBAL_VALIDATION_DIR / "组合止损范围测试_中文.csv"
    if not path.exists():
        path = GLOBAL_VALIDATION_DIR / "组合止损范围测试_中文.csv"
    df = read_csv_with_fallback(path)
    df = rename_by_position(df, STOP_SCAN_COLS)
    return filter_combo(df)


def load_gate_scan(local_first: bool = True) -> pd.DataFrame:
    path = VALIDATION_DIR / "combo_gate_range_scan.csv" if local_first else GLOBAL_VALIDATION_DIR / "组合门范围细扫_中文.csv"
    if not path.exists():
        path = GLOBAL_VALIDATION_DIR / "组合门范围细扫_中文.csv"
    df = read_csv_with_fallback(path)
    df = rename_by_position(df, GATE_SCAN_COLS)
    return filter_combo(df)


def load_top3_stage(local_first: bool = True) -> pd.DataFrame:
    path = VALIDATION_DIR / "combo_top3_stage12.csv" if local_first else GLOBAL_VALIDATION_DIR / "combo_top3_stage12.csv"
    if not path.exists():
        path = GLOBAL_VALIDATION_DIR / "combo_top3_stage12.csv"
    df = read_csv_with_fallback(path)
    return filter_combo(df)


def load_top3_position(local_first: bool = True) -> pd.DataFrame:
    path = VALIDATION_DIR / "combo_top3_position.csv" if local_first else GLOBAL_VALIDATION_DIR / "combo_top3_position.csv"
    if not path.exists():
        path = GLOBAL_VALIDATION_DIR / "combo_top3_position.csv"
    df = read_csv_with_fallback(path)
    return filter_combo(df)


def load_candidate_trades() -> pd.DataFrame:
    path = SIGNALS_DIR / "strategy_candidate_trades.csv"
    if not path.exists():
        path = VALIDATION_DIR / "strategy_candidate_trades.csv"
    return read_csv_with_fallback(path)


def load_variant_summary() -> pd.DataFrame:
    path = SIGNALS_DIR / "strategy_variant_summary.csv"
    if not path.exists():
        path = VALIDATION_DIR / "strategy_variant_summary.csv"
    return read_csv_with_fallback(path)


def write_text(name: str, text: str) -> None:
    path = STRATEGY_DIR / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def copy_source_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
