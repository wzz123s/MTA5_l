# -*- coding: utf-8 -*-
"""v11: click_input 展开 EA 目录树 + CB 枚举选择."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

BM_CLICK = 0x00F5
CB_GETCOUNT = 0x0146
CB_GETLBTEXT = 0x0148
CB_SETCURSEL = 0x014E
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
d = Desktop(backend="win32")
user32 = ctypes.windll.user32

def find_xau():
    for w in d.windows():
        try:
            t = w.window_text()
            if t and "Exness" in t and "[XAUUSDm" in t:
                return w
        except Exception:
            pass
    return None

mt5 = find_xau()
if mt5 is None:
    print("FAIL"); sys.exit(1)
hwnd = mt5.handle
user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.5)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)

ea_hwnd = None
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea_hwnd = c.handle
            r = c.rectangle()
            print("[EA] hwnd=%d rect=(%d,%d,%d,%d) 中心=(%d,%d)" % (ea_hwnd, r.left, r.top, r.right, r.bottom, (r.left+r.right)//2, (r.top+r.bottom)//2))
    except Exception:
        pass

print("[EA] click_input 前 项数=%d" % user32.SendMessageW(ea_hwnd, CB_GETCOUNT, 0, 0))

# click_input 点击 EA combo
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            c.click_input(); time.sleep(1.0)
            print("[EA] click_input 完成")
    except Exception as e:
        print("[EA] click_input 异常:", e)

print("[EA] click_input 后 项数=%d" % user32.SendMessageW(ea_hwnd, CB_GETCOUNT, 0, 0))
n = user32.SendMessageW(ea_hwnd, CB_GETCOUNT, 0, 0)
for i in range(min(n, 50)):
    buf = ctypes.create_unicode_buffer(512)
    user32.SendMessageW(ea_hwnd, CB_GETLBTEXT, i, ctypes.byref(buf))
    mark = " <== 目标" if "ABC_EA" in buf.value else ""
    print("    [%d] %s%s" % (i, buf.value, mark))

# 找 ABC 并选择
for i in range(n):
    buf = ctypes.create_unicode_buffer(512)
    user32.SendMessageW(ea_hwnd, CB_GETLBTEXT, i, ctypes.byref(buf))
    if "ABC_EA" in buf.value:
        user32.SendMessageW(ea_hwnd, CB_SETCURSEL, i, 0)
        time.sleep(0.5)
        print("[EA] 已选择索引 %d" % i)
        break

# 读回 EA 文本
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            print("[EA] 最终:", c.window_text()[:60])
    except Exception:
        pass

# 恢复非 TOPMOST
user32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
