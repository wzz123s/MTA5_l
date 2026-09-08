# -*- coding: utf-8 -*-
"""v28: 点击日期止下拉按钮，观察日历弹出"""
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

# 找日期止
for c in mt5.descendants():
    try:
        if "DateTimePick" in c.class_name() and c.window_text() == "2026.09.01":
            r = c.rectangle()
            print("日期止 rect=(%d,%d)-(%d,%d)" % (r.left, r.top, r.right, r.bottom))
            # 检查子控件
            print("子控件:")
            for ch in c.children():
                print("  class=%r text=%r rect=(%d,%d)-(%d,%d)" % (ch.class_name(), ch.window_text(), ch.rectangle().left, ch.rectangle().top, ch.rectangle().right, ch.rectangle().bottom))
            # 点击下拉按钮（右侧）
            drop_x = r.right - 10
            drop_y = (r.top + r.bottom) // 2
            print("点击下拉按钮 (%d,%d)" % (drop_x, drop_y))
            c.click_input(coords=(r.right - r.left - 10, (r.bottom - r.top) // 2))
            time.sleep(1.0)
            break
    except Exception:
        pass

# 枚举新窗口（日历）
print("\n=== 当前顶层窗口 ===")
d = Desktop(backend="win32")
for w in d.windows():
    try:
        t = w.window_text()
        r = w.rectangle()
        if r.width() > 50 and r.height() > 50:
            print("  class=%r text=%r rect=(%d,%d)-(%d,%d)" % (w.class_name(), t[:40], r.left, r.top, r.right, r.bottom))
    except Exception:
        pass
