# -*- coding: utf-8 -*-
import os
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
d = os.path.join(HERE, "..", "data", "validation", "final_ea_alignment_20260811")
exp = pd.read_csv(os.path.join(d, "python_expected_trade_ledger.csv"), encoding="utf-8-sig")
exp["tstr"] = pd.to_datetime(exp["signal_anchor_time"]).dt.strftime("%Y-%m-%d %H:%M")
for t in ["2025-10-07 13:30", "2025-10-07 14:00", "2025-10-09 00:00", "2025-10-09 00:30", "2025-10-14 17:30", "2025-10-14 18:00", "2022-11-14 15:30", "2022-11-14 16:00", "2024-04-03 15:30", "2024-04-03 16:00"]:
    rows = exp[exp["tstr"] == t]
    if len(rows):
        r = rows.iloc[0]
        print(f"{t}: {r['signal_src']} in expected")
    else:
        print(f"{t}: NOT in expected")
