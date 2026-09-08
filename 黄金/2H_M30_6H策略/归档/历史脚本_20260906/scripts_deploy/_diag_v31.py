# -*- coding: utf-8 -*-
"""v31: 键盘导航+上下箭头 调整日期止"""
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

target = None
for c in mt5.descendants():
    try:
        if "SysDateTimePick32" in c.class_name():
            r = c.rectangle()
            if r.top == 632 and r.left > 600:
                target = c
    except Exception:
        pass

if target is None:
    print("未找到日期止"); sys.exit(1)

print("初始: %r" % target.window_text())

# 点击控件，然后 Home 定位到年字段
print("\n点击 + Home")
target.click_input()
time.sleep(0.4)
send_keys("{HOME}")
time.sleep(0.4)
print("Home 后: %r" % target.window_text())

# 上箭头 1 次，看年是否变化
print("上箭头 x1")
send_keys("{UP}")
time.sleep(0.3)
print("UP x1 后: %r" % target.window_text())

# 再上箭头 3 次
print("上箭头 x3")
send_keys("{UP}{UP}{UP}")
time.sleep(0.3)
print("UP x3 后: %r" % target.window_text())
