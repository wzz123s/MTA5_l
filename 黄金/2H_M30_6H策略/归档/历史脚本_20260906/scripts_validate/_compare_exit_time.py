# -*- coding: utf-8 -*-
"""对比 matched 交易的 exit_time 差异"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

EA = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
PY = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\python_expected_2025_2026\python_expected_2h_abc_2025_2026.csv"

ea = pd.read_csv(EA, encoding='utf-8-sig')
py = pd.read_csv(PY, encoding='utf-8-sig')

ea['dir_n'] = ea['dir'].map({'BUY':'L','SELL':'S'})
ea['entry_ts'] = pd.to_datetime(ea['entry_time'])
ea['exit_ts'] = pd.to_datetime(ea['exit_time'])
py['entry_ts'] = pd.to_datetime(py['entry_time'])
py['exit_ts'] = pd.to_datetime(py['exit_time'])

ea['key'] = ea['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + ea['dir_n'] + '|S' + ea['stage'].astype(str)
py['key'] = py['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + py['dir'] + '|S' + py['stage'].astype(str)

merged = ea[['key','exit_ts']].merge(py[['key','exit_ts']], on='key', suffixes=('_ea','_py'))
print("匹配行数:", len(merged))
merged['exit_diff_min'] = (merged['exit_ts_ea'] - merged['exit_ts_py']).dt.total_seconds() / 60
print("\nexit_time 差异(分钟):")
print(merged['exit_diff_min'].describe().to_string())
print("\nexit_time 完全一致(0分钟):", (merged['exit_diff_min']==0).sum(), "/", len(merged))
print("\n差异分布:")
print(merged['exit_diff_min'].value_counts().head(10).to_string())

# 信号级 max exit（EA 每个信号的最后退出）
ea_sig = ea.groupby(['entry_ts','dir_n'])['exit_ts'].max().reset_index()
py_sig = py.groupby(['entry_ts','dir'])['exit_ts'].max().reset_index()
ea_sig['key'] = ea_sig['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + ea_sig['dir_n']
py_sig['key'] = py_sig['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + py_sig['dir']
sig_merged = ea_sig[['key','exit_ts']].merge(py_sig[['key','exit_ts']], on='key', suffixes=('_ea','_py'))
sig_merged['diff_min'] = (sig_merged['exit_ts_ea'] - sig_merged['exit_ts_py']).dt.total_seconds() / 60
print("\n=== 信号级 max exit 对比 ===")
print("信号数:", len(sig_merged))
print("max exit 一致(0分钟):", (sig_merged['diff_min']==0).sum(), "/", len(sig_merged))
