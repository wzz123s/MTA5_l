# -*- coding: utf-8 -*-
"""检查 MT5 进程 + IsWindow."""
import ctypes, sys
sys.stdout.reconfigure(encoding='utf-8')
import subprocess
user32 = ctypes.windll.user32

out = subprocess.run(["powershell", "-Command", "Get-Process terminal64 -ErrorAction SilentlyContinue | Select-Object Id,MainWindowHandle"], capture_output=True, text=True)
print("MT5 进程:")
print(out.stdout)
if out.stdout and "terminal64" not in out.stdout:
    print("  (无进程 = MT5 又退出)")
h = 3473596
print("IsWindow(3473596):", user32.IsWindow(h))
