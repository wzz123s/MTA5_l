# -*- coding: utf-8 -*-
"""乖离反转 Tester 全窗回放跑批 (v9 口径回放台账)
用法: python run_tester_bias_replay.py [--preflight]
--preflight: 只做 EA 切换 + 日期设置与校验, 不点开始.
"""
import ctypes, sys, time, os
sys.stdout.reconfigure(encoding="utf-8")
import argparse
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from collections import defaultdict
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

OUT = r"F:\use_code\MTA5_l\黄金\乖离反转策略\scripts\deploy"
AP = argparse.ArgumentParser()
AP.add_argument("--preflight", action="store_true")
AP.add_argument("--start-year", type=int, default=2015)
AP.add_argument("--start-month", type=int, default=1)
AP.add_argument("--start-day", type=int, default=1)
AP.add_argument("--stop-year", type=int, default=2026)
AP.add_argument("--stop-month", type=int, default=8)
AP.add_argument("--stop-day", type=int, default=21)
AP.add_argument("--ea", default="BiasReversal_Combo_EA")
args = AP.parse_args()

user32 = ctypes.windll.user32
BM_CLICK = 0x00F5

d = Desktop(backend="win32")
win = None
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t:
            win = w
            break
    except Exception:
        pass
if win is None:
    print("FAIL MT5")
    sys.exit(1)
hwnd = win.handle
print("hwnd", hwnd)
user32.ShowWindow(hwnd, 9); time.sleep(1.0)
user32.SetWindowPos(ctypes.c_void_p(hwnd), ctypes.c_void_p(0), 0, 0, 1700, 950, 0x0040)
time.sleep(0.4)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)
send_keys("^r"); time.sleep(3.5)

# ---- EA combo select ----
def combos():
    out = []
    for c in win.descendants():
        try:
            if "ComboBox" in c.class_name():
                out.append(c)
        except Exception:
            pass
    return out

ea = None
for c in combos():
    try:
        txt = c.window_text() or ""
        if "Advisors" in txt or "Experts" in txt:
            ea = c
            break
    except Exception:
        pass
if ea is None:
    print("FAIL EA combo"); sys.exit(1)
etxt = ea.window_text()
print("[EA before]", repr(etxt[:70]))
if args.ea not in etxt:
    # 展开下拉树 -> 点击树聚焦 -> 逐字符 type-ahead -> Enter (历史 2H/30m2H 同款)
    ea.click_input(); time.sleep(1.5)
    for c in win.descendants():
        try:
            if "SysTreeView32" in c.class_name() and c.is_visible():
                rr = c.rectangle()
                c.click_input(coords=(int(rr.width() * 0.3), int(rr.height() * 0.15)))
                time.sleep(0.6)
                print("tree focused")
                break
        except Exception:
            pass
    for ch in args.ea:
        send_keys(ch); time.sleep(0.15)
    time.sleep(1.2)
    send_keys("{ENTER}"); time.sleep(1.5)
print("[EA after ]", repr((ea.window_text() or "")[:70]))
if args.ea not in (ea.window_text() or ""):
    print("FAIL EA switch to", args.ea)
    sys.exit(1)

# ---- date pickers ----
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
            out.append((items[0][0], items[1][0], top))
    return out

def cur(ctrl):
    try:
        return ctrl.window_text()
    except Exception:
        return ""

def fix_seg(ctrl, field, want):
    keys_map = {"year": 0, "month": 1, "day": 2}
    fi = keys_map[field]
    want = int(want)
    for _ in range(90):
        txt = cur(ctrl)
        try:
            parts = txt.split(".")
            v = int(parts[fi])
        except Exception:
            return False
        if v == want:
            return True
        ctrl.set_focus(); time.sleep(0.3)
        if fi == 0:
            send_keys("{LEFT 2}"); time.sleep(0.25)
        elif fi == 2:
            send_keys("{RIGHT 1}"); time.sleep(0.25)
        send_keys("{UP}" if want > v else "{DOWN}")
        time.sleep(0.4)
    return False

def fix_date(ctrl, ty, tm, td):
    ok1 = fix_seg(ctrl, "year", ty)
    ok2 = fix_seg(ctrl, "month", tm)
    ok3 = fix_seg(ctrl, "day", td)
    return ok1 and ok2 and ok3

pairs = dtp_pairs(win)
print("dtp pairs:", len(pairs))
for p in pairs:
    print("  pair@top", p[2], "left=", cur(p[0]), "right=", cur(p[1]))
if not pairs:
    print("FAIL no dtp pairs"); sys.exit(1)
# choose main pair: the one whose left year >= right year-20 kind-of; simply first pair whose texts look like years
main = None
for p in pairs:
    lt, rt = cur(p[0]), cur(p[1])
    try:
        ly = int(lt.split(".")[0]); ry = int(rt.split(".")[0])
        if 1990 < ly < ry < 2040:
            main = p
            break
    except Exception:
        continue
if main is None:
    main = pairs[0]
print("choose main: left=", cur(main[0]), "right=", cur(main[1]))
ok_start = fix_date(main[0], args.start_year, args.start_month, args.start_day)
ok_stop = fix_date(main[1], args.stop_year, args.stop_month, args.stop_day)
print("after fix: start=", cur(main[0]), "| stop=", cur(main[1]), "| ok:", ok_start, ok_stop)
if not (ok_start and ok_stop):
    print("FAIL date set"); sys.exit(1)

if args.preflight:
    print("PREFLIGHT OK - not starting")
    sys.exit(0)

# ---- start & wait ----
def start_button():
    for c in win.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始", "停止"):
                return c
        except Exception:
            pass
    return None

sb = None
for c in win.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            sb = c.handle
    except Exception:
        pass
if not sb:
    print("FAIL 开始 button"); sys.exit(1)
user32.SendMessageW(sb, BM_CLICK, 0, 0)
time.sleep(5.0)
print("started:", start_button().window_text() if start_button() else "?")
t0 = time.time()
cap = 150  # 150 * 20s = 50 min
for i in range(cap):
    time.sleep(20)
    b = start_button()
    if b is not None and b.window_text() == "开始":
        print("done t=%.0fs" % (time.time() - t0))
        break
    if i % 6 == 0:
        print("t=%.0fs %s" % (time.time() - t0, b.window_text() if b else "?"))
else:
    print("timeout waiting")
print("final button:", start_button().window_text() if start_button() else "?")