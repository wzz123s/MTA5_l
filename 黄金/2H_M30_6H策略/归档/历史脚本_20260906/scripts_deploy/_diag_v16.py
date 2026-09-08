# -*- coding: utf-8 -*-
"""v16: 检查 MT5 窗口 rect 和状态"""
import sys, ctypes
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

SW_RESTORE = 9
SW_SHOW = 5

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

mt5 = find_mt5()
if mt5 is None:
    print("FAIL: MT5 未找到"); sys.exit(1)

r = mt5.rectangle()
print("MT5 rect:", (r.left, r.top, r.right, r.bottom))
print("MT5 visible:", mt5.is_visible())
print("MT5 minimized:", mt5.is_minimized())
print("MT5 maximized:", mt5.is_maximized())
print("MT5 handle:", mt5.handle)

# 如果最小化或位置异常，恢复
if mt5.is_minimized() or r.left < -1000 or r.top < -1000:
    print("尝试恢复窗口...")
    ctypes.windll.user32.ShowWindow(mt5.handle, SW_RESTORE)
    import time
    time.sleep(0.5)
    r2 = mt5.rectangle()
    print("恢复后 rect:", (r2.left, r2.top, r2.right, r2.bottom))

# 打印 Tester 面板(策略测试)状态
for c in mt5.descendants():
    try:
        if c.window_text() == "策略测试" or "策略测试" in c.window_text():
            print("策略测试面板:", c.window_text(), "visible:", c.is_visible(), "rect:", c.rectangle())
    except Exception:
        pass
