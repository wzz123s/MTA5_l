# -*- coding: utf-8 -*-
"""枚举 Exness 窗口状态."""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
d = Desktop(backend="win32")
found = 0
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t:
            found += 1
            print("hwnd=%d mini=%s vis=%s rect=%r %r" % (w.handle, w.is_minimized(), w.is_visible(), str(w.rectangle())[:40], t[:60]))
    except Exception:
        pass
if found == 0:
    print("无 Exness 窗口; 枚举所有可见窗口:")
    for w in d.windows():
        try:
            if w.is_visible() and w.window_text():
                print("  %d %r" % (w.handle, w.window_text()[:60]))
        except Exception:
            pass
