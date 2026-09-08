# -*- coding: utf-8 -*-
"""切换周期触发 .ini 重载 + 点开始."""
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
BM_CLICK = 0x00F5
d = Desktop(backend="win32")

mt5 = None
for w in d.windows():
    if w.handle == 726084:
        mt5 = w
if mt5 is None:
    print("FAIL"); sys.exit(1)
hwnd = mt5.handle
user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.4)
user32.SetForegroundWindow(hwnd); time.sleep(0.4)

# 找周期 ComboBox (M30)
per = None
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and c.window_text() == "M30":
            per = c
    except Exception:
        pass
if per is None:
    print("FAIL 无周期 combo"); sys.exit(1)
print("周期 combo 当前:", per.window_text())

# 切换 H1 -> M30 触发 .ini 重载
try:
    per.select("H1"); time.sleep(1.0)
    print("切到 H1:", per.window_text())
except Exception as e:
    print("select H1 失败:", e)
try:
    per.select("M30"); time.sleep(1.5)
    print("切回 M30:", per.window_text())
except Exception as e:
    print("select M30 失败:", e)

# 确认 EA 还是 ABC
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            print("EA:", c.window_text()[:50])
    except Exception:
        pass

# 点开始
start_hwnd = None
for c in mt5.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            start_hwnd = c.handle
    except Exception:
        pass
if not start_hwnd:
    print("FAIL 无开始按钮"); sys.exit(1)
print("[开始] BM_CLICK")
user32.SendMessageW(start_hwnd, BM_CLICK, 0, 0)
time.sleep(5.0)

def btn_state():
    for c in mt5.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始","停止"):
                return c.window_text()
        except Exception:
            pass
    return None
st = btn_state()
print("点开始后按钮:", st)
start_t = time.time()
for i in range(60):
    time.sleep(15)
    st = btn_state()
    elapsed = time.time() - start_t
    if st == "开始":
        print("t=%.0fs 回测完成" % elapsed); break
    if i % 4 == 0:
        print("t=%.0fs 状态=%r" % (elapsed, st))
else:
    print("超时 15 分钟")
print("最终按钮:", btn_state())
