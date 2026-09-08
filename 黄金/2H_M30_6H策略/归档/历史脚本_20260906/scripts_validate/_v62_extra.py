# -*- coding: utf-8 -*-
"""分析 v62 extra 40 交易"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

EA = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
PY = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\python_expected_2025_2026\python_expected_2h_abc_2025_2026.csv"

ea = pd.read_csv(EA, encoding='utf-8-sig')
py = pd.read_csv(PY, encoding='utf-8-sig')

ea['dir_n'] = ea['dir'].map({'BUY':'L','SELL':'S'})
ea['entry_ts'] = pd.to_datetime(ea['entry_time'])
py['entry_ts'] = pd.to_datetime(py['entry_time'])
ea['trade_k'] = ea['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + ea['dir_n']
py['trade_k'] = py['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + py['dir']

ea_tk = set(ea['trade_k'])
py_tk = set(py['trade_k'])
extra = ea_tk - py_tk
missing = py_tk - ea_tk

extra_df = ea[ea['trade_k'].isin(extra)].drop_duplicates('trade_k')
missing_df = py[py['trade_k'].isin(missing)].drop_duplicates('trade_k')

print("extra 交易 mode 分布:", extra_df.groupby('mode').size().to_dict())
print("missing 交易 mode 分布:", missing_df.groupby('mode').size().to_dict())

# matched 的 entry_diff
ea['key'] = ea['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + ea['dir_n'] + '|S' + ea['stage'].astype(str)
py['key'] = py['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + py['dir'] + '|S' + py['stage'].astype(str)
merged = ea[['key','entry','exit_price','pnl_points']].merge(
    py[['key','entry','exit_price','pnl_points']], on='key', suffixes=('_ea','_py'), how='inner')
print("\n匹配行数:", len(merged))
print("entry_diff max:", round((merged['entry_ea']-merged['entry_py']).abs().max(), 4))
print("exit_diff max:", round((merged['exit_price_ea']-merged['exit_price_py']).abs().max(), 4))
print("exit_diff>0.01 行数:", ((merged['exit_price_ea']-merged['exit_price_py']).abs()>0.01).sum(), "/", len(merged))

# extra 交易详情
print("\n=== extra 交易详情(前15) ===")
for _, r in extra_df.head(15).iterrows():
    print("  %s %s %s" % (r['entry_time'], r['dir'], r['mode']))
