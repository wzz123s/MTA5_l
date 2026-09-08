# -*- coding: utf-8 -*-
"""诊断前台窗口 + 置顶 MT5."""
import sys, time, ctypes
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

d = Desktop(backend="win32")
user32 = ctypes.windll.user32

# 当前前台窗口
fg = user32.GetForegroundWindow()
print("当前前台窗口 hwnd=%d" % fg)

# 枚举所有顶层窗口（可见的）
print("\n=== 可见顶层窗口 ===")
for w in d.windows():
    try:
        t = w.window_text()
        if t and w.is_visible():
            r = w.rectangle()
            print("  %r rect=(%d,%d) %dx%d hwnd=%d" % (t[:60], r.left, r.top, r.width(), r.height(), w.handle))
    except Exception:
        pass

# 找 MT5 XAUUSDm
mt5 = None
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t and "[XAUUSDm" in t:
            mt5 = w
    except Exception:
        pass
if mt5 is None:
    print("未找到 MT5"); sys.exit(1)

# 置顶 MT5
hwnd = mt5.handle
print("\n置顶 MT5 hwnd=%d" % hwnd)
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)
user32.BringWindowToTop(hwnd)
time.sleep(0.5)
fg2 = user32.GetForegroundWindow()
print("置顶后前台窗口 hwnd=%d (MT5=%d)" % (fg2, hwnd))
