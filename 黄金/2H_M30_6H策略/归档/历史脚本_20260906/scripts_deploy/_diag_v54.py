# -*- coding: utf-8 -*-
"""v54: 检查实例2 的真实按钮状态"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

d = Desktop(backend="win32")

for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t and "[" in t:
            # 找 EA=2H_M30_6H_ABC_EA 的实例
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
                        if "Button" in c.class_name() and c.window_text() in ("开始", "停止"):
                            print("  按钮:", c.window_text())
                    except Exception:
                        pass
    except Exception:
        pass
