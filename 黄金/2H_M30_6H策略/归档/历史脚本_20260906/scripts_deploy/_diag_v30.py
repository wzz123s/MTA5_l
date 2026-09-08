# -*- coding: utf-8 -*-
"""v30: 逐字段点击+输入日期止"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

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
target = None
for c in mt5.descendants():
    try:
        cls = c.class_name()
        if "DateTimePick" in cls:
            r = c.rectangle()
            txt = c.window_text()
            print("DTP: class=%r text=%r rect=(%d,%d)-(%d,%d)" % (cls, txt, r.left, r.top, r.right, r.bottom))
            if r.top == 632 and r.left > 600:
                target = c
                target_rect = r
    except Exception:
        pass

if target is None:
    print("未找到日期止"); sys.exit(1)

r = target_rect
w = r.right - r.left
h = r.bottom - r.top
print("\n目标日期止: %r, 宽=%d 高=%d" % (target.window_text(), w, h))

# 年字段 = 左 1/3, 月 = 中 1/3, 日 = 右 1/3
year_x = int(w * 0.25)
mon_x = int(w * 0.55)
day_x = int(w * 0.85)
mid_y = h // 2

# 1. 年字段
print("\n[1] 点击年字段 (%d,%d) 输入 2026" % (year_x, mid_y))
target.click_input(coords=(year_x, mid_y))
time.sleep(0.4)
send_keys("2026")
time.sleep(0.4)
print("  年后: %r" % target.window_text())

# 2. 月字段
print("[2] 点击月字段 (%d,%d) 输入 08" % (mon_x, mid_y))
target.click_input(coords=(mon_x, mid_y))
time.sleep(0.4)
send_keys("08")
time.sleep(0.4)
print("  月后: %r" % target.window_text())

# 3. 日字段
print("[3] 点击日字段 (%d,%d) 输入 14" % (day_x, mid_y))
target.click_input(coords=(day_x, mid_y))
time.sleep(0.4)
send_keys("14")
time.sleep(0.4)
print("  日后: %r" % target.window_text())

send_keys("{ENTER}")
time.sleep(0.3)
print("\n最终: %r" % target.window_text())
