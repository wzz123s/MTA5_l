# -*- coding: utf-8 -*-
"""
stage1_g3.py —— 1.5 G3 加仓价值（黄金，决策门）

规则（策略计划 7.4 E6）：底仓后价格回归日线 SMA55（±1%）且 4H 顺势穿越 → 加仓
通过标准：加仓（回归区入场）改善 PF 且不显著增回撤（这里用 EV_R/PF_R 衡量）

实现：A2 路径（4H 结构止损 + 1.5R/3R 退出）基础上
  - 底仓 = 全部入场
  - 回归加仓 = 入场 bar close 处于日线 SMA55 ±1% 回归带内
  - 对比：回归区入场 vs 全体入场 vs 两者合并的 EV_R / PF_R / 胜率
输出: data/processed/G3_加仓价值.csv / G3_汇总.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage1_common as C
import stage1_backtest as B


def main():
    sym = "XAUUSDm"
    d1 = C.analyze_tf(sym, "D1")
    h4 = C.analyze_tf(sym, "H4")
    cr = C.find_cross13_55(d1)
    cr = cr[pd.to_datetime(cr["time"]) >= "2017-03-01"].reset_index(drop=True)  # H4 真密度窗口
    print(f"G3 黄金：D1 穿越(2017-03+) = {len(cr)} 次")

    # 底仓（全体入场）
    base = B.backtest(cr, d1, h4, sym, "D1", "H4", lookback_days=40,
                      stop_mode="sub_struct", stop_spec=("pct", 0.003, 0.02),
                      exit_mode="1.5R_3R", time_exit_bars=120,
                      spread_price=0.10, swap_per_bar=0.002,
                      label="底仓全体")
    sb = B.summarize(base, "底仓全体")

    # 回归加仓：入场 bar close 在 D1 SMA55 ±1% 带内
    # 为每个 base 交易标记回归带状态：需要 entry bar 对应时刻的 D1 SMA55
    d1_t = d1["time"].values
    d1_sma55 = d1["SMA_55"].values

    def in_regression_band(entry_time, entry_price):
        idx = np.searchsorted(pd.to_datetime(d1_t), entry_time) - 1
        if idx < 0 or np.isnan(d1_sma55[idx]):
            return False
        return abs(entry_price - d1_sma55[idx]) / d1_sma55[idx] <= 0.01

    base["in_reg_band"] = base.apply(
        lambda r: in_regression_band(r["time"], r["entry"]), axis=1)
    adds = base[base["in_reg_band"]].copy()
    sa = B.summarize(adds, "回归加仓")

    # 合并（底仓+加仓，同一持仓逻辑下的全部入场）
    combined = base  # 加仓本就是入场子集；合并统计=全体
    sc = B.summarize(combined, "合并")

    print()
    print(f"  底仓全体: n={sb['n']} EV_R={sb['EV_R']} PF_R={sb['PF_R']} 胜率={sb['winrate']}%")
    print(f"  回归加仓: n={sa['n']} EV_R={sa['EV_R']} PF_R={sa['PF_R']} 胜率={sa['winrate']}% "
          f"(占底仓 {sa['n']/max(sb['n'],1)*100:.0f}%)")
    improvement = sa["PF_R"] >= sb["PF_R"] and sa["EV_R"] >= sb["EV_R"]
    print(f"  G3 结论: 回归加仓 PF_R {sa['PF_R']} vs 底仓 {sb['PF_R']} -> "
          f"{'✅ 加仓改善PF' if improvement else '❌ 加仓未改善PF'}")

    base.to_csv(C.PROC / "G3_加仓价值.csv", index=False, encoding="utf-8-sig")
    lines = [
        "# G3 加仓价值（阶段1 · 黄金）", "",
        f"窗口：2017-03 ~ 2026-09（H4 真密度）；D1 穿越 {len(cr)} 次。",
        "路径：A2 降档 4H 结构止损（pct 0.3%~2.0%）+ 1.5R/3R 退出；成本点差 0.1 + 隔夜 0.002/bar。", "",
        "| 组 | n | EV_R | PF_R | 胜率 | 说明 |",
        "|---|---|---|---|---|---|",
        f"| 底仓全体 | {sb['n']} | {sb['EV_R']} | {sb['PF_R']} | {sb['winrate']}% | 全部入场 |",
        f"| 回归加仓 | {sa['n']} | {sa['EV_R']} | {sa['PF_R']} | {sa['winrate']}% | 入场在日线 SMA55 ±1% 带内 |",
        "", f"**G3 结论：回归加仓 PF_R {sa['PF_R']} vs 底仓 {sb['PF_R']}；EV_R {sa['EV_R']} vs {sb['EV_R']} "
            f"-> {'✅ 加仓改善 PF 且不增风险' if improvement else '❌ 加仓未改善'}**",
        "", "> 回归加仓 = E6 第二档（价格回归日线 SMA55 且 4H 顺势穿越）；此处以入场点是否位于回归带近似。",
    ]
    (C.PROC / "G3_汇总.md").write_text("\n".join(lines), encoding="utf-8")
    print("  已保存 G3_加仓价值.csv / G3_汇总.md")


if __name__ == "__main__":
    main()
