# -*- coding: utf-8 -*-
"""EnumWindows 找 Exness + IsWindow + connect."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8')
user32 = ctypes.windll.user32

# EnumWindows 找 Exness 可见窗口
results = []
@ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
def cb(hwnd, lparam):
    ln = user32.GetWindowTextLengthW(hwnd)
    if ln > 0:
        buf = ctypes.create_unicode_buffer(ln+1)
        user32.GetWindowTextW(hwnd, buf, ln+1)
        t = buf.value
        if "Exness" in t:
            vis = user32.IsWindowVisible(hwnd)
            results.append((hwnd, vis, t[:60]))
    return True

user32.EnumWindows(cb, None)
print("Exness 窗口:")
for h, vis, t in results:
    print("  hwnd=%d vis=%s IsWindow=%s %r" % (h, vis, user32.IsWindow(h), t))

# 选第一个可见的
target = None
for h, vis, t in results:
    if vis:
        target = h
        break
if target is None and results:
    target = results[0][0]
if target:
    print("\n用 hwnd=%d connect" % target)
    from pywinauto import Application
    try:
        app = Application(backend="win32").connect(handle=target)
        win = app.window(handle=target)
        print("connect OK:", win.window_text()[:50])
    except Exception as e:
        print("connect 失败:", e)
