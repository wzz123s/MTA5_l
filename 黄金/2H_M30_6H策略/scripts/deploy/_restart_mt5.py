# -*- coding: utf-8 -*-
"""重启 MT5 terminal64"""
import sys, subprocess, time
sys.stdout.reconfigure(encoding='utf-8')

exe = r"F:\Program Files\MetaTrader 5\terminal64.exe"
print("启动 MT5...")
# 用 start 启动，不阻塞
subprocess.Popen([exe], cwd=r"F:\Program Files\MetaTrader 5")
time.sleep(8)
print("已等待 8 秒，检查进程:")
