# -*- coding: utf-8 -*-
"""展开树 + 等待加载 + 键盘导航选择 ABC EA."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
d = Desktop(backend="win32")
MT5_HWND = 17306644

mt5 = None
for w in d.windows():
    if w.handle == MT5_HWND:
        mt5 = w
hwnd = mt5.handle
user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.4)
user32.SetForegroundWindow(hwnd); time.sleep(0.4)

ea = None
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c
    except Exception:
        pass

print("[EA] 设置前:", ea.window_text()[:50])
ea.click_input(); time.sleep(1.5)  # 展开 + 等待加载

# 检查焦点
fg = user32.GetFocus()
print("GetFocus hwnd=%d" % fg)

# 键盘导航: HOME 到顶, 逐字符输入筛选
send_keys("{HOME}"); time.sleep(0.5)
for ch in "2H_M30_6H_ABC_EA":
    send_keys(ch); time.sleep(0.15)
time.sleep(0.8)
send_keys("{ENTER}"); time.sleep(0.8)
print("[EA] 设置后:", ea.window_text()[:50])

# 如果没变, 尝试方向键导航
if "ABC" not in ea.window_text():
    print("[EA] 字符输入无效, 尝试方向键导航...")
    ea.click_input(); time.sleep(1.0)
    send_keys("{HOME}"); time.sleep(0.4)
    # 向下导航找 ABC (在 Advisors 下, 2H_M30_6H_ABC 在 2H_M30_6H_CurrentCandidate 之前)
    for i in range(30):
        send_keys("{DOWN}"); time.sleep(0.08)
    # 这不对, 直接逐字符
    send_keys("{ENTER}"); time.sleep(0.5)
    print("[EA] 方向键后:", ea.window_text()[:50])
