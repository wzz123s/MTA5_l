# -*- coding: utf-8 -*-
"""检查两个 MT5 实例的 Tester 状态"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

d = Desktop(backend="win32")

for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t and "[" in t:
            print("=== 实例: %s (hwnd=%d) ===" % (t[:70], w.handle))
            # 检查 Tester 面板的关键配置
            for c in w.descendants():
                try:
                    if "ComboBox" in c.class_name():
                        txt = c.window_text()
                        if txt and any(k in txt for k in ["Advisors", "XAUUSDm", "USOILm", "M30", "H4", "仅使用开价", "每次报价"]):
                            print("  ComboBox: %r" % txt)
                    if "SysDateTimePick32" in c.class_name() and c.window_text():
                        print("  DateTime: %r" % c.window_text())
                except Exception:
                    pass
            # 开始/停止按钮
            for c in w.descendants():
                try:
                    if "Button" in c.class_name() and c.window_text() in ("开始", "停止"):
                        print("  按钮: %r" % c.window_text())
                except Exception:
                    pass
            print()
    except Exception:
        pass
