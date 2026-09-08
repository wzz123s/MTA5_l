# -*- coding: utf-8 -*-
"""枚举参数表格 SysListView32, 找 InpNanRegOn."""
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

# 找参数表格 (items=43 的 SysListView32)
target = None
for c in mt5.descendants():
    try:
        if "SysListView32" in c.class_name():
            r = c.rectangle()
            if r.width() > 1000 and r.height() > 100:
                try:
                    cnt = c.item_count()
                    if 30 <= cnt <= 60:
                        target = c
                        print("参数表格 hwnd=%d items=%d @(%d,%d,%d,%d)" % (c.handle, cnt, r.left, r.top, r.right, r.bottom))
                except Exception:
                    pass
    except Exception:
        pass

if target is None:
    print("未找到参数表格"); sys.exit(1)

# 用 pywinauto 读 items
try:
    items = target.items()
    print("\n=== 参数列表 (共 %d 项) ===" % len(items))
    for i, it in enumerate(items):
        txt = it.text()
        if txt and txt.strip():
            print("[%d] %r" % (i, txt))
except Exception as e:
    print("items() 失败:", e)
