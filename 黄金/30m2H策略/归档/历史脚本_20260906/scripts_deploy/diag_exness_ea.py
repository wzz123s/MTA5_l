# -*- coding: utf-8 -*-
"""EXNESS EA 树诊断: 展开 + 树结构 + 尝试选择."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8')
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from pywinauto import Application
from pywinauto.keyboard import send_keys

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
MT5_HWND = 5114106

app = Application(backend="win32").connect(handle=MT5_HWND)
win = app.window(handle=MT5_HWND)
user32.SetWindowPos(ctypes.c_void_p(MT5_HWND), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.3)
user32.SetForegroundWindow(MT5_HWND); time.sleep(0.5)

ea = None
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c
    except Exception:
        pass
print("EA:", ea.window_text()[:45])

# 展开
ea.click_input(); time.sleep(1.5)
print("click 后")

# 找树
trees = []
for c in win.descendants():
    try:
        if "SysTreeView32" in c.class_name():
            try:
                trees.append((c.is_visible(), c.rectangle()))
            except Exception:
                pass
    except Exception:
        pass
print("树数量:", len(trees))
for vis, r in trees[:4]:
    print("  可见=%s rect=(%d,%d,%d,%d)" % (vis, r.left, r.top, r.right, r.bottom))

# 尝试 send_keys 输入
for ch in "30m2H_ABC_EA":
    send_keys(ch); time.sleep(0.12)
time.sleep(1.0)
send_keys("{ENTER}"); time.sleep(1.0)
print("输入后 EA:", ea.window_text()[:45])
