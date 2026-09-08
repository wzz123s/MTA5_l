# -*- coding: utf-8 -*-
"""v48: 检查遮挡窗口 591344 + 开始按钮当前状态"""
import sys, ctypes
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

d = Desktop(backend="win32")

# 检查 hwnd=591344 是什么
print("=== hwnd 591344 的窗口 ===")
for w in d.windows():
    try:
        if w.handle == 591344:
            r = w.rectangle()
            print("  顶层: class=%r text=%r rect=(%d,%d)-(%d,%d) visible=%s" % (w.class_name(), w.window_text()[:50], r.left, r.top, r.right, r.bottom, w.is_visible()))
    except Exception:
        pass

# 在 MT5 后代里找 591344
mt5 = None
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t and "[" in t:
            mt5 = w
    except Exception:
        pass

if mt5:
    print("\n=== MT5 后代里 hwnd 591344 ===")
    for c in mt5.descendants():
        try:
            if c.handle == 591344:
                r = c.rectangle()
                print("  后代: class=%r text=%r rect=(%d,%d)-(%d,%d)" % (c.class_name(), c.window_text()[:50], r.left, r.top, r.right, r.bottom))
        except Exception:
            pass

    print("\n=== 开始按钮当前 rect/hwnd ===")
    for c in mt5.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始", "停止"):
                r = c.rectangle()
                print("  %r hwnd=%d rect=(%d,%d)-(%d,%d)" % (c.window_text(), c.handle, r.left, r.top, r.right, r.bottom))
        except Exception:
            pass

    print("\n=== 覆盖 (2498,780) 的 MT5 后代窗口 ===")
    for c in mt5.descendants():
        try:
            r = c.rectangle()
            if r.left <= 2498 <= r.right and r.top <= 780 <= r.bottom:
                cls = c.class_name()
                if c.is_visible():
                    print("  覆盖: class=%r text=%r rect=(%d,%d)-(%d,%d) hwnd=%d" % (cls, c.window_text()[:40], r.left, r.top, r.right, r.bottom, c.handle))
        except Exception:
            pass
