# -*- coding: utf-8 -*-
"""树展开后方向键导航找 30m2H_ABC_EA."""
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
user32.SetForegroundWindow(hwnd); time.sleep(0.4)

ea = None
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c
    except Exception:
        pass

def ea_text():
    return ea.window_text()[:45]

print("初始:", ea_text())
ea.click_input(); time.sleep(1.2)
print("展开后:", ea_text())

# 先试 UP 一次看是否移动 (若焦点在树顶部, UP 可能不动)
send_keys("{DOWN}"); time.sleep(0.5)
print("DOWN1:", ea_text())
send_keys("{DOWN}"); time.sleep(0.5)
print("DOWN2:", ea_text())
send_keys("{DOWN}"); time.sleep(0.5)
print("DOWN3:", ea_text())
send_keys("{ENTER}"); time.sleep(0.8)
print("ENTER后:", ea_text())
