# -*- coding: utf-8 -*-
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
import pandas as pd
import _current_baseline as base

d = os.path.join(HERE, "..", "data", "validation", "final_ea_alignment_20260811")
exp = pd.read_csv(os.path.join(d, "python_expected_trade_ledger.csv"), encoding="utf-8-sig")
act = pd.read_csv(os.path.join(d, "30m2H_strategy_trade_ledger_v335.csv"), encoding="utf-8-sig")
exp["tstr"] = pd.to_datetime(exp["signal_anchor_time"]).dt.strftime("%Y-%m-%d %H:%M")
act["tstr"] = pd.to_datetime(act["signal_anchor_time"]).dt.strftime("%Y-%m-%d %H:%M")
exp_a = set(exp["tstr"])
act_a = set(act["tstr"])
eo = sorted(exp_a - act_a)
ao = sorted(act_a - exp_a)
act_src = {}
for _, r in act.drop_duplicates("tstr").iterrows():
    act_src[r["tstr"]] = r["signal_src"]
exp_src = {}
for _, r in exp.drop_duplicates("tstr").iterrows():
    exp_src[r["tstr"]] = r["signal_src"]
print("=== EA 独有", len(ao), "笔 ===")
for k in ao:
    print(f"  {k}  src={act_src.get(k)}")
print()
print("=== expected 独有", len(eo), "笔 ===")
for k in eo:
    print(f"  {k}  src={exp_src.get(k)}")
