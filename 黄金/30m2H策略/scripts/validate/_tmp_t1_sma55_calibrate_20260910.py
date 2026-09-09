# -*- coding: utf-8 -*-
"""Check: recompute Python h2 SMA55 with EA mean-init vs EA q2_prev_sma55."""
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
h2 = h2[h2["SMA_55"].notna()].reset_index(drop=True)

close = h2["close"].values.astype(float)
n = len(close)
sma = np.full(n, np.nan)
period = 55
sma[period - 1] = float(close[:period].mean())
for i in range(period, n):
    sma[i] = (close[i] + (period - 1) * sma[i - 1]) / period
h2["sma55_recalc"] = sma

es = pd.read_csv(EA_SIG, encoding="utf-8-sig")
es["bar_time"] = pd.to_datetime(es["bar_time"], format="%Y.%m.%d %H:%M", errors="coerce")
es["py_open"] = es["bar_time"] - pd.Timedelta(minutes=30)
es = es[es["py_open"].isin(set(h2["date"]))].reset_index(drop=True)
ht = h2["date"].values.astype("datetime64[ns]")

prev_recalc = []
prev_file = []
for t in es["bar_time"]:
    idx = int(bisect.bisect_right(ht, np.datetime64(t))) - 1
    prev_recalc.append(sma[idx] if idx >= 0 else np.nan)
    prev_file.append(h2["SMA_55"].iloc[idx] if idx >= 0 else np.nan)
es["prev_recalc"] = prev_recalc
es["prev_file"] = prev_file
ea_prev = pd.to_numeric(es["q2_prev_sma55"], errors="coerce")
d1 = (es["prev_recalc"] - ea_prev).abs()
d2 = (es["prev_file"] - ea_prev).abs()
print("rows", len(es), "recalc vs EA prev: mismatch>1e-6", int((d1 > 1e-6).sum()), "max", round(float(d1.max()), 6))
print("file SMA55 vs EA prev: mismatch>1e-6", int((d2 > 1e-6).sum()), "max", round(float(d2.max()), 6))
