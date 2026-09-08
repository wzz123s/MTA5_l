# -*- coding: utf-8 -*-
"""读 v58 台账 + 统计日志 [SIM OPEN]"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

# 台账
EA = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_trade_ledger.csv"
ea = pd.read_csv(EA, encoding='utf-8-sig')
ea['ent'] = pd.to_datetime(ea['entry_time'])
ea['dir_n'] = ea['dir'].map({'BUY':'L','SELL':'S'})
ea['trade_k'] = ea['ent'].dt.strftime('%Y.%m.%d %H:%M:%S') + '|' + ea['dir_n']
print("台账行数:", len(ea))
print("交易数:", ea['trade_k'].nunique())
print("entry 范围:", ea['ent'].min(), "->", ea['ent'].max())

# 日志 [SIM OPEN]
LOG = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\logs\20260905.log"
lines = open(LOG, encoding='utf-16').read().splitlines()
passed_idx = -1
for i in range(len(lines)-1, -1, -1):
    if 'Test passed' in lines[i]:
        passed_idx = i; break
init_idx = -1
for i in range(passed_idx, -1, -1):
    if 'ABC EA initialized' in lines[i]:
        init_idx = i; break
seg = lines[init_idx:passed_idx+1]
open_cnt = sum(1 for l in seg if '[SIM] OPEN' in l)
stage_cnt = sum(1 for l in seg if '[SIM] stage' in l)
sig_cnt = sum(1 for l in seg if '[SIGNAL]' in l)
print("\n日志 [SIGNAL]=%d [SIM OPEN]=%d [SIM stage]=%d" % (sig_cnt, open_cnt, stage_cnt))
