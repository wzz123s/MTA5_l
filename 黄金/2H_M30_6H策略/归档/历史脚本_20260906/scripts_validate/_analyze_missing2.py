# -*- coding: utf-8 -*-
"""分析 missing 交易的日期范围 + gate/spec 过滤原因"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

EA = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
PY = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\python_expected_2025_2026\python_expected_2h_abc_2025_2026.csv"
F = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_signals_export.csv"

ea = pd.read_csv(EA, encoding='utf-8-sig')
py = pd.read_csv(PY, encoding='utf-8-sig')
sig = pd.read_csv(F, encoding='utf-8-sig')

ea['dir_n'] = ea['dir'].map({'BUY':'L','SELL':'S'})
ea['entry_ts'] = pd.to_datetime(ea['entry_time'])
py['entry_ts'] = pd.to_datetime(py['entry_time'])

# 交易级 key（entry|dir）
ea['trade_k'] = ea['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + ea['dir_n']
py['trade_k'] = py['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + py['dir']

ea_trades = set(ea['trade_k'])
py_trades = set(py['trade_k'])
missing = py_trades - ea_trades

# missing 交易的 entry_time 和 dir
miss_df = py[py['trade_k'].isin(missing)].drop_duplicates('trade_k')
miss_df['entry_ts'] = pd.to_datetime(miss_df['entry_time'])
miss_df['sig_bar'] = miss_df['entry_ts'] - pd.Timedelta(minutes=30)

# 1. 日期范围差异（entry > 2026.08.14）
cutoff = pd.Timestamp('2026.08.14')
after_cutoff = miss_df[miss_df['entry_ts'] > cutoff]
print("=== missing 交易中 entry_time > 2026.08.14 的:", len(after_cutoff), "/", len(miss_df))

# 2. 其余 missing 的信号 bar 在信号 CSV 里的情况
rest = miss_df[miss_df['entry_ts'] <= cutoff].copy()
print("\n=== 其余 missing (<= 08.14):", len(rest))

# 信号 CSV 的 bar_time -> gate_pass/dir 映射
sig['bar_ts'] = pd.to_datetime(sig['bar_time'])
sig['bar_key'] = sig['bar_ts'].dt.strftime('%Y.%m.%d %H:%M') + '|' + sig['dir']

# rest 的 signal bar key
rest['bar_key'] = rest['sig_bar'].dt.strftime('%Y.%m.%d %H:%M') + '|' + rest['dir'].str.upper().map({'L':'BUY','S':'SELL'})

# 匹配信号 CSV
sig_map = sig[['bar_key','gate_pass','mode','stop_distance']].drop_duplicates('bar_key')
merged = rest.merge(sig_map, on='bar_key', how='left', suffixes=('','_sig'))

print("\n=== 其余 missing 在信号 CSV 里的 gate 情况 ===")
print("gate=PASS:", (merged['gate_pass']=='PASS').sum())
print("gate=FAIL:", (merged['gate_pass']=='FAIL').sum())
print("信号CSV无记录:", merged['gate_pass'].isna().sum())

# gate PASS 的，看 stop_distance
pass_m = merged[merged['gate_pass']=='PASS']
if len(pass_m):
    sd = pd.to_numeric(pass_m['stop_distance'], errors='coerce')
    print("\ngate PASS 的 stop_distance(pt) in [500,3500]:", ((sd>=500)&(sd<=3500)).sum(), "/", len(sd))
