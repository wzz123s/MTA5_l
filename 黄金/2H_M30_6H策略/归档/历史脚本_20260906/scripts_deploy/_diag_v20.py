# -*- coding: utf-8 -*-
"""v20: 稳健完整诊断，含窗口状态"""
import sys, ctypes, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from ctypes import wintypes

SW_RESTORE = 9
DTM_GETSYSTEMTIME = 0x1001
GDT_VALID = 0

class SYSTEMTIME(ctypes.Structure):
    _fields_ = [("wYear", wintypes.WORD), ("wMonth", wintypes.WORD), ("wDayOfWeek", wintypes.WORD),
                ("wDay", wintypes.WORD), ("wHour", wintypes.WORD), ("wMinute", wintypes.WORD),
                ("wSecond", wintypes.WORD), ("wMilliseconds", wintypes.WORD)]

def find_mt5():
    d = Desktop(backend="win32")
    for w in d.windows():
        try:
            t = w.window_text()
            if t and "Exness" in t and "[" in t:
                return w
        except Exception:
            pass
    return None

def read_dtp(hwnd):
    st = SYSTEMTIME()
    r = ctypes.windll.user32.SendMessageW(hwnd, DTM_GETSYSTEMTIME, 0, ctypes.byref(st))
    if r == GDT_VALID:
        return "%04d.%02d.%02d" % (st.wYear, st.wMonth, st.wDay)
    return "GETFAIL(r=%d)" % r

mt5 = find_mt5()
if mt5 is None:
    print("FAIL: MT5 not found"); sys.exit(1)

r = mt5.rectangle()
print("MT5 rect:", (r.left, r.top, r.right, r.bottom), "minimized:", mt5.is_minimized(), "visible:", mt5.is_visible())

if mt5.is_minimized():
    print("恢复窗口...")
    ctypes.windll.user32.ShowWindow(mt5.handle, SW_RESTORE)
    time.sleep(1.0)
    r = mt5.rectangle()
    print("恢复后 rect:", (r.left, r.top, r.right, r.bottom))

print()
print("=== DateTimePick ===")
for c in mt5.descendants():
    try:
        if "DateTimePick" in c.class_name():
            r = c.rectangle()
            print("  text=%r get=%s rect=(%d,%d)-(%d,%d) hwnd=%d" % (c.window_text(), read_dtp(c.handle), r.left, r.top, r.right, r.bottom, c.handle))
    except Exception as e:
        print("  DTP error:", e)

print()
print("=== 关键 ComboBox ===")
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name():
            txt = c.window_text()
            if txt and any(k in txt for k in ["Advisors", "XAUUSDm", "USOILm", "M30", "H4", "仅使用开价", "每次报价", "每次分时"]):
                r = c.rectangle()
                print("  text=%r rect=(%d,%d)-(%d,%d) hwnd=%d" % (txt, r.left, r.top, r.right, r.bottom, c.handle))
    except Exception:
        pass

print()
print("=== 开始按钮 ===")
for c in mt5.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            r = c.rectangle()
            print("  开始 rect=(%d,%d)-(%d,%d) hwnd=%d" % (r.left, r.top, r.right, r.bottom, c.handle))
    except Exception:
        pass
