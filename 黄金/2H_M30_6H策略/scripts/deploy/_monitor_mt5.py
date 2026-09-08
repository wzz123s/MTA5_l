# -*- coding: utf-8 -*-
"""监控 MT5 启动后的存活情况"""
import sys, subprocess, time
sys.stdout.reconfigure(encoding='utf-8')

exe = r"F:\Program Files\MetaTrader 5\terminal64.exe"
import os
print("启动 MT5...")
subprocess.Popen([exe], cwd=r"F:\Program Files\MetaTrader 5")

for i in range(24):  # 24 * 5s = 120 秒
    time.sleep(5)
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq terminal64.exe", "/FO", "CSV", "/NH"],
                       capture_output=True, text=True)
    alive = "terminal64.exe" in r.stdout
    print("t=%3ds alive=%s" % ((i+1)*5, alive))
    if not alive:
        print("MT5 退出了，检查日志尾部:")
        break
