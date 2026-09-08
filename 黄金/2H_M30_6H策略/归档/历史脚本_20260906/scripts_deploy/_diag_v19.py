# -*- coding: utf-8 -*-
"""v19: 干净测试日期止设置 + DTM_GETSYSTEMTIME 读回"""
import sys, ctypes, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from ctypes import wintypes

DTM_GETSYSTEMTIME = 0x1001
DTM_SETSYSTEMTIME = 0x1002
GDT_VALID = 0
SW_RESTORE = 9
SW_SHOW = 5

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

def ensure_foreground(mt5):
    if mt5.is_minimized():
        ctypes.windll.user32.ShowWindow(mt5.handle, SW_RESTORE)
        time.sleep(0.8)
    # 置前
    ctypes.windll.user32.SetForegroundWindow(mt5.handle)
    time.sleep(0.5)

def get_dtp(mt5, text):
    for c in mt5.descendants():
        try:
            if "DateTimePick" in c.class_name() and c.window_text() == text:
                return c
        except Exception:
            pass
    return None

def read_dtp(hwnd):
    st = SYSTEMTIME()
    r = ctypes.windll.user32.SendMessageW(hwnd, DTM_GETSYSTEMTIME, 0, ctypes.byref(st))
    if r == GDT_VALID:
        return "%04d.%02d.%02d" % (st.wYear, st.wMonth, st.wDay)
    return "GET失败(r=%d)" % r

mt5 = find_mt5()
if mt5 is None:
    print("FAIL"); sys.exit(1)

ensure_foreground(mt5)

# 读所有 DTP 的 hwnd + 值
print("=== 当前 DTP ===")
dtps = []
for c in mt5.descendants():
    try:
        if "DateTimePick" in c.class_name():
            r = c.rectangle()
            hwnd = c.handle
            val = read_dtp(hwnd)
            print("  hwnd=%d text=%r get=%s rect.top=%d" % (hwnd, c.window_text(), val, r.top))
            dtps.append((c, r))
    except Exception:
        pass

# 日期止 = y 较大的那个（同一行的第二个），找到 hwnd
# 从之前布局：日期起(439,1094) 日期止(594,1094)，两个 top 相同，x 不同
dtps.sort(key=lambda x: (x[1].top, x[1].left))
for c, r in dtps:
    print("  sorted: text=%r left=%d top=%d hwnd=%d" % (c.window_text(), r.left, r.top, c.handle))

# 找到日期止（x 较大的那个，即日期起右边）
if len(dtps) >= 2:
    # 同一行 top 接近的两个
    row = [x for x in dtps if abs(x[1].top - dtps[0][1].top) < 20]
    row.sort(key=lambda x: x[1].left)
    if len(row) >= 2:
        dtp_stop = row[-1][0]  # 日期止 = 最右
        print("\n目标日期止 hwnd=%d 当前get=%s" % (dtp_stop.handle, read_dtp(dtp_stop.handle)))
        st = SYSTEMTIME()
        st.wYear, st.wMonth, st.wDay, st.wDayOfWeek = 2026, 8, 14, 0
        r_set = ctypes.windll.user32.SendMessageW(dtp_stop.handle, DTM_SETSYSTEMTIME, GDT_VALID, ctypes.byref(st))
        time.sleep(0.3)
        print("SET 2026.08.14 返回=%d, 读回=%s" % (r_set, read_dtp(dtp_stop.handle)))
