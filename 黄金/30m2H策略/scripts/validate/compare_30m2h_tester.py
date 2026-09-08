# -*- coding: utf-8 -*-
"""30m2H 台账 vs Python 预期对账."""
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
    raise RuntimeError("读失败 " + path)

led = read(ledger)
exp = read(expected)
print("台账 stage 行:", len(led), "| 预期 stage 行:", len(exp))

led['dir_n'] = led['dir'].astype(str).str.upper().map({'BUY':'L','SELL':'S'})
led['key'] = pd.to_datetime(led['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + led['dir_n'] + '|S' + led['stage'].astype(str)
exp['dir_n'] = exp['dir'].astype(str).str.upper().map({'BUY':'L','SELL':'S'})
exp['key'] = pd.to_datetime(exp['entry_time']).dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + exp['dir_n'] + '|S' + exp['stage'].astype(str)

exp_keys = set(exp['key']); led_keys = set(led['key'])
matched = len(exp_keys & led_keys)
print("matched:", matched, "/", len(exp_keys), "= %.1f%%" % (matched/len(exp_keys)*100))
print("missing(预期有台账无):", len(exp_keys - led_keys))
print("extra(台账有预期无):", len(led_keys - exp_keys))

# 分析台账 reason 分布 + pnl
print("\n=== 台账 exit_reason 分布 ===")
print(led['reason'].value_counts().to_string())
print("\n=== 台账 stage 分布 ===")
print(led['stage'].value_counts().sort_index().to_dict())
print("\n=== pnl 统计 ===")
print("pnl_points sum:", led['pnl_points'].astype(float).sum())
print("hold_bars=0 比例(同bar退出):", end=" ")
# 无 holding_bars 列, 用 exit_time==entry_time 近似
same = (pd.to_datetime(led['exit_time']) == pd.to_datetime(led['entry_time'])).mean()
print("%.1f%%" % (same*100))
print("\n=== 台账交易数(去重 signal_time+dir):", led.drop_duplicates(['signal_time','dir']).shape[0])
print("预期交易数:", exp.drop_duplicates(['signal_time','dir']).shape[0])
