# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r"F:\use_code\MTA5_l\scripts")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\scripts\signals")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\乖离反转策略\scripts")
import backtest_v8_matrix as v8

tr = v8.run_short_v8("H2", None, False, 0, "fixed")
print("baseline n:", len(tr))
if len(tr):
    print(tr.head(3).to_string())
tr2 = v8.run_short_v8("H2", 1.5, False, 0, "fixed")
print("b5=1.5 n:", len(tr2))
