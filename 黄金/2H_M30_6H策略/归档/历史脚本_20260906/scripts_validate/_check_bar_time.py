# -*- coding: utf-8 -*-
"""读信号 CSV 的 bar_time，确认和 [SIGNAL] signal_time 的关系"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

F = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_signals_export.csv"
sig = pd.read_csv(F, encoding='utf-8-sig')

# 找 2025.02.21 附近的记录
sub = sig[sig['bar_time'].str.contains('2025.02.21 1', na=False)]
print("=== 信号 CSV 里 2025.02.21 17:00-19:00 的记录 ===")
for _, row in sub.iterrows():
    print("  bar_time=%s dir=%s mode=%s gate=%s" % (row['bar_time'], row['dir'], row['mode'], row['gate_pass']))

# 也看 2025.02.21 全天的 gate PASS 记录
sub2 = sig[(sig['bar_time'].str.contains('2025.02.21', na=False)) & (sig['gate_pass']=='PASS')]
print("\n=== 2025.02.21 全天 gate PASS 记录 ===")
for _, row in sub2.iterrows():
    print("  bar_time=%s dir=%s mode=%s" % (row['bar_time'], row['dir'], row['mode']))
