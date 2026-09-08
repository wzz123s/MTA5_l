# -*- coding: utf-8 -*-
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
import pandas as pd
import _current_baseline as base
from _m15_early_entry_test import collect_post_candidates, collect_pre_cross_candidates, collect_cross_candidates

df, h2, m15 = base.load_market_context()
q2_pass_set, q2_factor_map, _, _ = base.h2t.early_precompute(h2, df, 2, False)
raw = (collect_pre_cross_candidates(df, q2_pass_set, q2_factor_map)
       + collect_cross_candidates(df, q2_pass_set, q2_factor_map, ea_mode=True)
       + collect_post_candidates(df, q2_pass_set, q2_factor_map))
print("raw 总数:", len(raw))
# 13:00-14:30 的候选
for r in raw:
    t = pd.to_datetime(r["date"])
    if pd.Timestamp("2025-10-07 13:00") <= t <= pd.Timestamp("2025-10-07 14:30"):
        print(f"  {t}  mode={r['mode']} dir={r['dir']} sd={r['sd']:.2f} spec={r['spec_pass']}")
