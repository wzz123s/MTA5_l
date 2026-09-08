# -*- coding: utf-8 -*-
"""WindowFromPoint 检查 EA combo 中心坐标下是哪个窗口."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

user32 = ctypes.windll.user32
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
print("MT5 hwnd=%d" % mt5.handle)

# 找 EA combo 坐标
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            r = c.rectangle()
            cx, cy = (r.left + r.right) // 2, (r.top + r.bottom) // 2
            print("EA combo 中心屏幕坐标: (%d,%d)" % (cx, cy))
            # WindowFromPoint
            h = user32.WindowFromPoint(ctypes.c_long(cx), ctypes.c_long(cy))
            print("WindowFromPoint(%d,%d) -> hwnd=%d" % (cx, cy, h))
            # 该窗口标题
            ln = user32.GetWindowTextLengthW(h)
            buf = ctypes.create_unicode_buffer(ln + 1)
            user32.GetWindowTextW(h, buf, ln + 1)
            print("  窗口标题: %r" % buf.value)
            # 该窗口类名
            cls = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(h, cls, 256)
            print("  类名: %r" % cls.value)
            # 该窗口是否 MT5 或其子窗口
            if h == mt5.handle:
                print("  -> 就是 MT5 主窗口 ✓")
            else:
                parent = user32.GetAncestor(h, 2)  # GA_ROOT
                print("  -> 根窗口 hwnd=%d (MT5=%d) 匹配=%s" % (parent, mt5.handle, parent == mt5.handle))
    except Exception as e:
        print("err:", e)
