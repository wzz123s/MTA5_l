# -*- coding: utf-8 -*-
"""分析 missing/extra 交易特征."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

led = pd.read_csv(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\30m2H_abc_trade_ledger.csv")
exp = pd.read_csv(r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade\python_expected_2025_2026\python_expected_30m2h_2025_2026.csv", encoding='utf-8-sig')

exp['dir_n'] = exp['dir'].astype(str).str.upper()
exp['key'] = pd.to_datetime(exp['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + exp['dir_n'] + '|S' + exp['stage'].astype(str)
led['dir_n'] = led['dir'].astype(str).str.upper().map({'BUY':'L','SELL':'S'})
led['key'] = pd.to_datetime(led['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + led['dir_n'] + '|S' + led['stage'].astype(str)

exp_keys = set(exp['key']); led_keys = set(led['key'])
missing_keys = exp_keys - led_keys
extra_keys = led_keys - exp_keys

# missing 交易的交易级 (signal_time+dir 去重)
miss_trades = exp[exp['key'].isin(missing_keys)].drop_duplicates(['signal_time','dir'])
extra_trades = led[led['key'].isin(extra_keys)].drop_duplicates(['signal_time','dir'])
print("missing 交易数:", len(miss_trades), "| extra 交易数:", len(extra_trades))
print("\n=== missing 交易 mode 分布 ===")
print(miss_trades['mode'].value_counts().to_string())
print("\n=== extra 交易 mode 分布 ===")
print(extra_trades['mode'].value_counts().to_string())
print("\n=== missing 交易 (前 8) ===")
print(miss_trades[['entry_time','dir','mode','entry','stop']].head(8).to_string())
print("\n=== extra 交易 (前 5) ===")
print(extra_trades[['entry_time','dir','mode','entry','stop','exit_time','reason']].head(5).to_string())

# 方向
print("\nmissing 方向:", miss_trades['dir'].value_counts().to_dict())
print("extra 方向:", extra_trades['dir'].value_counts().to_dict())
