# -*- coding: utf-8 -*-
"""直接查看 DAD3B8CC Tester EA (不 Ctrl+R)."""
import ctypes, sys
sys.stdout.reconfigure(encoding='utf-8')
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from pywinauto import Application
user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
MT5_HWND = 4851420
app = Application(backend="win32").connect(handle=MT5_HWND)
win = app.window(handle=MT5_HWND)
print("窗口:", win.window_text()[:50])
for c in win.descendants():
    try:
        txt = c.window_text()
        if "ComboBox" in c.class_name() and "Advisors" in txt:
            print("  EA:", txt[:55])
        if "ComboBox" in c.class_name() and txt in ("XAUUSDm","M30","H2","仅使用开价","每次报价"):
            print("  Combo:", txt)
        if "SysDateTimePick32" in c.class_name():
            r = c.rectangle()
            if r.width() > 60:
                print("  日期:", txt)
    except Exception:
        pass
