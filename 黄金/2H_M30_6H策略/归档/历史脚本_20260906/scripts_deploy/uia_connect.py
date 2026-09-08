# -*- coding: utf-8 -*-
"""win32 找 hwnd + UIA connect 探索 Tester 面板."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
from pywinauto import Desktop, Application

# 1) win32 找 MT5 hwnd
d32 = Desktop(backend="win32")
mt5_hwnd = None
for w in d32.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t and "[XAUUSDm" in t:
            mt5_hwnd = w.handle
            print("win32 MT5 hwnd:", mt5_hwnd, t[:50])
            break
    except Exception:
        pass
if mt5_hwnd is None:
    for w in d32.windows():
        try:
            t = w.window_text()
            if t and "Exness" in t:
                mt5_hwnd = w.handle
                print("win32 MT5 hwnd(fallback):", mt5_hwnd, t[:50])
                break
        except Exception:
            pass
if mt5_hwnd is None:
    print("FAIL 无 MT5"); sys.exit(1)

# 2) UIA connect
app = Application(backend="uia").connect(handle=mt5_hwnd)
print("UIA connect OK")
win = app.window()
print("UIA 窗口:", win.window_text()[:60])

# 3) 找策略测试面板
tester = None
for child in win.children():
    try:
        if "策略测试" in child.window_text():
            tester = child
            print("策略测试面板:", child.element_info.control_type)
            break
    except Exception:
        pass
if tester is None:
    print("需打开 Tester (Ctrl+R)")
    from pywinauto.keyboard import send_keys
    win.set_focus(); time.sleep(0.5)
    send_keys("^r"); time.sleep(2)
    for child in win.children():
        try:
            if "策略测试" in child.window_text():
                tester = child
                break
        except Exception:
            pass
if tester is None:
    print("无策略测试面板"); sys.exit(1)

# 4) 打印面板子控件 (找参数表格/Inp)
print("\n=== 策略测试面板子控件 ===")
for child in tester.children():
    try:
        t = child.window_text()
        ct = child.element_info.control_type
        if t:
            print("  [%s] %r" % (ct, t[:60]))
    except Exception:
        pass
