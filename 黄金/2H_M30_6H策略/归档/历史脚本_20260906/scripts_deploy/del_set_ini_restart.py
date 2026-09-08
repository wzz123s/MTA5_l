# -*- coding: utf-8 -*-
"""删 2H_M30_6H_ABC_EA.set + .ini + 重启."""
import sys, time, subprocess, os
sys.stdout.reconfigure(encoding='utf-8')

base = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65"
for fn in [
    r"MQL5\Profiles\Tester\2H_M30_6H_ABC_EA.set",
    r"MQL5\Profiles\Tester\2H_M30_6H_ABC_EA.XAUUSDm.M30.20250101_20260814.200.ini",
]:
    p = os.path.join(base, fn)
    if os.path.exists(p):
        os.remove(p)
        print("已删:", fn)
    else:
        print("不存在:", fn)

subprocess.run(["taskkill", "/IM", "terminal64.exe", "/F"], capture_output=True, text=True)
time.sleep(2)
subprocess.Popen([r"F:\Program Files\MetaTrader 5\terminal64.exe"])
print("重启, 等 35 秒...")
time.sleep(35)
print("done")
