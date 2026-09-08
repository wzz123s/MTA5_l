# -*- coding: utf-8 -*-
"""改 InpNanRegOn=1 + 重启 MT5 + 等待."""
import sys, re, time, subprocess
sys.stdout.reconfigure(encoding='utf-8')

ini = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Profiles\Tester\2H_M30_6H_ABC_EA.XAUUSDm.M30.20250101_20260814.200.ini"

raw = open(ini, 'r', encoding='utf-16-le').read()
# 值改成 1
raw = re.sub(r'InpNanRegOn=[^\r\n]*', 'InpNanRegOn=1||false||0||true||N', raw)
open(ini, 'w', encoding='utf-16-le', newline='').write(raw)
print("写 InpNanRegOn=1")

# 验证
v = open(ini, 'r', encoding='utf-16-le').read()
for l in v.split('\n'):
    if 'InpNanRegOn' in l:
        print("  验证:", repr(l))

# 重启 MT5
subprocess.run(["taskkill", "/IM", "terminal64.exe", "/F"], capture_output=True, text=True)
subprocess.Popen([r"F:\Program Files\MetaTrader 5\terminal64.exe"])
print("重启中, 等 35 秒...")
time.sleep(35)
print("done")
