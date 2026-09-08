# -*- coding: utf-8 -*-
"""v43: 直接点开始（不重新选 EA）"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

def find_mt5():
    d = Desktop(backend="win32")
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

start = None
for c in mt5.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            start = c
            r = c.rectangle()
            print("开始按钮 rect=(%d,%d)-(%d,%d)" % (r.left, r.top, r.right, r.bottom))
    except Exception:
        pass

if start:
    # 用 center 坐标点击
    r = start.rectangle()
    cx = (r.left + r.right) // 2
    cy = (r.top + r.bottom) // 2
    print("点击 center (%d,%d)" % (cx, cy))
    start.click_input(coords=((r.right-r.left)//2, (r.bottom-r.top)//2))
    time.sleep(3.0)
    # 读回状态
    for c in mt5.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始", "停止"):
                print("按钮状态: %r" % c.window_text())
        except Exception:
            pass
else:
    print("未找到开始按钮")
