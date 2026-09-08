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
final_acc["tstr"] = pd.to_datetime(final_acc["date"]).dt.strftime("%Y-%m-%d %H:%M")
for t in ["2025-10-07 13:00", "2025-10-07 13:30", "2025-10-07 14:00", "2025-10-07 14:30"]:
    rows = final_acc[final_acc["tstr"] == t]
    if len(rows):
        for _, r in rows.iterrows():
            print(f"{t}: mode={r['mode']} dir={r['dir']} sd={r['sd']:.2f} spec={r['spec_pass']} entry={r['entry']:.2f}")
    else:
        print(f"{t}: 无候选")
