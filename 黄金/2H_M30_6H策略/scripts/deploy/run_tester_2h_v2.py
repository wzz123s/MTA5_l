# -*- coding: utf-8 -*-
"""2H 复测 v2: 自校正日期(每按一次读回校验) + 点开始 + 等完成."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8')
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from collections import defaultdict
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
BM_CLICK = 0x00F5
CB_SETCURSEL = 0x014E

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
print("hwnd", hwnd)
user32.ShowWindow(hwnd, 9); time.sleep(1.0)
user32.SetWindowPos(ctypes.c_void_p(hwnd), ctypes.c_void_p(0), 0, 0, 1600, 900, 0x0040)
time.sleep(0.4)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)
send_keys("^r"); time.sleep(3.5)

ea = None
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c; break
    except Exception:
        pass
if ea is None:
    print("FAIL EA combo"); sys.exit(1)
etxt = ea.window_text()
print("[EA]", etxt[:60])
if "2H_M30_6H_ABC_EA" not in etxt:
    print("EA 不是 2H - 中止"); sys.exit(1)

# 模式
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name() and c.window_text() in ("每次报价", "仅使用开价", "1分钟OHLC"):
            user32.SendMessageW(c.handle, CB_SETCURSEL, 3, 0); time.sleep(0.3)
            break
    except Exception:
        pass

def dtp_pairs(m):
    groups = defaultdict(list)
    for c in m.descendants():
        try:
            if "SysDateTimePick32" in c.class_name():
                r = c.rectangle()
                if r.width() > 60:
                    groups[r.top].append((c, r))
        except Exception:
            pass
    out = []
    for top, items in groups.items():
        if len(items) >= 2:
            items.sort(key=lambda x: x[1].left)
            out.append((items[0][0], items[1][0]))
    return out

def cur(ctrl):
    try:
        return ctrl.window_text()
    except Exception:
        return ""

def fix_seg(ctrl, field, want):
    """field: 0=year 1=month 2=day. 逐次按键并读回校验."""
    keys_map = {"year": 0, "month": 1, "day": 2}
    fi = keys_map[field]
    want = int(want)
    for _ in range(80):
        txt = cur(ctrl)
        try:
            parts = txt.split(".")
            v = int(parts[fi])
        except Exception:
            return False
        if v == want:
            return True
        # focus the segment: click position by offsets
        ctrl.set_focus(); time.sleep(0.35)
        if fi == 0:
            send_keys("{LEFT 2}"); time.sleep(0.35)
        elif fi == 2:
            send_keys("{RIGHT 1}"); time.sleep(0.35)
        send_keys("{UP}" if want > v else "{DOWN}")
        time.sleep(0.45)
    return False

def fix_date(ctrl, ty, tm, td):
    ok = fix_seg(ctrl, "year", ty)
    ok = fix_seg(ctrl, "month", tm) and ok
    ok = fix_seg(ctrl, "day", td) and ok
    return ok and cur(ctrl).startswith("%d.%02d.%02d" % (ty, tm, td)) or ok and cur(ctrl)

pairs = dtp_pairs(win)
print("pairs:", len(pairs))
if not pairs:
    print("FAIL no dtp pairs"); sys.exit(1)
start, stop = pairs[0]
print("start now:", cur(start), "| stop now:", cur(stop))
ok1 = fix_date(start, 2025, 1, 1)
ok2 = fix_date(stop, 2026, 9, 4)
print("after fix start:", cur(start), "| stop:", cur(stop), "| ok:", ok1, ok2)

sh = None
for c in win.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            sh = c.handle
    except Exception:
        pass
if not sh:
    print("FAIL 开始按钮"); sys.exit(1)
user32.SendMessageW(sh, BM_CLICK, 0, 0)
time.sleep(4.0)

def bs():
    for c in win.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始", "停止"):
                return c.window_text()
        except Exception:
            pass
    return None

st = bs(); print("started:", st)
t0 = time.time()
for i in range(60):
    time.sleep(15)
    st = bs()
    if st == "开始":
        print("done t=%.0fs" % (time.time() - t0)); break
    if i % 4 == 0:
        print("t=%.0fs %r" % (time.time() - t0, st))
else:
    print("timeout")
print("final:", bs())
