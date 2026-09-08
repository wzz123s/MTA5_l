# -*- coding: utf-8 -*-
"""读信号 CSV bar_time=18:00 完整记录"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

F = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_signals_export.csv"
sig = pd.read_csv(F, encoding='utf-8-sig')

sub = sig[(sig['bar_time'].str.contains('2025.02.21', na=False)) & (sig['gate_pass']=='PASS')]
print("=== 2025.02.21 gate PASS 完整记录 ===")
print(sub[['bar_time','dir','mode','entry','stop','stop_distance','gate_pass']].to_string(index=False))
