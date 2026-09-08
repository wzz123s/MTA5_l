# -*- coding: utf-8 -*-
"""2H_M30_6H 门控: r13_55=(H6 SMA13-SMA55)/SMA55*100 阈值扫描 -8%..+8% (V4 结构, 叠价格).
输出: 各阈值 n/PF/EV/testPF(70/30)/pnl; 候选阈值 walk-forward + 按年.
"""
import sys as _sys
from pathlib import Path as _Path
_ROOT=_Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT/"scripts", _ROOT/"黄金"/"30m2H策略"/"参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*")]:
    s=str(_p)
    if s not in _sys.path: _sys.path.insert(0,s)
import bisect, sys
from pathlib import Path
import numpy as np, pandas as pd
from combined_abc_30m2h_2h_20260814 import (STRATS, add_m30_state, attach_context, build_combo,
    build_three_opportunities, load_strategy, replay_signals, replay_three_stage)
from experiment_1h_m30_4h_variants_20260813 import per_trade_from_stages, metric, split_test
OUT=Path(r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\data\validation\gate_variant_sma13_55")

cfg=STRATS["2H_M30_6H"]; m30,h6=load_strategy(cfg); m30_state=add_m30_state(m30)
sig=build_three_opportunities(m30,spec_lo=5.0,spec_hi=35.0); replayed=replay_signals(sig,m30)
enriched=attach_context(replayed,h6,"h6")
st=enriched.copy(); st["signal_time"]=pd.to_datetime(st["signal_time"])
h6t=pd.to_datetime(h6["date"]).values.astype("datetime64[ns]")
H6C=pd.to_numeric(h6["close"],errors="coerce").values; H6S5=pd.to_numeric(h6["SMA_5"],errors="coerce").values
H6S13=pd.to_numeric(h6["SMA_13"],errors="coerce").values; H6S55=pd.to_numeric(h6["SMA_55"],errors="coerce").values
C=[];S5=[];S13=[];S55=[];SD=[]
for _,r in st.iterrows():
    i=bisect.bisect_right(h6t,r["signal_time"].to_datetime64())-1
    if i<0: C.append(np.nan);S5.append(np.nan);S13.append(np.nan);S55.append(np.nan);SD.append("");continue
    C.append(H6C[i]);S5.append(H6S5[i]);S13.append(H6S13[i]);S55.append(H6S55[i]);SD.append(str(r["dir"]).upper())
st["h6c"]=C;st["h6s5"]=S5;st["h6s13"]=S13;st["h6s55"]=S55;st["side"]=SD
st["b5p"]=(st["h6c"]-st["h6s5"])/st["h6s5"]*100.0
st["b55p"]=(st["h6c"]-st["h6s55"])/st["h6s55"]*100.0
st["r13p"]=(st["h6s13"]-st["h6s55"])/st["h6s55"]*100.0
base=(pd.to_numeric(st["b5p"],errors="coerce")>0)&(pd.to_numeric(st["b55p"],errors="coerce")>0)
def perf(cand):
    t=cand.copy().reset_index(drop=True)
    t["entry_bar_idx"]=pd.to_numeric(t["entry_bar_idx"],errors="coerce").astype(int)
    tr=replay_three_stage(m30_state,t)
    if tr is None or tr.empty: return None,None
    per=per_trade_from_stages(tr); per["dir"]=per["dir"].astype(str)
    return per, metric(per["stage_pnl_weighted"])
print("== r13_55 阈值扫描 (门= r13_55>=thr & b5>0 & b55>0) ==")
print("%6s %5s %7s %8s %8s %8s %6s"%("thr%","n","PF","EV","testPF","pnl","WR%"))
rows=[]
for thr in np.arange(-8,8.01,0.5):
    msk=base & (pd.to_numeric(st["r13p"],errors="coerce")>=thr)
    cand=st[msk].copy()
    per,m=perf(cand)
    if per is None: continue
    test=split_test(per,"stage_pnl_weighted")
    rows.append((thr,m["n"],m["pf"],m["ev"],test["test_pf"],m["pnl"],m["wr"]))
    print("%6.1f %5d %7.3f %8.2f %8.3f %8.0f %6.1f"%(thr,m["n"],m["pf"],m["ev"],test["test_pf"],m["pnl"],m["wr"]))
# 稳健性: 对若干阈值做 walk-forward(test24-26) + 按年PF
print("\n== 关键阈值 walk-forward (test24-26 / test25-26) ==")
for thr in [-4.0,-2.0,-1.0,0.0,1.0,2.0,4.0]:
    msk=base & (pd.to_numeric(st["r13p"],errors="coerce")>=thr)
    per,m=perf(st[msk].copy())
    if per is None: continue
    per["_y"]=pd.to_datetime(per["signal_time"]).dt.year
    def pf(y0,y1):
        g=per[(per["_y"]>=y0)&(per["_y"]<=y1)];p=g["stage_pnl_weighted"]
        tw=p[p>0].sum();tl=abs(p[p<0].sum())
        return float(tw/tl) if tl>0 else (999.0 if tw>0 else 0.0)
    print("thr=%5.1f  n=%4d  test24-26=%6.3f  test25-26=%6.3f"%(thr,len(per),pf(2024,2026),pf(2025,2026)))
pd.DataFrame(rows,columns=["thr","n","pf","ev","testpf","pnl","wr"]).to_csv(OUT/"gate_threshold_scan.csv",index=False,encoding="utf-8-sig")
print("\nwrote",OUT/"gate_threshold_scan.csv")
