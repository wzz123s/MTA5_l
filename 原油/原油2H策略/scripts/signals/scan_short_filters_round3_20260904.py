# -*- coding: utf-8 -*-
"""第三轮：4H 门稳健性验证 + 组合 + 逆势对照"""
import numpy as np
import pandas as pd

STRAT = r"F:\use_code\MTA5_l\原油\原油2H策略"
tr = pd.read_csv(STRAT + r"\data\validation\experiments_20260815\short_trades_with_factors.csv")
tr["signal_time"] = pd.to_datetime(tr["signal_time"])

def calc_smma(s, n, m=1):
    sma = pd.Series(np.nan, index=s.index, dtype=float)
    if len(s) >= n:
        sma.iloc[n-1] = s.iloc[:n].mean()
        for i in range(n, len(s)):
            sma.iloc[i] = (m*s.iloc[i] + (n-m)*sma.iloc[i-1])/n
    return sma

h4 = pd.read_csv(r"F:\use_code\MTA5_l\原油\原油4H门策略\data\raw\mt5_history\usoil_4h_gate_live\USOILm_H4.csv")
h4["date"] = pd.to_datetime(h4["date_utc"], utc=True).dt.tz_convert(None) + pd.to_timedelta(4, unit="h")
h4 = h4.dropna(subset=["date","open","high","low","close"]).sort_values("date").reset_index(drop=True)
h4["close"] = pd.to_numeric(h4["close"], errors="coerce")
for n in [5,13,55]:
    h4[f"SMA{n}"] = calc_smma(h4["close"], n)
h4_times = pd.to_datetime(h4["date"]).values.astype("datetime64[ns]")
def h4_bias(t, col):
    idx = np.searchsorted(h4_times, np.datetime64(t), side="right") - 1
    if idx < 0: return np.nan
    c = h4.iloc[idx]["close"]; sma = h4.iloc[idx][col]
    return (c-sma)/sma*100 if (pd.notna(sma) and sma!=0) else np.nan
tr["h4_bias55"] = tr["signal_time"].apply(lambda t: h4_bias(t, "SMA55"))

def pf(p):
    w=p[p>0].sum(); l=abs(p[p<0].sum()); return w/l if l>0 else (999.0 if w>0 else 0.0)
def summ(sub):
    if len(sub)==0: return None
    p=sub["pnl_points"].astype(float)
    return {"n":int(len(sub)),"pf":round(pf(p),3),"wr":round((p>0).mean()*100,1),"ev":round(p.mean(),3),"pnl":round(p.sum(),2)}
def yearly(sub):
    if len(sub)==0: return ""
    return " ".join(f"{y}:{v:+.1f}" for y,v in sub.groupby("year")["pnl_points"].sum().items())

def wf(sub):
    sub = sub.sort_values("signal_time").reset_index(drop=True)
    if len(sub) < 6: return "样本太少"
    cut = int(len(sub)*0.7)
    a = summ(sub.iloc[:cut]); b = summ(sub.iloc[cut:])
    return f"train n={a['n']} PF={a['pf']:.2f} | test n={b['n']} PF={b['pf']:.2f}"

print("="*80)
print("【4H bias55 门稳健性】")
print("="*80)
for t in [0.0, -1.0]:
    sub = tr[tr["h4_bias55"]<=t]
    s = summ(sub)
    print(f"bias55<={t}%: 全样本 n={s['n']} PF={s['pf']:.3f} EV={s['ev']:+.3f}  分年[{yearly(sub)}]")
    print(f"           walk-forward: {wf(sub)}")
    for y in sorted(sub["year"].unique()):
        no = summ(sub[sub["year"]!=y])
        print(f"           去{y}: n={no['n']} PF={no['pf']:.3f} EV={no['ev']:+.3f}")
    print()

print("="*80)
print("【逆势对照：4H bias55 > 0 (超涨回调做空)】")
print("="*80)
for t in [0.0, 2.0, 4.0]:
    sub = tr[tr["h4_bias55"] > t]
    s = summ(sub)
    if s is None: continue
    print(f"  bias55 > {t}%: n={s['n']:3d} PF={s['pf']:.3f} WR={s['wr']:.1f}% EV={s['ev']:+.3f} 分年[{yearly(sub)}]")

print()
print("="*80)
print("【4H bias55门 × 止损距离 组合】")
print("="*80)
for b55 in [0.0, -1.0]:
    for lo,hi in [(0.3,0.7),(0.5,1.0)]:
        sub = tr[(tr["h4_bias55"]<=b55) & (tr["stop_pct"]>=lo) & (tr["stop_pct"]<=hi)]
        s = summ(sub)
        if s is None or s["n"]<3: continue
        print(f"  bias55<={b55} & stop({lo}-{hi}): n={s['n']:3d} PF={s['pf']:.3f} EV={s['ev']:+.3f} 分年[{yearly(sub)}]")

print()
print("="*80)
print("【综合最优候选的逐笔】bias55<=0 且 stop 0.5-1.0%")
print("="*80)
sub = tr[(tr["h4_bias55"]<=0) & (tr["stop_pct"]>=0.5) & (tr["stop_pct"]<=1.0)].sort_values("signal_time")
s = summ(sub)
if s: print(f"  n={s['n']} PF={s['pf']:.3f} EV={s['ev']:+.3f} 分年[{yearly(sub)}]")
for _,r in sub.iterrows():
    print(f"    {r['signal_time'].date()}  pnl={r['pnl_points']:+.2f}  stop={r['stop_pct']:.2f}%  bias55={r['h4_bias55']:+.2f}%  up_len={int(r['prev_up_len'])}")
