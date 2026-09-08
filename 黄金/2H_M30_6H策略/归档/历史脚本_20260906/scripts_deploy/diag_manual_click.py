# -*- coding: utf-8 -*-
"""手动 SetCursorPos + mouse_event 点击 EA combo, 检查是否展开."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
CB_GETCOUNT = 0x0146
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
hwnd = mt5.handle
user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.5)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)

for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            r = c.rectangle()
            # 点击右边缘(下拉箭头区) rel_x=0.97
            cx = int(r.left + r.width() * 0.97)
            cy = int(r.top + r.height() * 0.5)
            print("点击 EA combo 右边缘 (%d,%d)" % (cx, cy))
            # SetCursorPos
            user32.SetCursorPos(cx, cy)
            time.sleep(0.3)
            # 读回
            pt = ctypes.wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            print("GetCursorPos 读回: (%d,%d)" % (pt.x, pt.y))
            # mouse_event 点击
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.1)
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(1.0)
            # 检查 CB_GETCOUNT + 枚举新顶层窗口
            n = user32.SendMessageW(c.handle, CB_GETCOUNT, 0, 0)
            print("点击后 CB_GETCOUNT=%d" % n)
            # 枚举新出现的可见窗口
            print("=== 当前可见顶层窗口(可能含展开的树) ===")
            for w in d.windows():
                try:
                    t = w.window_text()
                    if t and w.is_visible():
                        rr = w.rectangle()
                        print("  %r rect=(%d,%d,%d,%d)" % (t[:50], rr.left, rr.top, rr.right, rr.bottom))
                except Exception:
                    pass
    except Exception as e:
        print("err:", e)
