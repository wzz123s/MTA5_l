# -*- coding: utf-8 -*-
"""恢复 + 移动 EXNESS 窗口."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8')
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from pywinauto import Application

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
MT5_HWND = 5114106
SW_RESTORE = 9
SWP_SHOWWINDOW = 0x0040

app = Application(backend="win32").connect(handle=MT5_HWND)
win = app.window(handle=MT5_HWND)

user32.ShowWindow(MT5_HWND, SW_RESTORE); time.sleep(1.0)
user32.SetWindowPos(ctypes.c_void_p(MT5_HWND), ctypes.c_void_p(0), 0, 0, 1600, 900, SWP_SHOWWINDOW)
time.sleep(1.0)
user32.SetForegroundWindow(MT5_HWND); time.sleep(0.5)

r2 = win.rectangle()
print("恢复后 rect:", r2.left, r2.top, r2.right, r2.bottom)
print("is_minimized:", win.is_minimized())
