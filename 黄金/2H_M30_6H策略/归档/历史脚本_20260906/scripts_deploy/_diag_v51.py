# -*- coding: utf-8 -*-
"""v51: 重新选 EA + BM_CLICK 点开始"""
import sys, time, ctypes
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

BM_CLICK = 0x00F5
d = Desktop(backend="win32")

def find_mt5():
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

for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            c.click_input()
            time.sleep(0.5)
            send_keys("2H_M30_6H_ABC_EA")
            time.sleep(0.5)
            send_keys("{ENTER}")
            time.sleep(0.6)
            print("EA ->", c.window_text())
    except Exception:
        pass

start_hwnd = None
for c in mt5.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            start_hwnd = c.handle
    except Exception:
        pass

if start_hwnd:
    ctypes.windll.user32.SendMessageW(start_hwnd, BM_CLICK, 0, 0)
    time.sleep(3.0)
    for c in mt5.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始", "停止"):
                print("按钮状态:", c.window_text())
        except Exception:
            pass
else:
    print("未找到开始按钮")
