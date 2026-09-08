# -*- coding: utf-8 -*-
"""读完整台账"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

EA = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
ea = pd.read_csv(EA, encoding='utf-8-sig')

print("行数:", len(ea))
ea['ent'] = pd.to_datetime(ea['entry_time'])
print("entry 范围:", ea['ent'].min(), "->", ea['ent'].max())
ea['dir_n'] = ea['dir'].map({'BUY':'L','SELL':'S'})
ea['trade_k'] = ea['ent'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + ea['dir_n']
print("交易数:", ea['trade_k'].nunique())
print("stage 分布:", ea['stage'].value_counts().to_dict())
