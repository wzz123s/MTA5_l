# -*- coding: utf-8 -*-
"""UTF-16 读日志，对比 [SIGNAL] stop_pts vs 信号 CSV stop_distance"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

LOG = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\logs\20260905.log"
F = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_signals_export.csv"

lines = open(LOG, encoding='utf-16').read().splitlines()
seg = lines[6102:6952]  # 这次回测段

# 提取 [SIGNAL] 的 signal_time + dir + stop_pts
sig_map = {}
for ln in seg:
    if '[SIGNAL]' in ln:
        m = re.search(r'\[SIGNAL\] (BUY|SELL) (\w+) signal_time=([\d.]+ \d+:\d+).*?stop_pts=([\d.]+)', ln)
        if m:
            d = m.group(1)
            t = m.group(3)
            sp = float(m.group(4))
            sig_map[t + '|' + d] = sp

print("[SIGNAL] 提取数:", len(sig_map))

# 信号 CSV spec 通过
sig = pd.read_csv(F, encoding='utf-8-sig')
pass_hit = sig[sig['gate_pass']=='PASS'].copy()
pass_hit['sd'] = pd.to_numeric(pass_hit['stop_distance'], errors='coerce')
spec_ok = pass_hit[(pass_hit['sd']>=5000)&(pass_hit['sd']<=35000)]
print("信号 CSV spec通过数:", len(spec_ok))

# 对比 stop_pts（日志）vs stop_distance（CSV）
csv_map = {}
for _, row in spec_ok.iterrows():
    csv_map[row['bar_time'] + '|' + row['dir']] = row['sd']

both = set(sig_map) & set(csv_map)
only_sig = set(sig_map) - set(csv_map)
only_csv = set(csv_map) - set(sig_map)
print("\n两者都有:", len(both))
print("日志[SIGNAL]有 CSV无:", len(only_sig))
print("CSV有 日志[SIGNAL]无:", len(only_csv))

# 对比 both 的 stop_pts vs stop_distance
diff_cnt = 0
for k in both:
    if abs(sig_map[k] - csv_map[k]) > 1:
        diff_cnt += 1
print("\nboth 中 stop_pts vs stop_distance 差异>1pt 的:", diff_cnt)

# only_csv 的样本（CSV spec通过 但日志无[SIGNAL]）
print("\n=== CSV spec通过 但日志无[SIGNAL] 的样本(前15) ===")
for k in list(only_csv)[:15]:
    print("  %s sd=%.1f" % (k, csv_map[k]))
