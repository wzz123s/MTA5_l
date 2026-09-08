# -*- coding: utf-8 -*-
"""Export signal-layer outputs for the 30m2H mainline strategy."""
from __future__ import annotations


import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_30m2h_common import (
    SIGNALS_DIR,
    START_CAPITAL,
    annualized_return_from_trades,
    build_summary_rows,
    ensure_dirs,
    export_csv,
    load_strategy_result,
    write_text,
)


def _format_signal_frames(result: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    accepted = result["accepted"].copy()
    picked = result["picked"].copy()
    trades = result["trades"].copy()

    if not accepted.empty:
        accepted.insert(0, "信号层级", "Layer1+Layer2通过")
    if not picked.empty:
        picked.insert(0, "信号层级", "Layer3入选")
    if not trades.empty:
        trades.insert(0, "信号层级", "Stage执行")
    return accepted, picked, trades


def main() -> None:
    ensure_dirs()
    result = load_strategy_result()
    accepted, picked, trades = _format_signal_frames(result)
    summary, years = build_summary_rows(result)

    export_csv(accepted, SIGNALS_DIR / "候选信号_Layer1_Layer2通过.csv")
    export_csv(picked, SIGNALS_DIR / "最终信号_Layer3入选.csv")
    export_csv(trades, SIGNALS_DIR / "执行交易_Stage结果.csv")
    export_csv(summary, SIGNALS_DIR / "信号汇总_中文.csv")
    export_csv(years, SIGNALS_DIR / "年度表现_中文.csv")

    annualized = annualized_return_from_trades(trades, start_capital=START_CAPITAL) * 100.0
    doc_lines = [
        "# 30m2H 主线信号汇总",
        "",
        "## 当前采用参数",
        "",
        "- Layer1：`|H2 Bias_55| > 3.0%`",
        "- Layer2：`pre_cross + cross + post_n(2-6)`，并将 M30 分解为两个 M15 时段做同口径判定",
        "- Layer3：`Bias_5 top 34%`",
        "- Stage 参数：`2.0 / 1.5 / 4.0`",
        "- 止损范围：`[5, 35] pt`",
        "",
        "## 主线结果",
        "",
        summary.to_markdown(index=False),
        "",
        "## 年度拆分",
        "",
        years.to_markdown(index=False) if not years.empty else "暂无年度数据",
        "",
        "## 补充指标",
        "",
        f"- 原始资金：`${START_CAPITAL:.2f}`",
        f"- 年化收益：`{annualized:.2f}%`",
    ]
    write_text(SIGNALS_DIR / "信号汇总.md", "\n".join(doc_lines))
    print("Exported signal outputs for 30m2H strategy.")


if __name__ == "__main__":
    main()
