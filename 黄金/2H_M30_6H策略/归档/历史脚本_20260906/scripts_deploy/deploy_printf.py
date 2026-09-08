# -*- coding: utf-8 -*-
"""部署 Print 版 ex5 + 删 ini + 重启."""
import sys, time, subprocess, shutil, os
sys.stdout.reconfigure(encoding='utf-8')

src = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_ABC_EA.ex5"
dst = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Experts\Advisors\2H_M30_6H_ABC_EA.ex5"
shutil.copy2(src, dst)
print("ex5 部署")

ini = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Profiles\Tester\2H_M30_6H_ABC_EA.XAUUSDm.M30.20250101_20260814.200.ini"
if os.path.exists(ini):
    os.remove(ini)
    print(".ini 已删")
else:
    print(".ini 不存在")

subprocess.run(["taskkill", "/IM", "terminal64.exe", "/F"], capture_output=True, text=True)
time.sleep(2)
subprocess.Popen([r"F:\Program Files\MetaTrader 5\terminal64.exe"])
print("重启, 等 35 秒...")
time.sleep(35)
print("done")
