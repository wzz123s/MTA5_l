# -*- coding: utf-8 -*-
"""用正确单位重新分析 missing 信号的 spec 过滤情况(修复列名)"""
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
ea['trade_k'] = ea['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + ea['dir_n']
py['trade_k'] = py['entry_ts'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + py['dir']

ea_trades = set(ea['trade_k'])
py_trades = set(py['trade_k'])
missing = py_trades - ea_trades

miss_df = py[py['trade_k'].isin(missing)].drop_duplicates('trade_k')
miss_df['entry_ts'] = pd.to_datetime(miss_df['entry_time'])
miss_df['sig_bar'] = miss_df['entry_ts'] - pd.Timedelta(minutes=30)
cutoff = pd.Timestamp('2026.08.14')
rest = miss_df[miss_df['entry_ts'] <= cutoff].copy()
rest['bar_key'] = rest['sig_bar'].dt.strftime('%Y.%m.%d %H:%M') + '|' + rest['dir'].str.upper().map({'L':'BUY','S':'SELL'})

sig['bar_ts'] = pd.to_datetime(sig['bar_time'])
sig['bar_key'] = sig['bar_ts'].dt.strftime('%Y.%m.%d %H:%M') + '|' + sig['dir']
sig_map = sig[['bar_key','gate_pass','stop_distance']].rename(columns={'stop_distance':'sd_sig'}).drop_duplicates('bar_key')

merged = rest[['bar_key','trade_k']].merge(sig_map, on='bar_key', how='left')
merged['sd'] = pd.to_numeric(merged['sd_sig'], errors='coerce')

print("=== 其余 missing(<=08.14):", len(merged))
print("gate PASS:", (merged['gate_pass']=='PASS').sum())
print("gate FAIL:", (merged['gate_pass']=='FAIL').sum())
print("无记录:", merged['gate_pass'].isna().sum())

pass_m = merged[merged['gate_pass']=='PASS']
print("\n=== gate PASS 的 stop_distance(pt) 分布 ===")
print("spec通过 [5000,35000]:", ((pass_m['sd']>=5000)&(pass_m['sd']<=35000)).sum())
print("spec不通过 <5000:", (pass_m['sd']<5000).sum())
print("spec不通过 >35000:", (pass_m['sd']>35000).sum())
