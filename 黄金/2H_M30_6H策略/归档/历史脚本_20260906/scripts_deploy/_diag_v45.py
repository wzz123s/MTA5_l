# -*- coding: utf-8 -*-
"""v45: 关闭弹窗 + 点开始"""
import sys, time, ctypes
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

d = Desktop(backend="win32")

# 关闭 自定义分析周期 弹窗
for w in d.windows():
    try:
        if w.window_text() == "自定义分析周期":
            print("聚焦弹窗 + Alt+F4")
            w.set_focus()
            time.sleep(0.5)
            send_keys("%{F4}")
            time.sleep(1.0)
    except Exception as e:
        print("close err:", e)

# 检查是否关闭
still = False
for w in d.windows():
    try:
        if w.window_text() == "自定义分析周期":
            still = True
    except Exception:
        pass
print("弹窗仍存在:", still)

# 点开始
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
else:
    print("MT5 not found")
