# -*- coding: utf-8 -*-
"""恢复原油实例 + 检查 Tester 状态(EA/日期/模式/参数区)."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SW_RESTORE = 9
d = Desktop(backend="win32")

# 找原油实例 (hwnd=726084)
mt5 = None
for w in d.windows():
    if w.handle == 726084:
        mt5 = w
if mt5 is None:
    # 兜底: 找任何可见的 Exness 窗口
    for w in d.windows():
        try:
            t = w.window_text()
            if t and "Exness" in t and not w.is_minimized():
                mt5 = w
        except Exception:
            pass
if mt5 is None:
    print("FAIL 无 MT5 窗口"); sys.exit(1)

hwnd = mt5.handle
print("MT5 hwnd=%d 标题=%r" % (hwnd, mt5.window_text()[:60]))
user32.ShowWindow(hwnd, SW_RESTORE); time.sleep(1.0)
user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.4)
user32.SetForegroundWindow(hwnd); time.sleep(0.4)

# 检查 Tester 关键控件
print("\n=== Tester 关键控件 ===")
for c in mt5.descendants():
    try:
        cls = c.class_name()
        txt = c.window_text()
        if "ComboBox" in cls and txt and any(k in txt for k in ["Advisors", "XAUUSDm", "USOILm", "M30", "H4", "仅使用开价", "每次报价"]):
            print("  Combo %r" % txt[:50])
        if "SysDateTimePick32" in cls:
            print("  日期 %r" % txt)
        if "Button" in cls and txt in ("开始","停止","加载","保存"):
            print("  按钮 %r" % txt)
    except Exception:
        pass

# 找"输入参数"/"设置"相关的页签和参数表格
print("\n=== 参数区域相关控件 ===")
for c in mt5.descendants():
    try:
        cls = c.class_name()
        txt = c.window_text()
        if any(k in txt for k in ["输入", "设置", "参数", "InpNan", "InpMax", "InpRisk", "InpStop"]):
            print("  [%s] %r" % (cls[:20], txt[:60]))
    except Exception:
        pass
