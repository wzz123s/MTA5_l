# -*- coding: utf-8 -*-
"""v29: 读当前 DTP + 测试日历下拉按钮"""
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

print("=== 当前 DTP ===")
target = None
for c in mt5.descendants():
    try:
        if "DateTimePick" in c.class_name():
            r = c.rectangle()
            print("  text=%r rect=(%d,%d)-(%d,%d) hwnd=%d" % (c.window_text(), r.left, r.top, r.right, r.bottom, c.handle))
            # 日期止 = top 632 行, x 更大的那个
            if r.top == 632 and r.left > 600:
                target = c
    except Exception:
        pass

if target:
    r = target.rectangle()
    print("\n目标日期止: %r" % target.window_text())
    print("子控件:")
    for ch in target.children():
        cr = ch.rectangle()
        print("  class=%r text=%r rect=(%d,%d)-(%d,%d)" % (ch.class_name(), ch.window_text(), cr.left, cr.top, cr.right, cr.bottom))
    # 点击右侧下拉按钮
    print("点击下拉按钮...")
    target.click_input(coords=(r.right - r.left - 12, (r.bottom - r.top) // 2))
    time.sleep(1.2)
    # 找 MonthCal 窗口
    print("=== MonthCal/日历窗口 ===")
    d = Desktop(backend="win32")
    for w in d.windows():
        try:
            cls = w.class_name()
            if "MonthCal" in cls or "monthcal" in cls.lower() or "日历" in w.window_text():
                wr = w.rectangle()
                print("  日历: class=%r text=%r rect=(%d,%d)-(%d,%d)" % (cls, w.window_text(), wr.left, wr.top, wr.right, wr.bottom))
        except Exception:
            pass
else:
    print("未找到日期止")
