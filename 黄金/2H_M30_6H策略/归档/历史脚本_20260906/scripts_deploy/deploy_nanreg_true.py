# -*- coding: utf-8 -*-
"""部署 .ex5 + 删 .ini 参数行 + 重启 MT5."""
import sys, re, time, subprocess, shutil
sys.stdout.reconfigure(encoding='utf-8')

# 1) 复制 .ex5 到 DAD3B8CC Experts\Advisors
src = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_ABC_EA.ex5"
dst = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Experts\Advisors\2H_M30_6H_ABC_EA.ex5"
shutil.copy2(src, dst)
print("已部署 .ex5")

# 2) 删 .ini 的 InpNanRegOn/InpM30SMA55/InpNanRegPct 行
ini = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Profiles\Tester\2H_M30_6H_ABC_EA.XAUUSDm.M30.20250101_20260814.200.ini"
raw = open(ini, 'r', encoding='utf-16-le').read()
lines = raw.split('\n')
keep = [l for l in lines if not any(k in l for k in ['InpNanRegOn', 'InpM30SMA55', 'InpNanRegPct'])]
open(ini, 'w', encoding='utf-16-le', newline='').write('\n'.join(keep))
print("已删 .ini 的三个参数行")

# 验证
v = open(ini, 'r', encoding='utf-16-le').read()
print("删除后含 InpNanRegOn:", 'InpNanRegOn' in v)

# 3) 重启 MT5
subprocess.run(["taskkill", "/IM", "terminal64.exe", "/F"], capture_output=True, text=True)
time.sleep(2)
subprocess.Popen([r"F:\Program Files\MetaTrader 5\terminal64.exe"])
print("重启 MT5, 等 35 秒...")
time.sleep(35)
print("done")
