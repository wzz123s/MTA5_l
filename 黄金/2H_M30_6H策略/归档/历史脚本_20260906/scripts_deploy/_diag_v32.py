# -*- coding: utf-8 -*-
"""v32: 测试方向键字段移动"""
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

# 点击，焦点在某字段
target.click_input()
time.sleep(0.4)

# 左方向键 x1，然后上箭头，看哪个字段变
print("\n左 x1 后上箭头 x1:")
send_keys("{LEFT}")
time.sleep(0.3)
send_keys("{UP}")
time.sleep(0.3)
print("  %r" % target.window_text())

# 再左 x1，上箭头
print("再左 x1 后上箭头 x1:")
send_keys("{LEFT}")
time.sleep(0.3)
send_keys("{UP}")
time.sleep(0.3)
print("  %r" % target.window_text())

# 右方向键 x1，上箭头（看是否回到月）
print("右 x1 后上箭头 x1:")
send_keys("{RIGHT}")
time.sleep(0.3)
send_keys("{UP}")
time.sleep(0.3)
print("  %r" % target.window_text())
