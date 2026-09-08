# -*- coding: utf-8 -*-
"""v56: 重新回测（正确等待实例2，回测期间不读台账）"""
import sys, time, ctypes
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

BM_CLICK = 0x00F5
d = Desktop(backend="win32")

def find_inst2():
    for w in d.windows():
        try:
            t = w.window_text()
            if t and "Exness" in t and "[" in t:
                for c in w.descendants():
                    try:
                        if "ComboBox" in c.class_name() and "2H_M30_6H_ABC_EA" in c.window_text():
                            return w
                    except Exception:
                        pass
        except Exception:
            pass
    return None

def btn_state(w):
    for c in w.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始", "停止"):
                return c.window_text(), c.handle
        except Exception:
            pass
    return None, None

mt5 = find_inst2()
if mt5 is None:
    print("FAIL"); sys.exit(1)
print("实例2 hwnd=%d" % mt5.handle)

# 重新选 EA
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            c.click_input(); time.sleep(0.5)
            send_keys("2H_M30_6H_ABC_EA"); time.sleep(0.5)
            send_keys("{ENTER}"); time.sleep(0.6)
    except Exception:
        pass

# BM_CLICK 开始
st, hwnd = btn_state(mt5)
if st == "开始":
    ctypes.windll.user32.SendMessageW(hwnd, BM_CLICK, 0, 0)
    time.sleep(3.0)

# 正确等待：轮询实例2 的按钮
print("等待回测完成（实例2）...")
start_t = time.time()
for i in range(40):
    time.sleep(15)
    st, _ = btn_state(mt5)
    elapsed = time.time() - start_t
    if st == "开始":
        print("t=%.0fs 回测完成！" % elapsed)
        break
    else:
        print("t=%.0fs 状态=%r" % (elapsed, st))

time.sleep(2.0)  # 确保台账 flush
print("回测结束，可读台账")
