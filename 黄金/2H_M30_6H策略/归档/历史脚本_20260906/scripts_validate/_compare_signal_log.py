# -*- coding: utf-8 -*-
"""对比日志 [SIGNAL] 和信号 CSV 的 spec 通过"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

LOG = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\logs\20260905.log"
F = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_signals_export.csv"

lines = open(LOG, encoding='utf-8', errors='ignore').read().splitlines()
# 取最近一次回测段（第6103-6953行，0-based 6102-6952）
seg = lines[6102:6952]

# 提取 [SIGNAL] 的 bar_time + dir + stop_pts
signal_keys = set()
signal_stop = {}
for ln in seg:
    if '[SIGNAL]' in ln:
        # 格式: ... 2025.01.06 12:30:00   [SIGNAL] SELL cross signal_time=2025.01.06 12:00 stop=... stop_pts=...
        m = re.search(r'[SIGNAL] (BUY|SELL) \w+ signal_time=([\d.]+ \d+:\d+) .*?stop_pts=([\d.]+)', ln)
        if m:
            d = m.group(1)
            t = m.group(2)
            sp = m.group(3)
            signal_keys.add(t + '|' + d)
            signal_stop[t + '|' + d] = sp

print("[SIGNAL] 提取数:", len(signal_keys))

# 信号 CSV spec 通过
sig = pd.read_csv(F, encoding='utf-8-sig')
pass_hit = sig[sig['gate_pass']=='PASS'].copy()
pass_hit['sd'] = pd.to_numeric(pass_hit['stop_distance'], errors='coerce')
spec_ok = pass_hit[(pass_hit['sd']>=5000)&(pass_hit['sd']<=35000)]
spec_keys = set(spec_ok['bar_time'] + '|' + spec_ok['dir'])
print("信号 CSV spec通过数:", len(spec_keys))

# 差异
only_signal = signal_keys - spec_keys  # 日志有信号CSV无
only_spec = spec_keys - signal_keys  # 信号CSV有日志无
both = signal_keys & spec_keys
print("\n两者都有:", len(both))
print("日志[SIGNAL]有 信号CSV无:", len(only_signal))
print("信号CSV有 日志[SIGNAL]无:", len(only_spec))

# 看 only_spec 的样本（信号CSV spec通过但日志没[SIGNAL]）
print("\n=== 信号CSV spec通过但日志无[SIGNAL] 的样本(前10) ===")
for k in list(only_spec)[:10]:
    print("  ", k)
