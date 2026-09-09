# -*- coding: utf-8 -*-
"""Regime |H2 Bias55|<=T 禁入阈值敏感性：完整管线逐 T 重跑 (T=4.5/5.0/5.5)。"""
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

es = pd.read_csv(os.path.join(DST, "30m2H_strategy_signals_export_t1export4_20260910.csv"), encoding="utf-8-sig")
es["bar_time"] = pd.to_datetime(es["bar_time"], format="%Y.%m.%d %H:%M", errors="coerce")
es["layer1_ea"] = (es["h2_comp_bias55"] > 3.0) | (es["q2_early_pass"] == 1)
pass_map = dict(zip(es["bar_time"], es["layer1_ea"].astype(int)))
bias_map = dict(zip(es["bar_time"], es["h2_comp_bias55"].astype(float)))

orig = cb.apply_layer3_ea_executable


def make_wrapper(threshold: float):
    def wrapper(final_acc, h2, top_pct=34, lookback=500):
        th, out = orig(final_acc, h2, top_pct=top_pct, lookback=lookback)
        keep = []
        for _, row in out.iterrows():
            ev = pd.Timestamp(row["date"]) + pd.Timedelta(minutes=30)
            if bool(pass_map.get(ev, 0)) and float(bias_map.get(ev, 99)) <= threshold:
                keep.append(row)
        return th, pd.DataFrame(keep).reset_index(drop=True)

    return wrapper


def perf(sub):
    if len(sub) == 0:
        return dict(n=0, win=0, loss=0, pts=0.0, pf=float("nan"), payoff=float("nan"))
    w = sub[sub["pnl_points"] > 0]
    l = sub[sub["pnl_points"] < 0]
    gl = g[g["k"].isin(sub["k"])]
    wl = gl[gl["pnl_points"] > 0]
    ll = gl[gl["pnl_points"] < 0]
    return dict(
        n=len(sub),
        win=len(wl),
        loss=len(ll),
        pts=round(sub["pnl_points"].sum(), 1),
        pf=round(wl["pnl_points"].sum() / abs(ll["pnl_points"].sum()), 2) if len(ll) else None,
        payoff=round(wl["pnl_points"].mean() / abs(ll["pnl_points"].mean()), 2) if len(ll) else None,
    )


rows = []
for th in (4.5, 5.0, 5.5):
    tag = ("%g" % th).replace(".", "p")
    out_led = os.path.join(DST, f"30m2H_python_regimeBias{tag}_expected_trade_ledger_mp3.csv")
    ble.LEDGER_PATH = out_led
    ble.SUMMARY_PATH = out_led.replace(".csv", "_summary.md")
    cb.apply_layer3_ea_executable = make_wrapper(th)
    print(f"building regime bias<={th} expected ledger...", flush=True)
    ble.build_ledger(ea_executable=True, rolling_merged=True, max_pos_sim=3)

    led = pd.read_csv(out_led, encoding="utf-8-sig")
    led["anchor"] = pd.to_datetime(led["signal_anchor_time"], errors="coerce")
    led["k"] = led["anchor"].dt.strftime("%Y-%m-%d %H:%M") + "|" + led["dir"]
    led["year"] = led["anchor"].dt.year
    g = led.groupby("k")["pnl_points"].sum().reset_index()
    g["year"] = g["k"].map(led.drop_duplicates("k").set_index("k")["year"])

    full = perf(g)
    train = perf(g[g["year"] < 2024])
    test = perf(g[g["year"] >= 2024])
    rows.append({"T": th, "scope": "full", **full})
    rows.append({"T": th, "scope": "train20-23", **train})
    rows.append({"T": th, "scope": "test24-26", **test})
    print(f"T={th} full n{full['n']} win{full['win']} pts{full['pts']} PF{full['pf']} payoff{full['payoff']}")
    print(f"T={th} train n{train['n']} pts{train['pts']} PF{train['pf']} payoff{train['payoff']}")
    print(f"T={th} test  n{test['n']} pts{test['pts']} PF{test['pf']} payoff{test['payoff']}")
    for y in range(2020, 2027):
        yr = perf(g[g["year"] == y])
        print(f"  T={th} {y}: n{yr['n']} win{yr['win']} pts{yr['pts']} PF{yr['pf']} payoff{yr['payoff']}")

res = pd.DataFrame(rows)
res.to_csv(os.path.join(DST, "T1_regime_threshold_sens_20260910.csv"), index=False, encoding="utf-8-sig")
print("DONE", flush=True)
