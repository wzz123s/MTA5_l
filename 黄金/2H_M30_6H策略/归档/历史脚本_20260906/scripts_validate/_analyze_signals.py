# -*- coding: utf-8 -*-
"""分析信号 CSV bar_time 规律"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

F = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_signals_export.csv"
try:
    sig = pd.read_csv(F, encoding='utf-8-sig')
except Exception as e:
    print("读取失败:", e)
    sys.exit(1)

print("行数:", len(sig))
print("列:", list(sig.columns))
print("\n=== 前 15 行 bar_time + dir + gate ===")
for i, row in sig.head(15).iterrows():
    print("  %s %s %s %s" % (row.get('bar_time'), row.get('dir'), row.get('gate_pass'), row.get('decision')))

print("\n=== 后 5 行 ===")
for i, row in sig.tail(5).iterrows():
    print("  %s %s %s %s" % (row.get('bar_time'), row.get('dir'), row.get('gate_pass'), row.get('decision')))

# bar_time 是否连续
bt = pd.to_datetime(sig['bar_time'], errors='coerce')
diffs = bt.diff().dt.total_seconds() / 60
print("\nbar_time 差值(分钟) 分布:")
print(diffs.value_counts().head(10).to_string())

# 非 BUY/SELL/NONE 的信号（有信号的）
hit = sig[sig['dir'].isin(['BUY','SELL'])]
print("\n有信号(BUY/SELL)的行数:", len(hit))
print("gate PASS 数:", (sig['gate_pass']=='PASS').sum())
