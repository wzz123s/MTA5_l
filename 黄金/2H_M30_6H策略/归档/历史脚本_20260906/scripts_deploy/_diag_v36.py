# -*- coding: utf-8 -*-
"""v36: 滚动 Tester 面板，读模式 ComboBox items"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

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
    print("FAIL"); sys.exit(1)

# 找到 Tester 面板
panel = None
for c in mt5.descendants():
    try:
        if "策略测试" in c.window_text() and c.rectangle().width() > 1000:
            panel = c
    except Exception:
        pass

if panel is None:
    print("未找到面板"); sys.exit(1)
pr = panel.rectangle()
print("面板 rect=(%d,%d)-(%d,%d)" % (pr.left, pr.top, pr.right, pr.bottom))

# 在面板中间向下滚动（负 wheel_dist = 向下滚动）
cx = (pr.left + pr.right) // 2
cy = (pr.top + pr.bottom) // 2
print("在 (%d,%d) 向下滚动" % (cx, cy))
for i in range(5):
    panel.wheel_mouse_input(-3, coords=(cx - pr.left, cy - pr.top))
    time.sleep(0.3)

# 读回所有 ComboBox
print("\n=== 滚动后 ComboBox ===")
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name():
            txt = c.window_text()
            r = c.rectangle()
            if txt and ("OHLC" in txt or "开价" in txt or "报价" in txt or "建模" in txt or "500" in txt or "2000" in txt):
                print("  %r rect=(%d,%d)-(%d,%d)" % (txt, r.left, r.top, r.right, r.bottom))
    except Exception:
        pass
