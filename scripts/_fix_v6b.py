# -*- coding: utf-8 -*-
p = r"F:\use_code\MTA5_l\黄金\乖离反转策略\backtest_v6_pairs.py"
s = open(p, encoding="utf-8-sig").read()
old = 'LBL = {"H4": "4H", "H6": "6H", "H1": "1H"}'
new = 'LBL = {"H1": "1H", "H2": "2H", "H4": "4H", "H6": "6H"}'
assert old in s
open(p, "w", encoding="utf-8-sig").write(s.replace(old, new))
print("patched LBL")
