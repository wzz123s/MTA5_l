# -*- coding: utf-8 -*-
"""v47: 点击弹窗 应用 按钮关闭 + 检查遮挡"""
import sys, time, ctypes
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

d = Desktop(backend="win32")

# 1. 检查开始按钮位置被什么窗口遮挡
pt = (2498, 780)
h = ctypes.windll.user32.WindowFromPoint(pt[0], pt[1])
print("WindowFromPoint(2498,780) hwnd=%d" % h)

# 2. 点弹窗 应用 按钮
dlg = None
for w in d.windows():
    try:
        if w.window_text() == "自定义分析周期":
            dlg = w
    except Exception:
        pass

if dlg:
    for c in dlg.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() == "应用":
                print("点击 应用 按钮...")
                c.click_input()
                time.sleep(1.0)
        except Exception:
            pass

# 3. 检查弹窗是否关闭
still = False
for w in d.windows():
    try:
        if w.window_text() == "自定义分析周期":
            still = True
    except Exception:
        pass
print("弹窗仍存在:", still)

# 4. 点开始
mt5 = None
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t and "[" in t:
            mt5 = w
    except Exception:
        pass

if mt5:
    for c in mt5.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() == "开始":
                print("点开始...")
                c.click_input()
                time.sleep(3.0)
        except Exception:
            pass
    for c in mt5.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始", "停止"):
                print("按钮状态: %r" % c.window_text())
        except Exception:
            pass
