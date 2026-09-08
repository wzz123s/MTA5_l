# -*- coding: utf-8 -*-
"""枚举 z-order, 找 MT5 上面的窗口(可能拦截鼠标)."""
import ctypes, sys
sys.stdout.reconfigure(encoding='utf-8')
user32 = ctypes.windll.user32

GW_HWNDFIRST = 0
GW_HWNDNEXT = 2

# 找 MT5 XAUUSDm 窗口 hwnd
mt5_hwnd = None
from pywinauto import Desktop
d = Desktop(backend="win32")
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t and "[XAUUSDm" in t:
            mt5_hwnd = w.handle
    except Exception:
        pass
print("MT5 hwnd=%d" % mt5_hwnd)

# 从最顶层遍历 z-order
print("\n=== z-order (从顶到底) ===")
hwnd = user32.GetTopWindow(0)
i = 0
while hwnd and i < 40:
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    title = buf.value
    visible = user32.IsWindowVisible(hwnd)
    mark = " <== MT5" if hwnd == mt5_hwnd else ""
    if visible or title:
        print("  [%d] hwnd=%d visible=%d %r%s" % (i, hwnd, visible, title[:50], mark))
    hwnd = user32.GetWindow(hwnd, GW_HWNDNEXT)
    i += 1
