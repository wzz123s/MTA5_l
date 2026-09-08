# -*- coding: utf-8 -*-
"""click_input EA 后枚举 MT5 子控件找 TreeView."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
d = Desktop(backend="win32")
MT5_HWND = 17306644

mt5 = None
for w in d.windows():
    if w.handle == MT5_HWND:
        mt5 = w
if mt5 is None:
    print("FAIL"); sys.exit(1)

hwnd = mt5.handle
user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.5)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)

ea = None
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c
    except Exception:
        pass

if ea is None:
    print("FAIL 无 EA combo"); sys.exit(1)

print("=== EA combo 附近控件 (click 前) ===")
r = ea.rectangle()
for c in mt5.descendants():
    try:
        rr = c.rectangle()
        if abs(rr.top - r.top) < 30 and abs(rr.left - r.left) < 900:
            print("  %s %r @(%d,%d,%d,%d)" % (c.class_name()[:20], c.window_text()[:40], rr.left, rr.top, rr.right, rr.bottom))
    except Exception:
        pass

print("\n=== click_input EA ===")
ea.click_input(); time.sleep(1.0)

print("=== click 后出现的新控件 (TreeView/ListBox/窗口) ===")
for c in mt5.descendants():
    try:
        cls = c.class_name()
        if any(k in cls for k in ["TreeView", "ListBox", "SysTreeView", "List", "Tree"]):
            rr = c.rectangle()
            print("  [树] %s @(%d,%d,%d,%d) 可见=%s" % (cls, rr.left, rr.top, rr.right, rr.bottom, c.is_visible()))
    except Exception:
        pass

# 也检查顶层窗口是否有弹出
print("=== 顶层可见窗口 ===")
for w in d.windows():
    try:
        t = w.window_text()
        if t and w.is_visible():
            rr = w.rectangle()
            print("  %r @(%d,%d,%d,%d)" % (t[:45], rr.left, rr.top, rr.right, rr.bottom))
    except Exception:
        pass
