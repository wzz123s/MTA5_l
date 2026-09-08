# -*- coding: utf-8 -*-
"""找 Tester 面板的 Tab 页签和参数表格."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

d = Desktop(backend="win32")
mt5 = None
for w in d.windows():
    if w.handle == 726084:
        mt5 = w
if mt5 is None:
    print("FAIL"); sys.exit(1)

# 找 Tab 控件
print("=== Tab 控件 ===")
for c in mt5.descendants():
    try:
        cls = c.class_name()
        if "Tab" in cls or "SysTabControl" in cls:
            r = c.rectangle()
            print("  [%s] @(%d,%d,%d,%d)" % (cls, r.left, r.top, r.right, r.bottom))
    except Exception:
        pass

# 找所有 ComboBox 和 Edit (参数值输入框)
print("\n=== ComboBox / Edit 控件 ===")
for c in mt5.descendants():
    try:
        cls = c.class_name()
        txt = c.window_text()
        if "ComboBox" in cls or "Edit" in cls:
            if txt:
                r = c.rectangle()
                print("  [%s] %r @(%d,%d,%d,%d)" % (cls[:15], txt[:45], r.left, r.top, r.right, r.bottom))
    except Exception:
        pass

# 找 SysListView32 (参数表格/报告)
print("\n=== SysListView32 (前10个有内容的) ===")
n = 0
for c in mt5.descendants():
    try:
        if "SysListView32" in c.class_name():
            cnt = c.item_count() if hasattr(c, 'item_count') else -1
            r = c.rectangle()
            if r.width() > 200 and r.height() > 100:
                print("  SysListView32 @(%d,%d,%d,%d) items=%s" % (r.left, r.top, r.right, r.bottom, cnt))
                n += 1
                if n > 8: break
    except Exception:
        pass
