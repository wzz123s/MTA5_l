# -*- coding: utf-8 -*-
"""v24: 纯读 DTP，无任何写操作"""
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
print("=== DateTimePick (纯读) ===")
for c in mt5.descendants():
    try:
        if "DateTimePick" in c.class_name():
            r = c.rectangle()
            print("  text=%r rect=(%d,%d)-(%d,%d) hwnd=%d" % (c.window_text(), r.left, r.top, r.right, r.bottom, c.handle))
    except Exception:
        pass
