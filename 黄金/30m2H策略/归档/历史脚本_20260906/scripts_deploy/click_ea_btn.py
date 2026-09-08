# -*- coding: utf-8 -*-
"""点击 EA combo 右侧按钮, 检查是否弹文件对话框."""
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
d = Desktop(backend="win32")

mt5 = None
for w in d.windows():
    try:
        if w.handle == 4654538:
            mt5 = w
    except Exception:
        pass
hwnd = mt5.handle
user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.4)
user32.SetForegroundWindow(hwnd); time.sleep(0.4)

# 找 EA combo 右侧的 Button (EA combo 的 rect 右边)
ea = None
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c
    except Exception:
        pass
if ea is None:
    print("无 EA"); sys.exit(1)
er = ea.rectangle()
print("EA combo rect:", er.left, er.top, er.right, er.bottom)

# 找 EA combo 附近的 Button (x 在 EA 右侧)
buttons = []
for c in mt5.descendants():
    try:
        if "Button" in c.class_name():
            r = c.rectangle()
            if abs(r.top - er.top) < 40 and r.left > er.left - 5 and r.right < er.right + 120:
                buttons.append((c, r))
    except Exception:
        pass
print("EA 附近 Button:", len(buttons))
for c, r in buttons[:6]:
    print("  Button @(%d,%d,%d,%d) txt=%r" % (r.left, r.top, r.right, r.bottom, c.window_text()))

# 点击每个按钮, 检查新窗口
for i, (c, r) in enumerate(buttons[:2]):
    print("\n点击 Button %d @(%d,%d)" % (i, (r.left+r.right)//2, (r.top+r.bottom)//2))
    try:
        c.click_input()
    except Exception as e:
        print("  click 异常:", e)
    time.sleep(1.0)
    # 检查顶层窗口变化 (文件对话框)
    for w in d.windows():
        try:
            t = w.window_text()
            if t and "打开" in t or ("EA" in t and w.is_visible() and w.handle != hwnd):
                print("  新窗口: %r hwnd=%d" % (t[:60], w.handle))
        except Exception:
            pass
