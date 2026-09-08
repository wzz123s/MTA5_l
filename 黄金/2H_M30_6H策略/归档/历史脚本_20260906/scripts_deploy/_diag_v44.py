# -*- coding: utf-8 -*-
"""v44: 检查并关闭 自定义分析周期 弹窗"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

d = Desktop(backend="win32")

# 找 自定义分析周期 弹窗
dlg = None
for w in d.windows():
    try:
        t = w.window_text()
        if t == "自定义分析周期":
            dlg = w
            r = w.rectangle()
            print("找到弹窗: %r rect=(%d,%d)-(%d,%d)" % (t, r.left, r.top, r.right, r.bottom))
    except Exception:
        pass

if dlg:
    print("=== 弹窗内控件 ===")
    for c in dlg.descendants():
        try:
            cls = c.class_name()
            txt = c.window_text()
            r = c.rectangle()
            print("  class=%r text=%r rect=(%d,%d)-(%d,%d)" % (cls, txt, r.left, r.top, r.right, r.bottom))
        except Exception:
            pass
    # 尝试关闭（ESC 或点取消）
    print("\n发送 ESC 关闭...")
    from pywinauto.keyboard import send_keys
    send_keys("{ESC}")
    time.sleep(1.0)
    # 检查是否关闭
    still = False
    for w in d.windows():
        try:
            if w.window_text() == "自定义分析周期":
                still = True
        except Exception:
            pass
    print("关闭后仍存在:", still)
else:
    print("未找到 自定义分析周期 弹窗")
