# -*- coding: utf-8 -*-
"""枚举 + 恢复所有 Exness 窗口."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8')
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from pywinauto import Desktop

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SW_RESTORE = 9
d = Desktop(backend="win32")

wins = []
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t:
            wins.append(w)
            print("hwnd=%d mini=%s vis=%s %r" % (w.handle, w.is_minimized(), w.is_visible(), t[:50]))
    except Exception:
        pass

if wins:
    # 恢复第一个非最小化的或最小化的
    target = None
    for w in wins:
        try:
            if not w.is_minimized() and w.is_visible():
                target = w
        except Exception:
            pass
    if target is None:
        target = wins[0]
    hwnd = target.handle
    user32.ShowWindow(hwnd, SW_RESTORE); time.sleep(1.0)
    user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
    time.sleep(0.5)
    user32.SetForegroundWindow(hwnd); time.sleep(0.5)
    print("\n恢复 hwnd=%d 标题=%r" % (hwnd, target.window_text()[:50]))
