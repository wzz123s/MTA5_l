# -*- coding: utf-8 -*-
"""Regime baseline: bucket matched trades by H2 bias strength / early-pass."""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

ROOT = r"F:\use_code\MTA5_l"
DST = os.path.join(ROOT, "黄金", "30m2H策略", "data", "validation", "mainline_v337_tester_20260907")

grp = pd.read_csv(os.path.join(DST, "T1_EA匹配64笔_逐笔计算_20260910.csv"), encoding="utf-8-sig")
grp["anchor"] = pd.to_datetime(grp["anchor"])
sig = pd.read_csv(os.path.join(DST, "30m2H_strategy_signals_export_t1export4_20260910.csv"), encoding="utf-8-sig")
sig["bar_time"] = pd.to_datetime(sig["bar_time"], format="%Y.%m.%d %H:%M", errors="coerce")
sig["anchor"] = sig["bar_time"] - pd.Timedelta(minutes=30)
f = sig[["anchor", "h2_comp_bias55", "h2_comp_bias5", "q2_early_pass"]].merge(grp, on="anchor", how="inner")
f["bias_bucket"] = pd.cut(f["h2_comp_bias55"], [-1, 3.5, 5.0, 99], labels=["low", "mid", "high"])

for name, sub in f.groupby("bias_bucket"):
    w = sub[sub["net_usd"] > 0]; l = sub[sub["net_usd"] < 0]
    payoff = w["net_usd"].mean() / abs(l["net_usd"].mean()) if len(l) else float("nan")
    print(name, "n", len(sub), "win", len(w), "sum", round(sub["net_usd"].sum(), 2),
          "PF", round(w["net_usd"].sum() / abs(l["net_usd"].sum()), 2) if len(l) else None,
          "payoff", round(payoff, 2))

for q in (0, 1):
    sub = f[f["q2_early_pass"] == q]
    w = sub[sub["net_usd"] > 0]; l = sub[sub["net_usd"] < 0]
    print("q2early", q, "n", len(sub), "win", len(w), "sum", round(sub["net_usd"].sum(), 2),
          "payoff", round(w["net_usd"].mean() / abs(l["net_usd"].mean()), 2) if len(l) else None)
