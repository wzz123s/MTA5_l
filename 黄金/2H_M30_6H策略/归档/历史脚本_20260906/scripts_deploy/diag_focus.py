# -*- coding: utf-8 -*-
"""诊断 set_focus 后日期焦点字段 + EA combo 键盘响应."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from pywinauto.keyboard import send_keys
from collections import defaultdict

d = Desktop(backend="win32")

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

# 1) 日期焦点诊断
groups = defaultdict(list)
for c in mt5.descendants():
    try:
        if "SysDateTimePick32" in c.class_name():
            r = c.rectangle()
            groups[r.top].append((c, r))
    except Exception:
        pass
dtps = []
for top, items in groups.items():
    if len(items) >= 2:
        items.sort(key=lambda x: x[1].left)
        dtps = [items[0][0], items[1][0]]
        break

for i, ctrl in enumerate(dtps):
    t0 = ctrl.window_text()
    ctrl.set_focus(); time.sleep(0.5)
    send_keys("{UP}"); time.sleep(0.4)
    t1 = ctrl.window_text()
    # 再测试 RIGHT 后 UP 的效果
    send_keys("{RIGHT}"); time.sleep(0.3)
    send_keys("{UP}"); time.sleep(0.4)
    t2 = ctrl.window_text()
    print("日期%d: set_focus=%s | UP后=%s | RIGHT+UP后=%s" % (i, t0, t1, t2))
    # 恢复：DOWN 抵消
    send_keys("{DOWN}"); time.sleep(0.2)
    send_keys("{LEFT}"); time.sleep(0.2)
    send_keys("{DOWN}"); time.sleep(0.2)
    send_keys("{ENTER}"); time.sleep(0.3)

# 2) EA combo 键盘响应
print("\n=== EA combo 测试 ===")
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            t0 = c.window_text()
            c.set_focus(); time.sleep(0.5)
            send_keys("2"); time.sleep(0.5)
            t1 = c.window_text()
            print("EA set_focus=%s | 按'2'后=%s" % (t0[:50], t1[:50]))
    except Exception as e:
        print("EA 测试异常:", e)
