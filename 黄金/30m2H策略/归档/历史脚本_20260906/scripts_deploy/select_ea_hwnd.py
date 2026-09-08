# -*- coding: utf-8 -*-
"""hwnd 连接 MT5: Ctrl+R + 选 EA 30m2H_ABC_EA."""
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
MT5_HWND = 656414

app = Application(backend="win32").connect(handle=MT5_HWND)
win = app.window(handle=MT5_HWND)
print("连接 MT5:", win.window_text()[:50])

user32.SetWindowPos(ctypes.c_void_p(MT5_HWND), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.5)
user32.SetForegroundWindow(MT5_HWND); time.sleep(0.5)

# Ctrl+R 打开 Tester
send_keys("^r"); time.sleep(3.0)
print("已 Ctrl+R")

# 找 EA combo
ea = None
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c
            break
    except Exception:
        pass
if ea is None:
    print("FAIL 无 EA combo"); sys.exit(1)
print("[EA] 当前:", ea.window_text()[:50])

# 选 30m2H_ABC_EA
ea.click_input(); time.sleep(1.0)
send_keys("30m2H_ABC_EA", with_spaces=True); time.sleep(1.0)
send_keys("{ENTER}"); time.sleep(1.2)
print("[EA] 选择后:", ea.window_text()[:50])

# 检查配置
for c in win.descendants():
    try:
        cls = c.class_name()
        txt = c.window_text()
        if "ComboBox" in cls and txt and any(k in txt for k in ["XAUUSDm", "M30", "仅使用开价"]):
            print("  Combo %r" % txt[:40])
        if "SysDateTimePick32" in cls:
            print("  日期 %r" % txt)
    except Exception:
        pass
