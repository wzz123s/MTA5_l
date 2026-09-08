# -*- coding: utf-8 -*-
"""1H 对账 v3: 容差比较 + 残差分类 (A2 报告用)."""
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
    raise RuntimeError("读失败")

led = read(ledger); exp = read(expected)
exp['dir_n'] = exp['dir'].astype(str).str.upper()
exp['key'] = (pd.to_datetime(exp['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + exp['dir_n'] + '|S' + exp['stage'].astype(str))
led['dir_n'] = led['dir'].astype(str).str.upper().map({'BUY': 'L', 'SELL': 'S'})
led['key'] = (pd.to_datetime(led['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + led['dir_n'] + '|S' + led['stage'].astype(str))

def num(x): return pd.to_numeric(x, errors='coerce').round(3)
exp['entry_n'] = num(exp['entry']); exp['stop_n'] = num(exp['stop']); exp['ep_n'] = num(exp['exit_price'])
led['entry_n'] = num(led['entry']); led['stop_n'] = num(led['stop']); led['ep_n'] = num(led['exit_price'])
exp['et'] = pd.to_datetime(exp['exit_time']); led['et'] = pd.to_datetime(led['exit_time'])

exp_keys = set(exp['key']); led_keys = set(led['key'])
common = exp_keys & led_keys
print("KEY match: %d / %d = %.2f%%" % (len(common), len(exp_keys), len(common) / len(exp_keys) * 100))
print("missing(all exp not in led):", len(exp_keys - led_keys), "| extra:", len(led_keys - exp_keys))

m = led[led['key'].isin(common)].merge(exp[exp['key'].isin(common)], on='key', suffixes=('_ea', '_py'))
print("merged:", len(m))
print("entry equal@3dp:", int((m['entry_n_ea'] == m['entry_n_py']).sum()), "/", len(m))
print("stop  equal@3dp:", int((m['stop_n_ea'] == m['stop_n_py']).sum()), "/", len(m))
print("exit_price equal@3dp:", int((m['ep_n_ea'] == m['ep_n_py']).sum()), "/", len(m))
print("exit_time equal:", int((m['et_ea'] == m['et_py']).sum()), "/", len(m))
fully_same = ((m['entry_n_ea'] == m['entry_n_py']) & (m['stop_n_ea'] == m['stop_n_py'])
              & (m['ep_n_ea'] == m['ep_n_py']) & (m['et_ea'] == m['et_py'])
              & (m['reason'] == m['exit_reason']))
print("fully same row (entry/stop/exit_px/exit_time/reason):", int(fully_same.sum()), "/", len(m))

miss = exp[exp['key'].isin(exp_keys - led_keys)]
print("\nmissing rows by stage:", miss['stage'].value_counts().sort_index().to_dict())
print("missing trades count:", miss.drop_duplicates(['signal_time', 'dir']).shape[0])
print("ledger trades:", led.drop_duplicates(['signal_time', 'dir']).shape[0],
      "| exp trades:", exp.drop_duplicates(['signal_time', 'dir']).shape[0])
print("ledger rows by stage:", led['stage'].value_counts().sort_index().to_dict())
print("expected rows by stage:", exp['stage'].value_counts().sort_index().to_dict())

rd = m[m['reason'] != m['exit_reason']]
print("\nreason-diff rows among matched keys:", len(rd))
if len(rd):
    pd.set_option('display.width', 250)
    print(rd[['key', 'mode_py', 'stage_py', 'reason', 'exit_reason', 'et_ea', 'et_py']].head(25).to_string(max_colwidth=16))
