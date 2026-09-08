# -*- coding: utf-8 -*-
"""v55: 读实例2 完整配置"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

d = Desktop(backend="win32")

for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t and "[" in t:
            ea_ok = False
            for c in w.descendants():
                try:
                    if "ComboBox" in c.class_name() and "2H_M30_6H_ABC_EA" in c.window_text():
                        ea_ok = True
                except Exception:
                    pass
            if ea_ok:
                print("实例2 hwnd=%d" % w.handle)
                for c in w.descendants():
                    try:
                        cls = c.class_name()
                        txt = c.window_text()
                        if "ComboBox" in cls and txt and any(k in txt for k in ["Advisors", "XAUUSDm", "USOILm", "M30", "H4", "仅使用开价", "每次报价", "100", "500", "2000"]):
                            print("  ComboBox:", txt)
                        if "SysDateTimePick32" in cls and txt:
                            print("  DateTime:", txt)
                    except Exception:
                        pass
    except Exception:
        pass
