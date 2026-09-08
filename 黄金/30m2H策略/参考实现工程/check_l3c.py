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
h2 = base.load_h2_context()
threshold, picked = base.apply_layer3_ea_executable(final_acc, h2, top_pct=34)
final_acc["tstr"] = pd.to_datetime(final_acc["date"]).dt.strftime("%Y-%m-%d %H:%M")
picked["tstr"] = pd.to_datetime(picked["date"]).dt.strftime("%Y-%m-%d %H:%M")
for t in ["2022-11-08 15:30", "2022-11-08 16:00", "2025-09-05 13:30", "2025-09-05 14:00"]:
    pk = picked[picked["tstr"] == t]
    fa = final_acc[final_acc["tstr"] == t]
    print(f"{t}: final_acc={'有' if len(fa) else '无'}  picked={'有' if len(pk) else '无'}", end="")
    if len(pk):
        r = pk.iloc[0]
        print(f"  bias5={r['Bias_5_ea']:.4f} thr={r['layer3_threshold_ea']:.4f}", end="")
    print()
