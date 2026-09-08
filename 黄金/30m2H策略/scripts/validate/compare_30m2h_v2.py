# -*- coding: utf-8 -*-
"""30m2H 对账 v2: 预期用 trade_key 列."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

ledger = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\30m2H_abc_trade_ledger.csv"
expected = r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade\python_expected_2025_2026\python_expected_30m2h_2025_2026.csv"

def read(path):
    for enc in ['utf-8-sig','utf-8','gbk','mbcs','utf-16']:
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    raise RuntimeError("读失败")

led = read(ledger); exp = read(expected)
print("台账 stage:", len(led), "| 预期 stage:", len(exp))

# 预期 trade_key 已含 entry|dir|S{stage}
exp['dir_n'] = exp['dir'].astype(str).str.upper()  # L/S
exp['key'] = pd.to_datetime(exp['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + exp['dir_n'] + '|S' + exp['stage'].astype(str)

# 台账
led['dir_n'] = led['dir'].astype(str).str.upper().map({'BUY':'L','SELL':'S'})
led['key'] = pd.to_datetime(led['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + led['dir_n'] + '|S' + led['stage'].astype(str)

exp_keys = set(exp['key']); led_keys = set(led['key'])
matched = len(exp_keys & led_keys)
print("matched:", matched, "/", len(exp_keys), "= %.1f%%" % (matched/len(exp_keys)*100))
print("missing(预期有台账无):", len(exp_keys - led_keys))
print("extra(台账有预期无):", len(led_keys - exp_keys))

# 差异示例
if len(exp_keys - led_keys) < 10:
    print("missing 示例:", sorted(exp_keys - led_keys)[:5])
if len(led_keys - exp_keys) < 10:
    print("extra 示例:", sorted(led_keys - exp_keys)[:5])

# 台账 trade 数
print("\n台账交易:", led.drop_duplicates(['signal_time','dir']).shape[0], "| 预期:", exp.drop_duplicates(['signal_time','dir']).shape[0])
