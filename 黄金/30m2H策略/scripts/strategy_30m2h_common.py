# -*- coding: utf-8 -*-
"""Shared helpers for the 30m x 2H mainline strategy workspace."""
from __future__ import annotations

import math
import shutil
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = ROOT / "黄金" / "30m2H策略"
SCRIPTS_DIR = STRATEGY_DIR / "scripts"
DATA_DIR = STRATEGY_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SIGNALS_DIR = DATA_DIR / "signals"
VALIDATION_DIR = DATA_DIR / "validation"
RESULTS_DIR = ROOT / "data" / "results"
GLOBAL_VALIDATION_DIR = ROOT / "shadow_tests" / "multi_tf_matrix" / "data" / "validation_20260701"
COMBO = "30M_2H_MAINLINE"
START_CAPITAL = 500.0
EXECUTION_PNL_MULTIPLIER = 5.0
EXECUTION_LOTS = "0.05"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import _current_baseline as cb  # type: ignore  # noqa: E402


RESULT_SOURCES = {
    "current_strategy": RESULTS_DIR / "current_strategy_20260627",
    "m15_h2_early_trigger": RESULTS_DIR / "m15_h2_early_trigger_20260626",
    "layer1_strict": RESULTS_DIR / "layer1_strict_certify_20260628",
    "layer3_strict": RESULTS_DIR / "layer3_strict_certify_20260627",
    "stage12": RESULTS_DIR / "stage12_combo_20260627",
    "stop_spec": RESULTS_DIR / "stop_spec_strict_certify_20260627",
    "position_sizing": RESULTS_DIR / "position_sizing_strict_certify_20260628",
    "ea_python_diff": RESULTS_DIR / "ea_python_signal_diff_20260704",
}


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


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def copy_source_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def read_csv_with_fallback(path: Path, encodings: list[str] | None = None) -> pd.DataFrame:
    attempts = encodings or ["utf-8-sig", "utf-8", "gbk"]
    last_error: Exception | None = None
    for encoding in attempts:
        try:
            return pd.read_csv(path, encoding=encoding)
        except Exception as exc:  # pragma: no cover - fallback path
            last_error = exc
    raise RuntimeError(f"Unable to read CSV: {path}") from last_error


def load_strategy_result(ea_executable_diag: bool = False) -> dict:
    return cb.summarize_strategy(ea_executable_diag=ea_executable_diag)


