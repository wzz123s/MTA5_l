# -*- coding: utf-8 -*-
"""重新枚举所有 Exness 窗口, 找 XAUUSDm 实例."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

d = Desktop(backend="win32")
print("=== 所有 Exness 窗口 ===")
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t:
            r = w.rectangle()
            print("hwnd=%d mini=%s visible=%s rect=(%d,%d,%d,%d) %r" % (w.handle, w.is_minimized(), w.is_visible(), r.left, r.top, r.right, r.bottom, t[:60]))
    except Exception as e:
        print("err:", e)

# 也找含 XAUUSDm 的任何窗口
print("\n=== 含 XAUUSDm 的窗口 ===")
for w in d.windows():
    try:
        t = w.window_text()
        if t and "XAUUSDm" in t:
            print("hwnd=%d %r" % (w.handle, t[:60]))
    except Exception:
        pass
