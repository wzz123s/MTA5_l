# -*- coding: utf-8 -*-
"""v4b: R3 扩展网格 + 年度分解（修复 best 选择：n>=15）"""
import sys
sys.path.insert(0, r"F:\use_code\MTA5_l\scripts")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\scripts\signals")
import numpy as np
import pandas as pd
from pathlib import Path
from backtest_v4_large_scale import run, summ

OUT = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\validation")
print("=== R3 扩展网格（H4门 thr=2.5/3.0/3.5）===")
results = []
for gt in [2.5, 3.0, 3.5]:
    for tr_ in [1.5, 2.0, 2.5, 3.0]:
        for tw in [0.5, 0.6, 0.7]:
            m = summ(run("R3", gt, tr_, tw))
            if m and m["n"] >= 15:
                results.append((gt, tr_, tw, m))
                print("gate=%4.1f rise>=%4.1f%% w>=%.1f  n=%3d pf=%.3f ev=%7.2f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
                    gt, tr_, tw, m["n"], m["pf"], m["ev"], m["pnl"], m["test_pf"], m["wr"]))
results.sort(key=lambda x: -x[3]["pf"])
print()
print("=== Top5（n>=15）===")
for gt, tr_, tw, m in results[:5]:
    print("gate=%4.1f rise=%4.1f w=%.1f  n=%d pf=%.3f pnl=%.1f test_pf=%.3f" % (gt, tr_, tw, m["n"], m["pf"], m["pnl"], m["test_pf"]))
# recommended: top1 with n>=15
if results:
    gt, tr_, tw, m = results[0]
    print()
    print("=== 推荐组合: gate=%s rise>=%s w>=%s ===" % (gt, tr_, tw))
    tr = run("R3", gt, tr_, tw)
    tr.to_csv(OUT / "bias_reversal_v4_recommended_trades.csv", index=False, encoding="utf-8-sig")
    df = tr.copy(); df["year"] = pd.to_datetime(df["signal_time"]).dt.year
    print(df.groupby("year").agg(n=("pnl_points", "size"), pnl=("pnl_points", "sum"),
                                  wr=("pnl_points", lambda x: (x > 0).mean() * 100)).round(2).to_string())
    print()
    print("exit reasons:", tr["exit_reason"].value_counts().to_dict())
    print("dir counts:", tr["dir"].value_counts().to_dict())
    print("avg hold bars:", round(tr["holding_bars"].mean(), 1), "avg pnl:", round(tr["pnl_points"].mean(), 2))
