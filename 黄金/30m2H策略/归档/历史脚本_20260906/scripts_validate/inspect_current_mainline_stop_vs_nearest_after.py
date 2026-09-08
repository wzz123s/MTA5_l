# -*- coding: utf-8 -*-
"""Inspect current-mainline MT5-only gaps: exact stop, nearest_after, and M15 price proxies."""
from __future__ import annotations


import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
ROOT_SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(STRATEGY_SCRIPTS_DIR))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT_SCRIPTS_DIR))

from strategy_30m2h_common import VALIDATION_DIR, export_csv, write_text  # noqa: E402
import _current_baseline as cb  # type: ignore  # noqa: E402
import _h2_early_gate_test as h2t  # type: ignore  # noqa: E402
import _m15_early_entry_test as m15t  # type: ignore  # noqa: E402
import _m15_h2_combo_test as combo  # type: ignore  # noqa: E402


CURRENT_MAINLINE_DIR = (
    VALIDATION_DIR / "mt5_log_session_diff_current_mainline_20260708" / "session_01" / "session_01"
)
OUTPUT_DIR = VALIDATION_DIR / "mt5_log_session_diag_current_mainline_20260708" / "session_01" / "session_01"


def normalize_mode(mode: str) -> str:
    if mode.startswith("pre_cross"):
        return "pre_cross"
    if mode.startswith("cross"):
        return "cross"
    if mode.startswith("post_n"):
        return mode.split("_", 2)[0] if "_" in mode else mode
    return mode


def find_candidate(raw_df: pd.DataFrame, anchor_time: pd.Timestamp, direction: str, mode_raw: str, exact_only: bool) -> pd.Series | None:
    target_norm = normalize_mode(mode_raw)
    subset = raw_df[raw_df["dir"] == direction].copy()
    subset["mode_norm"] = subset["mode"].astype(str).map(normalize_mode)
    subset = subset[subset["mode_norm"] == target_norm]
    if exact_only:
        subset = subset[pd.to_datetime(subset["date"]) == anchor_time]
        if subset.empty:
            return None
        return subset.sort_values("date").iloc[0]

    subset = subset[
        (pd.to_datetime(subset["date"]) > anchor_time)
        & (pd.to_datetime(subset["date"]) <= anchor_time + pd.Timedelta(hours=2))
    ]
    if subset.empty:
        return None
    return subset.sort_values("date").iloc[0]


def prior_segment_start(i: int, direction: np.ndarray) -> int | None:
    k = i - 1
    while k >= 0 and direction[k] not in ("good", "bad"):
        k -= 1
    return k if k >= 0 else None


def segment_variant_metrics(i: int, is_long: bool, direction: np.ndarray, sma13: np.ndarray) -> dict[str, object]:
    k = prior_segment_start(i, direction)
    if k is None:
        return {"边界微调同值": False, "基准止损": np.nan}

    variants = {
        "k:i": sma13[k:i],
        "k+1:i": sma13[k + 1 : i],
        "k:i+1": sma13[k : i + 1],
        "k+1:i+1": sma13[k + 1 : i + 1],
        "k-1:i": sma13[max(0, k - 1) : i],
    }
    values: list[float] = []
    for seg in variants.values():
        seg = seg[~np.isnan(seg)]
        if len(seg) == 0:
            continue
        values.append(float(np.nanmin(seg) if is_long else np.nanmax(seg)))
    if not values:
        return {"边界微调同值": False, "基准止损": np.nan}
    base = values[0]
    same = all(abs(v - base) < 1e-9 for v in values[1:])
    return {"边界微调同值": same, "基准止损": base}


