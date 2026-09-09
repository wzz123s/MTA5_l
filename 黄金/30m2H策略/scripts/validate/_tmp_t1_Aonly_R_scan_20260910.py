# -*- coding: utf-8 -*-
"""A-only R scan (no mode filter): rebuild expected ledger for R variants + OOS split."""
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

# EA Layer1 truth map
es = pd.read_csv(os.path.join(DST, "30m2H_strategy_signals_export_t1export4_20260910.csv"), encoding="utf-8-sig")
es["bar_time"] = pd.to_datetime(es["bar_time"], format="%Y.%m.%d %H:%M", errors="coerce")
es["layer1_ea"] = (es["h2_comp_bias55"] > 3.0) | (es["q2_early_pass"] == 1)
ea_map = dict(zip(es["bar_time"], es["layer1_ea"].astype(int)))

orig = cb.apply_layer3_ea_executable


def wrapper(final_acc, h2, top_pct=34, lookback=500):
    threshold, out = orig(final_acc, h2, top_pct=top_pct, lookback=lookback)
    keep = []
    for _, row in out.iterrows():
        ev = pd.Timestamp(row["date"]) + pd.Timedelta(minutes=30)
        if bool(ea_map.get(ev, 1)):
            keep.append(row)
    return threshold, pd.DataFrame(keep).reset_index(drop=True)


cb.apply_layer3_ea_executable = wrapper


def run(name, s1, tr, fo):
    out = os.path.join(DST, f"30m2H_python_Aonly_{name}_expected_trade_ledger_mp3.csv")
    ble.STAGE1_R = s1
    ble.STAGE2_TRAIL_R = tr
    ble.STAGE2_FORCE_R = fo
    ble.LEDGER_PATH = out
    ble.SUMMARY_PATH = out.replace(".csv", "_summary.md")
    print("building", name, flush=True)
    ble.build_ledger(ea_executable=True, rolling_merged=True, max_pos_sim=3)
    led = pd.read_csv(out, encoding="utf-8-sig")
    led["anchor"] = pd.to_datetime(led["signal_anchor_time"], errors="coerce")
    led["k"] = led["anchor"].dt.strftime("%Y-%m-%d %H:%M") + "|" + led["dir"]
    led["year"] = led["anchor"].dt.year
    g = led.groupby("k")["pnl_points"].sum().reset_index()
    g["year"] = g["k"].map(led.drop_duplicates("k").set_index("k")["year"])

    def metric(label, sub):
        w = sub[sub["pnl_points"] > 0]; l = sub[sub["pnl_points"] < 0]
        payoff = w["pnl_points"].mean() / abs(l["pnl_points"].mean()) if len(l) else float("nan")
        print(name, label, "n", len(sub), "win", len(w), "sum", round(sub["pnl_points"].sum(), 1),
              "PF", round(w["pnl_points"].sum() / abs(l["pnl_points"].sum()), 2) if len(l) else None,
              "payoff", round(payoff, 2), flush=True)

    metric("full", g)
    metric("train20-23", g[g["year"] < 2024])
    metric("test24-26", g[g["year"] >= 2024])


run("R25", 2.5, 2.0, 5.0)
run("R30", 3.0, 2.5, 6.0)
run("R35", 3.5, 3.0, 7.0)
