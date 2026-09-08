# -*- coding: utf-8 -*-
"""检查 + 恢复 MT5 窗口."""
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
SW_RESTORE = 9
d = Desktop(backend="win32")

print("=== Exness 窗口 ===")
target = None
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t:
            h = w.handle
            mini = w.is_minimized()
            vis = w.is_visible()
            r = w.rectangle()
            print("hwnd=%d mini=%s vis=%s rect=(%d,%d,%d,%d) %r" % (h, mini, vis, r.left, r.top, r.right, r.bottom, t[:60]))
            if not mini and vis:
                target = w
    except Exception:
        pass

if target is None:
    for w in d.windows():
        try:
            t = w.window_text()
            if t and "Exness" in t:
                target = w
                break
        except Exception:
            pass

if target:
    hwnd = target.handle
    user32.ShowWindow(hwnd, SW_RESTORE); time.sleep(1.0)
    user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    time.sleep(0.5)
    user32.SetForegroundWindow(hwnd); time.sleep(0.5)
    print("\n恢复 MT5 hwnd=%d" % hwnd)
