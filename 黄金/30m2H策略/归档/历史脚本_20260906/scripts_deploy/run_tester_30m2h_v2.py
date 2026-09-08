# -*- coding: utf-8 -*-
"""30m2H Tester v2: hwnd 连接 + 选 EA + 点开始."""
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
BM_CLICK = 0x00F5
MT5_HWND = 3473596

app = Application(backend="win32").connect(handle=MT5_HWND)
win = app.window(handle=MT5_HWND)
print("连接:", win.window_text()[:50])
user32.SetWindowPos(ctypes.c_void_p(MT5_HWND), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.4)
user32.SetForegroundWindow(MT5_HWND); time.sleep(0.5)

# Ctrl+R 打开 Tester
send_keys("^r"); time.sleep(3.0)
print("Ctrl+R 后")

# 选 EA
ea = None
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c
            break
    except Exception:
        pass
if ea is None:
    print("无 EA combo"); sys.exit(1)
print("[EA] 当前:", ea.window_text()[:50])
if "30m2H_ABC_EA" not in ea.window_text():
    ea.click_input(); time.sleep(1.0)
    send_keys("30m2H_ABC_EA", with_spaces=True); time.sleep(1.0)
    send_keys("{ENTER}"); time.sleep(1.2)
print("[EA] 结果:", ea.window_text()[:50])

# 检查日期/模式
for c in win.descendants():
    try:
        txt = c.window_text()
        if "SysDateTimePick32" in c.class_name():
            print("  日期 %r" % txt)
        if "ComboBox" in c.class_name() and txt in ("仅使用开价","每次报价","M30","H2","XAUUSDm"):
            print("  Combo %r" % txt)
    except Exception:
        pass
