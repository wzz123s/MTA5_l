# -*- coding: utf-8 -*-
"""验证恢复原始索引后的台账时间戳"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

EA = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
ea = pd.read_csv(EA, encoding='utf-8-sig')

print("行数:", len(ea))
ea['sig'] = pd.to_datetime(ea['signal_time'])
ea['ent'] = pd.to_datetime(ea['entry_time'])
ea['ex'] = pd.to_datetime(ea['exit_time'])
ea['sig_to_ent'] = (ea['ent'] - ea['sig']).dt.total_seconds() / 60
ea['sig_to_ex'] = (ea['ex'] - ea['sig']).dt.total_seconds() / 60
ea['ent_to_ex'] = (ea['ex'] - ea['ent']).dt.total_seconds() / 60

print("\n=== 差值(分钟) ===")
print("signal->entry: min=%.0f max=%.0f mean=%.1f" % (ea['sig_to_ent'].min(), ea['sig_to_ent'].max(), ea['sig_to_ent'].mean()))
print("signal->exit : min=%.0f max=%.0f mean=%.1f" % (ea['sig_to_ex'].min(), ea['sig_to_ex'].max(), ea['sig_to_ex'].mean()))
print("entry->exit  : min=%.0f max=%.0f mean=%.1f" % (ea['ent_to_ex'].min(), ea['ent_to_ex'].max(), ea['ent_to_ex'].mean()))

print("\n=== 前 8 行 ===")
for i, row in ea.head(8).iterrows():
    print("  sig=%s ent=%s exit=%s %s %s S%d" % (row['signal_time'], row['entry_time'], row['exit_time'], row['dir'], row['mode'], row['stage']))

print("\n=== 日期范围 ===")
print("signal:", ea['sig'].min(), "->", ea['sig'].max())
print("entry :", ea['ent'].min(), "->", ea['ent'].max())
