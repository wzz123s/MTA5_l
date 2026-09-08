# -*- coding: utf-8 -*-
"""截图 MT5 窗口看 Tester 面板实际状态."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

d = Desktop(backend="win32")
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t and "[XAUUSDm" in t:
            img = w.capture_as_image()
            out = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\scripts\deploy\mt5_screenshot.png"
            img.save(out)
            print("saved:", out, "size:", img.size)
            break
    except Exception as e:
        print("err:", e)
