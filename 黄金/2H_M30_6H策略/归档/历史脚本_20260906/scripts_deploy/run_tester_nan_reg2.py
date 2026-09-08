# -*- coding: utf-8 -*-
"""打开 Tester + 检查配置 + 点开始 (重启后 .ini 含 InpNanRegOn=true)."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
BM_CLICK = 0x00F5
d = Desktop(backend="win32")

mt5 = None
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t and not w.is_minimized():
            mt5 = w
            break
    except Exception:
        pass
if mt5 is None:
    # 兜底 hwnd=726044
    for w in d.windows():
        if w.handle == 726044:
            mt5 = w
if mt5 is None:
    print("FAIL 无 MT5 窗口"); sys.exit(1)

hwnd = mt5.handle
print("MT5 hwnd=%d 标题=%r" % (hwnd, mt5.window_text()[:55]))
user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.5)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)

# Ctrl+R 打开 Tester
send_keys("^r"); time.sleep(3.0)
print("已发送 Ctrl+R")

# 检查 Tester 配置
print("\n=== Tester 配置 ===")
for c in mt5.descendants():
    try:
        cls = c.class_name()
        txt = c.window_text()
        if "ComboBox" in cls and txt and any(k in txt for k in ["Advisors", "XAUUSDm", "M30", "H4", "仅使用开价", "每次报价"]):
            print("  Combo %r" % txt[:45])
        if "SysDateTimePick32" in cls:
            print("  日期 %r" % txt)
        if "Button" in cls and txt in ("开始","停止"):
            print("  按钮 %r" % txt)
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
print("\n[开始] BM_CLICK")
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
