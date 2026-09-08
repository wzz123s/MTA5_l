# -*- coding: utf-8 -*-
"""v49: BM_CLICK 直接点击开始按钮（绕过 wh6 遮挡）"""
import sys, time, ctypes
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

BM_CLICK = 0x00F5
d = Desktop(backend="win32")

# 找 MT5 和开始按钮
mt5 = None
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t and "[" in t:
            mt5 = w
    except Exception:
        pass

if mt5 is None:
    print("FAIL: MT5 not found"); sys.exit(1)

start_hwnd = None
for c in mt5.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            start_hwnd = c.handle
            print("开始按钮 hwnd=%d" % start_hwnd)
    except Exception:
        pass

if start_hwnd:
    print("BM_CLICK 点击...")
    r = ctypes.windll.user32.SendMessageW(start_hwnd, BM_CLICK, 0, 0)
    print("BM_CLICK 返回:", r)
    time.sleep(3.0)
    # 检查按钮状态
    for c in mt5.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始", "停止"):
                print("按钮状态: %r" % c.window_text())
        except Exception:
            pass
