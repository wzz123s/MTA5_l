# -*- coding: utf-8 -*-
"""v59 对比"""
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
ea['key'] = ea['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + ea['dir_n'] + '|S' + ea['stage'].astype(str)
py['key'] = py['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + py['dir'] + '|S' + py['stage'].astype(str)

ea_set = set(ea['key']); py_set = set(py['key'])
both = ea_set & py_set; missing = py_set - ea_set; extra = ea_set - py_set
print("EA 行数:", len(ea), " Python 行数:", len(py))
print("匹配:", len(both), " Python有EA无:", len(missing), " EA有Python无:", len(extra))

# 交易数
ea_trades = ea.drop_duplicates(['entry_ts','dir_n'])
py_trades = py.drop_duplicates(['entry_ts','dir'])
print("\n交易数: EA", len(ea_trades), " Python", len(py_trades))

# 交易级 missing/extra
ea_tk = set(ea['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + ea['dir_n'])
py_tk = set(py['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + py['dir'])
miss_t = py_tk - ea_tk
extra_t = ea_tk - py_tk
print("交易级: missing", len(miss_t), " extra", len(extra_t))

# 匹配的价格 diff
merged = ea[['key','entry','stop','exit_price','pnl_points']].merge(
    py[['key','entry','stop','exit_price','pnl_points']], on='key', suffixes=('_ea','_py'), how='inner')
print("\n匹配行数:", len(merged))
if len(merged):
    print("entry_diff max:", round((merged['entry_ea']-merged['entry_py']).abs().max(), 4))
    print("exit_diff  max:", round((merged['exit_price_ea']-merged['exit_price_py']).abs().max(), 4))
    print("pnl_diff   max:", round((merged['pnl_points_ea']-merged['pnl_points_py']).abs().max(), 4))
    # exit_diff > 0.01 的行数
    big_exit = ((merged['exit_price_ea']-merged['exit_price_py']).abs() > 0.01).sum()
    print("exit_diff>0.01 的行数:", big_exit, "/", len(merged))
