# -*- coding: utf-8 -*-
"""v41: 重新选 EA + 点开始（.ex5 已更新）"""
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

# 重新选 EA
ea = None
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c
    except Exception:
        pass

if ea:
    print("[EA] 重新选择...")
    ea.click_input()
    time.sleep(0.5)
    send_keys("2H_M30_6H_ABC_EA")
    time.sleep(0.5)
    send_keys("{ENTER}")
    time.sleep(0.6)
    print("  -> %r" % ea.window_text())
else:
    print("[EA] 未找到")

# 点开始
start = None
for c in mt5.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            start = c
    except Exception:
        pass

if start:
    print("点击开始...")
    start.click_input()
    time.sleep(2.0)
    # 读回状态
    for c in mt5.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始", "停止"):
                print("按钮状态: %r" % c.window_text())
        except Exception:
            pass
else:
    print("未找到开始按钮")
