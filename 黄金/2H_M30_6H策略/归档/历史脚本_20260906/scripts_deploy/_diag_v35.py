# -*- coding: utf-8 -*-
"""v35: 读所有 ComboBox + Tester 面板 rect"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

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

print("=== 策略测试面板 ===")
for c in mt5.descendants():
    try:
        if "策略测试" in c.window_text():
            r = c.rectangle()
            print("  策略测试 rect=(%d,%d)-(%d,%d)" % (r.left, r.top, r.right, r.bottom))
    except Exception:
        pass

print("=== 所有 ComboBox ===")
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name():
            r = c.rectangle()
            txt = c.window_text()
            print("  %r rect=(%d,%d)-(%d,%d) hwnd=%d" % (txt, r.left, r.top, r.right, r.bottom, c.handle))
    except Exception:
        pass

print("=== 所有 Button ===")
for c in mt5.descendants():
    try:
        if "Button" in c.class_name():
            txt = c.window_text()
            r = c.rectangle()
            if txt:
                print("  %r rect=(%d,%d)-(%d,%d)" % (txt, r.left, r.top, r.right, r.bottom))
    except Exception:
        pass
