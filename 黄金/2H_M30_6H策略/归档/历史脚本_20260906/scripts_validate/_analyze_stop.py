# -*- coding: utf-8 -*-
"""读信号 CSV 的 entry/stop 值，定位 stop 计算异常"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

F = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_signals_export.csv"
sig = pd.read_csv(F, encoding='utf-8-sig')

# gate PASS 的信号
pass_hit = sig[sig['gate_pass']=='PASS'].copy()
pass_hit['entry_n'] = pd.to_numeric(pass_hit['entry'], errors='coerce')
pass_hit['stop_n'] = pd.to_numeric(pass_hit['stop'], errors='coerce')
pass_hit['sd_n'] = pd.to_numeric(pass_hit['stop_distance'], errors='coerce')

print("=== gate PASS 信号前 20 个 (bar_time, dir, mode, entry, stop, stop_distance) ===")
for i, row in pass_hit.head(20).iterrows():
    print("  %s %s %-9s entry=%.3f stop=%.3f sd=%.1f" % (row['bar_time'], row['dir'], row['mode'], row['entry_n'], row['stop_n'], row['sd_n']))

print("\n=== stop 值分布 ===")
print("stop=0 的:", (pass_hit['stop_n']==0).sum())
print("stop<100 的:", (pass_hit['stop_n']<100).sum())
print("stop 合理(2000-3000)的:", ((pass_hit['stop_n']>2000)&(pass_hit['stop_n']<3000)).sum())
print("\nstop_n 描述:")
print(pass_hit['stop_n'].describe().to_string())

print("\n=== entry vs stop 差异 ===")
pass_hit['diff'] = (pass_hit['entry_n'] - pass_hit['stop_n']).abs()
print("|entry-stop| 描述(美元):")
print(pass_hit['diff'].describe().to_string())
print("\n|entry-stop| in [5,35]美元:", ((pass_hit['diff']>=5)&(pass_hit['diff']<=35)).sum(), "/", len(pass_hit))
