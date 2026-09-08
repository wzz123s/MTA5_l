# -*- coding: utf-8 -*-
import os
import sys
import bisect
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
import pandas as pd
import _current_baseline as base

df, final_acc = base.build_final_accepted(spec_lo=5, spec_hi=35, ea_executable_diag=True, rolling_merged=True)
h2 = base.load_h2_context()
h2_bias = base._build_h2_bias5_lookup(h2)
h2_times = pd.to_datetime(h2_bias["date"]).tolist()
h2_vals = h2_bias["Bias_5_calc"].tolist()

final_acc["tstr"] = pd.to_datetime(final_acc["date"]).dt.strftime("%Y-%m-%d %H:%M")
for t in ["2025-10-07 13:30", "2025-10-07 14:00"]:
    rows = final_acc[final_acc["tstr"] == t]
    if len(rows) == 0:
        print(f"{t}: 不在 final_acc")
        continue
    r = rows.iloc[0]
    date = pd.Timestamp(r["date"])
    eval_time = date + pd.Timedelta(minutes=30)
    idx = bisect.bisect_right(h2_times, eval_time) - 1
    bias5 = float(h2_vals[idx])
    thr = base._rolling_top_threshold(h2_vals[max(0, idx - 500):idx], 34)
    print(f"{t}: mode={r['mode']} date={date} eval={eval_time} idx={idx} h2t={h2_times[idx]} bias5={bias5:.5f} thr={thr:.5f} pass={bias5>=thr}")
