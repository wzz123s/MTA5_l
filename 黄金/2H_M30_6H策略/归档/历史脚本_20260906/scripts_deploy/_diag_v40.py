# -*- coding: utf-8 -*-
"""v40: 检查 Tester 当前配置（.ex5 已更新后）"""
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
    print("FAIL: MT5 not found"); sys.exit(1)

print("MT5 minimized:", mt5.is_minimized())

print("=== 关键配置 ===")
for c in mt5.descendants():
    try:
        cls = c.class_name()
        txt = c.window_text()
        if "ComboBox" in cls and txt and any(k in txt for k in ["Advisors", "XAUUSDm", "USOILm", "M30", "H4", "仅使用开价", "每次报价", "500", "1:2000"]):
            print("  ComboBox: %r" % txt)
        if "SysDateTimePick32" in cls and txt:
            print("  DateTime: %r" % txt)
    except Exception:
        pass

print("=== 开始/停止按钮 ===")
for c in mt5.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() in ("开始", "停止", "跳过"):
            r = c.rectangle()
            print("  %r rect=(%d,%d)-(%d,%d)" % (c.window_text(), r.left, r.top, r.right, r.bottom))
    except Exception:
        pass
