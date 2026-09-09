# -*- coding: utf-8 -*-
"""D' full flow: Python candidates only completed Bias55>3 (no early gate), OOS split."""
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

import _build_expected_ledger as ble  # noqa: E402
import _current_baseline as cb  # noqa: E402

DST = os.path.join(ROOT, "黄金", "30m2H策略", "data", "validation", "mainline_v337_tester_20260907")
OUT_LED = os.path.join(DST, "30m2H_python_completedOnly_expected_trade_ledger_mp3.csv")

df0, h2x, _ = cb.load_market_context()
df0 = df0.copy().reset_index(drop=True)
df0["date"] = pd.to_datetime(df0["date"])
h2x = h2x.copy().reset_index(drop=True)
h2x["date"] = pd.to_datetime(h2x["date"])
h2x = h2x[h2x["SMA_55"].notna()].reset_index(drop=True)
ht = h2x["date"].values.astype("datetime64[ns]")
close_map = dict(zip(df0["date"], df0["close"].astype(float)))


def completed_only(t_open):
    import bisect
    tick = np.datetime64(t_open) + np.timedelta64(30, "m")
    idx = int(bisect.bisect_right(ht, tick)) - 1
    if idx < 0:
        return False
    return abs((h2x["close"].iloc[idx] - h2x["SMA_55"].iloc[idx]) / h2x["SMA_55"].iloc[idx]) * 100 > 3.0


orig = cb.apply_layer3_ea_executable


def wrapper(final_acc, h2, top_pct=34, lookback=500):
    threshold, out = orig(final_acc, h2, top_pct=top_pct, lookback=lookback)
    keep = [row for _, row in out.iterrows() if completed_only(pd.Timestamp(row["date"]))]
    return threshold, pd.DataFrame(keep).reset_index(drop=True)


cb.apply_layer3_ea_executable = wrapper
ble.LEDGER_PATH = OUT_LED
ble.SUMMARY_PATH = OUT_LED.replace(".csv", "_summary.md")
print("building completed-only expected ledger...", flush=True)
ble.build_ledger(ea_executable=True, rolling_merged=True, max_pos_sim=3)

led = pd.read_csv(OUT_LED, encoding="utf-8-sig")
led["anchor"] = pd.to_datetime(led["signal_anchor_time"], errors="coerce")
led["k"] = led["anchor"].dt.strftime("%Y-%m-%d %H:%M") + "|" + led["dir"]
led["year"] = led["anchor"].dt.year
g = led.groupby("k")["pnl_points"].sum().reset_index()
g["year"] = g["k"].map(led.drop_duplicates("k").set_index("k")["year"])


def perf(name, sub):
    w = sub[sub["pnl_points"] > 0]; l = sub[sub["pnl_points"] < 0]
    payoff = w["pnl_points"].mean() / abs(l["pnl_points"].mean()) if len(l) else float("nan")
    print(name, "n", len(sub), "win", len(w), "sum", round(sub["pnl_points"].sum(), 1),
          "PF", round(w["pnl_points"].sum() / abs(l["pnl_points"].sum()), 2) if len(l) else None,
          "payoff", round(payoff, 2), flush=True)


perf("D' completed-only full", g)
perf("train2020-23", g[g["year"] < 2024])
perf("test2024-26", g[g["year"] >= 2024])
