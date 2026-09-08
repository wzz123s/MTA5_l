# -*- coding: utf-8 -*-
"""复现 Python 在 2025.02.04 09:30 的 SMA 交叉"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

F = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\data\raw\mt5_history\2h_m30_6h_live\XAUUSDm_M30.csv"
df = pd.read_csv(F)

# 找 2025.02.04 附近
df['ts'] = pd.to_datetime(df['time'])
sub = df[(df['ts'] >= '2025-02-03') & (df['ts'] <= '2025-02-04 12:00')].reset_index(drop=True)

def calc_smma(series, n, m=1):
    sma = pd.Series(index=series.index, dtype=float)
    sma.iloc[:n-1] = pd.NA
    if len(series) >= n:
        sma.iloc[n-1] = series.iloc[:n].mean()
        for i in range(n, len(series)):
            sma.iloc[i] = (m*series.iloc[i] + (n-m)*sma.iloc[i-1]) / n
    return sma

# 用全量数据算 SMA（从 2020 开始，保证 mean-init 正确）
df['ts'] = pd.to_datetime(df['time'])
df['SMA5'] = calc_smma(df['close'], 5)
df['SMA13'] = calc_smma(df['close'], 13)

# 看 2025.02.04 09:00-10:00 的 SMA 和方向
view = df[(df['ts'] >= '2025-02-04 08:30') & (df['ts'] <= '2025-02-04 10:30')].reset_index(drop=True)
view['gt'] = view['SMA5'] > view['SMA13']
view['prev_gt'] = view['gt'].shift(1)
print("=== 2025.02.04 08:30-10:30 SMA5/SMA13 ===")
for _, r in view.iterrows():
    d = "good" if (r['gt'] and not r['prev_gt']) else ("bad" if (not r['gt'] and r['prev_gt']) else ("up" if r['gt'] else "down"))
    print("  %s close=%.3f SMA5=%.6f SMA13=%.6f diff=%.6f 方向=%s" % (r['time'][:16], r['close'], r['SMA5'], r['SMA13'], r['SMA5']-r['SMA13'], d))
