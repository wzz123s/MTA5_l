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

T = "2025-10-07 13:30"
df, h2, m15 = base.load_market_context()
q2_pass_set, q2_factor_map, _, _ = base.h2t.early_precompute(h2, df, 2, False)
df["tstr"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d %H:%M")
i = df.index[df["tstr"] == T]
if len(i) == 0:
    print("bar 不存在")
else:
    i = i[0]
    print(f"bar idx={i} 在 q2_pass_set: {i in q2_pass_set}")
    # 候选收集
    raw = (collect_pre_cross_candidates(df, q2_pass_set, q2_factor_map)
           + collect_cross_candidates(df, q2_pass_set, q2_factor_map, ea_mode=True)
           + collect_post_candidates(df, q2_pass_set, q2_factor_map))
    hits = [r for r in raw if r["date"] == pd.Timestamp(T)]
    print(f"候选命中: {len(hits)}")
    for h in hits:
        print(f"  mode={h['mode']} dir={h['dir']} entry={h['entry']:.3f} stop={h['stop']:.3f} sd={h['sd']:.2f} spec={h['spec_pass']} reason={h['spec_reason']}")
