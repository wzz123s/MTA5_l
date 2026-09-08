# -*- coding: utf-8 -*-
"""乖离反转 Tester 回放: 校验 EA/日期(不改) -> 点开始 -> 等到完成."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding="utf-8")
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from collections import defaultdict
from pywinauto import Desktop
from pywinauto.keyboard import send_keys
user32 = ctypes.windll.user32
BM_CLICK = 0x00F5

d = Desktop(backend="win32")
win = None
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t:
            win = w; break
    except Exception:
        pass
if win is None:
    print("FAIL MT5"); sys.exit(1)
hwnd = win.handle
user32.ShowWindow(hwnd, 9); time.sleep(1.0)
user32.SetWindowPos(ctypes.c_void_p(hwnd), ctypes.c_void_p(0), 0, 0, 1700, 950, 0x0040)
time.sleep(0.4)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)
send_keys("^r"); time.sleep(3.5)

def cur(ctrl):
    try:
        return ctrl.window_text()
    except Exception:
        return ""

ea_txt = ""
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name() and ("Advisors" in (c.window_text() or "") or "Experts" in (c.window_text() or "")):
            ea_txt = c.window_text()
            break
    except Exception:
        pass
print("EA:", repr(ea_txt[:70]))
if "BiasReversal_Combo_EA" not in ea_txt:
    print("FAIL EA not BiasReversal_Combo_EA"); sys.exit(1)

# dates (print only)
groups = defaultdict(list)
for c in win.descendants():
    try:
        if "SysDateTimePick32" in c.class_name():
            r = c.rectangle()
            if r.width() > 60:
                groups[r.top].append((c, r.left))
    except Exception:
        pass
for top, items in sorted(groups.items()):
    items.sort(key=lambda x: x[1])
    vals = [cur(c) for c, _ in items]
    print("date row top=%d: %s" % (top, vals))

# modeling combo (print only)
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name():
            t = (c.window_text() or "").strip()
            if t in ("每次报价", "仅使用开价", "1分钟OHLC"):
                print("model:", t)
                break
    except Exception:
        pass

start = None
for c in win.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            start = c.handle
    except Exception:
        pass
if start is None:
    print("FAIL start button"); sys.exit(1)

def btn_state():
    for c in win.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始", "停止"):
                return c.window_text()
        except Exception:
            pass
    return None

user32.SendMessageW(start, BM_CLICK, 0, 0)
time.sleep(6.0)
print("after click:", btn_state())
t0 = time.time()
for i in range(160):   # 160*20s ~ 53 min
    time.sleep(20)
    st = btn_state()
    if st == "开始":
        print("DONE elapsed=%.0fs state=%s" % (time.time() - t0, st))
        break
    if i % 6 == 0:
        print("t=%.0fs state=%s" % (time.time() - t0, st))
else:
    print("TIMEOUT")
print("final state:", btn_state())
