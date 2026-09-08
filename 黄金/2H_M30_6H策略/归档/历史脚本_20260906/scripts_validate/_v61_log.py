# -*- coding: utf-8 -*-
"""检查 v61 日志段"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

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
print("v61 段: 行 %d ~ %d" % (init_idx+1, passed_idx+1))
print("[GATEDBG]:", sum(1 for l in seg if '[GATEDBG]' in l))
print("[SIGNAL]:", sum(1 for l in seg if '[SIGNAL]' in l))
print("[SIM OPEN]:", sum(1 for l in seg if '[SIM] OPEN' in l))
print("[SIM stage]:", sum(1 for l in seg if '[SIM] stage' in l))

# 看一个 missing cross 的 signal bar 09:30 在 [GATEDBG] 里的情况
for ln in seg:
    if '2025.02.04 09:30' in ln or '2025.02.04 09:00' in ln:
        print("  " + ln.strip()[:150])
