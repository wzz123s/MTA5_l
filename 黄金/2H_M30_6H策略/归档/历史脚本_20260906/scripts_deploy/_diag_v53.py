# -*- coding: utf-8 -*-
"""v53: 在配置正确的实例上重新选 EA + BM_CLICK 点开始"""
import sys, time, ctypes
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

BM_CLICK = 0x00F5
d = Desktop(backend="win32")

# 找 Tester 里 EA=2H_M30_6H_ABC_EA 的实例
target = None
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t and "[" in t:
            # 检查 Tester 的 EA 和日期
            ea_ok = False
            date_ok = False
            for c in w.descendants():
                try:
                    if "ComboBox" in c.class_name() and "2H_M30_6H_ABC_EA" in c.window_text():
                        ea_ok = True
                    if "SysDateTimePick32" in c.class_name() and c.window_text() == "2025.01.01":
                        date_ok = True
                except Exception:
                    pass
            if ea_ok and date_ok:
                target = w
                print("找到配置正确的实例 hwnd=%d" % w.handle)
                break
    except Exception:
        pass

if target is None:
    print("FAIL: 未找到配置正确的实例"); sys.exit(1)

# 重新选 EA（加载新 .ex5）
for c in target.descendants():
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

# BM_CLICK 开始
start_hwnd = None
for c in target.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            start_hwnd = c.handle
    except Exception:
        pass

if start_hwnd:
    ctypes.windll.user32.SendMessageW(start_hwnd, BM_CLICK, 0, 0)
    time.sleep(3.0)
    for c in target.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始", "停止"):
                print("按钮状态:", c.window_text())
        except Exception:
            pass
else:
    print("未找到开始按钮")
