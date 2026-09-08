# -*- coding: utf-8 -*-
"""搜索日志 seg 里 2025.02.21 18:30 的所有行"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

LOG = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\logs\20260905.log"
lines = open(LOG, encoding='utf-16').read().splitlines()
seg = lines[6102:6952]

print("=== seg 里含 2025.02.21 的所有行 ===")
for ln in seg:
    if '2025.02.21' in ln:
        print("  " + ln.strip()[:170])
