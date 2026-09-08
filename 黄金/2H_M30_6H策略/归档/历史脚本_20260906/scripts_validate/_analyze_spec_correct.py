# -*- coding: utf-8 -*-
"""用正确单位(_Point=0.001, spec=5000-35000pt)重新分析信号过滤"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

F = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_signals_export.csv"
sig = pd.read_csv(F, encoding='utf-8-sig')

pass_hit = sig[sig['gate_pass']=='PASS'].copy()
pass_hit['sd'] = pd.to_numeric(pass_hit['stop_distance'], errors='coerce')

print("=== gate PASS 信号 stop_distance(pt) 分布 ===")
print("total:", len(pass_hit))
print("sd in [5000,35000](spec通过):", ((pass_hit['sd']>=5000)&(pass_hit['sd']<=35000)).sum())
print("sd < 5000 (止损太近):", (pass_hit['sd']<5000).sum())
print("sd > 35000 (止损太远):", (pass_hit['sd']>35000).sum())

# 去重（bar_time + dir）
pass_hit['bar_ts'] = pd.to_datetime(pass_hit['bar_time'])
pass_hit['bar_key'] = pass_hit['bar_ts'].dt.strftime('%Y.%m.%d %H:%M') + '|' + pass_hit['dir']
dedup = pass_hit.drop_duplicates('bar_key')
print("\n去重后 gate PASS 信号数:", len(dedup))

# 去重后 spec 通过
dedup_spec = dedup[(dedup['sd']>=5000)&(dedup['sd']<=35000)]
print("去重后 spec 通过的信号数:", len(dedup_spec))

# 按 mode 分布
print("\n=== 去重后 spec 通过的 mode 分布 ===")
print(dedup_spec.groupby('mode').size().to_string())

# Python 交易数对比
print("\nPython 交易数: 493")
