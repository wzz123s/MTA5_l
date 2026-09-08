# -*- coding: utf-8 -*-
"""重新读这次回测的信号 CSV，统计 gate PASS 和 spec 通过"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

F = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_signals_export.csv"
sig = pd.read_csv(F, encoding='utf-8-sig')

print("信号 CSV 行数:", len(sig))
pass_hit = sig[sig['gate_pass']=='PASS'].copy()
pass_hit['sd'] = pd.to_numeric(pass_hit['stop_distance'], errors='coerce')
print("gate PASS:", len(pass_hit))
print("spec通过(sd in [5000,35000]):", ((pass_hit['sd']>=5000)&(pass_hit['sd']<=35000)).sum())
print("spec不通过 <5000:", (pass_hit['sd']<5000).sum())
print("spec不通过 >35000:", (pass_hit['sd']>35000).sum())

# stop_distance 分布
print("\nstop_distance 描述:")
print(pass_hit['sd'].describe().to_string())

# 前 10 个 gate PASS 的 sd
print("\n前 10 个 gate PASS 的 sd:")
for i, row in pass_hit.head(10).iterrows():
    print("  %s %s %s sd=%.0f" % (row['bar_time'], row['dir'], row['mode'], row['sd']))