def add_candidate_fields(detail: dict[str, object], prefix: str, candidate: pd.Series | None, direction_arr: np.ndarray, sma13: np.ndarray) -> None:
    if candidate is None:
        detail[f"{prefix}候选时间"] = pd.NaT
        detail[f"{prefix}候选模式"] = ""
        detail[f"{prefix}候选入场"] = np.nan
        detail[f"{prefix}候选止损"] = np.nan
        detail[f"{prefix}候选止损距离"] = np.nan
        detail[f"{prefix}候选spec"] = ""
        detail[f"{prefix}边界微调同值"] = False
        return

    is_long = str(candidate["dir"]) == "L"
    metrics = segment_variant_metrics(int(candidate["i"]), is_long, direction_arr, sma13)
    detail[f"{prefix}候选时间"] = pd.Timestamp(candidate["date"])
    detail[f"{prefix}候选模式"] = str(candidate["mode"])
    detail[f"{prefix}候选入场"] = round(float(candidate["entry"]), 6)
    detail[f"{prefix}候选止损"] = round(float(candidate["stop"]), 6)
    detail[f"{prefix}候选止损距离"] = round(float(candidate["sd"]), 6)
    detail[f"{prefix}候选spec"] = str(candidate.get("spec_reason", ""))
    detail[f"{prefix}边界微调同值"] = bool(metrics["边界微调同值"])


def m15_rows(m15: pd.DataFrame, anchor_time: pd.Timestamp) -> tuple[pd.Series | None, pd.Series | None]:
    seg = m15t.m15_window(m15, anchor_time)
    if seg.empty:
        return None, None
    slot1 = seg.iloc[0] if len(seg) >= 1 else None
    slot2 = seg.iloc[1] if len(seg) >= 2 else None
    return slot1, slot2


def add_proxy_fields(detail: dict[str, object], prefix: str, row: pd.Series | None, stop_price: float | None) -> None:
    price_cols = ("open", "high", "low", "close")
    if row is None or stop_price is None:
        detail[f"{prefix}时间"] = pd.NaT
        for col in price_cols:
            detail[f"{prefix}_{col}_止损距离"] = np.nan
        return

    detail[f"{prefix}时间"] = pd.Timestamp(row["date"])
    for col in price_cols:
        detail[f"{prefix}_{col}_止损距离"] = round(abs(float(row[col]) - stop_price), 6)


def best_proxy_label(detail: dict[str, object], mt5_sd: float) -> tuple[str, float]:
    best_name = ""
    best_err = np.inf
    for key, value in detail.items():
        if not key.endswith("_止损距离") or pd.isna(value):
            continue
        err = abs(float(value) - mt5_sd)
        if err < best_err:
            best_name = key.replace("_止损距离", "")
            best_err = err
    return best_name, best_err


def classify_row(detail: dict[str, object]) -> str:
    exact_sd = detail.get("同锚点候选止损距离")
    nearest_sd = detail.get("顺延候选止损距离")
    mt5_sd = float(detail["MT5止损距离"])
    proxy_name = str(detail.get("最接近MT5的M15代理", ""))
    proxy_err = float(detail.get("代理误差", np.nan)) if pd.notna(detail.get("代理误差")) else np.nan

    if pd.notna(exact_sd):
        exact_err = abs(float(exact_sd) - mt5_sd)
        if proxy_name and pd.notna(proxy_err) and proxy_err + 1e-9 < exact_err:
            return "同锚点候选已存在，但更像执行时报价差"
        return "同锚点候选已存在，优先看执行口径"
    if pd.notna(nearest_sd):
        nearest_err = abs(float(nearest_sd) - mt5_sd)
        if proxy_name and pd.notna(proxy_err) and proxy_err + 1e-9 < nearest_err:
            return "只有顺延候选，但顺延仍不如M15代理接近MT5"
        return "只有顺延候选，需继续复核顺延锚点"
    return "无同模式候选，需继续复核信号生成"


