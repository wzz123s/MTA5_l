# -*- coding: utf-8 -*-
"""归一化对比: dir 映射 + entry_time 对齐(EA entry = Python entry)"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

EA = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
PY = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\python_expected_2025_2026\python_expected_2h_abc_2025_2026.csv"

ea = pd.read_csv(EA, encoding='utf-8-sig')
py = pd.read_csv(PY, encoding='utf-8-sig')

# dir 归一化
ea['dir_n'] = ea['dir'].map({'BUY':'L','SELL':'S'})

# entry_time 统一格式
ea['entry_ts'] = pd.to_datetime(ea['entry_time'])
py['entry_ts'] = pd.to_datetime(py['entry_time'])

# key
ea['key'] = ea['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + ea['dir_n'] + '|S' + ea['stage'].astype(str)
py['key'] = py['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + py['dir'] + '|S' + py['stage'].astype(str)

print("EA 行数:", len(ea), "去重:", ea['key'].nunique())
print("PY 行数:", len(py), "去重:", py['key'].nunique())

ea_set = set(ea['key']); py_set = set(py['key'])
both = ea_set & py_set; missing = py_set - ea_set; extra = ea_set - py_set
print("\n归一化后:")
print("  匹配:", len(both))
print("  Python有EA无:", len(missing))
print("  EA有Python无:", len(extra))

# 匹配的价格 diff
merged = ea[['key','entry','stop','exit_price','pnl_points']].merge(
    py[['key','entry','stop','exit_price','pnl_points']],
    on='key', suffixes=('_ea','_py'), how='inner'
)
print("\n匹配行数:", len(merged))
if len(merged):
    merged['entry_diff'] = (merged['entry_ea'] - merged['entry_py']).abs()
    merged['exit_diff'] = (merged['exit_price_ea'] - merged['exit_price_py']).abs()
    merged['pnl_diff'] = (merged['pnl_points_ea'] - merged['pnl_points_py']).abs()
    print("entry_diff max:", round(merged['entry_diff'].max(), 3))
    print("exit_diff  max:", round(merged['exit_diff'].max(), 3))
    print("pnl_diff   max:", round(merged['pnl_diff'].max(), 3))
    print("\n样本匹配(前3):")
    print(merged.head(3).to_string())
