# -*- coding: utf-8 -*-
"""v15: 重新读取所有 DateTime 当前值"""
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

print("=== DateTimePick ===")
for c in mt5.descendants():
    try:
        if "DateTimePick" in c.class_name():
            r = c.rectangle()
            print("  text=%r  rect=(%d,%d)-(%d,%d)" % (c.window_text(), r.left, r.top, r.right, r.bottom))
    except Exception:
        pass

print("=== ComboBox (y 632-700 行) ===")
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name():
            r = c.rectangle()
            if r.top > 620 and r.top < 710:
                print("  text=%r  rect=(%d,%d)-(%d,%d)" % (c.window_text(), r.left, r.top, r.right, r.bottom))
    except Exception:
        pass
