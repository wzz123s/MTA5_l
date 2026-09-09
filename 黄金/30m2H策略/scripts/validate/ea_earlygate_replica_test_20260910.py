# -*- coding: utf-8 -*-
"""EA CalcBias55EarlyQ Python replica vs EA exported q2_early_pass (full-window match test)."""
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
# assume python h2 'date' = H2 bar open; completed close = open+2h
h2 = h2.copy().reset_index(drop=True)
h2["date"] = pd.to_datetime(h2["date"])
h2 = h2[h2["SMA_55"].notna() & (h2["SMA_5"].notna())].reset_index(drop=True)
ht = h2["date"].values.astype("datetime64[ns]")
sma55 = h2["SMA_55"].values.astype(float)
close_map = dict(zip(df["date"], df["close"].astype(float)))


def sim_q2(t_open: pd.Timestamp) -> tuple[bool, float, int]:
    tick = np.datetime64(t_open) + np.timedelta64(30, "m")
    idx = int(bisect.bisect_right(ht, tick)) - 1  # forming H2 open <= tick
    if idx < 1:
        return False, 0.0, 0
    cur_open = pd.Timestamp(ht[idx])
    if t_open < cur_open:  # EA: last_m30_open < current_h2_open -> early false
        return False, 0.0, 0
    prev_open = pd.Timestamp(ht[idx - 1])
    if t_open < prev_open:
        return False, 0.0, 0
    elapsed = int((t_open - prev_open) / pd.Timedelta(minutes=30))
    if elapsed < 2:
        return False, 0.0, elapsed
    prev_sma55 = sma55[idx]  # calibrated h2 date=decision/close: idx is EA shift1
    partial = close_map.get(pd.Timestamp(t_open))
    if partial is None or prev_sma55 == 0:
        return False, 0.0, elapsed
    est55 = prev_sma55 + (partial - prev_sma55) / 55.0
    est_bias = abs((partial - est55) / est55) * 100 if est55 else 0.0
    return bool(est_bias > 3.0), float(est_bias), elapsed


es = pd.read_csv(EA_SIG, encoding="utf-8-sig")
es["bar_time"] = pd.to_datetime(es["bar_time"], format="%Y.%m.%d %H:%M", errors="coerce")
es["py_open"] = es["bar_time"] - pd.Timedelta(minutes=30)
es = es[es["py_open"].isin(set(df["date"]))].reset_index(drop=True)

sim = []
for t in es["py_open"]:
    ok, est, elapsed = sim_q2(pd.Timestamp(t))
    sim.append((int(ok), est, elapsed))
res = pd.DataFrame(sim, columns=["sim_pass", "sim_bias", "sim_elapsed"])
ea_q = (es["q2_early_pass"] == 1).astype(int).reset_index(drop=True)
comp = pd.concat([res, ea_q.rename("ea_q")], axis=1)
m = (comp["sim_pass"] != comp["ea_q"]).sum()
print("rows", len(comp), "EA q2=1", int(comp["ea_q"].sum()), "sim=1", int(comp["sim_pass"].sum()), "mismatch", int(m))
print(comp[comp["sim_pass"] != comp["ea_q"]].head(8).to_string(index=False))
