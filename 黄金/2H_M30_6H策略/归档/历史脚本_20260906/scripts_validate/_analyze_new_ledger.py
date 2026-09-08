# -*- coding: utf-8 -*-
"""分析新台账时间戳规律"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

EA = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
ea = pd.read_csv(EA, encoding='utf-8-sig')

print("行数:", len(ea))
print("=== 前 10 行 (signal_time, entry_time, exit_time, dir, mode, stage) ===")
for i, row in ea.head(10).iterrows():
    print("  sig=%s entry=%s exit=%s %s %s S%d" % (row['signal_time'], row['entry_time'], row['exit_time'], row['dir'], row['mode'], row['stage']))

print("=== 时间差统计 ===")
ea['sig_ts'] = pd.to_datetime(ea['signal_time'])
ea['entry_ts'] = pd.to_datetime(ea['entry_time'])
ea['exit_ts'] = pd.to_datetime(ea['exit_time'])
ea['sig_to_entry_h'] = (ea['entry_ts'] - ea['sig_ts']).dt.total_seconds() / 3600
ea['entry_to_exit_h'] = (ea['exit_ts'] - ea['entry_ts']).dt.total_seconds() / 3600

print("signal->entry 小时 分布:")
print(ea['sig_to_entry_h'].describe().to_string())
print("\nentry->exit 小时 分布:")
print(ea['entry_to_exit_h'].describe().to_string())
print("\n同 bar 退出(entry==exit) 比例:", (ea['entry_to_exit_h']==0).sum(), "/", len(ea))