def render_markdown(detail: pd.DataFrame, summary: pd.DataFrame) -> str:
    lines = [
        "# current_mainline MT5独有样本止损/顺延复核",
        "",
        "## 汇总",
        "",
        summary.to_markdown(index=False),
        "",
        "## 逐笔明细",
        "",
        detail[
            [
                "锚点时间",
                "方向",
                "触发类型",
                "原始模式",
                "MT5止损距离",
                "同锚点候选时间",
                "同锚点候选止损距离",
                "同锚点候选spec",
                "顺延候选时间",
                "顺延候选止损距离",
                "顺延候选spec",
                "最接近MT5的M15代理",
                "代理误差",
                "诊断结论",
            ]
        ].to_markdown(index=False),
        "",
        "## 判断口径",
        "",
        "- “同锚点候选”指 Python 原始候选里同时间、同方向、同模式族的样本。",
        "- “顺延候选”指同方向、同模式族、未来 2 小时内最早出现的样本。",
        "- “边界微调同值”表示把 prior segment 的切片起止做微调后，止损极值仍完全不变，可用来排除 `FindStopSMA` 的简单边界误差。",
        "- “最接近MT5的M15代理”只用于诊断执行报价差，不代表应直接替换主线执行逻辑。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    df, h2, m15 = cb.load_market_context()
    q2_pass_set, q2_factor_map, _, _ = h2t.early_precompute(h2, df, 2, False)
    raw_df, _ = combo.build_candidate_frames(df, q2_pass_set, q2_factor_map)
    raw_df = raw_df.copy()
    raw_df["date"] = pd.to_datetime(raw_df["date"])

    df = df.copy().reset_index(drop=True)
    df["date"] = pd.to_datetime(df["date"])
    direction_arr = df["方向"].values
    sma13 = df["SMA_13"].values

    m15 = m15.copy()
    m15["date"] = pd.to_datetime(m15["date"])

    mt5_only = pd.read_csv(CURRENT_MAINLINE_DIR / "mt5_only_signals.csv", encoding="utf-8-sig")
    mt5_only["anchor_time"] = pd.to_datetime(mt5_only["anchor_time"])
    mt5_only = mt5_only[mt5_only["trigger"] == "M15 SLOT1"].copy().sort_values("anchor_time").reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for _, row in mt5_only.iterrows():
        anchor_time = pd.Timestamp(row["anchor_time"])
        direction = str(row["dir"])
        mode_raw = str(row["mode_raw"])
        mt5_sd = float(row["mt5_stop_dist"])

        exact = find_candidate(raw_df, anchor_time, direction, mode_raw, exact_only=True)
        nearest_after = find_candidate(raw_df, anchor_time, direction, mode_raw, exact_only=False)
        chosen_for_proxy = exact if exact is not None else nearest_after
        stop_price = float(chosen_for_proxy["stop"]) if chosen_for_proxy is not None else None
        slot1, slot2 = m15_rows(m15, anchor_time)

        detail: dict[str, object] = {
            "锚点时间": anchor_time,
            "方向": direction,
            "触发类型": str(row["trigger"]),
            "原始模式": mode_raw,
            "MT5止损距离": mt5_sd,
        }
        add_candidate_fields(detail, "同锚点", exact, direction_arr, sma13)
        add_candidate_fields(detail, "顺延", nearest_after, direction_arr, sma13)
        add_proxy_fields(detail, "slot1", slot1, stop_price)
        add_proxy_fields(detail, "slot2", slot2, stop_price)
        proxy_name, proxy_err = best_proxy_label(detail, mt5_sd)
        detail["最接近MT5的M15代理"] = proxy_name
        detail["代理误差"] = round(proxy_err, 6) if np.isfinite(proxy_err) else np.nan
        detail["诊断结论"] = classify_row(detail)
        rows.append(detail)

    detail_df = pd.DataFrame(rows)
    summary = pd.DataFrame(
        [
            {
                "MT5独有_M15样本数": int(len(detail_df)),
                "存在同锚点候选数": int(detail_df["同锚点候选时间"].notna().sum()) if not detail_df.empty else 0,
                "只有顺延候选数": int((detail_df["同锚点候选时间"].isna() & detail_df["顺延候选时间"].notna()).sum()) if not detail_df.empty else 0,
                "无同模式候选数": int((detail_df["同锚点候选时间"].isna() & detail_df["顺延候选时间"].isna()).sum()) if not detail_df.empty else 0,
                "同锚点边界微调仍同值数": int(detail_df["同锚点边界微调同值"].fillna(False).sum()) if "同锚点边界微调同值" in detail_df else 0,
                "更像执行报价差样本数": int(detail_df["诊断结论"].astype(str).str.contains("执行时报价差").sum()) if not detail_df.empty else 0,
            }
        ]
    )

    export_csv(detail_df, OUTPUT_DIR / "mt5独有_stop与顺延明细_20260708.csv")
    export_csv(summary, OUTPUT_DIR / "mt5独有_stop与顺延汇总_20260708.csv")
    write_text(OUTPUT_DIR / "mt5独有_stop与顺延复核_20260708.md", render_markdown(detail_df, summary))
    print(f"Wrote {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
