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
picked["tstr"] = pd.to_datetime(picked["date"]).dt.strftime("%Y-%m-%d %H:%M")
for t in ["2025-10-07 13:00", "2025-10-07 13:30", "2025-10-07 14:00"]:
    rows = picked[picked["tstr"] == t]
    if len(rows):
        r = rows.iloc[0]
        print(f"{t}: in picked  bias5={r['Bias_5_ea']:.5f} thr={r['layer3_threshold_ea']:.5f} pass={r['layer3_pass_ea']}")
    else:
        print(f"{t}: NOT in picked")
