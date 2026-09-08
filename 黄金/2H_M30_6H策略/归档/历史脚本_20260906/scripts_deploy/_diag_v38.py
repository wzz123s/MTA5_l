# -*- coding: utf-8 -*-
"""v38: 确认配置 + 点开始"""
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

# 确认关键配置
print("=== 关键配置确认 ===")
for c in mt5.descendants():
    try:
        cls = c.class_name()
        txt = c.window_text()
        if "ComboBox" in cls and txt and any(k in txt for k in ["Advisors", "XAUUSDm", "M30", "仅使用开价", "500", "1:2000"]):
            print("  %r" % txt)
        if "SysDateTimePick32" in cls and txt:
            print("  %r" % txt)
    except Exception:
        pass

# 找开始按钮并点击
start = None
for c in mt5.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() == "开始":
            start = c
            r = c.rectangle()
            print("\n开始按钮 rect=(%d,%d)-(%d,%d)" % (r.left, r.top, r.right, r.bottom))
    except Exception:
        pass

if start:
    print("点击开始...")
    start.click_input()
    time.sleep(2.0)
    # 读回状态（开始按钮可能变停止）
    print("\n点击后按钮状态:")
    for c in mt5.descendants():
        try:
            if "Button" in c.class_name():
                txt = c.window_text()
                if txt in ("开始", "停止", "跳过"):
                    r = c.rectangle()
                    print("  %r rect=(%d,%d)-(%d,%d)" % (txt, r.left, r.top, r.right, r.bottom))
        except Exception:
            pass
else:
    print("未找到开始按钮")
