# -*- coding: utf-8 -*-
"""分析 EA vs Python 台账差异"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

EA = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
PY = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\python_expected_2025_2026\python_expected_2h_abc_2025_2026.csv"

ea = pd.read_csv(EA, encoding='utf-8-sig')
py = pd.read_csv(PY, encoding='utf-8-sig')

print("=== EA 台账 ===")
print("行数:", len(ea))
print("列:", list(ea.columns))
print("dir 分布:", ea['dir'].value_counts().to_dict())
print("stage 分布:", ea['stage'].value_counts().to_dict())
print("mode 分布:", ea['mode'].value_counts().to_dict())
print("日期范围:", ea['entry_time'].min(), "->", ea['entry_time'].max())
print("\n前 5 行:")
print(ea.head().to_string())

print("\n=== Python 台账 ===")
print("行数:", len(py))
print("列:", list(py.columns))
print("dir 分布:", py['dir'].value_counts().to_dict())
print("stage 分布:", py['stage'].value_counts().to_dict())
print("mode 分布:", py['mode'].value_counts().to_dict())
print("日期范围:", py['entry_time'].min(), "->", py['entry_time'].max())
print("\n前 5 行:")
print(py.head().to_string())
