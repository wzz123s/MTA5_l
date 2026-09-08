# -*- coding: utf-8 -*-
"""正确 ctypes 签名置顶 MT5, 验证后设置 EA/点开始."""
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
# 正确签名
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user32.SetWindowPos.restype = ctypes.c_int
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
BM_CLICK = 0x00F5
CB_GETCOUNT = 0x0146
CB_GETLBTEXT = 0x0148
CB_SETCURSEL = 0x014E
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

def press(keys, n=1, gap=0.3):
    for _ in range(max(0, n)):
        send_keys(keys)
        time.sleep(gap)

def set_date(ctrl, ty, tm, td):
    txt = ctrl.window_text()
    cy, cm, cd = int(txt.split(".")[0]), int(txt.split(".")[1]), int(txt.split(".")[2])
    ctrl.set_focus(); time.sleep(0.6)
    press("{LEFT}", 2); press("{UP}" if ty>cy else "{DOWN}", abs(ty-cy))
    press("{RIGHT}", 1); press("{UP}" if tm>cm else "{DOWN}", abs(tm-cm))
    press("{RIGHT}", 1); press("{UP}" if td>cd else "{DOWN}", abs(td-cd))
    press("{ENTER}", 1)
    print("  日期结果: %r" % ctrl.window_text())

def get_dtp_pair(mt5):
    groups = defaultdict(list)
    for c in mt5.descendants():
        try:
            if "SysDateTimePick32" in c.class_name():
                r = c.rectangle(); groups[r.top].append((c, r))
        except Exception:
            pass
    for top, items in groups.items():
        if len(items) >= 2:
            items.sort(key=lambda x: x[1].left); return items[0][0], items[1][0]
    return None, None

mt5 = find_xau()
if mt5 is None:
    print("FAIL"); sys.exit(1)
hwnd = mt5.handle

# TOPMOST (正确签名)
r = user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
print("SetWindowPos TOPMOST 返回=%d" % r)
time.sleep(0.6)
user32.SetForegroundWindow(hwnd); time.sleep(0.6)

# 验证 WindowFromPoint
ea_ok = False
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            rr = c.rectangle(); cx, cy = (rr.left+rr.right)//2, (rr.top+rr.bottom)//2
            h = user32.WindowFromPoint(cx, cy)
            print("EA combo (%d,%d) -> hwnd=%d (MT5=%d) %s" % (cx, cy, h, hwnd, "✓MT5" if h==hwnd else "还是被挡"))
            ea_ok = (h == hwnd)
    except Exception:
        pass

if ea_ok:
    # 模式
    for c in mt5.descendants():
        try:
            if "ComboBox" in c.class_name() and c.window_text() in ("每次报价","仅使用开价","1分钟OHLC","每次基于实时点"):
                user32.SendMessageW(c.handle, CB_SETCURSEL, 3, 0); time.sleep(0.3)
                print("[模式] 设置 仅使用开价")
        except Exception:
            pass
    # EA: click_input 展开 + 选择
    for c in mt5.descendants():
        try:
            if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
                print("[EA] 当前:", c.window_text()[:50])
                c.click_input(); time.sleep(1.0)
                n = user32.SendMessageW(c.handle, CB_GETCOUNT, 0, 0)
                print("[EA] 展开后项数=%d" % n)
                for i in range(min(n,50)):
                    buf = ctypes.create_unicode_buffer(512)
                    user32.SendMessageW(c.handle, CB_GETLBTEXT, i, ctypes.byref(buf))
                    if "ABC_EA" in buf.value:
                        user32.SendMessageW(c.handle, CB_SETCURSEL, i, 0); time.sleep(0.4)
                        print("[EA] 选中索引 %d" % i)
                send_keys("{ENTER}"); time.sleep(0.5)
                print("[EA] 最终:", c.window_text()[:60])
        except Exception as e:
            print("[EA] 异常:", e)
    # 日期
    start, stop = get_dtp_pair(mt5)
    if start: set_date(start, 2025, 1, 1)
    if stop: set_date(stop, 2026, 8, 14)
    # 点开始
    start_hwnd = None
    for c in mt5.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() == "开始":
                start_hwnd = c.handle
        except Exception:
            pass
    if start_hwnd:
        print("[开始] BM_CLICK")
        user32.SendMessageW(start_hwnd, BM_CLICK, 0, 0)
        time.sleep(5.0)
        for c in mt5.descendants():
            try:
                if "Button" in c.class_name() and c.window_text() in ("开始","停止"):
                    print("按钮状态:", c.window_text())
            except Exception:
                pass
else:
    print("EA 仍被遮挡, 无法自动点击")
