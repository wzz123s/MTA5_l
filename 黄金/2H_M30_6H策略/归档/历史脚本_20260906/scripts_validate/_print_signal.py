# -*- coding: utf-8 -*-
"""打印日志里 [SIGNAL] 的确切格式"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

LOG = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\logs\20260905.log"
lines = open(LOG, encoding='utf-8', errors='ignore').read().splitlines()
seg = lines[6102:6952]

n = 0
for ln in seg:
    if '[SIGNAL]' in ln:
        print(repr(ln[:200]))
        n += 1
        if n >= 3:
            break
print("total [SIGNAL] in seg:", sum(1 for l in seg if '[SIGNAL]' in l))
