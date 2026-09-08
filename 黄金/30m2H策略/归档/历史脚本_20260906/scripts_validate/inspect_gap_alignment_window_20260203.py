# -*- coding: utf-8 -*-
"""Inspect the raw/prepared gap window around 2026-02-03 01:00 alignment mismatch."""
from __future__ import annotations


import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
ROOT_SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(STRATEGY_SCRIPTS_DIR))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT_SCRIPTS_DIR))

from strategy_30m2h_common import VALIDATION_DIR, export_csv, write_text  # noqa: E402
from processing.prepare import prepare  # noqa: E402


OUTPUT_DIR = VALIDATION_DIR / "mt5_log_session_diag_current_mainline_20260708" / "session_01" / "session_01"
TARGET_RAW_ANCHOR = pd.Timestamp("2026-02-02 23:30:00")
TARGET_ALIGN_PLUS_90 = TARGET_RAW_ANCHOR + pd.Timedelta(minutes=90)


def load_raw_m30() -> pd.DataFrame:
    df = pd.read_csv("base_data/XAUUSDm30.csv", encoding="gbk")
    df.columns = ["date", "open", "high", "low", "close", "volume", "spread", "real_volume", "symbol", "time_diff"]
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def load_raw_m15() -> pd.DataFrame:
    df = pd.read_csv("base_data/XAUUSDm15.csv", encoding="gbk")
    df.columns = ["date", "open", "high", "low", "close", "volume", "spread", "real_volume", "symbol", "time_diff"]
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def add_gap_minutes(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["gap_minutes"] = out["date"].diff().dt.total_seconds().div(60)
    return out


def render_markdown(summary: pd.DataFrame, raw_m30: pd.DataFrame, raw_m15: pd.DataFrame, prep_m30: pd.DataFrame) -> str:
    lines = [
        "# 2026-02-03 对齐缺口窗口复核",
        "",
        "## 汇总",
        "",
        summary.to_markdown(index=False),
        "",
        "## 原始 M30 窗口",
        "",
        raw_m30.to_markdown(index=False),
        "",
        "## 原始 M15 窗口",
        "",
        raw_m15.to_markdown(index=False),
        "",
        "## Python prepared M30 窗口",
        "",
        prep_m30.to_markdown(index=False),
        "",
        "## 结论",
        "",
        "- 原始数据在该窗口确实存在时间缺口，不是 `prepare()` 额外制造出来的。",
        "- 对这笔 MT5 日志来说，`mt5_raw_anchor_time = 2026-02-02 23:30:00`。",
        "- 按固定 `+90分钟` 对齐后会落到 `2026-02-03 01:00:00`，但这根 bar 不在 Python M30 时间轴上。",
        "- 当前窗口下，Python prepared M30 的下一根可用 bar 是 `2026-02-03 01:30:00`，相当于这笔在 gap 场景下实际更像 `+120分钟`。",
        "- 因此这笔不能只按普通 `nearest_after` 处理；它先是“gap 导致的对齐缺口”，然后才是“顺延后止损距离仍不一致”。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    raw_m30 = add_gap_minutes(load_raw_m30())
    raw_m15 = add_gap_minutes(load_raw_m15())
    prep_m30, _ = prepare("base_data/XAUUSDm30.csv", min_len=8)
    prep_m30["date"] = pd.to_datetime(prep_m30["date"])
    prep_m30 = prep_m30.sort_values("date").reset_index(drop=True)
    prep_m30 = add_gap_minutes(prep_m30)

    raw_m30_win = raw_m30[
        (raw_m30["date"] >= pd.Timestamp("2026-02-02 20:00:00"))
        & (raw_m30["date"] <= pd.Timestamp("2026-02-03 04:00:00"))
    ][["date", "open", "high", "low", "close", "gap_minutes"]].reset_index(drop=True)

    raw_m15_win = raw_m15[
        (raw_m15["date"] >= pd.Timestamp("2026-02-02 21:00:00"))
        & (raw_m15["date"] <= pd.Timestamp("2026-02-03 01:00:00"))
    ][["date", "open", "high", "low", "close", "gap_minutes"]].reset_index(drop=True)

    prep_m30_win = prep_m30[
        (prep_m30["date"] >= pd.Timestamp("2026-02-02 22:00:00"))
        & (prep_m30["date"] <= pd.Timestamp("2026-02-03 05:00:00"))
    ][["date", "open", "high", "low", "close", "gap_minutes"]].reset_index(drop=True)

    prep_dates = set(prep_m30["date"])
    next_prep = prep_m30.loc[prep_m30["date"] > TARGET_ALIGN_PLUS_90, "date"].min()
    summary = pd.DataFrame(
        [
            {
                "mt5_raw_anchor_time": TARGET_RAW_ANCHOR,
                "固定+90结果": TARGET_ALIGN_PLUS_90,
                "固定+90是否存在于Python时间轴": bool(TARGET_ALIGN_PLUS_90 in prep_dates),
                "gap后下一根Python M30": next_prep,
                "原始M30最大gap分钟": float(raw_m30_win["gap_minutes"].fillna(0).max()),
                "原始M15最大gap分钟": float(raw_m15_win["gap_minutes"].fillna(0).max()),
            }
        ]
    )

    export_csv(summary, OUTPUT_DIR / "gap窗口对齐复核汇总_20260709.csv")
    export_csv(raw_m30_win, OUTPUT_DIR / "gap窗口原始M30_20260709.csv")
    export_csv(raw_m15_win, OUTPUT_DIR / "gap窗口原始M15_20260709.csv")
    export_csv(prep_m30_win, OUTPUT_DIR / "gap窗口Prepared_M30_20260709.csv")
    write_text(
        OUTPUT_DIR / "gap窗口对齐复核_20260709.md",
        render_markdown(summary, raw_m30_win, raw_m15_win, prep_m30_win),
    )
    print(f"Wrote {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
