# -*- coding: utf-8 -*-
"""v33: 用方向键+箭头 设置日期起(2025.01.01)和日期止(2026.08.14)"""
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

def get_dtp(mt5, top, left_gt):
    for c in mt5.descendants():
        try:
            if "SysDateTimePick32" in c.class_name():
                r = c.rectangle()
                if r.top == top and r.left > left_gt:
                    return c, r
        except Exception:
            pass
    return None, None

def set_date(ctrl, target_y, target_m, target_d):
    """点击后焦点在日字段。左=日->月->年，右=年->月->日"""
    # 解析当前值
    txt = ctrl.window_text()
    parts = txt.split(".")
    cy, cm, cd = int(parts[0]), int(parts[1]), int(parts[2])
    print("  %s -> %04d.%02d.%02d" % (txt, target_y, target_m, target_d))
    ctrl.click_input()
    time.sleep(0.4)
    # 焦点现在在日字段。左x2 到年
    send_keys("{LEFT}{LEFT}")
    time.sleep(0.2)
    # 调整年
    dy = target_y - cy
    if dy > 0:
        send_keys("{UP}" * dy)
    elif dy < 0:
        send_keys("{DOWN}" * (-dy))
    time.sleep(0.3)
    # 右到月
    send_keys("{RIGHT}")
    time.sleep(0.2)
    dm = target_m - cm
    if dm > 0:
        send_keys("{UP}" * dm)
    elif dm < 0:
        send_keys("{DOWN}" * (-dm))
    time.sleep(0.3)
    # 右到日
    send_keys("{RIGHT}")
    time.sleep(0.2)
    dd = target_d - cd
    if dd > 0:
        send_keys("{UP}" * dd)
    elif dd < 0:
        send_keys("{DOWN}" * (-dd))
    time.sleep(0.3)
    send_keys("{ENTER}")
    time.sleep(0.3)
    print("  结果: %r" % ctrl.window_text())

mt5 = find_mt5()
if mt5 is None:
    print("FAIL"); sys.exit(1)

# 日期起 = top 632 左 (x<600), 日期止 = top 632 右 (x>600)
start, _ = get_dtp(mt5, 632, 0)
stop, _ = get_dtp(mt5, 632, 600)

print("=== 日期起 ===")
if start:
    set_date(start, 2025, 1, 1)
print("=== 日期止 ===")
if stop:
    set_date(stop, 2026, 8, 14)

# 最终读回
print("\n=== 最终 DTP ===")
for c in mt5.descendants():
    try:
        if "SysDateTimePick32" in c.class_name():
            r = c.rectangle()
            print("  %r rect=(%d,%d)" % (c.window_text(), r.left, r.top))
    except Exception:
        pass
