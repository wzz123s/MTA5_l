# -*- coding: utf-8 -*-
"""检查 223 个 only_csv 信号在日志里的实际情况"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

LOG = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\logs\20260905.log"
F = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files\2H_M30_6H_abc_signals_export.csv"

lines = open(LOG, encoding='utf-16').read().splitlines()
seg = lines[6102:6952]

# 223 个 only_csv 的样本
samples = ["2025.02.21 18:00", "2025.09.30 17:30", "2025.03.19 22:00"]

for s in samples:
    print("=== 搜索 %s 在日志 seg 里的记录 ===" % s)
    found = False
    for ln in seg:
        if s in ln and ('SIGNAL' in ln or 'OPEN' in ln or 'stage' in ln):
            print("  " + ln.strip()[:160])
            found = True
    if not found:
        print("  (无 SIGNAL/OPEN/stage 记录)")

# 也看看这些 bar 在日志里的任何记录（比如 FAIL）
print("\n=== 搜索 2025.02.21 18:00 附近的所有日志行 ===")
for i, ln in enumerate(seg):
    if '2025.02.21 18:00' in ln or '2025.02.21 18:30' in ln:
        print("  " + ln.strip()[:160])
