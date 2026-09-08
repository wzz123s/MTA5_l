# -*- coding: utf-8 -*-
"""v42: 检查点击后的状态 + 弹窗"""
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

print("=== 开始/停止按钮 ===")
for c in mt5.descendants():
    try:
        if "Button" in c.class_name() and c.window_text() in ("开始", "停止", "跳过"):
            r = c.rectangle()
            print("  %r rect=(%d,%d)-(%d,%d) hwnd=%d" % (c.window_text(), r.left, r.top, r.right, r.bottom, c.handle))
    except Exception:
        pass

print("=== 所有顶层弹窗 ===")
d = Desktop(backend="win32")
for w in d.windows():
    try:
        t = w.window_text()
        r = w.rectangle()
        if t and r.width() > 100 and r.height() > 80 and "Exness" not in t:
            # 只看可能的对话框
            cls = w.class_name()
            if "#32770" in cls or "Dialog" in cls or "Message" in cls or "警告" in t or "错误" in t or "Alert" in t:
                print("  弹窗: class=%r text=%r rect=(%d,%d)-(%d,%d)" % (cls, t[:60], r.left, r.top, r.right, r.bottom))
    except Exception:
        pass

# 也读 Tester 日志/结果区
print("=== Tester 日志区文本 ===")
for c in mt5.descendants():
    try:
        cls = c.class_name()
        if "Edit" in cls or "RichEdit" in cls:
            txt = c.window_text()
            if txt and ("回测" in txt or "test" in txt.lower() or "开始" in txt or "完成" in txt or "error" in txt.lower() or "错误" in txt):
                print("  %r: %r" % (cls, txt[:200]))
    except Exception:
        pass
