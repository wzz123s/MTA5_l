# -*- coding: utf-8 -*-
"""重新枚举 MT5 窗口 + IsWindow 检查 + 最小化 Edge."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
d = Desktop(backend="win32")

# 枚举所有 MT5 相关窗口
print("=== 所有 Exness 窗口 ===")
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t:
            h = w.handle
            isw = user32.IsWindow(h)
            visible = w.is_visible()
            r = w.rectangle()
            print("hwnd=%d IsWindow=%s visible=%s rect=(%d,%d,%d,%d) %r" % (h, isw, visible, r.left, r.top, r.right, r.bottom, t[:50]))
    except Exception as e:
        print("err:", e)

# 检查 Edge hwnd=66870 是否有效
print("\nEdge hwnd=66870 IsWindow=%s" % user32.IsWindow(66870))
