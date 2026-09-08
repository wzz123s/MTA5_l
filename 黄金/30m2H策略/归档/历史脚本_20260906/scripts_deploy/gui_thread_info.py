# -*- coding: utf-8 -*-
"""GetGUIThreadInfo 检查 MT5 线程键盘焦点."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8')
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from pywinauto import Desktop

user32 = ctypes.windll.user32
d = Desktop(backend="win32")

class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("hwndActive", ctypes.c_void_p),
        ("hwndFocus", ctypes.c_void_p),
        ("hwndCapture", ctypes.c_void_p),
        ("hwndMenuOwner", ctypes.c_void_p),
        ("hwndMoveSize", ctypes.c_void_p),
        ("hwndCaret", ctypes.c_void_p),
    ]

mt5 = None
for w in d.windows():
    try:
        if w.handle == 4654538:
            mt5 = w
    except Exception:
        pass
hwnd = mt5.handle
tid = user32.GetWindowThreadProcessId(hwnd, None)
print("MT5 hwnd:", hwnd, "线程:", tid)

gui = GUITHREADINFO()
gui.cbSize = ctypes.sizeof(GUITHREADINFO)
ok = user32.GetGUIThreadInfo(tid, ctypes.byref(gui))
print("GetGUIThreadInfo:", ok)
print("  hwndActive:", gui.hwndActive)
print("  hwndFocus:", gui.hwndFocus)

# 判断 hwndFocus 属于哪个窗口
if gui.hwndFocus:
    ln = user32.GetWindowTextLengthW(gui.hwndFocus)
    buf = ctypes.create_unicode_buffer(ln+1)
    user32.GetWindowTextW(gui.hwndFocus, buf, ln+1)
    print("  焦点窗口标题:", buf.value[:60])
