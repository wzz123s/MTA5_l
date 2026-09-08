# -*- coding: utf-8 -*-
"""1H 深度对账 v2: matched 行再比 entry/stop/exit_time/exit_price."""
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

m = led.merge(exp, on='key', suffixes=('_ea', '_py'))
print("matched keys:", len(m))

def num(x): return pd.to_numeric(x, errors='coerce')
m['entry_ea'] = num(m['entry_ea']); m['entry_py'] = num(m['entry_py'])
m['stop_ea'] = num(m['stop_ea']); m['stop_py'] = num(m['stop_py'])
m['ep_ea'] = num(m['exit_price_ea']); m['ep_py'] = num(m['exit_price_py'])
m['et_ea'] = pd.to_datetime(m['exit_time_ea']); m['et_py'] = pd.to_datetime(m['exit_time_py'])

print("entry == :", (m['entry_ea'] == m['entry_py']).sum(), "/", len(m))
print("stop  == :", (m['stop_ea'] == m['stop_py']).sum(), "/", len(m))
print("exit_price ==:", (m['ep_ea'] == m['ep_py']).sum(), "/", len(m))
print("exit_time == :", (m['et_ea'] == m['et_py']).sum(), "/", len(m))

ad = (m['entry_ea'] - m['entry_py']).abs()
print("entry abs diff max:", ad.max(), " nonzero:", (ad > 0).sum())
sd = (m['stop_ea'] - m['stop_py']).abs()
print("stop abs diff max:", sd.max(), " nonzero:", (sd > 0).sum())
ed = (m['ep_ea'] - m['ep_py']).abs()
print("exit_price abs diff max:", ed.max(), " nonzero:", (ed > 0).sum())
td = (m['et_ea'] - m['et_py']).dt.total_seconds().abs()
print("exit_time diff: max %.0fs nonzero %d" % (td.max(), (td > 0).sum()))
print(td.value_counts().head(10).to_dict())

# reason distribution EA vs py on matched
print("\nEA reason:", m['reason'].value_counts().to_dict())
print("PY reason:", m['exit_reason'].value_counts().to_dict())
# show rows where all 4 differ
bad = m[(ad > 0) | (sd > 0) | (ed > 0) | (td > 0)]
print("\nrows with any diff:", len(bad))
if len(bad):
    cols = ['key', 'dir_ea', 'mode_py', 'stage_py', 'entry_ea', 'entry_py', 'stop_ea', 'stop_py',
            'exit_time_ea', 'exit_time_py', 'exit_price_ea', 'exit_price_py', 'reason', 'exit_reason']
    pd.set_option('display.width', 250)
    print(bad[cols].head(18).to_string())
