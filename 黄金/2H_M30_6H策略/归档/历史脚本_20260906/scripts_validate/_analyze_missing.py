# -*- coding: utf-8 -*-
"""分析 missing/extra 交易的 mode 分布"""
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

# 交易数（entry|dir 去重）
ea_trades = ea.drop_duplicates(['entry_ts','dir_n'])
py_trades = py.drop_duplicates(['entry_ts','dir'])
print("=== 交易数(entry|dir 去重) ===")
print("EA:", len(ea_trades), " Python:", len(py_trades))

# EA mode 分布（按交易）
ea_mode = ea_trades.groupby('mode').size()
py_mode = py_trades.groupby('mode').size()
print("\n=== EA mode 分布(交易) ===")
print(ea_mode.to_string())
print("\n=== Python mode 分布(交易) ===")
print(py_mode.to_string())

# missing 分析
ea_set = set(ea['key']); py_set = set(py['key'])
missing = py_set - ea_set
extra = ea_set - py_set

# missing 的交易（去掉 stage）
missing_trades = set()
for k in missing:
    # key = entry|dir|Sstage, 去掉 Sstage
    parts = k.rsplit('|S', 1)
    missing_trades.add(parts[0])

extra_trades = set()
for k in extra:
    parts = k.rsplit('|S', 1)
    extra_trades.add(parts[0])

print("\n=== missing 交易数:", len(missing_trades), " extra 交易数:", len(extra_trades))

# missing 交易的 mode 分布
py['trade_k'] = py['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + py['dir']
missing_py = py[py['trade_k'].isin(missing_trades)]
print("\n=== missing 交易的 mode 分布 ===")
print(missing_py.drop_duplicates('trade_k').groupby('mode').size().to_string())

# extra 交易的 mode 分布
ea['trade_k'] = ea['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + ea['dir_n']
extra_ea = ea[ea['trade_k'].isin(extra_trades)]
print("\n=== extra 交易的 mode 分布 ===")
print(extra_ea.drop_duplicates('trade_k').groupby('mode').size().to_string())

# missing 交易的时间范围
print("\n=== missing 交易 entry_time 范围 ===")
miss_ts = pd.to_datetime(missing_py.drop_duplicates('trade_k')['entry_time'])
print(miss_ts.min(), "->", miss_ts.max())

# 按年份统计 missing
print("\n=== missing 按年份 ===")
print(missing_py.drop_duplicates('trade_k')['entry_ts'].dt.year.value_counts().sort_index().to_string())
