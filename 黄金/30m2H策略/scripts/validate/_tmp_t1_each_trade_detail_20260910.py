# -*- coding: utf-8 -*-
"""Detailed per-trade calc: matched 64 groups (group = 1 signal x 3 stage rows)."""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = r"F:\use_code\MTA5_l"
DST = os.path.join(ROOT, "黄金", "30m2H策略", "data", "validation", "mainline_v337_tester_20260907")


def read(p):
    return pd.read_csv(p, encoding="utf-8-sig")


ea0 = read(os.path.join(DST, "30m2H_strategy_trade_ledger.csv"))
ea0["anchor"] = pd.to_datetime(ea0["signal_anchor_time"], errors="coerce")
ea0["dir"] = ea0["dir"].str.upper().map({"BUY": "L", "SELL": "S"})
ea0["k"] = ea0["anchor"].dt.strftime("%Y-%m-%d %H:%M") + "|" + ea0["dir"]

py = read(os.path.join(DST, "30m2H_python_acceptance_expected_trade_ledger_mp3.csv"))
py["a"] = pd.to_datetime(py["signal_anchor_time"], errors="coerce")
py["dir"] = py["dir"].str.upper().map({"BUY": "L", "SELL": "S"})
py["pk"] = py["a"].dt.strftime("%Y-%m-%d %H:%M") + "|" + py["dir"]
py = py.drop_duplicates(["pk"]).sort_values("a").reset_index(drop=True)

eaU = ea0.drop_duplicates(["k"]).sort_values("anchor").reset_index(drop=True)
w0, w1 = pd.Timestamp("2020-03-06"), pd.Timestamp("2026-06-11 23:59")
eaU = eaU[(eaU["anchor"] >= w0) & (eaU["anchor"] <= w1)].reset_index(drop=True)
py = py[(py["a"] >= w0) & (py["a"] <= w1)].reset_index(drop=True)
mc = {("2022-03-07 19:30", "L"), ("2026-01-26 18:30", "S")}
py = py[~py["pk"].isin([f"{t}|{x}" for t, x in mc])].reset_index(drop=True)

use = set()
matched_ea = []
for _, r in py.iterrows():
    cand = eaU[(eaU["dir"] == r["dir"]) & ((eaU["anchor"] - r["a"]).abs() <= pd.Timedelta(minutes=120)) & (~eaU.index.isin(use))]
    if len(cand):
        j = cand.index[0]
        use.add(j)
        matched_ea.append(eaU.loc[j, "k"])

grp = ea0[ea0["k"].isin(set(matched_ea))].copy()
rows = []
for k, g in grp.groupby("k"):
    s = {}
    s["anchor"] = k.split("|")[0]
    s["dir"] = k.split("|")[1]
    s["mode"] = g["signal_src"].iloc[0]
    s["open_time"] = pd.to_datetime(g["open_time"].iloc[0]).strftime("%Y-%m-%d %H:%M")
    s["close_time"] = pd.to_datetime(g["exit_time"]).max().strftime("%Y-%m-%d %H:%M")
    s["entry"] = round(float(g["signal_entry"].iloc[0]), 5)
    s["stop"] = round(float(g["signal_stop"].iloc[0]), 5)
    s["net_usd"] = round(float(g["net_profit"].sum()), 2)
    s["s1_net"] = round(float(g.loc[g["stage"] == 1, "net_profit"].sum()), 2) if (g["stage"] == 1).any() else 0.0
    s["s2_net"] = round(float(g.loc[g["stage"] == 2, "net_profit"].sum()), 2) if (g["stage"] == 2).any() else 0.0
    s["s3_net"] = round(float(g.loc[g["stage"] == 3, "net_profit"].sum()), 2) if (g["stage"] == 3).any() else 0.0
    c = g["deal_comment"].fillna("").astype(str)
    s["sl_count"] = int(c.str.startswith("sl ").sum())
    s["tp_count"] = int(c.str.startswith("tp ").sum())
    s["ea_exit_reasons"] = "|".join(g["local_exit_reason"].fillna("NA").tolist())
    rows.append(s)

out = pd.DataFrame(rows).sort_values("anchor").reset_index(drop=True)
out["cum_usd"] = out["net_usd"].cumsum().round(2)
out.to_csv(os.path.join(DST, "T1_EA匹配64笔_逐笔计算_20260910.csv"), index=False, encoding="utf-8-sig")
ea0[ea0["k"].isin(set(matched_ea))].to_csv(os.path.join(DST, "T1_EA匹配192子仓_逐行明细_20260910.csv"), index=False, encoding="utf-8-sig")
print("groups", len(out), "net total", round(out["net_usd"].sum(), 2), "win groups", int((out["net_usd"] > 0).sum()), "loss groups", int((out["net_usd"] < 0).sum()))
print(out.head(12).to_string(index=False))
