# -*- coding: utf-8 -*-
"""改 .ini(InpNanRegOn=true) + 重启 MT5 + 等待."""
import sys, time, subprocess
sys.stdout.reconfigure(encoding='utf-8')

ini = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Profiles\Tester\2H_M30_6H_ABC_EA.XAUUSDm.M30.20250101_20260814.200.ini"

# 1) 读 + 改 .ini
raw = None
for enc in ['utf-16', 'utf-8']:
    try:
        with open(ini, 'r', encoding=enc) as f:
            raw = f.read()
        print("ini 读取编码:", enc)
        break
    except Exception:
        pass
if raw is None:
    print("无法读 ini"); sys.exit(1)

import re
raw = re.sub(r'InpNanRegOn=.*', 'InpNanRegOn=true||false||0||true||N', raw)
if 'InpNanRegOn' not in raw:
    anchor = 'InpM30SMA13=13||13||1||130||N'
    if anchor in raw:
        raw = raw.replace(anchor, anchor + "\nInpM30SMA55=55||55||1||550||N\nInpNanRegOn=true||false||0||true||N\nInpNanRegPct=0.5||0.5||0.050000||5.000000||N")
    else:
        print("锚点未找到"); sys.exit(1)

with open(ini, 'w', encoding='utf-16', newline='') as f:
    f.write(raw)
print("ini 已写回 utf-16 (InpNanRegOn=true)")

# 2) 关闭 MT5
r = subprocess.run(["taskkill", "/IM", "terminal64.exe", "/F"], capture_output=True, text=True)
print("taskkill:", r.stdout.strip(), r.stderr.strip())

# 3) 启动 MT5
subprocess.Popen([r"F:\Program Files\MetaTrader 5\terminal64.exe"])
print("已启动 terminal64, 等待 35 秒...")
time.sleep(35)
print("等待完成")
