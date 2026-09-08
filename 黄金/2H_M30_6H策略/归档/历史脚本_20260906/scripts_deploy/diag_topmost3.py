# -*- coding: utf-8 -*-
"""danger-full-access: 置顶 MT5 覆盖 Edge, 验证后设置 EA."""
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
kernel32 = ctypes.windll.kernel32
HWND_TOPMOST = -1
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

# TOPMOST
r = user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
err = kernel32.GetLastError()
print("SetWindowPos TOPMOST 返回=%d LastError=%d" % (r, err))
time.sleep(0.6)
user32.SetForegroundWindow(hwnd); time.sleep(0.6)

# 验证
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            rr = c.rectangle()
            cx, cy = (rr.left + rr.right)//2, (rr.top + rr.bottom)//2
            h = user32.WindowFromPoint(cx, cy)
            print("EA combo (%d,%d) -> hwnd=%d (MT5=%d) %s" % (cx, cy, h, hwnd, "✓MT5" if h==hwnd else "还是被挡"))
            if h == hwnd:
                # click_input 展开
                c.click_input(); time.sleep(1.0)
                n = user32.SendMessageW(c.handle, CB_GETCOUNT, 0, 0)
                print("click_input 后项数=%d" % n)
                for i in range(min(n, 50)):
                    buf = ctypes.create_unicode_buffer(512)
                    user32.SendMessageW(c.handle, CB_GETLBTEXT, i, ctypes.byref(buf))
                    print("    [%d] %s%s" % (i, buf.value, " <== 目标" if "ABC_EA" in buf.value else ""))
    except Exception as e:
        print("err:", e)
