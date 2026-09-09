# -*- coding: utf-8 -*-
"""List 31 post_n counter mismatch rows and inspect phase/absorption context."""
from __future__ import annotations

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

df, _h2, _ = cb.load_market_context()
df = df.copy().reset_index(drop=True)
df["date"] = pd.to_datetime(df["date"])
mcodes, mpn = cb.rolling_merged_postn(df)
df["py_roll_pn"] = mpn

es = pd.read_csv(EA_SIG, encoding="utf-8-sig")
es["bar_time"] = pd.to_datetime(es["bar_time"], format="%Y.%m.%d %H:%M", errors="coerce")
es["py_open"] = es["bar_time"] - pd.Timedelta(minutes=30)
dfi = df.set_index("date")
es = es[es["py_open"].isin(dfi.index)].reset_index(drop=True)
es = es.join(dfi[["py_roll_pn"]], on="py_open")
es["diff"] = es["py_roll_pn"].astype(int) - es["merged_post_n_counter"].astype(int)
mm = es[es["diff"] != 0].copy()
print("EA counter vs Python: mismatch", len(mm), flush=True)
print("diff value counts:", mm["diff"].value_counts().to_dict(), flush=True)
print(mm[["bar_time", "merged_post_n_counter", "py_roll_pn", "diff", "m30_merged_code", "m30_merged_dir"]].head(40).to_string(index=False), flush=True)
