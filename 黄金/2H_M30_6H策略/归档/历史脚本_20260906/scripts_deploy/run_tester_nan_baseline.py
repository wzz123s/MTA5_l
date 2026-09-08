# -*- coding: utf-8 -*-
"""v14: 用 hwnd=17306644 定位, 恢复+TOPMOST+EA设置+点开始."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from pywinauto.keyboard import send_keys
from collections import defaultdict

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
BM_CLICK = 0x00F5
CB_SETCURSEL = 0x014E
SW_RESTORE = 9
d = Desktop(backend="win32")

MT5_HWND = 17306644

# 定位 MT5 (用 hwnd)
mt5 = None
for w in d.windows():
    try:
        if w.handle == MT5_HWND:
            mt5 = w
    except Exception:
        pass
if mt5 is None:
    print("FAIL hwnd=%d 未找到" % MT5_HWND); sys.exit(1)

hwnd = mt5.handle
user32.ShowWindow(hwnd, SW_RESTORE); time.sleep(1.0)
user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.5)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)

print("MT5 hwnd=%d 标题=%r" % (hwnd, mt5.window_text()[:70]))
fg = user32.GetForegroundWindow()
print("前台 hwnd=%d (MT5=%d) %s" % (fg, hwnd, "✓" if fg==hwnd else "≠"))

# 检查 Tester 控件
ea_combo = None
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea_combo = c
            rr = c.rectangle(); cx, cy = (rr.left+rr.right)//2, (rr.top+rr.bottom)//2
            h = user32.WindowFromPoint(cx, cy)
            print("EA combo (%d,%d) WindowFromPoint=%d (MT5=%d) %s" % (cx, cy, h, hwnd, "✓" if h==hwnd else "≠被挡"))
    except Exception:
        pass

if ea_combo is None:
    print("FAIL 未找到 EA combo"); sys.exit(1)

# 模式
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and c.window_text() in ("每次报价","仅使用开价","1分钟OHLC","每次基于实时点"):
            user32.SendMessageW(c.handle, CB_SETCURSEL, 3, 0); time.sleep(0.3)
            print("[模式] 设置 仅使用开价")
    except Exception:
        pass

# EA
print("[EA] 设置前:", ea_combo.window_text()[:50])
ea_combo.click_input(); time.sleep(0.8)
send_keys("2H_M30_6H_ABC_EA", with_spaces=True); time.sleep(0.8)
send_keys("{ENTER}"); time.sleep(0.8)
print("[EA] 设置后:", ea_combo.window_text()[:50])

# 日期读回
for c in mt5.descendants():
    try:
        if "SysDateTimePick32" in c.class_name():
            print("[日期] %r" % c.window_text())
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
    print("FAIL 未找到开始按钮"); sys.exit(1)
print("[开始] BM_CLICK")
user32.SendMessageW(start_hwnd, BM_CLICK, 0, 0)
time.sleep(5.0)

def btn_state(mt5):
    for c in mt5.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始","停止"):
                return c.window_text()
        except Exception:
            pass
    return None
st = btn_state(mt5)
print("点开始后按钮:", st)
start_t = time.time()
for i in range(60):
    time.sleep(15)
    st = btn_state(mt5)
    elapsed = time.time() - start_t
    if st == "开始":
        print("t=%.0fs 回测完成" % elapsed); break
    if i % 4 == 0:
        print("t=%.0fs 状态=%r" % (elapsed, st))
else:
    print("超时 15 分钟")
print("最终按钮:", btn_state(mt5))
