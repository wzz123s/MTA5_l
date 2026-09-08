# -*- coding: utf-8 -*-
"""读信号 CSV 里 2025.02.04 附近所有记录"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

F = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_signals_export.csv"
sig = pd.read_csv(F, encoding='utf-8-sig')

# 2025.02.04 全天记录
sub = sig[sig['bar_time'].str.contains('2025.02.04', na=False)]
print("=== 2025.02.04 信号 CSV 记录 ===")
for _, row in sub.iterrows():
    print("  bar_time=%s dir=%s mode=%s gate=%s stop_distance=%s" % (row['bar_time'], row['dir'], row['mode'], row['gate_pass'], row['stop_distance']))
