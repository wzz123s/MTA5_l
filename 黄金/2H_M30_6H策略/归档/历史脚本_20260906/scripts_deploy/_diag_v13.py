# -*- coding: utf-8 -*-
"""v13: 定位所有 DateTimePick 的 rect + 值，区分日期起/止"""
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
    print("FAIL")
    sys.exit(1)

print("=== DateTimePick 列表 (含 rect) ===")
for c in mt5.descendants():
    try:
        cls = c.class_name()
        if "DateTimePick" in cls:
            r = c.rectangle()
            print("  text=%r  rect=(%d,%d)-(%d,%d)" % (c.window_text(), r.left, r.top, r.right, r.bottom))
    except Exception:
        pass

print()
print("=== ComboBox 列表 (含 rect) ===")
for c in mt5.descendants():
    try:
        cls = c.class_name()
        if "ComboBox" in cls:
            txt = c.window_text()
            r = c.rectangle()
            print("  text=%r  rect=(%d,%d)-(%d,%d)" % (txt, r.left, r.top, r.right, r.bottom))
    except Exception:
        pass
