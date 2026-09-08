# -*- coding: utf-8 -*-
"""恢复 + 移动 MT5 窗口到主屏幕."""
import sys, time, ctypes
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

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

w = find_xau()
if w is None:
    print("FAIL"); sys.exit(1)
hwnd = w.handle
SW_RESTORE = 9
SWP_SHOWWINDOW = 0x0040

# 1) 恢复
ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
time.sleep(1.5)

# 2) 移到 (0,0)
ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 1600, 900, SWP_SHOWWINDOW)
time.sleep(1.0)

# 3) 读回状态
w2 = find_xau()
r2 = w2.rectangle()
print("恢复+移动后 rect: (%d,%d,%d,%d) 尺寸 %dx%d" % (r2.left, r2.top, r2.right, r2.bottom, r2.width(), r2.height()))
print("is_maximized:", w2.is_maximized(), " is_minimized:", w2.is_minimized())
