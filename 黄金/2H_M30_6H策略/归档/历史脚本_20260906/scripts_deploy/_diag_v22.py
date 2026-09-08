# -*- coding: utf-8 -*-
"""v22: MT5 重启后诊断，确认 Tester 面板状态"""
import sys, ctypes, time
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
    print("FAIL: MT5 not found"); sys.exit(1)

r = mt5.rectangle()
print("MT5:", mt5.window_text()[:80])
print("rect:", (r.left, r.top, r.right, r.bottom), "minimized:", mt5.is_minimized())

print()
print("=== 策略测试面板 ===")
found = False
for c in mt5.descendants():
    try:
        if "策略测试" in c.window_text():
            r = c.rectangle()
            print("  策略测试 rect=(%d,%d)-(%d,%d) visible=%s" % (r.left, r.top, r.right, r.bottom, c.is_visible()))
            found = True
    except Exception:
        pass
if not found:
    print("  未找到策略测试面板")

print()
print("=== DateTimePick ===")
for c in mt5.descendants():
    try:
        if "DateTimePick" in c.class_name():
            r = c.rectangle()
            print("  text=%r rect=(%d,%d)-(%d,%d)" % (c.window_text(), r.left, r.top, r.right, r.bottom))
    except Exception:
        pass

print()
print("=== 关键 ComboBox ===")
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name():
            txt = c.window_text()
            if txt and any(k in txt for k in ["Advisors", "XAUUSDm", "USOILm", "M30", "H4", "仅使用开价", "每次报价"]):
                r = c.rectangle()
                print("  text=%r rect=(%d,%d)-(%d,%d)" % (txt, r.left, r.top, r.right, r.bottom))
    except Exception:
        pass
