# -*- coding: utf-8 -*-
"""2H_M30_6H 门控变体 A/B: 现门(bias5&55>0) vs SMA13/SMA55 结构比值 vs bias13."""
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT/"scripts", _ROOT/"黄金"/"30m2H策略"/"参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*")]:
    s=str(_p)
    if s not in _sys.path: _sys.path.insert(0, s)
import bisect, sys
from pathlib import Path
import numpy as np, pandas as pd
from combined_abc_30m2h_2h_20260814 import (STRATS, add_m30_state, attach_context, build_combo,
    build_three_opportunities, load_strategy, replay_signals, replay_three_stage, per_trade, metric)
from experiment_1h_m30_4h_variants_20260813 import per_trade_from_stages, split_test

cfg = STRATS["2H_M30_6H"]
m30, h6 = load_strategy(cfg)
m30_state = add_m30_state(m30)
sig = build_three_opportunities(m30, spec_lo=5.0, spec_hi=35.0)
replayed = replay_signals(sig, m30)
enriched = attach_context(replayed, h6, "h6")
# h6 time/SMA13/SMA55 映射
h6t = pd.to_datetime(h6["date"]).values.astype("datetime64[ns]")
h6.close = pd.to_numeric(h6["close"], errors="coerce").values
h6.sma5 = pd.to_numeric(h6["SMA_5"], errors="coerce").values
h6.sma13 = pd.to_numeric(h6["SMA_13"], errors="coerce").values
h6.sma55 = pd.to_numeric(h6["SMA_55"], errors="coerce").values
def h6_at(t):
    i = bisect.bisect_right(h6t, t.to_datetime64()) - 1
    if i < 0: return None
    return i
st = enriched.copy(); st["signal_time"] = pd.to_datetime(st["signal_time"])
n = len(st)
# 组特征
close=[]; s5=[]; s13=[]; s55=[]; side=[]
for _,row in st.iterrows():
    i = h6_at(row["signal_time"])
    if i is None or i<0:
        close.append(np.nan); s5.append(np.nan); s13.append(np.nan); s55.append(np.nan); side.append("")
        continue
    close.append(h6.close[i]); s5.append(h6.sma5[i]); s13.append(h6.sma13[i]); s55.append(h6.sma55[i])
    side.append(str(row["dir"]).upper())
st["h6c"]=close; st["h6s5"]=s5; st["h6s13"]=s13; st["h6s55"]=s55; st["side"]=side
st["b5_pos"] = (st["h6c"] - st["h6s5"]) / st["h6s5"] * 100.0
st["b55_pos"] = (st["h6c"] - st["h6s55"]) / st["h6s55"] * 100.0
st["b13_pos"] = (st["h6c"] - st["h6s13"]) / st["h6s13"] * 100.0
st["sma13_over_55"] = (st["h6s13"] - st["h6s55"]) / st["h6s55"] * 100.0
def gate_and(df, col, thr=0.0, inv=False):
    # 多头: col>0 需为正; 空头: 取反
    val = pd.to_numeric(df[col], errors="coerce")
    side = df["side"]
    if inv:
        mask = ((side=="L") & (val <= thr)) | ((side=="S") & (val >= thr))
    else:
        mask = ((side=="L") & (val > thr)) | ((side=="S") & (val < thr))
    return mask & val.notna()
def run(mask, label):
    t = st[mask].copy().reset_index(drop=True)
    t["entry_bar_idx"] = pd.to_numeric(t["entry_bar_idx"], errors="coerce").astype(int)
    tr = replay_three_stage(m30_state, t)
    if tr.empty or len(tr)==0: return None
    tr["signal_time"]=pd.to_datetime(tr["signal_time"])
    tr = tr[tr["signal_time"].dt.year.isin([2025,2026])]
    per = per_trade_from_stages(tr)
    per["dir"]=per["dir"].astype(str)
    m = metric(per["stage_pnl_weighted"])
    test = split_test(per, "stage_pnl_weighted")
    return (label, m["n"], m["pf"], m["ev"], test["test_pf"], (per["stage_pnl_weighted"]>0).mean()*100)
rows=[]
rows.append(run((st["b5_pos"]>0)&(st["b55_pos"]>0), "V0 现门 b5>0&b55>0"))
rows.append(run((st["sma13_over_55"]>0)&(st["b5_pos"]>0), "V1 SMA13/SMA55>0 & b5>0"))
rows.append(run(st["sma13_over_55"]>0, "V2 SMA13/SMA55>0 (仅结构)"))
rows.append(run((st["b13_pos"]>0)&(st["b55_pos"]>0), "V3 b13>0&b55>0 (曾删的bias13口径)"))
rows.append(run((st["sma13_over_55"]>0)&(st["b55_pos"]>0)&(st["b5_pos"]>0), "V4 全结构+价格: sma13/55>0&b5>0&b55>0"))
print("%-30s %5s %7s %8s %8s %6s"%("variant","n","PF","EV","testPF","WR%"))
for r in rows:
    if r: print("%-30s %5d %7.3f %8.2f %8.3f %6.1f"%r)
    else: print("(0 trades)")
