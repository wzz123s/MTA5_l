# -*- coding: utf-8 -*-
import os
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
d = os.path.join(HERE, "..", "data", "validation", "final_ea_alignment_20260811")
exp = pd.read_csv(os.path.join(d, "python_expected_trade_ledger.csv"), encoding="utf-8-sig")
act = pd.read_csv(os.path.join(d, "30m2H_strategy_trade_ledger_v335.csv"), encoding="utf-8-sig")
exp_a = set(pd.to_datetime(exp["signal_anchor_time"]).dt.strftime("%Y-%m-%d %H:%M"))
act_a = set(pd.to_datetime(act["signal_anchor_time"]).dt.strftime("%Y-%m-%d %H:%M"))
print(f"交集 {len(exp_a & act_a)} | expected {len(exp_a)} | EA {len(act_a)}")
eo = sorted(exp_a - act_a)
ao = sorted(act_a - exp_a)
print("expected 独有:", len(eo))
print("EA 独有:", len(ao))
