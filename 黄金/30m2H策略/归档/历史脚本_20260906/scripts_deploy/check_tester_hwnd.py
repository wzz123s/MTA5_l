# -*- coding: utf-8 -*-
"""连接 hwnd + Ctrl+R + 检查 Tester 状态."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8')
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from pywinauto import Application
from pywinauto.keyboard import send_keys

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
MT5_HWND = 721950

app = Application(backend="win32").connect(handle=MT5_HWND)
win = app.window(handle=MT5_HWND)
print("连接:", win.window_text()[:50])
user32.SetWindowPos(ctypes.c_void_p(MT5_HWND), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.3)
user32.SetForegroundWindow(MT5_HWND); time.sleep(0.5)
send_keys("^r"); time.sleep(3.0)
print("Ctrl+R 后")

# 检查控件
for c in win.descendants():
    try:
        cls = c.class_name()
        txt = c.window_text()
        if "ComboBox" in cls and txt and any(k in txt for k in ["Advisors", "XAUUSDm", "USOILm", "M30", "H4", "仅使用开价", "每次报价"]):
            print("  Combo %r" % txt[:50])
        if "SysDateTimePick32" in cls:
            print("  日期 %r" % txt)
        if "Button" in cls and txt in ("开始","停止"):
            print("  按钮 %r" % txt)
    except Exception:
        pass
