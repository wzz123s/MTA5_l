# -*- coding: utf-8 -*-
"""debug missing key 差异."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

led = pd.read_csv(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\30m2H_abc_trade_ledger.csv")
exp = pd.read_csv(r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade\python_expected_2025_2026\python_expected_30m2h_2025_2026.csv", encoding='utf-8-sig')

exp['dir_n'] = exp['dir'].astype(str).str.upper()
exp['key'] = pd.to_datetime(exp['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + exp['dir_n'] + '|S' + exp['stage'].astype(str)
led['dir_n'] = led['dir'].astype(str).str.upper().map({'BUY':'L','SELL':'S'})
led['key'] = pd.to_datetime(led['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + led['dir_n'] + '|S' + led['stage'].astype(str)

# 第一笔 missing: 2025-04-13 22:30 S
print("=== 预期 2025-04-13 22:30 S ===")
p = exp[(pd.to_datetime(exp['entry_time'])=='2025-04-13 22:30:00')]
print(p[['signal_time','entry_time','dir','mode','stage','entry','stop','key']].to_string())
print("\n=== 台账 2025-04-13 22:30 附近 S ===")
l = led[(pd.to_datetime(led['entry_time'])>='2025-04-13 21:30') & (pd.to_datetime(led['entry_time'])<='2025-04-14 00:00')]
print(l[['signal_time','entry_time','dir','mode','stage','entry','stop','reason','key']].to_string())

# 预期 signal_time vs entry_time 差
print("\n=== 预期 entry - signal 差 (分钟) ===")
d = (pd.to_datetime(exp['entry_time'])-pd.to_datetime(exp['signal_time'])).dt.total_seconds()/60
print(d.value_counts().to_string())
print("\n=== 台账 entry - signal 差 ===")
d2 = (pd.to_datetime(led['entry_time'])-pd.to_datetime(led['signal_time'])).dt.total_seconds()/60
print(d2.value_counts().to_string())
