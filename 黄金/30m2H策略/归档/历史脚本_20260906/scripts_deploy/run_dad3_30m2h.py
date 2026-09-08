# -*- coding: utf-8 -*-
"""DAD3B8CC: 检查 EA + 设模式/日期 + 点开始."""
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
BM_CLICK = 0x00F5
CB_SETCURSEL = 0x014E
MT5_HWND = 4851420

app = Application(backend="win32").connect(handle=MT5_HWND)
win = app.window(handle=MT5_HWND)
user32.ShowWindow(MT5_HWND, 9); time.sleep(1.0)
user32.SetWindowPos(ctypes.c_void_p(MT5_HWND), ctypes.c_void_p(0), 0, 0, 1600, 900, 0x0040)
time.sleep(0.5)
user32.SetForegroundWindow(MT5_HWND); time.sleep(0.6)
send_keys("^r"); time.sleep(4.0)
print("Ctrl+R 后")

ea = None
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c; break
    except Exception:
        pass
if ea is None:
    print("无 EA"); sys.exit(1)
ea_txt = ea.window_text()
print("[EA] 当前:", ea_txt[:55])
if "30m2H_ABC_EA" not in ea_txt:
    print("EA 不是 30m2H_ABC_EA - 无法继续"); sys.exit(1)

def press(k, n=1, gap=0.3):
    for _ in range(max(0, n)):
        send_keys(k); time.sleep(gap)

def get_dtp_pair(m):
    groups = defaultdict(list)
    for c in m.descendants():
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
    press("{LEFT}", 2); press("{UP}" if ty>cy else "{DOWN}", abs(ty-cy))
    press("{RIGHT}", 1); press("{UP}" if tm>cm else "{DOWN}", abs(tm-cm))
    press("{RIGHT}", 1); press("{UP}" if td>cd else "{DOWN}", abs(td-cd))
    press("{ENTER}", 1); time.sleep(0.3)

# 模式
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name() and c.window_text() in ("每次报价","仅使用开价","1分钟OHLC"):
            user32.SendMessageW(c.handle, CB_SETCURSEL, 3, 0); time.sleep(0.3)
            print("[模式] set")
    except Exception:
        pass

# 日期读回 (先看当前值)
for c in win.descendants():
    try:
        if "SysDateTimePick32" in c.class_name():
            r = c.rectangle()
            if r.width() > 60:
                print("  日期当前:", c.window_text())
    except Exception:
        pass

start, stop = get_dtp_pair(win)
if start: set_date(start, 2025, 1, 1)
if stop: set_date(stop, 2026, 8, 25)
print("日期设置完")

sh = None
for c in win.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            sh = c.handle
    except Exception:
        pass
if not sh:
    print("无开始"); sys.exit(1)
print("[开始] BM_CLICK")
user32.SendMessageW(sh, BM_CLICK, 0, 0)
time.sleep(5.0)

def bs():
    for c in win.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始","停止"):
                return c.window_text()
        except Exception:
            pass
    return None
st = bs()
print("开始后:", st)
t0 = time.time()
for i in range(20):
    time.sleep(15)
    st = bs()
    if st == "开始":
        print("t=%.0fs 完成" % (time.time()-t0)); break
    if i % 4 == 0:
        print("t=%.0fs %r" % (time.time()-t0, st))
else:
    print("超时")
print("最终:", bs())
