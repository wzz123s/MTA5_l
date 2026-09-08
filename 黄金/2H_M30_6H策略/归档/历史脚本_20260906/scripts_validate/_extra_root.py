# -*- coding: utf-8 -*-
"""复现 extra 交易的 Python 检测条件（planned_exit vs 同侧校验）"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
import pandas as pd

F = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\data\raw\mt5_history\2h_m30_6h_live\XAUUSDm_M30.csv"
df = pd.read_csv(F)
df['ts'] = pd.to_datetime(df['time'])

def calc_smma(series, n, m=1):
    sma = pd.Series(index=series.index, dtype=float)
    sma.iloc[:n-1] = pd.NA
    if len(series) >= n:
        sma.iloc[n-1] = series.iloc[:n].mean()
        for i in range(n, len(series)):
            sma.iloc[i] = (m*series.iloc[i] + (n-m)*sma.iloc[i-1]) / n
    return sma

df['SMA5'] = calc_smma(df['close'], 5)
df['SMA13'] = calc_smma(df['close'], 13)
valid = df['SMA13'].notna() & df['SMA5'].notna()
df['方向'] = None
scoped = df.loc[valid].copy()
gt = scoped['SMA5'] > scoped['SMA13']
prev = gt.shift(1, fill_value=False)
scoped['方向'] = np.select([gt & ~prev, ~gt & prev, gt & prev, ~gt & ~prev], ['good','bad','up','down'], default=None)
scoped.loc[scoped.index[0], '方向'] = 'up' if bool(gt.loc[scoped.index[0]]) else 'down'
df.loc[scoped.index, '方向'] = scoped['方向']

raw = np.zeros(len(df), dtype=int)
raw[df['方向']=='good'] = 2; raw[df['方向']=='bad'] = -2; raw[df['方向']=='up'] = 1; raw[df['方向']=='down'] = -1
merged = raw.copy()
stack = []; state = None
for i in range(len(df)):
    d = raw[i]
    if abs(d) == 2:
        if state is None: state = -1 if d == 2 else 1
        if stack:
            pi = stack[-1]; typ = raw[pi]; rc = 0
            for k in range(pi+1, i):
                if (typ==2 and raw[k]==1) or (typ==-2 and raw[k]==-1): rc += 1
            if rc < 8: merged[i] = state; stack.pop()
            else: merged[i] = raw[i]; state = 1 if typ==2 else -1; stack.pop(); stack.append(i)
        else: merged[i] = raw[i]; stack.append(i)
df['raw'] = raw; df['merged'] = merged

post_n = np.zeros(len(df), dtype=int)
counter = 0; last_cross = None
for i in range(len(df)):
    d = merged[i]
    if d == 2: counter = 1; last_cross = 1
    elif d == -2: counter = -1; last_cross = -1
    elif d == 1 and last_cross == 1: counter += 1
    elif d == -1 and last_cross == -1: counter -= 1
    else: counter = 0; last_cross = 0
    post_n[i] = counter
df['post_n'] = post_n

# extra 交易（EA 有 Python 无）的 entry_time
extra_entries = ['2025-01-06 13:00', '2025-01-17 17:00', '2025-01-27 12:00', '2025-04-02 02:30', '2025-04-02 03:00', '2025-04-02 03:30']
for et in extra_entries:
    # signal bar = entry - 30min
    sig_ts = pd.Timestamp(et) - pd.Timedelta(minutes=30)
    idx = df.index[df['ts'] == sig_ts]
    if len(idx) == 0:
        print("%s: signal bar 未找到" % et); continue
    i = idx[0]
    row = df.iloc[i]
    entry = df.iloc[i+1]['open'] if i+1 < len(df) else np.nan
    sl = row['SMA13']
    pn = post_n[i]
    is_long = pn > 0
    side_ok = (is_long and sl < entry) or ((not is_long) and sl > entry)
    # planned_exit
    opp = -2 if is_long else 2
    has_exit = False
    for j in range(i+1, len(df)):
        if raw[j] == opp: has_exit = True; break
    print("%s pn=%d 方向=%s sl=%.3f entry=%.3f side_ok=%s planned_exit=%s" % (et, pn, str(row['方向']), sl, entry, side_ok, has_exit))
