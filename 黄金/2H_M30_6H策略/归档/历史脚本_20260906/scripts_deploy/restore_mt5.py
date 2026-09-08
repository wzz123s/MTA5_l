# -*- coding: utf-8 -*-
"""恢复 MT5 XAUUSDm 窗口."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

user32 = ctypes.windll.user32
SW_RESTORE = 9
d = Desktop(backend="win32")

print("=== 所有 Exness 窗口 ===")
target = None
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t:
            h = w.handle
            mini = w.is_minimized()
            r = w.rectangle()
            print("hwnd=%d mini=%s rect=(%d,%d) %r" % (h, mini, r.left, r.top, t[:70]))
            if "[XAUUSDm" in t:
                target = w
    except Exception as e:
        print("err:", e)

if target is None:
    print("未找到 XAUUSDm 窗口, 尝试从所有窗口找")
    for w in d.windows():
        try:
            t = w.window_text()
            if t and "Exness" in t and "XAUUSDm" in t:
                target = w
        except Exception:
            pass

if target is None:
    print("FAIL"); sys.exit(1)

# 恢复
h = target.handle
user32.ShowWindow(h, SW_RESTORE)
time.sleep(1.0)
# 重新获取
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t and "XAUUSDm" in t:
            r = w.rectangle()
            print("恢复后: hwnd=%d mini=%s rect=(%d,%d,%d,%d) %r" % (w.handle, w.is_minimized(), r.left, r.top, r.right, r.bottom, t[:60]))
    except Exception:
        pass