def build_processed_frames() -> dict[str, pd.DataFrame]:
    raw_m30, h2, m15 = cb.load_market_context()
    return {
        "m30_standardized": raw_m30.copy(),
        "h2_context_bars": h2.copy(),
        "m15_context_bars": m15.copy(),
    }


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def _profit_factor(points: pd.Series) -> float:
    gross_profit = float(points[points > 0].sum())
    gross_loss = float((-points[points < 0]).sum())
    if gross_loss == 0:
        return math.inf if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def build_summary_rows(result: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    accepted = result["accepted"].copy()
    picked = result["picked"].copy()
    trades = result["trades"].copy()

    if not accepted.empty:
        accepted["date"] = pd.to_datetime(accepted["date"])
    if not picked.empty:
        picked["date"] = pd.to_datetime(picked["date"])
        picked["entry_time"] = pd.to_datetime(picked["entry_time"])
    if not trades.empty:
        trades["date"] = pd.to_datetime(trades["date"])
        trades["stage3_time"] = pd.to_datetime(trades["stage3_time"])

    base_profit = float(trades["total_$"].sum()) if not trades.empty else 0.0
    total_profit = base_profit * EXECUTION_PNL_MULTIPLIER
    final_capital = START_CAPITAL + total_profit
    total_trades = int(len(trades))
    win_count = int((trades["total_points"] > 0).sum()) if not trades.empty else 0
    loss_count = total_trades - win_count
    win_rate = _safe_ratio(win_count, total_trades) * 100.0
    pf = _profit_factor(trades["total_points"]) if not trades.empty else 0.0
    stage1_stop = int((trades["stage1_exit"] == "SL hit").sum()) if not trades.empty else 0
    stage2_stop = int(trades["stage2_exit"].astype(str).str.contains("SL", regex=False).sum()) if not trades.empty else 0
    stage3_stop = int(trades["stage3_exit"].astype(str).str.contains("SL", regex=False).sum()) if not trades.empty else 0
    any_stop_mask = (
        (trades["stage1_exit"] == "SL hit")
        | trades["stage2_exit"].astype(str).str.contains("SL", regex=False)
        | trades["stage3_exit"].astype(str).str.contains("SL", regex=False)
    ) if not trades.empty else pd.Series(dtype=bool)
    full_stop_mask = (
        (trades["stage1_exit"] == "SL hit")
        & trades["stage2_exit"].astype(str).str.contains("SL", regex=False)
        & trades["stage3_exit"].astype(str).str.contains("SL", regex=False)
    ) if not trades.empty else pd.Series(dtype=bool)
    any_stop_count = int(any_stop_mask.sum()) if not trades.empty else 0
    full_stop_count = int(full_stop_mask.sum()) if not trades.empty else 0
    any_stop_ratio = _safe_ratio(any_stop_count, total_trades) * 100.0
    full_stop_ratio = _safe_ratio(full_stop_count, total_trades) * 100.0

    summary = pd.DataFrame(
        [
            {
                "策略": "30m2H主线",
                "组合编码": COMBO,
                "原始资金": START_CAPITAL,
                "当前执行倍率": EXECUTION_PNL_MULTIPLIER,
                "当前手数": EXECUTION_LOTS,
                "候选信号数": int(len(accepted)),
                "Layer3入选信号数": int(len(picked)),
                "执行交易数": total_trades,
                "盈利笔数": win_count,
                "亏损笔数": loss_count,
                "胜率(%)": round(win_rate, 4),
                "Stage1止损笔数": stage1_stop,
                "Stage2含SL笔数": stage2_stop,
                "Stage3含SL笔数": stage3_stop,
                "任一阶段止损笔数": any_stop_count,
                "任一阶段止损占比(%)": round(any_stop_ratio, 4),
                "三阶段均止损笔数": full_stop_count,
                "三阶段均止损占比(%)": round(full_stop_ratio, 4),
                "基础口径总盈利($)": round(base_profit, 4),
                "总盈利($)": round(total_profit, 4),
                "最终资金额($)": round(final_capital, 4),
                "平均单笔收益($)": round(_safe_ratio(total_profit, total_trades), 4),
                "最大盈亏比": round(float(trades["total_points"].max()), 6) if not trades.empty else 0.0,
                "最小盈亏比": round(float(trades["total_points"].min()), 6) if not trades.empty else 0.0,
                "平均盈亏比": round(float(trades["total_points"].mean()), 6) if not trades.empty else 0.0,
                "中位数盈亏比": round(float(trades["total_points"].median()), 6) if not trades.empty else 0.0,
                "利润因子PF": round(float(pf), 6) if math.isfinite(pf) else "inf",
                "Layer3阈值": round(float(result["threshold"]), 6) if pd.notna(result["threshold"]) else "",
                "Stage参数": "2.0 / 1.5 / 4.0",
                "止损范围(pt)": "[5, 35]",
            }
        ]
    )

    if trades.empty:
        years = pd.DataFrame(columns=["年份", "交易次数", "盈利($)", "止损次数", "胜率(%)"])
    else:
        years = (
            trades.assign(
                年份=trades["date"].dt.year,
                是否盈利=trades["total_points"] > 0,
                是否止损=any_stop_mask.values,
                是否三段均止损=full_stop_mask.values,
            )
            .groupby("年份", as_index=False)
            .agg(
                交易次数=("date", "size"),
                基础盈利=("total_$", "sum"),
                止损次数=("是否止损", "sum"),
                三段均止损次数=("是否三段均止损", "sum"),
                胜率=("是否盈利", "mean"),
            )
        )
        years["基础盈利($)"] = years["基础盈利"].round(4)
        years["盈利($)"] = (years["基础盈利"] * EXECUTION_PNL_MULTIPLIER).round(4)
        years["胜率(%)"] = (years["胜率"] * 100.0).round(4)
        years = years.drop(columns=["基础盈利", "胜率"])

    return summary, years


def annualized_return_from_trades(trades: pd.DataFrame, start_capital: float = START_CAPITAL) -> float:
    if trades.empty:
        return 0.0
    dates = pd.to_datetime(trades["date"]).sort_values()
    start = dates.iloc[0]
    end = dates.iloc[-1]
    years = max((end - start).days / 365.25, 1.0 / 365.25)
    final_capital = start_capital + float(trades["total_$"].sum()) * EXECUTION_PNL_MULTIPLIER
    if start_capital <= 0 or final_capital <= 0:
        return 0.0
    return (final_capital / start_capital) ** (1.0 / years) - 1.0


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "| 空 | 空 |\n| --- | --- |"
    headers = list(frame.columns)
    lines = [
        "| " + " | ".join(str(x) for x in headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in headers) + " |")
    return "\n".join(lines)
