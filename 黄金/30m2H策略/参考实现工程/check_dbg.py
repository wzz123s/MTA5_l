# -*- coding: utf-8 -*-
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
import numpy as np
import pandas as pd
import _current_baseline as base

df, h2, m15 = base.load_market_context()
q2_pass_set, q2_factor_map, _, _ = base.h2t.early_precompute(h2, df, 2, False)
print("q2_pass_set 大小:", len(q2_pass_set))
df["tstr"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d %H:%M")
i = df.index[df["tstr"] == "2025-10-07 13:30"][0]
print(f"i={i}  i in pass_set: {i in q2_pass_set}")
pn = df["merged_post_cross_n"].iloc[i]
print(f"merged_post_cross_n[i] = {pn} (来自 df 列)")
# 检查 collect_post_candidates 内部
from _m15_early_entry_test import collect_post_candidates
rows = collect_post_candidates(df, q2_pass_set, q2_factor_map)
print("collect_post 总数:", len(rows))
# 检查 df 列名
print("df 列:", [c for c in df.columns if "post" in c.lower() or "merged" in c.lower()])
