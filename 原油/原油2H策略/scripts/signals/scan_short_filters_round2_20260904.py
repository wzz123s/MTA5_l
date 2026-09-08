# -*- coding: utf-8 -*-
"""第二轮：4H 趋势门扫描 + up_len 因子稳健性验证"""
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

# 加载 4H 数据
h4 = pd.read_csv(r"F:\use_code\MTA5_l\原油\原油4H门策略\data\raw\mt5_history\usoil_4h_gate_live\USOILm_H4.csv")
h4["date"] = pd.to_datetime(h4["date_utc"], utc=True).dt.tz_convert(None) + pd.to_timedelta(4, unit="h")
h4 = h4.dropna(subset=["date","open","high","low","close"]).sort_values("date").reset_index(drop=True)
h4["close"] = pd.to_numeric(h4["close"], errors="coerce")
h4["SMA5"] = calc_smma(h4["close"], 5)
h4["SMA13"] = calc_smma(h4["close"], 13)
h4["SMA55"] = calc_smma(h4["close"], 55)

h4_times = pd.to_datetime(h4["date"]).values.astype("datetime64[ns]")
def h4_bias(sig_time, sma_col):
    idx = np.searchsorted(h4_times, np.datetime64(sig_time), side="right") - 1
    if idx < 0: return np.nan
    c = h4.iloc[idx]["close"]; sma = h4.iloc[idx][sma_col]
    if pd.isna(sma) or sma == 0: return np.nan
    return (c - sma) / sma * 100.0

tr["h4_bias5"] = tr["signal_time"].apply(lambda t: h4_bias(t, "SMA5"))
tr["h4_bias13"] = tr["signal_time"].apply(lambda t: h4_bias(t, "SMA13"))
tr["h4_bias55"] = tr["signal_time"].apply(lambda t: h4_bias(t, "SMA55"))

def pf(pnl):
    w = pnl[pnl>0].sum(); l = abs(pnl[pnl<0].sum())
    return w/l if l>0 else (999.0 if w>0 else 0.0)
def summ(sub):
    if len(sub)==0: return None
    p = sub["pnl_points"].astype(float)
    return {"n": int(len(sub)), "pf": round(pf(p),3), "wr": round((p>0).mean()*100,1), "ev": round(p.mean(),3), "pnl": round(p.sum(),2)}
def yearly(sub):
    if len(sub)==0: return ""
    g = sub.groupby("year")["pnl_points"].sum()
    return " ".join(f"{y}:{v:+.1f}" for y,v in g.items())

print("空单基线 n=%d PF=0.722" % len(tr))
print()
print("="*80)
print("【4H 趋势门】(空单希望 4H 为空头 bias<0)")
print("="*80)
for col, label in [("h4_bias55","4H bias55"), ("h4_bias13","4H bias13"), ("h4_bias5","4H bias5")]:
    for t in [0.0, -1.0, -2.0, -3.0]:
        sub = tr[tr[col] <= t]
        s = summ(sub)
        if s is None: continue
        flag = "  <<< PF>=1" if s["pf"]>=1.0 else ""
        print(f"  {label} <= {t}%: n={s['n']:3d} PF={s['pf']:.3f} WR={s['wr']:.1f}% EV={s['ev']:+.3f} 分年[{yearly(sub)}]{flag}")
    print()

print("="*80)
print("【4H 空头趋势 × up_len 段长 组合】")
print("="*80)
for b55 in [0.0, -2.0]:
    for pl in [21, 34, 55]:
        sub = tr[(tr["h4_bias55"]<=b55) & (tr["prev_up_len"]>=pl)]
        s = summ(sub)
        if s is None or s["n"]<3: continue
        flag = "  <<< PF>=1" if s["pf"]>=1.0 else ""
        print(f"  h4_bias55<={b55} & up_len>={pl}: n={s['n']:3d} PF={s['pf']:.3f} WR={s['wr']:.1f}% EV={s['ev']:+.3f} 分年[{yearly(sub)}]{flag}")

print()
print("="*80)
print("【稳健性：up_len 因子去 2021 检验】")
print("="*80)
for pl in [34, 55]:
    sub = tr[tr["prev_up_len"]>=pl]
    s = summ(sub)
    no21 = summ(sub[sub["year"]!=2021])
    print(f"  up_len>={pl}: 全样本 n={s['n']} PF={s['pf']:.3f} | 去2021 n={no21['n']} PF={no21['pf']:.3f} EV={no21['ev']:+.3f}")

print()
print("="*80)
print("【稳健性：up_len>=34 的逐笔明细】")
print("="*80)
sub = tr[tr["prev_up_len"]>=34].sort_values("signal_time")
for _, r in sub.iterrows():
    print(f"  {r['signal_time'].date()}  up_len={int(r['prev_up_len']):3d}  pnl={r['pnl_points']:+.2f}  stop_pct={r['stop_pct']:.2f}%  h4_bias55={r['h4_bias55']:+.2f}%")

# walk-forward: 前70%训练 -> 后30%测试 (up_len>=34)
print()
print("="*80)
print("【walk-forward: up_len>=34】")
print("="*80)
sub = tr[tr["prev_up_len"]>=34].sort_values("signal_time").reset_index(drop=True)
cut = int(len(sub)*0.7)
trn = sub.iloc[:cut]; tst = sub.iloc[cut:]
st = summ(trn); stt = summ(tst)
print(f"  训练({trn['year'].min()}-{trn['year'].max()}): n={st['n']} PF={st['pf']:.3f} EV={st['ev']:+.3f}")
print(f"  测试({tst['year'].min()}-{tst['year'].max()}): n={stt['n']} PF={stt['pf']:.3f} EV={stt['ev']:+.3f}")
