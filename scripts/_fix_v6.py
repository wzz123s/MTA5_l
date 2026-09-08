# -*- coding: utf-8 -*-
import re
p = r"F:\use_code\MTA5_l\黄金\乖离反转策略\backtest_v6_pairs.py"
s = open(p, encoding="utf-8-sig").read()
old1 = 'def gate_state(gate_tf, thr):\n    g = pipeline(RAW / ("XAUUSDm_" + gate_tf + ".csv"), gate_tf if gate_tf != "H4" else "4H")'
new1 = 'LBL = {"H4": "4H", "H6": "6H", "H1": "1H"}\n\n\ndef gate_state(gate_tf, thr):\n    g = pipeline(RAW / ("XAUUSDm_" + gate_tf + ".csv"), LBL.get(gate_tf, gate_tf))'
old2 = 'def seg_extremes(tf):\n    f = pipeline(RAW / ("XAUUSDm_" + tf + ".csv"), tf if tf != "H4" else "4H")'
new2 = 'def seg_extremes(tf):\n    f = pipeline(RAW / ("XAUUSDm_" + tf + ".csv"), LBL.get(tf, tf))'
assert old1 in s, "old1 missing"
assert old2 in s, "old2 missing"
s = s.replace(old1, new1).replace(old2, new2)
open(p, "w", encoding="utf-8-sig").write(s)
print("patched")
