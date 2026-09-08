# -*- coding: utf-8 -*-
import os
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
p = os.path.join(HERE, "..", "data", "validation", "final_ea_alignment_20260811", "python_vs_ea_alignment_summary.csv")
s = pd.read_csv(p, encoding="utf-8-sig")
print("matched:", s["matched_rows"].iloc[0], " tolerance:", s["tolerance_matched_rows"].iloc[0],
      " expected_rows:", s["expected_rows"].iloc[0], " exit_tm:", s["exit_time_match_count"].iloc[0],
      " pnl_sign:", s["pnl_sign_match_count"].iloc[0])
