# -*- coding: utf-8 -*-
"""v26: 纯读状态"""
import sys, time
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

print("MT5 minimized:", mt5.is_minimized())
print("=== DTP ===")
for c in mt5.descendants():
    try:
        if "DateTimePick" in c.class_name():
            r = c.rectangle()
            print("  text=%r rect=(%d,%d)-(%d,%d)" % (c.window_text(), r.left, r.top, r.right, r.bottom))
    except Exception:
        pass

print("=== ComboBox ===")
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name():
            txt = c.window_text()
            if txt and any(k in txt for k in ["Advisors", "XAUUSDm", "USOILm", "M30", "H4", "仅使用开价", "每次报价", "每次分时"]):
                r = c.rectangle()
                print("  text=%r rect=(%d,%d)-(%d,%d)" % (txt, r.left, r.top, r.right, r.bottom))
    except Exception:
        pass

print("=== 开始 ===")
for c in mt5.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            r = c.rectangle()
            print("  开始 rect=(%d,%d)-(%d,%d)" % (r.left, r.top, r.right, r.bottom))
    except Exception:
        pass
