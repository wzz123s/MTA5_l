# -*- coding: utf-8 -*-
"""v18: 完整诊断 Tester 面板所有相关控件"""
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
            print("  %r rect=(%d,%d)-(%d,%d) hwnd=%d" % (c.window_text(), r.left, r.top, r.right, r.bottom, c.handle))
    except Exception:
        pass

print()
print("=== 所有 DateTimePick ===")
for c in mt5.descendants():
    try:
        if "DateTimePick" in c.class_name():
            r = c.rectangle()
            print("  text=%r  rect=(%d,%d)-(%d,%d)  hwnd=%d" % (c.window_text(), r.left, r.top, r.right, r.bottom, c.handle))
    except Exception:
        pass

print()
print("=== 所有 ComboBox (含关键词) ===")
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name():
            r = c.rectangle()
            txt = c.window_text()
            print("  text=%r  rect=(%d,%d)-(%d,%d)  hwnd=%d" % (txt, r.left, r.top, r.right, r.bottom, c.handle))
    except Exception:
        pass

print()
print("=== 所有 Button (含关键词) ===")
for c in mt5.descendants():
    try:
        if "Button" in c.class_name():
            txt = c.window_text()
            if txt and any(k in txt for k in ["开始", "停止", "跳过", "EA", "设置"]):
                r = c.rectangle()
                print("  text=%r  rect=(%d,%d)-(%d,%d)  hwnd=%d" % (txt, r.left, r.top, r.right, r.bottom, c.handle))
    except Exception:
        pass
