# -*- coding: utf-8 -*-
"""展开树 -> 找树 hwnd -> set_focus -> 输入."""
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

print("EA:", ea.window_text()[:40])
ea.click_input(); time.sleep(1.5)

# GetFocus 检查
fg = user32.GetFocus()
print("GetFocus hwnd:", fg)

# 找树
tree = None
for c in mt5.descendants():
    try:
        if "SysTreeView32" in c.class_name():
            try:
                if c.is_visible():
                    tree = c
            except Exception:
                pass
    except Exception:
        pass
if tree is None:
    print("无可见树"); sys.exit(1)
print("Tree hwnd:", tree.handle)

# set_focus 树
tree.set_focus(); time.sleep(0.5)
fg2 = user32.GetFocus()
print("set_focus后 GetFocus:", fg2, "(tree=", tree.handle, ")")

# 逐字符输入
for ch in "30m2H_ABC_EA":
    send_keys(ch); time.sleep(0.12)
time.sleep(1.0)
send_keys("{ENTER}"); time.sleep(1.0)
print("EA 结果:", ea.window_text()[:45])
