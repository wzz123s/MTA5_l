# -*- coding: utf-8 -*-
"""Zero the 190: find EA prev_sma55 index offset matching q2_early_bias55."""
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
EA_SIG = os.path.join(DST, "30m2H_strategy_signals_export_t1export3_20260910.csv")

df, h2, _ = cb.load_market_context()
df = df.copy().reset_index(drop=True)
df["date"] = pd.to_datetime(df["date"])
h2 = h2.copy().reset_index(drop=True)
h2["date"] = pd.to_datetime(h2["date"])
h2 = h2[h2["SMA_55"].notna()].reset_index(drop=True)
ht = h2["date"].values.astype("datetime64[ns]")
s55 = h2["SMA_55"].values.astype(float)
close_map = dict(zip(df["date"], df["close"].astype(float)))

es = pd.read_csv(EA_SIG, encoding="utf-8-sig")
es["bar_time"] = pd.to_datetime(es["bar_time"], format="%Y.%m.%d %H:%M", errors="coerce")
es["py_open"] = es["bar_time"] - pd.Timedelta(minutes=30)
es = es[es["py_open"].isin(close_map)].reset_index(drop=True)
ea_q = (es["q2_early_pass"] == 1).astype(int).values
ea_b = pd.to_numeric(es["q2_early_bias55"], errors="coerce").values
ea_el = pd.to_numeric(es["q2_elapsed_q"], errors="coerce").values

for off in (-2, -1, 0):
    sim = []
    sim_b = []
    sim_el = []
    for t in es["py_open"]:
        tick = np.datetime64(t) + np.timedelta64(30, "m")
        idx = int(bisect.bisect_right(ht, tick)) - 1
        prev = idx + off
        if prev < 0 or prev >= len(s55) or s55[prev] == 0:
            sim.append(0); sim_b.append(np.nan); sim_el.append(0)
            continue
        cur_open = pd.Timestamp(ht[idx]) if idx >= 0 else None
        if cur_open is None or pd.Timestamp(t) < cur_open:
            sim.append(0); sim_b.append(np.nan); sim_el.append(0)
            continue
        prev_time = pd.Timestamp(ht[prev])
        if pd.Timestamp(t) < prev_time:
            sim.append(0); sim_b.append(np.nan); sim_el.append(0)
            continue
        elapsed = int((pd.Timestamp(t) - prev_time) / pd.Timedelta(minutes=30))
        if elapsed < 2:
            sim.append(0); sim_b.append(np.nan); sim_el.append(elapsed)
            continue
        partial = close_map.get(pd.Timestamp(t))
        if partial is None:
            sim.append(0); sim_b.append(np.nan); sim_el.append(elapsed)
            continue
        est = s55[prev] + (partial - s55[prev]) / 55.0
        b = abs((partial - est) / est) * 100 if est else 0.0
        sim.append(1 if b > 3.0 else 0)
        sim_b.append(b)
        sim_el.append(elapsed)
    sim = np.array(sim); sim_b = np.array(sim_b); sim_el = np.array(sim_el)
    mm = int((sim != ea_q).sum())
    print("offset", off, "mismatch", mm, "sim1/EA0", int(((sim == 1) & (ea_q == 0)).sum()), "EA1/sim0", int(((sim == 0) & (ea_q == 1)).sum()), flush=True)
    if off == -1:
        mask = (sim != ea_q)
        d = sim_b[mask] - ea_b[mask]
        print("  on mismatches: sim_b vs EA bias sample", list(zip(np.round(sim_b[mask][:8], 5), np.round(ea_b[mask][:8], 5))), flush=True)
