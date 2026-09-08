# -*- coding: utf-8 -*-
"""检查 v60 回测段"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

LOG = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\logs\20260905.log"
lines = open(LOG, encoding='utf-16').read().splitlines()

# 所有 Test passed 的行号和前后时间
for i, ln in enumerate(lines):
    if 'Test passed' in ln:
        # 找这行的时间戳
        print("Test passed 在行 %d: %s" % (i+1, ln.strip()[:120]))

# 最近 initialized
print("\n--- 最近 3 个 initialized ---")
cnt = 0
for i in range(len(lines)-1, -1, -1):
    if 'ABC EA initialized' in lines[i]:
        print("行 %d: %s" % (i+1, lines[i].strip()[:100]))
        cnt += 1
        if cnt >= 3:
            break
