# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\乖离反转策略\scripts")
from backtest_bias_reversal import run, metrics

# diagnose: cost sensitivity on the best param set
for cost in [0.0, 0.02, 0.05, 0.10]:
    tr = run(2.0, 1.2, 3.0, cost_pct=cost)
    m = metrics(tr)
    if m:
        print("cost=%.2f%%  n=%d  pf=%.3f  ev=%.3f  pnl=%.1f  test_pf=%.3f  wr=%.1f%%" % (
            cost, m["n"], m["pf"], m["ev"], m["pnl"], m["test_pf"], m["wr"]))
# also wider stops
for sp in [1.5, 2.0]:
    tr = run(2.0, sp, 3.0, cost_pct=0.05)
    m = metrics(tr)
    if m:
        print("stop=%.1f%%  n=%d  pf=%.3f  ev=%.3f  pnl=%.1f  test_pf=%.3f  wr=%.1f%%" % (
            sp, m["n"], m["pf"], m["ev"], m["pnl"], m["test_pf"], m["wr"]))
