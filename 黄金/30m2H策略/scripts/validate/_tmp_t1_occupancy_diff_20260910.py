# -*- coding: utf-8 -*-
"""EA ledger occupancy vs Python acceptance MAXPOS trajectory diff around residual anchors."""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = r"F:\use_code\MTA5_l"
DST = os.path.join(ROOT, "黄金", "30m2H策略", "data", "validation", "mainline_v337_tester_20260907")


def read(p):
    for enc in ("utf-8-sig", "utf-8", "gbk", "mbcs", "utf-16"):
        try:
            return pd.read_csv(p, encoding=enc)
        except Exception:
            continue
    raise RuntimeError(p)


def parse(s):
    a = pd.to_datetime(s, format="%Y.%m.%d %H:%M:%S", errors="coerce")
    if a.isna().any():
        a = pd.to_datetime(s, format="%Y.%m.%d %H:%M", errors="coerce")
    if a.isna().any():
        a = pd.to_datetime(s, errors="coerce")
    return a


ea = read(os.path.join(DST, "30m2H_strategy_trade_ledger.csv"))
py = read(os.path.join(DST, "30m2H_python_acceptance_expected_trade_ledger_mp3.csv"))
for f in (ea, py):
    f["open_time"] = parse(f["open_time"])
    f["exit_time"] = parse(f["exit_time"])


def occ(df, t):
    return int(((df["open_time"] <= t) & (df["exit_time"] > t)).sum())


WINDOWS = {
    "MISS_postn_2020-07-28": ("2020-07-28 05:00", "2020-07-28 09:00"),
    "MISS_postn_2025-10-17": ("2025-10-17 11:00", "2025-10-17 15:00"),
    "MISS_postn_2025-10-20": ("2025-10-20 10:00", "2025-10-20 13:30"),
    "EXTRA_2020-03-08": ("2020-03-08 00:00", "2020-03-08 01:30"),
    "EXTRA_2021-06-16": ("2021-06-16 19:00", "2021-06-16 21:30"),
    "EXTRA_2025-09-09": ("2025-09-09 14:00", "2025-09-09 15:30"),
}

for name, (s0, s1) in WINDOWS.items():
    print("\n###", name)
    t = pd.Timestamp(s0)
    end = pd.Timestamp(s1)
    while t <= end:
        print(t.strftime("%H:%M"), "EA_open", occ(ea, t), "PY_open", occ(py, t))
        t += pd.Timedelta(minutes=30)
