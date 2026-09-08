# -*- coding: utf-8 -*-
"""复现 filter_short_segments_causal 在 2025.02.04 的 raw/merged(修复)"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
import pandas as pd

F = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\data\raw\mt5_history\2h_m30_6h_live\XAUUSDm_M30.csv"
df = pd.read_csv(F)

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

# mark_direction（对齐 replay_1h_way_momentum_filter_scan）
valid = df['SMA13'].notna() & df['SMA5'].notna()
df['方向'] = None
scoped = df.loc[valid].copy()
gt = scoped['SMA5'] > scoped['SMA13']
prev = gt.shift(1, fill_value=False)
scoped['方向'] = np.select([gt & ~prev, ~gt & prev, gt & prev, ~gt & ~prev], ['good','bad','up','down'], default=None)
first_idx = scoped.index[0]
scoped.loc[first_idx, '方向'] = 'up' if bool(gt.loc[first_idx]) else 'down'
df.loc[scoped.index, '方向'] = scoped['方向']

# filter_short_segments_causal
raw = np.zeros(len(df), dtype=int)
raw[df['方向']=='good'] = 2
raw[df['方向']=='bad'] = -2
raw[df['方向']=='up'] = 1
raw[df['方向']=='down'] = -1
merged = raw.copy()
stack = []
state = None
for i in range(len(df)):
    d = raw[i]
    if abs(d) == 2:
        if state is None:
            state = -1 if d == 2 else 1
        if stack:
            prev_i = stack[-1]
            typ = raw[prev_i]
            rc = 0
            for k in range(prev_i+1, i):
                if (typ==2 and raw[k]==1) or (typ==-2 and raw[k]==-1):
                    rc += 1
            if rc < 8:
                merged[i] = state
                stack.pop()
            else:
                merged[i] = raw[i]
                state = 1 if typ==2 else -1
                stack.pop(); stack.append(i)
        else:
            merged[i] = raw[i]
            stack.append(i)

df['raw'] = raw
df['merged'] = merged

sub = df[(df['time'] >= '2025-02-04 07:00') & (df['time'] <= '2025-02-04 10:30')].reset_index()
print("=== 2025.02.04 07:00-10:30 ===")
for _, r in sub.iterrows():
    print("  %s 方向=%-5s raw=%d merged=%d" % (r['time'][:16], str(r['方向']), r['raw'], r['merged']))
