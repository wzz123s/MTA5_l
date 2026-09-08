# -*- coding: utf-8 -*-
"""v14: 用 DTM_SETSYSTEMTIME 设置日期止 2026.08.14"""
import sys, ctypes, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from ctypes import wintypes

DTM_SETSYSTEMTIME = 0x1002
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

def get_dtp(mt5, text):
    for c in mt5.descendants():
        try:
            if "DateTimePick" in c.class_name() and c.window_text() == text:
                return c
        except Exception:
            pass
    return None

mt5 = find_mt5()
if mt5 is None:
    print("FAIL"); sys.exit(1)

# 日期止: 当前 '2008.04.26'
dtp = get_dtp(mt5, "2008.04.26")
if dtp is None:
    # 也可能还是别的值，打印所有
    print("未找到 2008.04.26, 现有:")
    for c in mt5.descendants():
        try:
            if "DateTimePick" in c.class_name():
                print("  ", c.window_text())
        except Exception:
            pass
    sys.exit(1)

print("找到日期止控件, handle=%d" % dtp.handle)
st = SYSTEMTIME()
st.wYear, st.wMonth, st.wDay, st.wDayOfWeek = 2026, 8, 14, 0
st.wHour = st.wMinute = st.wSecond = st.wMilliseconds = 0

r = ctypes.windll.user32.SendMessageW(dtp.handle, DTM_SETSYSTEMTIME, GDT_VALID, ctypes.byref(st))
print("SendMessage DTM_SETSYSTEMTIME 返回值:", r)

time.sleep(0.5)

# 读回验证
dtp2 = get_dtp(mt5, "2026.08.14")
print("读回验证:", "成功 2026.08.14" if dtp2 else "失败")

# 打印所有 DateTime 当前值
print("=== 当前 DateTime ===")
for c in mt5.descendants():
    try:
        if "DateTimePick" in c.class_name():
            print("  ", c.window_text())
    except Exception:
        pass
