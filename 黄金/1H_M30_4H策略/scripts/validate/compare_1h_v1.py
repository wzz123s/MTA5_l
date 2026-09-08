# -*- coding: utf-8 -*-
"""1H_M30_4H 对账 (A2): Tester 台账 vs Python expected (trade_key = entry|L/S|S{stage})."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

ledger = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\1H_M30_4H_abc_trade_ledger.csv"
expected = r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\auto_trade\python_expected_2025_2026\python_expected_1h_2025_2026.csv"

def read(path):
    for enc in ['utf-8-sig', 'utf-8', 'gbk', 'mbcs', 'utf-16']:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    raise RuntimeError("读失败: " + path)

led = read(ledger); exp = read(expected)
print("台账 stage:", len(led), "| 预期 stage:", len(exp))

exp['dir_n'] = exp['dir'].astype(str).str.upper()
exp['key'] = (pd.to_datetime(exp['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|'
              + exp['dir_n'] + '|S' + exp['stage'].astype(str))

led['dir_n'] = led['dir'].astype(str).str.upper().map({'BUY': 'L', 'SELL': 'S'})
led['key'] = (pd.to_datetime(led['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|'
              + led['dir_n'] + '|S' + led['stage'].astype(str))

exp_keys = set(exp['key']); led_keys = set(led['key'])
matched = len(exp_keys & led_keys)
den = len(exp_keys) or 1
print("matched:", matched, "/", len(exp_keys), "= %.1f%%" % (matched / den * 100))
miss = sorted(exp_keys - led_keys)
extra = sorted(led_keys - exp_keys)
print("missing(预期有台账无):", len(miss))
print("extra(台账有预期无):", len(extra))

# stage/mode breakdown of missing/extra
def breakdown(keys, frame):
    from collections import Counter
    kset = set(keys)
    sub = frame[frame['key'].isin(kset)]
    return Counter(sub['stage'].astype(str) + '_' + sub['mode'].astype(str))

print("missing by stage_mode:", dict(breakdown(miss, exp)))
print("extra   by stage_mode:", dict(breakdown(extra, led)))

# 交易数 & 示例
def trades(f):
    return f.drop_duplicates(['signal_time', 'dir']).shape[0]
print("\n台账交易:", trades(led), "| 预期:", trades(exp))
if len(miss) <= 12:
    print("missing 示例:", miss[:12])
if len(extra) <= 12:
    print("extra 示例:", extra[:12])
