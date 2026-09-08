# -*- coding: utf-8 -*-
"""分析 v58 的 24 个 missing 交易"""
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
extra = ea_trades - py_trades

print("missing 交易数:", len(missing))
print("extra 交易数:", len(extra))

# missing 交易的 mode/dir
miss_df = py[py['trade_k'].isin(missing)].drop_duplicates('trade_k')
print("\n=== missing 交易的 mode 分布 ===")
print(miss_df.groupby('mode').size().to_string())
print("\n=== missing 交易的 dir 分布 ===")
print(miss_df['dir'].value_counts().to_string())

# missing 交易在 EA 信号 CSV 里的 gate 情况
miss_df['sig_bar'] = miss_df['entry_ts'] - pd.Timedelta(minutes=30)
miss_df['bar_key'] = miss_df['sig_bar'].dt.strftime('%Y.%m.%d %H:%M') + '|' + miss_df['dir'].str.upper().map({'L':'BUY','S':'SELL'})
sig['bar_ts'] = pd.to_datetime(sig['bar_time'])
sig['bar_key'] = sig['bar_ts'].dt.strftime('%Y.%m.%d %H:%M') + '|' + sig['dir']
sig_map = sig[['bar_key','gate_pass','stop_distance']].rename(columns={'stop_distance':'sd'}).drop_duplicates('bar_key')
merged = miss_df[['trade_k','bar_key','mode']].merge(sig_map, on='bar_key', how='left')
print("\n=== missing 交易在 EA 信号 CSV 的 gate 情况 ===")
print(merged['gate_pass'].value_counts().to_string())
print("\n=== missing 交易详情(前30) ===")
for _, row in merged.head(30).iterrows():
    print("  %s %s gate=%s sd=%s" % (row['trade_k'], row['mode'], row['gate_pass'], row['sd']))
