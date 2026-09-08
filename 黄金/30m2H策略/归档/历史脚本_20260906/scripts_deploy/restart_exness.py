# -*- coding: utf-8 -*-
"""重启 EXNESS + 等 + 检查 Tester EA 是否持久化."""
import subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')

subprocess.run(["taskkill", "/IM", "terminal64.exe", "/F"], capture_output=True, text=True)
time.sleep(2)
subprocess.Popen([r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"])
print("EXNESS 重启, 等 55 秒...")
time.sleep(55)
print("done")
