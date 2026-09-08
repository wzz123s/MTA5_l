# -*- coding: utf-8 -*-
"""统计 EA 退出行为和持仓时间"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

EA = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
ea = pd.read_csv(EA, encoding='utf-8-sig')

print("=== EA reason 分布 ===")
print(ea['reason'].value_counts().to_string())

ea['entry_ts'] = pd.to_datetime(ea['entry_time'])
ea['exit_ts'] = pd.to_datetime(ea['exit_time'])
ea['hold_bars'] = (ea['exit_ts'] - ea['entry_ts']).dt.total_seconds() / 1800

print("\n=== 持仓 bar 数分布 ===")
print(ea['hold_bars'].value_counts().sort_index().to_string())

print("\n=== 同 bar 退出 (hold_bars==0) 比例 ===")
same = (ea['hold_bars'] == 0).sum()
print("同bar退出:", same, "/", len(ea), "=", "%.1f%%" % (100*same/len(ea)))

print("\n=== exit_time == entry_time 样本 ===")
print(ea[ea['hold_bars']==0].head(8).to_string())

print("\n=== 持仓 > 1 bar 的样本 ===")
print(ea[ea['hold_bars'] > 1].head(8).to_string())

# Python 退出 reason 分布
PY = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\python_expected_2025_2026\python_expected_2h_abc_2025_2026.csv"
py = pd.read_csv(PY, encoding='utf-8-sig')
print("\n=== Python exit_reason 分布 ===")
print(py['exit_reason'].value_counts().to_string())
