# -*- coding: utf-8 -*-
"""EXNESS 窗口移到 (0,0) 并检查."""
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
HWND_TOP = 0
SWP_SHOWWINDOW = 0x0040

app = Application(backend="win32").connect(handle=MT5_HWND)
win = app.window(handle=MT5_HWND)
r = win.rectangle()
print("移动前 rect:", r.left, r.top, r.right, r.bottom)

# 移到 (0,0) 1600x900
user32.SetWindowPos(ctypes.c_void_p(MT5_HWND), ctypes.c_void_p(0), 0, 0, 1600, 900, SWP_SHOWWINDOW)
time.sleep(1.0)
r2 = win.rectangle()
print("移动后 rect:", r2.left, r2.top, r2.right, r2.bottom)
print("is_minimized:", win.is_minimized(), "is_visible:", win.is_visible())
