# -*- coding: utf-8 -*-
"""检查日志当前状态"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

LOG = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\logs\20260905.log"
lines = open(LOG, encoding='utf-8', errors='ignore').read().splitlines()
print("总行数:", len(lines))
print("[SIGNAL] 总数:", sum(1 for l in lines if '[SIGNAL]' in l))
print("[SIM] OPEN 总数:", sum(1 for l in lines if '[SIM] OPEN' in l))
print("[SIM] stage 总数:", sum(1 for l in lines if '[SIM] stage' in l))
print("Test passed 总数:", sum(1 for l in lines if 'Test passed' in l))

# 最近 Test passed 的行号
for i in range(len(lines)-1, -1, -1):
    if 'Test passed' in lines[i]:
        print("最近 Test passed 在第", i+1, "行")
        # 往前找 initialized
        for j in range(i, -1, -1):
            if 'initialized' in lines[j]:
                print("对应 initialized 在第", j+1, "行")
                break
        break
