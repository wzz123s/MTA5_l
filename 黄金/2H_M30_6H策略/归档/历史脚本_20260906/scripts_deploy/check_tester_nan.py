# -*- coding: utf-8 -*-
"""检查 MT5 Tester 面板当前状态 (XAUUSDm 实例)."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

d = Desktop(backend="win32")

def find_xau():
    for w in d.windows():
        try:
            t = w.window_text()
            if t and "Exness" in t and "[XAUUSDm" in t:
                return w
        except Exception:
            pass
    return None

w = find_xau()
if w is None:
    print("FAIL: 未找到 XAUUSDm 实例")
    sys.exit(1)
print("实例: %r hwnd=%d" % (w.window_text(), w.handle))

# 扫描关键控件
combo_found = []
for c in w.descendants():
    try:
        cls = c.class_name()
        txt = c.window_text()
        if "ComboBox" in cls and txt:
            r = c.rectangle()
            combo_found.append((txt[:40], r.left, r.top))
        if "Button" in cls and txt in ("开始", "停止", "跳过"):
            r = c.rectangle()
            print("  [按钮] %r @(%d,%d) hwnd=%d" % (txt, r.left, r.top, c.handle))
        if "SysDateTimePick32" in cls:
            r = c.rectangle()
            print("  [日期] %r @(%d,%d)" % (txt, r.left, r.top))
    except Exception:
        pass

print("\n=== 关键 ComboBox ===")
for t, x, y in combo_found:
    if any(k in t for k in ["Advisors", "XAUUSDm", "USOILm", "M30", "H4", "H1", "仅使用开价", "每次报价", "每次基于实时点"]):
        print("  %r @(%d,%d)" % (t, x, y))
