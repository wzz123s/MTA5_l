# -*- coding: utf-8 -*-
"""精确模拟 InpMaxOpenVirtual 过滤（用 EA 的 469 个 spec 通过信号 + Python 退出时间）"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

F = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_signals_export.csv"
PY = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\python_expected_2025_2026\python_expected_2h_abc_2025_2026.csv"

sig = pd.read_csv(F, encoding='utf-8-sig')
py = pd.read_csv(PY, encoding='utf-8-sig')

# spec 通过的信号（gate PASS + stop_distance in [5000,35000]）
pass_hit = sig[sig['gate_pass']=='PASS'].copy()
pass_hit['sd'] = pd.to_numeric(pass_hit['stop_distance'], errors='coerce')
spec_ok = pass_hit[(pass_hit['sd']>=5000)&(pass_hit['sd']<=35000)].copy()

# entry = bar_time + 30min
spec_ok['bar_ts'] = pd.to_datetime(spec_ok['bar_time'])
spec_ok['entry_ts'] = spec_ok['bar_ts'] + pd.Timedelta(minutes=30)
spec_ok['dir_n'] = spec_ok['dir'].map({'BUY':'L','SELL':'S'})
spec_ok['key'] = spec_ok['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + spec_ok['dir_n']

# Python 的 exit（max exit per 交易）
py['entry_ts'] = pd.to_datetime(py['entry_time'])
py['exit_ts'] = pd.to_datetime(py['exit_time'])
py['key'] = py['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + py['dir']
py_exit = py.groupby('key')['exit_ts'].max().reset_index()

# 合并 exit
merged = spec_ok.merge(py_exit, on='key', how='left')
print("spec 通过信号数:", len(spec_ok))
print("能匹配到 exit 的:", merged['exit_ts'].notna().sum())

# 按 entry 排序，模拟 InpMaxOpenVirtual
merged = merged.sort_values('entry_ts').reset_index(drop=True)

def simulate(cap):
    active = []  # 持仓信号的 exit 时间
    opened = 0
    for _, r in merged.iterrows():
        e = r['entry_ts']
        x = r['exit_ts']
        if pd.isna(x):
            continue  # 无 exit 信息，跳过（或假设立即退出）
        active = [a for a in active if a > e]  # 移除已退出的
        if len(active) < cap:
            active.append(x)
            opened += 1
    return opened

for cap in [3, 5, 10, 100]:
    print("cap=%d -> 开仓 %d / %d" % (cap, simulate(cap), len(spec_ok)))

# 检查：EA 实际开仓 139，看 cap 多少才到 139
print("\nEA 实际开仓: 139")
