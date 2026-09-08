# -*- coding: utf-8 -*-
"""v21: 完整枚举 MT5 可见控件，找 Tester 面板状态"""
import sys, ctypes, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

SW_RESTORE = 9

def find_mt5():
    d = Desktop(backend="win32")
    for w in d.windows():
        try:
            t = w.window_text()
            if t and "Exness" in t and "[" in t:
                return w
        except Exception:
            pass
    return None

mt5 = find_mt5()
if mt5 is None:
    print("FAIL"); sys.exit(1)

if mt5.is_minimized():
    ctypes.windll.user32.ShowWindow(mt5.handle, SW_RESTORE)
    time.sleep(1.0)

print("MT5 所有可见顶层子窗口(含 class):")
for c in mt5.children():
    try:
        if c.is_visible():
            r = c.rectangle()
            txt = c.window_text()
            if r.width() > 10 and r.height() > 10:
                print("  class=%r text=%r rect=(%d,%d)-(%d,%d)" % (c.class_name(), txt[:40], r.left, r.top, r.right, r.bottom))
    except Exception:
        pass

print()
print("=== Tab / 页面控件 ===")
for c in mt5.descendants():
    try:
        cls = c.class_name()
        if any(k in cls for k in ["Tab", "Page", "Pane", "Dialog", "Afx"]):
            if c.is_visible():
                r = c.rectangle()
                txt = c.window_text()
                if r.width() > 20 and r.height() > 20:
                    print("  class=%r text=%r rect=(%d,%d)-(%d,%d)" % (cls, txt[:50], r.left, r.top, r.right, r.bottom))
    except Exception:
        pass
