# -*- coding: utf-8 -*-
"""诊断 EA/模式 ComboBox 是否为标准 Win32 ComboBox (CB_ 消息)."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

CB_GETCOUNT = 0x0146
CB_GETLBTEXT = 0x0148
user32 = ctypes.windll.user32

d = Desktop(backend="win32")
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t and "[XAUUSDm" in t:
            mt5 = w
    except Exception:
        pass

for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name():
            txt = c.window_text()
            if "Advisors" in txt or txt in ("每次报价", "仅使用开价", "1分钟OHLC", "每次基于实时点"):
                hwnd = c.handle
                count = user32.SendMessageW(hwnd, CB_GETCOUNT, 0, 0)
                print("Combo %r hwnd=%d 项数=%d" % (txt[:40], hwnd, count))
                if count > 0 and count < 100:
                    for i in range(min(count, 30)):
                        buf = ctypes.create_unicode_buffer(256)
                        user32.SendMessageW(hwnd, CB_GETLBTEXT, i, ctypes.byref(buf))
                        mark = " <== 目标" if ("ABC" in buf.value or buf.value == "仅使用开价") else ""
                        print("    [%d] %s%s" % (i, buf.value, mark))
    except Exception as e:
        pass
