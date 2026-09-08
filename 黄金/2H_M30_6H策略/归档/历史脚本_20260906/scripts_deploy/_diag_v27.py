# -*- coding: utf-8 -*-
"""v27: 测试日期止输入法（点击+全选+type_keys）"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

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

def read_dtp_texts(mt5):
    out = []
    for c in mt5.descendants():
        try:
            if "DateTimePick" in c.class_name():
                r = c.rectangle()
                out.append((c.window_text(), r.left, r.top, c))
        except Exception:
            pass
    return out

mt5 = find_mt5()
if mt5 is None:
    print("FAIL"); sys.exit(1)

print("=== 设置前 DTP ===")
for txt, l, t, c in read_dtp_texts(mt5):
    print("  %r left=%d top=%d" % (txt, l, t))

# 找日期止 = 第二个 (x 更大的), 当前 '2026.09.01'
dtps = read_dtp_texts(mt5)
# 过滤掉时间戳那种 (top=584 的)
dtps = [x for x in dtps if x[2] > 600]  # top > 600 的才是日期输入
dtps.sort(key=lambda x: (x[2], x[1]))
print("\n候选日期控件:")
for txt, l, t, c in dtps:
    print("  %r left=%d top=%d" % (txt, l, t))

# 日期止 = 同一行 x 更大的
if len(dtps) >= 2:
    row = [x for x in dtps if abs(x[2] - dtps[0][2]) < 20]
    row.sort(key=lambda x: x[1])
    stop = row[-1][3]
    print("\n目标日期止: %r" % stop.window_text())
    print("点击 + Ctrl+A + type_keys '2026/08/14'")
    stop.click_input()
    time.sleep(0.5)
    send_keys("^a")
    time.sleep(0.3)
    send_keys("2026/08/14")
    time.sleep(0.3)
    send_keys("{ENTER}")
    time.sleep(0.5)
    print("设置后 window_text=%r" % stop.window_text())
