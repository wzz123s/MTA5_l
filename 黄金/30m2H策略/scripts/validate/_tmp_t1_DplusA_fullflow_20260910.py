# -*- coding: utf-8 -*-
"""D+A full-flow recompute: rebuild expected ledger, OOS split metrics, EA alignment."""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = r"F:\use_code\MTA5_l"
REF = os.path.join(ROOT, "黄金", "30m2H策略", "参考实现工程")
for p in (REF, os.path.join(REF, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import _build_expected_ledger as ble  # noqa: E402
import _current_baseline as cb  # noqa: E402

DST = os.path.join(ROOT, "黄金", "30m2H策略", "data", "validation", "mainline_v337_tester_20260907")
OUT_LED = os.path.join(DST, "30m2H_python_DplusA_expected_trade_ledger_mp3.csv")

# --- D+A parameters ---
ble.STAGE1_R = 3.0
ble.STAGE2_TRAIL_R = 2.5
ble.STAGE2_FORCE_R = 6.0


def read(p):
    return pd.read_csv(p, encoding="utf-8-sig")


es = read(os.path.join(DST, "30m2H_strategy_signals_export_t1export4_20260910.csv"))
es["bar_time"] = pd.to_datetime(es["bar_time"], format="%Y.%m.%d %H:%M", errors="coerce")
es["layer1_ea"] = (es["h2_comp_bias55"] > 3.0) | (es["q2_early_pass"] == 1)
ea_map = dict(zip(es["bar_time"], es["layer1_ea"].astype(int)))

orig = cb.apply_layer3_ea_executable


def wrapper(final_acc, h2, top_pct=34, lookback=500):
    threshold, out = orig(final_acc, h2, top_pct=top_pct, lookback=lookback)
    keep = []
    for _, row in out.iterrows():
        ev = pd.Timestamp(row["date"]) + pd.Timedelta(minutes=30)
        if row.get("mode") == "post_n4":
            continue
        if bool(ea_map.get(ev, 1)):
            keep.append(row)
    return threshold, pd.DataFrame(keep).reset_index(drop=True)


cb.apply_layer3_ea_executable = wrapper
ble.LEDGER_PATH = OUT_LED
ble.SUMMARY_PATH = OUT_LED.replace(".csv", "_summary.md")
print("building D+A expected ledger...", flush=True)
ble.build_ledger(ea_executable=True, rolling_merged=True, max_pos_sim=3)

led = read(OUT_LED)
led["anchor"] = pd.to_datetime(led["signal_anchor_time"], errors="coerce")
led["dir"] = led["dir"].str.upper().map({"BUY": "L", "SELL": "S"})
led["k"] = led["anchor"].dt.strftime("%Y-%m-%d %H:%M") + "|" + led["dir"]
led["year"] = led["anchor"].dt.year
grp = led.groupby("k")["pnl_points"].sum().reset_index()
grp["year"] = led.drop_duplicates("k").set_index("k")["year"]
grp["year"] = grp["k"].map(led.drop_duplicates("k").set_index("k")["year"])


def perf(g, name):
    w = g[g["pnl_points"] > 0]; l = g[g["pnl_points"] < 0]
    payoff = w["pnl_points"].mean() / abs(l["pnl_points"].mean()) if len(l) else float("nan")
    print(name, "n", len(g), "win", len(w), "sum", round(g["pnl_points"].sum(), 1),
          "PF", round(w["pnl_points"].sum() / abs(l["pnl_points"].sum()), 2) if len(l) else None,
          "payoff", round(payoff, 2), flush=True)


perf(grp, "D+A full")
perf(grp[grp["year"] < 2024], "D+A train2020-23")
perf(grp[grp["year"] >= 2024], "D+A test2024-26")

# EA alignment (market-closed excluded)
ea = read(os.path.join(DST, "30m2H_strategy_trade_ledger.csv"))
ea["anchor"] = pd.to_datetime(ea["signal_anchor_time"], errors="coerce")
ea["dir"] = ea["dir"].str.upper().map({"BUY": "L", "SELL": "S"})
ea["k"] = ea["anchor"].dt.strftime("%Y-%m-%d %H:%M") + "|" + ea["dir"]
eu = ea.drop_duplicates(["k"]).sort_values("anchor").reset_index(drop=True)
py = led.drop_duplicates(["k"]).sort_values("anchor").reset_index(drop=True)
w0, w1 = pd.Timestamp("2020-03-06"), pd.Timestamp("2026-06-11 23:59")
eu = eu[(eu["anchor"] >= w0) & (eu["anchor"] <= w1)].reset_index(drop=True)
py = py[(py["anchor"] >= w0) & (py["anchor"] <= w1)].reset_index(drop=True)
mc = {("2022-03-07 19:30", "L"), ("2026-01-26 18:30", "S")}
py = py[~py["k"].isin([f"{t}|{x}" for t, x in mc])].reset_index(drop=True)
use = set(); mm = 0
for _, r in py.iterrows():
    cand = eu[(eu["dir"] == r["dir"]) & ((eu["anchor"] - r["anchor"]).abs() <= pd.Timedelta(minutes=120)) & (~eu.index.isin(use))]
    if len(cand):
        use.add(cand.index[0]); mm += 1
print("D+A alignment expected", len(py), "matched", mm, f"={100*mm/max(len(py),1):.2f}%", "extra", len(eu) - len(use), flush=True)
