# -*- coding: utf-8 -*-
"""Verify L3 threshold 22,568 after h2 SMA calibration: run full compare variants."""
from __future__ import annotations

import bisect
import os
import sys

import numpy as np
import pandas as pd

ROOT = r"F:\use_code\MTA5_l"
REF = os.path.join(ROOT, "黄金", "30m2H策略", "参考实现工程")
for p in (REF, os.path.join(REF, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import _current_baseline as cb  # noqa: E402

DST = os.path.join(ROOT, "黄金", "30m2H策略", "data", "validation", "mainline_v337_tester_20260907")
EA_SIG = os.path.join(DST, "30m2H_strategy_signals_export_t1export4_20260910.csv")

_, h2, _ = cb.load_market_context()
h2 = h2.copy().reset_index(drop=True)
h2["date"] = pd.to_datetime(h2["date"])
h2 = h2[h2["SMA_5"].notna()].reset_index(drop=True)
ht = h2["date"].values.astype("datetime64[ns]")
b5 = np.abs((h2["close"] - h2["SMA_5"]) / h2["SMA_5"] * 100).values

es = pd.read_csv(EA_SIG, encoding="utf-8-sig")
es["bar_time"] = pd.to_datetime(es["bar_time"], format="%Y.%m.%d %H:%M", errors="coerce")

m = {k: 0 for k in ["excl329", "excl330", "incl329", "incl330"]}
total = 0
for _, r in es.iterrows():
    t = r["bar_time"]
    if pd.isna(t):
        continue
    j = int(bisect.bisect_right(ht, np.datetime64(t))) - 1
    if j < 500:
        continue
    ea_th = float(r["h2_comp_l3_threshold"])
    total += 1
    a_ex = np.sort(b5[j - 500:j])
    a_in = np.sort(b5[j - 499:j + 1])
    if abs(a_ex[329] - ea_th) > 1e-6:
        m["excl329"] += 1
    if abs(a_ex[330] - ea_th) > 1e-6:
        m["excl330"] += 1
    if abs(a_in[329] - ea_th) > 1e-6:
        m["incl329"] += 1
    if abs(a_in[330] - ea_th) > 1e-6:
        m["incl330"] += 1

print("total", total, "mismatch after calibration:", m)
