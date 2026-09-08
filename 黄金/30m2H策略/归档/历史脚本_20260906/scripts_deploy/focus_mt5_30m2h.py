# -*- coding: utf-8 -*-
"""点击 MT5 内部激活键盘焦点, 再操作 EA."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8')
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
d = Desktop(backend="win32")

mt5 = None
for w in d.windows():
    try:
        if w.handle == 4654538:
            mt5 = w
    except Exception:
        pass
hwnd = mt5.handle
user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.4)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)

# 点 MT5 窗口内 (图表区, 避开 Tester 面板) - 用 win32 点击
r = mt5.rectangle()
cx, cy = (r.left + r.right)//2, r.top + 200  # 图表区
print("点击 (%d,%d)" % (cx, cy))
user32.SetCursorPos(cx, cy); time.sleep(0.2)
user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
time.sleep(0.1)
user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
time.sleep(0.5)

fg = user32.GetFocus()
print("点击后 GetFocus:", fg)

# 现在操作 EA
ea = None
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c
    except Exception:
        pass
if ea:
    print("EA:", ea.window_text()[:40])
    ea.click_input(); time.sleep(1.2)
    fg2 = user32.GetFocus()
    print("EA click后 GetFocus:", fg2)
