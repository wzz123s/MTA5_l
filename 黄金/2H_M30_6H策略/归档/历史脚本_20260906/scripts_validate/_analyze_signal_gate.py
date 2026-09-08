# -*- coding: utf-8 -*-
"""分析信号 CSV 的 gate PASS 和信号检测情况"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

F = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_signals_export.csv"
sig = pd.read_csv(F, encoding='utf-8-sig')

print("信号 CSV 行数:", len(sig))
print("\n=== dir 分布 ===")
print(sig['dir'].value_counts().to_string())
print("\n=== gate_pass 分布 ===")
print(sig['gate_pass'].value_counts().to_string())
print("\n=== decision 分布 ===")
print(sig['decision'].value_counts().to_string())

# 有信号（BUY/SELL）+ gate PASS 的交易数
hit = sig[sig['dir'].isin(['BUY','SELL'])]
pass_hit = hit[hit['gate_pass']=='PASS']
print("\n有信号(BUY/SELL):", len(hit))
print("gate PASS 的信号:", len(pass_hit))

# gate PASS 的 mode 分布
print("\n=== gate PASS 信号的 mode 分布 ===")
print(pass_hit.groupby('mode').size().to_string())

# 这些信号是否真的开仓了（decision）
print("\n=== gate PASS 的 decision 分布 ===")
print(pass_hit.groupby('decision').size().to_string())

# gate PASS 但 SKIP 的原因（stop_pts 不满足？）
print("\n=== gate PASS 信号的 stop_distance 分布 ===")
sd = pd.to_numeric(pass_hit['stop_distance'], errors='coerce')
print("min=%.1f max=%.1f mean=%.1f" % (sd.min(), sd.max(), sd.mean()))
print("stop_distance in [5,35]:", ((sd>=5)&(sd<=35)).sum(), "/", len(sd))
