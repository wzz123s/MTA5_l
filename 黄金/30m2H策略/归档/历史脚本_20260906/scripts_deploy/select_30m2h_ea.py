# -*- coding: utf-8 -*-
"""树展开后逐字符输入选 30m2H_ABC_EA."""
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

print("[EA] 前:", ea.window_text()[:45])
ea.click_input(); time.sleep(1.5)  # 展开树

# 点击树聚焦 (树中心靠上一点, 避免点到空白)
for c in mt5.descendants():
    try:
        if "SysTreeView32" in c.class_name():
            try:
                if c.is_visible():
                    r = c.rectangle()
                    c.click_input(coords=(int(r.width()*0.3), int(r.height()*0.15)))
                    time.sleep(0.5)
                    print("已点击树聚焦")
                    break
            except Exception:
                pass
    except Exception:
        pass

# 逐字符输入
for ch in "30m2H_ABC_EA":
    send_keys(ch); time.sleep(0.15)
time.sleep(1.0)
send_keys("{ENTER}"); time.sleep(1.0)
print("[EA] 后:", ea.window_text()[:45])
