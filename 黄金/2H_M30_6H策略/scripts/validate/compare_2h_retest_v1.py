# -*- coding: utf-8 -*-
"""2H 复测对账: 新口径(P2-2)台账 vs Python expected."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

ledger = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
expected = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\python_expected_2025_2026\python_expected_2h_abc_2025_2026.csv"

def read(path):
    for enc in ['utf-8-sig', 'utf-8', 'gbk', 'mbcs', 'utf-16']:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    raise RuntimeError("read fail")

led = read(ledger); exp = read(expected)
exp['dir_n'] = exp['dir'].astype(str).str.upper()
exp['key'] = (pd.to_datetime(exp['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + exp['dir_n'] + '|S' + exp['stage'].astype(str))
led['dir_n'] = led['dir'].astype(str).str.upper().map({'BUY': 'L', 'SELL': 'S'})
led['key'] = (pd.to_datetime(led['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + led['dir_n'] + '|S' + led['stage'].astype(str))
exp_keys = set(exp['key']); led_keys = set(led['key'])
common = exp_keys & led_keys
print("led rows:", len(led), "exp rows:", len(exp))
print("matched %d/%d = %.2f%%" % (len(common), len(exp_keys), len(common) / len(exp_keys) * 100))
print("missing:", len(exp_keys - led_keys), "| extra:", len(led_keys - exp_keys))
miss = exp[exp['key'].isin(exp_keys - led_keys)]
print("missing by stage:", miss['stage'].value_counts().sort_index().to_dict())
print("missing by mode:", miss.drop_duplicates('key')['mode'].value_counts().to_dict())
print("led trades:", led.drop_duplicates(['signal_time', 'dir']).shape[0], "exp trades:", exp.drop_duplicates(['signal_time', 'dir']).shape[0])
print("led rows by stage:", led['stage'].value_counts().sort_index().to_dict())
print("exp rows by stage:", exp['stage'].value_counts().sort_index().to_dict())
if len(exp_keys - led_keys) <= 20:
    print("missing samples:", sorted(exp_keys - led_keys)[:20])
if len(led_keys - exp_keys) <= 20:
    print("extra samples:", sorted(led_keys - exp_keys)[:20])
