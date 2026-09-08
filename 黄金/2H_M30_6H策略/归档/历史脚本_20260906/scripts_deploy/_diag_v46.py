# -*- coding: utf-8 -*-
"""v46: 用 WM_CLOSE 关闭弹窗"""
import sys, time, ctypes
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

WM_CLOSE = 0x0010
d = Desktop(backend="win32")

# 找弹窗
dlg_hwnd = None
for w in d.windows():
    try:
        if w.window_text() == "自定义分析周期":
            dlg_hwnd = w.handle
            print("弹窗 hwnd=%d" % dlg_hwnd)
    except Exception:
        pass

if dlg_hwnd:
    # 发 WM_CLOSE
    r = ctypes.windll.user32.SendMessageW(dlg_hwnd, WM_CLOSE, 0, 0)
    time.sleep(1.0)
    print("WM_CLOSE 返回:", r)

# 检查是否关闭
still = False
for w in d.windows():
    try:
        if w.window_text() == "自定义分析周期":
            still = True
    except Exception:
        pass
print("弹窗仍存在:", still)

# 列出所有 #32770 弹窗
print("=== 当前所有 #32770 弹窗 ===")
for w in d.windows():
    try:
        cls = w.class_name()
        if "#32770" in cls:
            t = w.window_text()
            r = w.rectangle()
            print("  %r rect=(%d,%d)-(%d,%d) hwnd=%d" % (t, r.left, r.top, r.right, r.bottom, w.handle))
    except Exception:
        pass
