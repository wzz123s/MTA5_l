# -*- coding: utf-8 -*-
"""置顶 MT5 覆盖 Edge, 验证 WindowFromPoint, 然后设置 EA."""
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
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
CB_GETCOUNT = 0x0146
CB_GETLBTEXT = 0x0148
CB_SETCURSEL = 0x014E
d = Desktop(backend="win32")

def find_xau():
    for w in d.windows():
        try:
            t = w.window_text()
            if t and "Exness" in t and "[XAUUSDm" in t:
                return w
        except Exception:
            pass
    return None

mt5 = find_xau()
if mt5 is None:
    print("FAIL"); sys.exit(1)
hwnd = mt5.handle

# 置顶 MT5
r = user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
print("SetWindowPos TOPMOST 返回=%d" % r)
time.sleep(0.5)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)

# 验证 WindowFromPoint
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            rr = c.rectangle()
            cx, cy = (rr.left + rr.right)//2, (rr.top + rr.bottom)//2
            h = user32.WindowFromPoint(cx, cy)
            print("EA combo (%d,%d) WindowFromPoint -> hwnd=%d (MT5=%d) %s" % (cx, cy, h, hwnd, "✓MT5" if h==hwnd else "还是被挡"))
    except Exception:
        pass
