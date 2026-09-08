# -*- coding: utf-8 -*-
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
import pandas as pd
import _current_baseline as base

df, final_acc = base.build_final_accepted(spec_lo=5, spec_hi=35, ea_executable_diag=True, rolling_merged=True)
codes, roll_pn = base.rolling_merged_postn(df)
df["tstr"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d %H:%M")
df = df.reset_index(drop=True)
final_acc["tstr"] = pd.to_datetime(final_acc["date"]).dt.strftime("%Y-%m-%d %H:%M")
for pair in [("2022-11-08 15:30", "2022-11-08 16:00"), ("2025-09-05 13:30", "2025-09-05 14:00"), ("2025-10-08 23:30", "2025-10-09 00:00"), ("2026-03-24 09:30", "2026-03-24 10:00")]:
    py_t, ea_t = pair
    i1 = df.index[df["tstr"] == py_t][0]
    i2 = df.index[df["tstr"] == ea_t][0]
    fa1 = final_acc[final_acc["tstr"] == py_t]
    fa2 = final_acc[final_acc["tstr"] == ea_t]
    print(f"{py_t}: pn={roll_pn[i1]} final_acc={'有' if len(fa1) else '无'}"
          f"  |  {ea_t}: pn={roll_pn[i2]} final_acc={'有' if len(fa2) else '无'}")
    if len(fa1):
        r = fa1.iloc[0]
        print(f"    {py_t} 候选: mode={r['mode']} spec={r['spec_pass']}")
    if len(fa2):
        r = fa2.iloc[0]
        print(f"    {ea_t} 候选: mode={r['mode']} spec={r['spec_pass']}")
