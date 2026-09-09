# -*- coding: utf-8 -*-
"""D+A simulation: filter modes + raise Stage1/2 targets on Python matched acceptance signals."""
from __future__ import annotations

import os
import sys

import pandas as pd

ROOT = r"F:\use_code\MTA5_l"
REF = os.path.join(ROOT, "黄金", "30m2H策略", "参考实现工程")
for p in (REF, os.path.join(REF, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import _current_baseline as cb  # noqa: E402
import _stage12_combo_test as s12  # noqa: E402

DST = os.path.join(ROOT, "黄金", "30m2H策略", "data", "validation", "mainline_v337_tester_20260907")

df, _h2, _ = cb.load_market_context()
df = df.copy().reset_index(drop=True)
df["date"] = pd.to_datetime(df["date"])
idx_by_date = {t: i for i, t in enumerate(df["date"])}


def read(p):
    return pd.read_csv(p, encoding="utf-8-sig")


py0 = read(os.path.join(DST, "30m2H_python_acceptance_expected_trade_ledger_mp3.csv"))
ea0 = read(os.path.join(DST, "30m2H_strategy_trade_ledger.csv"))
for f in (py0, ea0):
    f["anchor"] = pd.to_datetime(f["signal_anchor_time"], errors="coerce")
    f["dir"] = f["dir"].astype(str).str.upper().map({"BUY": "L", "SELL": "S"})
    f["k"] = f["anchor"].dt.strftime("%Y-%m-%d %H:%M") + "|" + f["dir"]
py = py0.drop_duplicates(["k"]).sort_values("anchor").reset_index(drop=True)
ea = ea0.drop_duplicates(["k"]).sort_values("anchor").reset_index(drop=True)
w0, w1 = pd.Timestamp("2020-03-06"), pd.Timestamp("2026-06-11 23:59")
py = py[(py["anchor"] >= w0) & (py["anchor"] <= w1)].reset_index(drop=True)
ea = ea[(ea["anchor"] >= w0) & (ea["anchor"] <= w1)].reset_index(drop=True)
mc = {("2022-03-07 19:30", "L"), ("2026-01-26 18:30", "S")}
py = py[~py["k"].isin([f"{t}|{d}" for t, d in mc])].reset_index(drop=True)

use = set()
matched_py = []
for _, r in py.iterrows():
    cand = ea[(ea["dir"] == r["dir"]) & ((ea["anchor"] - r["anchor"]).abs() <= pd.Timedelta(minutes=120)) & (~ea.index.isin(use))]
    if len(cand):
        j = cand.index[0]
        use.add(j)
        matched_py.append(r)
matched = pd.DataFrame(matched_py)
print("matched py signals", len(matched))


def group_pnl(row, s1r, trail, force):
    i = idx_by_date.get(pd.Timestamp(row["anchor"]))
    if i is None:
        return None
    tr = pd.Series({"i": i, "dir": row["dir"], "entry": float(row["signal_entry"]), "stop": float(row["signal_stop"])})
    p1, _, _ = s12.stage1_exit(df, tr, s1r)
    p2, _, _ = s12.stage2_exit(df, tr, trail, force)
    p3, _, _ = s12.stage3_exit(df, tr)
    return p1 + p2 + p3


def stats(label, sub, s1r, trail, force):
    pnls = [group_pnl(r, s1r, trail, force) for _, r in sub.iterrows()]
    s = pd.Series([x for x in pnls if x is not None])
    win = s[s > 0]; loss = s[s < 0]
    payoff = win.mean() / abs(loss.mean()) if len(loss) else float("nan")
    print(label, "n", len(s), "win", len(win), "sum", round(s.sum(), 2),
          "PF", round(win.sum() / abs(loss.sum()), 2) if len(loss) else None,
          "payoff", round(payoff, 2))


for label, sub in [("BASE 2/1.5/4", matched),
                   ("D+A 全量 3/2.5/6", matched),
                   ("D+A 去post_n4", matched[matched["signal_src"] != "post_n4"]),
                   ("D+A 去pre_cross", matched[matched["signal_src"] != "pre_cross"]),
                   ("D+A 去post_n4+pre_cross", matched[~matched["signal_src"].isin(["post_n4", "pre_cross"])])]:
    s1r, trail, force = (2.0, 1.5, 4.0) if label.startswith("BASE") else (3.0, 2.5, 6.0)
    stats(label, sub, s1r, trail, force)
