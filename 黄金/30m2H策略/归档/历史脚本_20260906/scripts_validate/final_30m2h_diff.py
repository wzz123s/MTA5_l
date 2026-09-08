# -*- coding: utf-8 -*-
"""确认 missing 14 组成."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

led = pd.read_csv(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\30m2H_abc_trade_ledger.csv")
exp = pd.read_csv(r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade\python_expected_2025_2026\python_expected_30m2h_2025_2026.csv", encoding='utf-8-sig')

exp['dir_n'] = exp['dir'].astype(str).str.upper()
exp['key'] = pd.to_datetime(exp['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + exp['dir_n'] + '|S' + exp['stage'].astype(str)
led['dir_n'] = led['dir'].astype(str).str.upper().map({'BUY':'L','SELL':'S'})
led['key'] = pd.to_datetime(led['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + led['dir_n'] + '|S' + led['stage'].astype(str)
exp['sig_dt'] = pd.to_datetime(exp['signal_time']); led['sig_dt'] = pd.to_datetime(led['signal_time'])

ek = set(exp['key']); lk = set(led['key'])
miss_keys = ek - lk
extra_keys = lk - ek

# missing 按 stage
from collections import Counter
print("missing stage 分布:", Counter(k.split('|')[-1] for k in miss_keys))
print("extra stage 分布:", Counter(k.split('|')[-1] for k in extra_keys))

# missing 交易级 (mode)
miss_rows = exp[exp['key'].isin(miss_keys)]
print("\nmissing 交易(去重 sig+dir):", miss_rows.drop_duplicates(['signal_time','dir']).shape[0])
miss_t = miss_rows.drop_duplicates(['signal_time','dir'])
print("missing mode:", miss_t['mode'].value_counts().to_dict())
print("missing 交易详情:")
print(miss_t[['signal_time','dir','mode','stage','entry']].to_string())

# extra 交易
extra_rows = led[led['key'].isin(extra_keys)]
print("\nextra 交易:", extra_rows.drop_duplicates(['signal_time','dir'])[['signal_time','dir','mode','entry','reason']].to_string())
