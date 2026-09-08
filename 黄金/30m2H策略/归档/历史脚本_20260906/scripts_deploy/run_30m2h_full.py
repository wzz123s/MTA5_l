# -*- coding: utf-8 -*-
"""30m2H Tester 完整流程: 找 MT5 -> Ctrl+R -> 选EA -> 点开始 -> 等回测."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8')
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from pywinauto import Application
from pywinauto.keyboard import send_keys

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
BM_CLICK = 0x00F5

# 找 MT5 窗口
def find_mt5():
    hwnds = []
    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, lp):
        ln = user32.GetWindowTextLengthW(h)
        if ln > 0:
            buf = ctypes.create_unicode_buffer(ln+1)
            user32.GetWindowTextW(h, buf, ln+1)
            t = buf.value
            if ("Exness" in t or "MT5Trial" in t) and user32.IsWindowVisible(h):
                hwnds.append(h)
        return True
    user32.EnumWindows(cb, None)
    return hwnds

found = find_mt5()
print("MT5 窗口:", found)
if not found:
    print("FAIL 无 MT5"); sys.exit(1)
MT5_HWND = found[0]

app = Application(backend="win32").connect(handle=MT5_HWND)
win = app.window(handle=MT5_HWND)
print("连接:", win.window_text()[:50])
user32.SetWindowPos(ctypes.c_void_p(MT5_HWND), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.4)
user32.SetForegroundWindow(MT5_HWND); time.sleep(0.6)

# Ctrl+R 打开 Tester
send_keys("^r"); time.sleep(4.0)
print("Ctrl+R 后")

# 找 EA combo
ea = None
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c
            break
    except Exception:
        pass
if ea is None:
    print("无 EA combo"); sys.exit(1)
print("[EA] 当前:", ea.window_text()[:50])

if "30m2H_ABC_EA" not in ea.window_text():
    # 选 30m2H_ABC_EA
    ea.click_input(); time.sleep(1.2)
    for ch in "30m2H_ABC_EA":
        send_keys(ch); time.sleep(0.1)
    time.sleep(0.8)
    send_keys("{ENTER}"); time.sleep(1.5)
    print("[EA] 选择后:", ea.window_text()[:50])
else:
    print("[EA] 已是 30m2H_ABC_EA")

# 检查日期/模式
for c in win.descendants():
    try:
        txt = c.window_text()
        if "SysDateTimePick32" in c.class_name() and c.rectangle().width() > 50:
            print("  日期 %r" % txt)
    except Exception:
        pass

# 点开始
start_hwnd = None
for c in win.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            start_hwnd = c.handle
    except Exception:
        pass
if not start_hwnd:
    print("无开始按钮(可能需切设置页签)"); sys.exit(1)
print("[开始] BM_CLICK")
user32.SendMessageW(start_hwnd, BM_CLICK, 0, 0)
time.sleep(5.0)

def btn_state():
    for c in win.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始","停止"):
                return c.window_text()
        except Exception:
            pass
    return None
st = btn_state()
print("点开始后按钮:", st)
start_t = time.time()
for i in range(20):  # 最多 5 分钟
    time.sleep(15)
    st = btn_state()
    elapsed = time.time() - start_t
    if st == "开始":
        print("t=%.0fs 回测完成" % elapsed); break
    if i % 4 == 0:
        print("t=%.0fs 状态=%r" % (elapsed, st))
else:
    print("超时 5 分钟")
print("最终按钮:", btn_state())
