# -*- coding: utf-8 -*-
"""
stage1_g2.py —— 1.3 G2 黄金穿越胜率基线（决策门）

规则（策略计划 4.3 / 7.3）：
  日线 SMA13x55 穿越（不分方向）后 20/60/120 日收益分布、创新高/新低比例
  通过标准：方向胜率 > 55%

输出:
  data/processed/G2_黄金穿越胜率.csv      逐穿越明细
  data/processed/G2_胜率汇总.md          汇总
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage1_common as C


def main():
    sym = "XAUUSDm"
    df = C.analyze_tf(sym, "D1")
    cr = C.find_cross13_55(df)
    fs = C.forward_stats(df, cr)
    fs.insert(0, "time", cr["time"].values[:len(fs)])
    fs.insert(1, "price", cr["price"].values[:len(fs)])
    fs.to_csv(C.PROC / "G2_黄金穿越胜率.csv", index=False, encoding="utf-8-sig")

    # 汇总
    rows = []
    for d, label in [(1, "LONG(上穿)"), (-1, "SHORT(下穿)"), (0, "全部")]:
        sub = fs if d == 0 else fs[fs["dir"] == d]
        if len(sub) == 0:
            continue
        s = {"方向": label, "n": len(sub)}
        for h in (20, 60, 120):
            s[f"胜率r{h}"] = f"{sub[f'win{h}'].mean()*100:.1f}%"
            s[f"中位r{h}"] = f"{sub[f'r{h}'].median()*100:+.2f}%"
            s[f"均值r{h}"] = f"{sub[f'r{h}'].mean()*100:+.2f}%"
        s["60日创新高/新低"] = f"{sub['win60_struct'].mean()*100:.1f}%"
        s["60日结构胜率"] = f"{sub['win60_struct'].mean()*100:.1f}%"
        rows.append(s)
    summ = pd.DataFrame(rows)
    print(summ.to_string(index=False))

    # 决策门
    overall_60 = fs["win60"].mean()
    long_60 = fs[fs["dir"] == 1]["win60"].mean()
    short_60 = fs[fs["dir"] == -1]["win60"].mean()
    gate_pass = overall_60 > 0.55
    print()
    print(f"G2 决策门：60日方向胜率 = {overall_60*100:.1f}% "
          f"(LONG={long_60*100:.1f}% / SHORT={short_60*100:.1f}%)"
          f"  -> {'✅ 通过 (>55%)' if gate_pass else '❌ 未通过 (≤55%)'}")

    lines = [
        "# G2 黄金穿越胜率基线（阶段1 · 决策门）", "",
        f"品种：XAUUSDm 日线 ｜ 穿越数：{len(fs)} ｜ 数据：2016-01 ~ 2026-09", "",
        "| 方向 | n | 胜率r20 | 胜率r60 | 胜率r120 | 中位r60 | 均值r60 | 60日新高/新低 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['方向']} | {r['n']} | {r['胜率r20']} | {r['胜率r60']} | "
                     f"{r['胜率r120']} | {r['中位r60']} | {r['均值r60']} | {r['60日创新高/新低']} |")
    lines += [
        "", f"**G2 决策门（60日方向胜率 > 55%）：{overall_60*100:.1f}% -> "
            f"{'✅ 通过' if gate_pass else '❌ 未通过'}**",
        "", "> 胜率rH = 穿越后 H 根收益为正比例（LONG）或为负比例（SHORT）；",
        "> 60日新高/新低 = 穿越后 60 根内创新高（LONG）/创新低（SHORT）比例。",
    ]
    (C.PROC / "G2_胜率汇总.md").write_text("\n".join(lines), encoding="utf-8")
    print("  已保存 G2_黄金穿越胜率.csv / G2_胜率汇总.md")


if __name__ == "__main__":
    main()
