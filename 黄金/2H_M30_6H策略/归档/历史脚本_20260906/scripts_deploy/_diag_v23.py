# -*- coding: utf-8 -*-
"""v23: 前台状态下测试日期止 DTM 设置 + 读回"""
import sys, ctypes, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from ctypes import wintypes

DTM_GETSYSTEMTIME = 0x1001
DTM_SETSYSTEMTIME = 0x1002
GDT_VALID = 0
GDT_NONE = 1
SW_RESTORE = 9

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
    print("FAIL"); sys.exit(1)

if mt5.is_minimized():
    ctypes.windll.user32.ShowWindow(mt5.handle, SW_RESTORE)
    time.sleep(1.0)

ctypes.windll.user32.SetForegroundWindow(mt5.handle)
time.sleep(0.5)

# 找日期止 = 第二个 DTP (当前 '2026.09.01')
dtps = []
for c in mt5.descendants():
    try:
        if "DateTimePick" in c.class_name():
            r = c.rectangle()
            dtps.append((c, r))
    except Exception:
        pass

dtps.sort(key=lambda x: (x[1].top, x[1].left))
print("DTP 列表:")
for c, r in dtps:
    print("  text=%r hwnd=%d left=%d top=%d get=%s" % (c.window_text(), c.handle, r.left, r.top, read_dtp(c.handle)))

# 日期止 = 同一行 x 更大的那个
if len(dtps) >= 2:
    row = [x for x in dtps if abs(x[1].top - dtps[0][1].top) < 20]
    row.sort(key=lambda x: x[1].left)
    stop = row[-1][0]
    print("\n设置日期止 hwnd=%d 当前=%s" % (stop.handle, read_dtp(stop.handle)))
    st = SYSTEMTIME()
    st.wYear, st.wMonth, st.wDay, st.wDayOfWeek = 2026, 8, 14, 0
    r_set = ctypes.windll.user32.SendMessageW(stop.handle, DTM_SETSYSTEMTIME, GDT_VALID, ctypes.byref(st))
    time.sleep(0.5)
    print("SET 返回=%d (0=成功)" % r_set)
    print("读回=%s" % read_dtp(stop.handle))
    # 再读 window_text
    print("window_text=%r" % stop.window_text())
