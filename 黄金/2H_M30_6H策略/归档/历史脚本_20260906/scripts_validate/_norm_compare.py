# -*- coding: utf-8 -*-
"""归一化对比: dir 映射 + EA entry_time -30min"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

EA = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
PY = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\python_expected_2025_2026\python_expected_2h_abc_2025_2026.csv"

ea = pd.read_csv(EA, encoding='utf-8-sig')
py = pd.read_csv(PY, encoding='utf-8-sig')

# dir 归一化
ea['dir_n'] = ea['dir'].map({'BUY':'L','SELL':'S'})
py['dir_n'] = py['dir']

# EA entry_time -30min 对齐
ea['entry_ts'] = pd.to_datetime(ea['entry_time']) - pd.Timedelta(minutes=30)
py['entry_ts'] = pd.to_datetime(py['entry_time'])

# 归一化 key: entry_ts|dir|stage
ea['key'] = ea['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + ea['dir_n'] + '|S' + ea['stage'].astype(str)
py['key'] = py['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + py['dir_n'] + '|S' + py['stage'].astype(str)

print("EA key 数:", len(ea), "去重:", ea['key'].nunique())
print("PY key 数:", len(py), "去重:", py['key'].nunique())

# 交集
ea_set = set(ea['key'])
py_set = set(py['key'])
both = ea_set & py_set
missing = py_set - ea_set
extra = ea_set - py_set
print("\n归一化后:")
print("  匹配(交集):", len(both))
print("  Python 有 EA 无:", len(missing))
print("  EA 有 Python 无:", len(extra))

# 交易数（按 entry_ts|dir 去重，不含 stage）
ea_trade = ea[['entry_ts','dir_n']].drop_duplicates()
py_trade = py[['entry_ts','dir_n']].drop_duplicates()
print("\n交易数(entry|dir 去重):")
print("  EA:", len(ea_trade), " Python:", len(py_trade))

# EA entry_ts 的日期范围
print("\nEA entry_ts 范围:", ea['entry_ts'].min(), "->", ea['entry_ts'].max())
print("PY entry_ts 范围:", py['entry_ts'].min(), "->", py['entry_ts'].max())

# 匹配的交易，看 entry 价格 diff
merged = ea[['key','entry','stop','exit_price','pnl_points']].merge(
    py[['key','entry','stop','exit_price','pnl_points']],
    on='key', suffixes=('_ea','_py'), how='inner'
)
print("\n匹配行数:", len(merged))
if len(merged):
    merged['entry_diff'] = merged['entry_ea'] - merged['entry_py']
    merged['exit_diff'] = merged['exit_price_ea'] - merged['exit_price_py']
    merged['pnl_diff'] = merged['pnl_points_ea'] - merged['pnl_points_py']
    print("entry_diff max:", merged['entry_diff'].abs().max())
    print("exit_diff max:", merged['exit_diff'].abs().max())
    print("pnl_diff max:", merged['pnl_diff'].abs().max())
    # 样本
    print("\n样本匹配(前3):")
    print(merged.head(3).to_string())
