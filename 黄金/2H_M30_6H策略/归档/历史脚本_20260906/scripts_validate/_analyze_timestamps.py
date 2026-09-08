# -*- coding: utf-8 -*-
"""精确分析台账三列时间差值"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

EA = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
ea = pd.read_csv(EA, encoding='utf-8-sig')

ea['sig'] = pd.to_datetime(ea['signal_time'])
ea['ent'] = pd.to_datetime(ea['entry_time'])
ea['ex'] = pd.to_datetime(ea['exit_time'])
ea['sig_to_ent_min'] = (ea['ent'] - ea['sig']).dt.total_seconds() / 60
ea['sig_to_ex_min'] = (ea['ex'] - ea['sig']).dt.total_seconds() / 60
ea['ent_to_ex_min'] = (ea['ex'] - ea['ent']).dt.total_seconds() / 60

print("=== 差值(分钟) 统计 ===")
print("signal->entry: min=%.0f max=%.0f mean=%.1f" % (ea['sig_to_ent_min'].min(), ea['sig_to_ent_min'].max(), ea['sig_to_ent_min'].mean()))
print("signal->exit : min=%.0f max=%.0f mean=%.1f" % (ea['sig_to_ex_min'].min(), ea['sig_to_ex_min'].max(), ea['sig_to_ex_min'].mean()))
print("entry->exit  : min=%.0f max=%.0f mean=%.1f" % (ea['ent_to_ex_min'].min(), ea['ent_to_ex_min'].max(), ea['ent_to_ex_min'].mean()))

print("\n=== signal->exit 分布 ===")
print(ea['sig_to_ex_min'].value_counts().head(15).to_string())

print("\n=== signal->entry 分布(唯一值) ===")
print(ea['sig_to_ent_min'].round(0).value_counts().head(15).to_string())

print("\n=== 前 20 行 (sig, ent, ex, sig->ent分钟, sig->ex分钟) ===")
for i, row in ea.head(20).iterrows():
    print("  %s | %s | %s | %+.0f | %+.0f" % (row['signal_time'], row['entry_time'], row['exit_time'], row['sig_to_ent_min'], row['sig_to_ex_min']))
