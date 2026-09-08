# -*- coding: utf-8 -*-
"""click_input EA combo, 检查树是否展开."""
import ctypes, sys
sys.stdout.reconfigure(encoding='utf-8')
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import time
from pywinauto import Desktop

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
d = Desktop(backend="win32")

mt5 = None
for w in d.windows():
    try:
        if w.handle == 4654538:
            mt5 = w
    except Exception:
        pass
if mt5 is None:
    for w in d.windows():
        try:
            if "Exness" in w.window_text() and not w.is_minimized():
                mt5 = w
        except Exception:
            pass
if mt5 is None:
    print("FAIL"); sys.exit(1)
hwnd = mt5.handle
user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.5)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)

# 检查前台
fg = user32.GetForegroundWindow()
print("前台:", fg, "MT5:", hwnd, fg==hwnd)

ea = None
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c
    except Exception:
        pass
if ea is None:
    print("无 EA combo"); sys.exit(1)
rr = ea.rectangle()
cx, cy = (rr.left+rr.right)//2, (rr.top+rr.bottom)//2
h = user32.WindowFromPoint(cx, cy)
print("EA combo 中心(%d,%d) WindowFromPoint=%d (MT5=%d) %s" % (cx, cy, h, hwnd, "MT5" if h==hwnd else "被挡"))

# click_input
ea.click_input(); time.sleep(1.2)
print("已 click_input")

# 枚举树
trees = []
for c in mt5.descendants():
    try:
        if "SysTreeView32" in c.class_name():
            try:
                vis = c.is_visible()
                trees.append((vis, c.rectangle()))
            except Exception:
                pass
    except Exception:
        pass
print("SysTreeView32 数量:", len(trees))
for vis, r in trees[:5]:
    print("  可见=%s rect=(%d,%d,%d,%d)" % (vis, r.left, r.top, r.right, r.bottom))
