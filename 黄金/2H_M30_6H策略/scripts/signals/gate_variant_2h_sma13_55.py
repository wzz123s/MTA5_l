# -*- coding: utf-8 -*-
"""2H_M30_6H 门控变体: bias5&bias55 现门 vs SMA13/SMA55 结构比值叠加 (2026-09-06 立项).
输出: 变体主表 + 按年 (n/PF/pnl) + 2 组 walk-forward(训练/测试) 对比 V0 vs V4.
"""
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
    build_three_opportunities, load_strategy, replay_signals, replay_three_stage)
from experiment_1h_m30_4h_variants_20260813 import per_trade_from_stages, metric, split_test

OUT = Path(r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\data\validation\gate_variant_sma13_55")

def load():
    cfg = STRATS["2H_M30_6H"]
    m30, h6 = load_strategy(cfg)
    m30_state = add_m30_state(m30)
    sig = build_three_opportunities(m30, spec_lo=5.0, spec_hi=35.0)
    replayed = replay_signals(sig, m30)
    enriched = attach_context(replayed, h6, "h6")
    return cfg, m30, m30_state, enriched, h6

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    _, _, m30_state, st, h6 = load()
    st = st.copy(); st["signal_time"] = pd.to_datetime(st["signal_time"])
    h6t = pd.to_datetime(h6["date"]).values.astype("datetime64[ns]")
    h6c = pd.to_numeric(h6["close"], errors="coerce").values
    h6s5 = pd.to_numeric(h6["SMA_5"], errors="coerce").values
    h6s13 = pd.to_numeric(h6["SMA_13"], errors="coerce").values
    h6s55 = pd.to_numeric(h6["SMA_55"], errors="coerce").values
    def h6_at(t):
        i = bisect.bisect_right(h6t, t.to_datetime64()) - 1
        return i if i >= 0 else -1
    J = np.zeros(len(st), dtype=int); C=np.zeros(len(st)); S5=np.zeros(len(st)); S13=np.zeros(len(st)); S55=np.zeros(len(st)); SD=[]
    for k,row in enumerate(st.iterrows()):
        _,r=row; i=h6_at(r["signal_time"])
        if i<0: J[k]=-1; C[k]=np.nan; S5[k]=np.nan; S13[k]=np.nan; S55[k]=np.nan; SD.append(""); continue
        J[k]=i; C[k]=h6c[i]; S5[k]=h6s5[i]; S13[k]=h6s13[i]; S55[k]=h6s55[i]; SD.append(str(r["dir"]).upper())
    st["_i"]=J; st["h6c"]=C; st["h6s5"]=S5; st["h6s13"]=S13; st["h6s55"]=S55; st["side"]=SD
    st["b5p"]=(st["h6c"]-st["h6s5"])/st["h6s5"]*100.0
    st["b55p"]=(st["h6c"]-st["h6s55"])/st["h6s55"]*100.0
    st["r13_55"]=(st["h6s13"]-st["h6s55"])/st["h6s55"]*100.0
    def M(col, thr=0.0, gt=True):
        v=pd.to_numeric(st[col], errors="coerce"); sd=st["side"]
        if gt: return ((sd=="L")&(v>thr))|((sd=="S")&(v<thr))
        return ((sd=="L")&(v<=thr))|((sd=="S")&(v>=thr))
    masks={
        "V0_b5_b55": M("b5p")&M("b55p"),
        "V1_r1355_b5": M("r13_55")&M("b5p"),
        "V2_r1355": M("r13_55"),
        "V3_b13_b55": M("b5p")&M("b55p"),  # 占位, 后续用真b13另算
        "V4_r1355_b5_b55": M("r13_55")&M("b5p")&M("b55p"),
    }
    def perf(df):
        t=df.copy().reset_index(drop=True)
        t["entry_bar_idx"]=pd.to_numeric(t["entry_bar_idx"],errors="coerce").astype(int)
        tr=replay_three_stage(m30_state, t)
        if tr is None or tr.empty: return None
        per=per_trade_from_stages(tr); per["dir"]=per["dir"].astype(str)
        m=metric(per["stage_pnl_weighted"]); test=split_test(per,"stage_pnl_weighted")
        return per, m, test
    rows=[]
    for name,msk in masks.items():
        cand=st[msk].copy()
        cand["_y"]=pd.to_datetime(cand["signal_time"]).dt.year
        row={"variant":name,"n":0,"pf":0.0,"ev":0.0,"testpf":0.0,"wr":0.0,"pnl":0.0}
        per,m,test=perf(cand)
        if per is not None and len(per):
            row.update(n=m["n"],pf=m["pf"],ev=m["ev"],testpf=test["test_pf"],wr=m["wr"],pnl=m["pnl"])
            years=per.copy(); years["_y"]=pd.to_datetime(years["signal_time"]).dt.year
        rows.append(row)
    # 按年 for V0 & V4
    def yearly(msk,label):
        cand=st[msk].copy(); cand["_y"]=pd.to_datetime(cand["signal_time"]).dt.year
        per,m,_=perf(cand)
        out={}
        if per is None or len(per)==0: return out
        per["_y"]=pd.to_datetime(per["signal_time"]).dt.year
        for y,g in per.groupby("_y"):
            mm=metric(g["stage_pnl_weighted"]); out[int(y)]=(mm["n"],mm["pf"],mm["pnl"],mm["wr"])
        return out
    # WF: train/test by year splits
    def wf(msk,label):
        cand=st[msk].copy(); per,m,_=perf(cand)
        if per is None or len(per)==0: return None
        per["_y"]=pd.to_datetime(per["signal_time"]).dt.year
        def pf_range(y0,y1):
            g=per[(per["_y"]>=y0)&(per["_y"]<=y1)]; p=g["stage_pnl_weighted"]
            tw=p[p>0].sum(); tl=abs(p[p<0].sum()); 
            return (len(p), float(tw/tl) if tl>0 else (999.0 if tw>0 else 0.0), float(p.sum()))
        return {"train_20_23":pf_range(2020,2023),"test_24_26":pf_range(2024,2026),
                "train_20_24":pf_range(2020,2024),"test_25_26":pf_range(2025,2026)}
    print("== 变体主表 ==")
    print("%-22s %5s %7s %8s %8s %6s" % ("variant","n","PF","EV","testPF","WR%"))
    for r in rows:
        print("%-22s %5d %7.3f %8.2f %8.3f %6.1f" % (r["variant"],r["n"],r["pf"],r["ev"],r["testpf"],r["wr"]))
    print("\n== 按年 (n/PF/pnl/wr%) V0 vs V4 ==")
    y0=yearly(masks["V0_b5_b55"],"V0"); y4=yearly(masks["V4_r1355_b5_b55"],"V4")
    all_y=sorted(set(y0)|set(y4))
    print("%-6s %-22s %-22s" % ("year","V0 n/pf/pnl/wr","V4 n/pf/pnl/wr"))
    for y in all_y:
        a=y0.get(y,(0,0,0,0)); b=y4.get(y,(0,0,0,0))
        print("%-6d %-22s %-22s" % (y, "%.0f/%.2f/%.0f/%.0f%%"%(a[0],a[1],a[2],a[3]), "%.0f/%.2f/%.0f/%.0f%%"%(b[0],b[1],b[2],b[3])))
    print("\n== walk-forward (训练/测试) V0 vs V4 ==")
    for lbl,msk in [("V0",masks["V0_b5_b55"]),("V4",masks["V4_r1355_b5_b55"])]:
        w=wf(msk,lbl)
        if w: print("%s: train20-23 %s | test24-26 %s || train20-24 %s | test25-26 %s" % (lbl,
            tuple(round(x,3) for x in w["train_20_23"]), tuple(round(x,3) for x in w["test_24_26"]),
            tuple(round(x,3) for x in w["train_20_24"]), tuple(round(x,3) for x in w["test_25_26"])))
    # save summary
    pd.DataFrame(rows).to_csv(OUT/"gate_variant_summary.csv", index=False, encoding="utf-8-sig")
    print("\nwrote", OUT/"gate_variant_summary.csv")

if __name__=="__main__":
    main()
