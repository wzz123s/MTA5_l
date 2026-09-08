# -*- coding: utf-8 -*-
"""
stage1_g1.py —— 1.4 G1 原油边际验证（决策门，v2 双路径）

路径：
  G1-A1 日线结构止损（home_struct，不过滤）→ 边际按 R 倍数衡量
  G1-A2 降档 4H 结构止损（sub_struct，StopSpec 0.8%~2.5%）→ "操作意义止损小"路径
  G1-B  D1 穿越直接入场（fixed_delay_1，60bar 持仓）→ 信号原始边际参考
通过标准：成本后 EV_R > 0 且 PF_R ≥ 1.2
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
    sym = "USOILm"
    d1 = C.analyze_tf(sym, "D1")
    h4 = C.analyze_tf(sym, "H4")
    cr = C.find_cross13_55(d1)
    cr = cr[pd.to_datetime(cr["time"]) >= "2021-07-01"].reset_index(drop=True)
    print(f"G1 原油：D1 穿越(2021-07+) = {len(cr)} 次")

    costs = [("无成本", 0.00, 0.0000),
             ("点差3pt", 0.03, 0.0000),
             ("点差3pt+隔夜", 0.03, 0.0005),
             ("点差5pt+隔夜", 0.05, 0.0010)]

    all_trades = []
    print()
    print("== G1-A1：日线结构止损（不过滤 StopSpec，1.5R/3R 退出）==")
    for name, sp, sw in costs:
        tr = B.backtest(cr, d1, h4, sym, "D1", "H4", lookback_days=40,
                        stop_mode="home_struct", stop_spec=None,
                        exit_mode="1.5R_3R", time_exit_bars=120,
                        spread_price=sp, swap_per_bar=sw)
        s = B.summarize(tr, name)
        print(f"  A1 {name}: n={s['n']} (L={s['n_long']}/S={s['n_short']}) "
              f"EV_R={s['EV_R']} PF_R={s['PF_R']} 胜率={s['winrate']}% 均持={s['avg_hold_bars']}bar")
        if len(tr):
            tr["path"] = "A1"; tr["variant"] = name
            all_trades.append(tr)

    print()
    print("== G1-A2：降档 4H 结构止损（StopSpec 0.8%~2.5%，1.5R/3R 退出）==")
    for name, sp, sw in costs:
        tr = B.backtest(cr, d1, h4, sym, "D1", "H4", lookback_days=40,
                        stop_mode="sub_struct", stop_spec=("pct", 0.008, 0.025),
                        exit_mode="1.5R_3R", time_exit_bars=120,
                        spread_price=sp, swap_per_bar=sw)
        s = B.summarize(tr, name)
        print(f"  A2 {name}: n={s['n']} (L={s['n_long']}/S={s['n_short']}) "
              f"EV_R={s['EV_R']} PF_R={s['PF_R']} 胜率={s['winrate']}% 均持={s['avg_hold_bars']}bar")
        if len(tr):
            tr["path"] = "A2"; tr["variant"] = name
            all_trades.append(tr)

    print()
    print("== G1-B：D1 穿越直接入场（fixed_delay_1，60bar 持仓）==")
    d1b = d1[d1["time"] >= "2019-03-01"].reset_index(drop=True)
    crb = C.find_cross13_55(d1b)
    for name, sp, sw in costs:
        tr = B.backtest(crb, d1b, d1b, sym, "D1", "D1", lookback_days=30,
                        stop_mode="home_struct", stop_spec=None,
                        exit_mode="fixedH", time_exit_bars=60,
                        spread_price=sp, swap_per_bar=sw * 6,
                        direct_entry=True)
        s = B.summarize(tr, name)
        print(f"  B {name}: n={s['n']} (L={s['n_long']}/S={s['n_short']}) "
              f"EV_R={s['EV_R']} PF_R={s['PF_R']} 胜率={s['winrate']}%")
        if len(tr):
            tr["path"] = "B"; tr["variant"] = name
            all_trades.append(tr)

    if all_trades:
        pd.concat(all_trades, ignore_index=True).to_csv(
            C.PROC / "G1_原油边际验证.csv", index=False, encoding="utf-8-sig")

    # 决策门：主路径 A2（降档4H，点差3pt+隔夜）
    tr_main = B.backtest(cr, d1, h4, sym, "D1", "H4", lookback_days=40,
                         stop_mode="sub_struct", stop_spec=("pct", 0.008, 0.025),
                         exit_mode="1.5R_3R", time_exit_bars=120,
                         spread_price=0.03, swap_per_bar=0.0005)
    sm = B.summarize(tr_main, "A2主")
    gate = sm["EV_R"] > 0 and sm["PF_R"] >= 1.2
    print()
    print(f"G1 决策门（A2 降档4H + 点差3pt+隔夜）：n={sm['n']} EV_R={sm['EV_R']} PF_R={sm['PF_R']} "
          f"-> {'✅ 通过 → 原油立项' if gate else '❌ 未通过 → 原油挂起'}")

    lines = [
        "# G1 原油边际验证（阶段1 · 决策门）", "",
        "数据约束：原油 D1 真密度 2019-03 起；H4 真密度 2021-07 起（服务器深度限制）。",
        f"主实验窗口 2021-07 ~ 2026-09（约 5.2 年），D1 13×55 穿越 {len(cr)} 次。", "",
        "路径说明：", "- **A1** 日线结构止损（D1 prev_seg SMA13 极值，R 天然 6~20%，仓位极小）",
        "- **A2** 降档 4H 结构止损（StopSpec 0.8%~2.5%，'操作意义止损小'，计划 S4 允许路径）",
        "- **B**  D1 穿越直接入场 60 根持仓（信号原始边际参考）", "",
        "| 路径 | 变体 | n | L/S | EV_R | PF_R | 胜率 |",
        "|---|---|---|---|---|---|---|",
    ]
    for tr in all_trades:
        s = B.summarize(tr)
        lines.append(f"| {tr['path']} | {tr['variant']} | {s['n']} | {s['n_long']}/{s['n_short']} "
                     f"| {s['EV_R']} | {s['PF_R']} | {s['winrate']}% |")
    lines += [
        "", f"**G1 决策门（A2 降档4H + 点差3pt+隔夜：EV_R>0 且 PF_R≥1.2）："
            f"n={sm['n']} EV_R={sm['EV_R']} PF_R={sm['PF_R']} "
            f"-> {'✅ 通过 → 原油立项' if gate else '❌ 未通过 → 原油挂起'}**",
        "", "> EV_R = 每笔净盈亏 / 该笔结构止损距离 R（R 倍数，跨 R 可比）；",
        "> PF_R = 盈利 R 之和 / |亏损 R 之和|。成本：1pt=$0.01/桶；隔夜 4H bar 计。",
    ]
    (C.PROC / "G1_汇总.md").write_text("\n".join(lines), encoding="utf-8")
    print("  已保存 G1_原油边际验证.csv / G1_汇总.md")


if __name__ == "__main__":
    main()
