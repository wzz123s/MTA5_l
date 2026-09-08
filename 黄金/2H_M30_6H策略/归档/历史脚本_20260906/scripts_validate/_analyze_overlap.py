# -*- coding: utf-8 -*-
"""分析 Python 信号的时间重叠，估算 InpMaxOpenVirtual=3 的过滤影响"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

PY = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\python_expected_2025_2026\python_expected_2h_abc_2025_2026.csv"
py = pd.read_csv(PY, encoding='utf-8-sig')

# 按信号分组（signal_time|dir），持仓区间 = [entry, max(exit)]
py['sig_ts'] = pd.to_datetime(py['signal_time'])
py['ent_ts'] = pd.to_datetime(py['entry_time'])
py['ex_ts'] = pd.to_datetime(py['exit_time'])

groups = py.groupby(['sig_ts','dir']).agg(
    entry=('ent_ts','min'),
    exit=('ex_ts','max')
).reset_index().sort_values('entry')

print("信号数:", len(groups))

# 计算任意时刻的重叠信号数（用扫描线）
events = []
for _, r in groups.iterrows():
    events.append((r['entry'], 1))
    events.append((r['exit'], -1))
events.sort(key=lambda x: (x[0], x[1]))

max_overlap = 0
cur = 0
overlap_count = []  # 记录每个时刻的重叠数
for t, delta in events:
    cur += delta
    max_overlap = max(max_overlap, cur)

print("最大同时持仓信号数:", max_overlap)

# 模拟 InpMaxOpenVirtual 过滤：只允许同时最多 N 个
def simulate(cap):
    active = []
    opened = 0
    for _, r in groups.iterrows():
        # 移除已退出的
        active = [a for a in active if a > r['entry']]
        if len(active) < cap:
            active.append(r['exit'])
            opened += 1
    return opened

for cap in [1,2,3,5,10,100]:
    print("cap=%d 开仓=%d / %d" % (cap, simulate(cap), len(groups)))
