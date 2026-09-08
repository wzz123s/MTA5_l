# -*- coding: utf-8 -*-
"""EXNESS 30m2H Tester: 选EA + 设日期/模式 + 点开始 + 等回测."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8')
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from collections import defaultdict
from pywinauto import Application
from pywinauto.keyboard import send_keys

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
BM_CLICK = 0x00F5
CB_SETCURSEL = 0x014E
MT5_HWND = 5114106

app = Application(backend="win32").connect(handle=MT5_HWND)
win = app.window(handle=MT5_HWND)
print("连接:", win.window_text()[:50])
user32.SetWindowPos(ctypes.c_void_p(MT5_HWND), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.4)
user32.SetForegroundWindow(MT5_HWND); time.sleep(0.6)
send_keys("^r"); time.sleep(4.0)
print("Ctrl+R 后")

def press(keys, n=1, gap=0.3):
    for _ in range(max(0, n)):
        send_keys(keys); time.sleep(gap)

def get_dtp_pair(mt5):
    groups = defaultdict(list)
    for c in mt5.descendants():
        try:
            if "SysDateTimePick32" in c.class_name():
                r = c.rectangle()
                if r.width() > 60:
                    groups[r.top].append((c, r))
        except Exception:
            pass
    for top, items in groups.items():
        if len(items) >= 2:
            items.sort(key=lambda x: x[1].left)
            return items[0][0], items[1][0]
    return None, None

def set_date(ctrl, ty, tm, td):
    try:
        txt = ctrl.window_text()
        cy, cm, cd = int(txt.split(".")[0]), int(txt.split(".")[1]), int(txt.split(".")[2])
    except Exception:
        return
    ctrl.set_focus(); time.sleep(0.5)
    press("{LEFT}", 2)
    press("{UP}" if ty > cy else "{DOWN}", abs(ty - cy))
    press("{RIGHT}", 1)
    press("{UP}" if tm > cm else "{DOWN}", abs(tm - cm))
    press("{RIGHT}", 1)
    press("{UP}" if td > cd else "{DOWN}", abs(td - cd))
    press("{ENTER}", 1)
    time.sleep(0.3)

# 找 EA combo
ea = None
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c; break
    except Exception:
        pass
if ea is None:
    print("无 EA combo"); sys.exit(1)
print("[EA] 当前:", ea.window_text()[:50])
if "30m2H_ABC_EA" not in ea.window_text():
    ea.click_input(); time.sleep(1.0)
    send_keys("30m2H_ABC_EA", with_spaces=True); time.sleep(1.0)
    send_keys("{ENTER}"); time.sleep(1.5)
    print("[EA] 选择后:", ea.window_text()[:50])

# 模式 -> 仅使用开价 (index 3)
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name() and c.window_text() in ("每次报价","仅使用开价","1分钟OHLC","每次基于实时点"):
            user32.SendMessageW(c.handle, CB_SETCURSEL, 3, 0); time.sleep(0.3)
            print("[模式] ->", c.window_text()[:20] if c.window_text() else "set")
    except Exception:
        pass

# 日期
start, stop = get_dtp_pair(win)
if start: set_date(start, 2025, 1, 1)
if stop: set_date(stop, 2026, 8, 14)
print("日期设置完")

# 点开始
start_hwnd = None
for c in win.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            start_hwnd = c.handle
    except Exception:
        pass
if not start_hwnd:
    print("无开始按钮"); sys.exit(1)
print("[开始] BM_CLICK")
user32.SendMessageW(start_hwnd, BM_CLICK, 0, 0)
time.sleep(5.0)

def btn_state():
    for c in win.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始","停止"):
                return c.window_text()
        except Exception:
            pass
    return None
st = btn_state()
print("点开始后按钮:", st)
start_t = time.time()
for i in range(20):
    time.sleep(15)
    st = btn_state()
    el = time.time() - start_t
    if st == "开始":
        print("t=%.0fs 回测完成" % el); break
    if i % 4 == 0:
        print("t=%.0fs 状态=%r" % (el, st))
else:
    print("超时")
print("最终:", btn_state())
