# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
print("start", flush=True)
try:
    from pywinauto import Desktop, Application
    print("import ok", flush=True)
    d32 = Desktop(backend="win32")
    mt5_hwnd = None
    for w in d32.windows():
        try:
            t = w.window_text()
            if t and "Exness" in t:
                mt5_hwnd = w.handle
                break
        except Exception:
            pass
    print("hwnd:", mt5_hwnd, flush=True)
    app = Application(backend="uia").connect(handle=mt5_hwnd)
    print("UIA connect ok", flush=True)
    win = app.window()
    print("UIA window:", win.window_text()[:50], flush=True)
    children = win.children()
    print("children count:", len(children), flush=True)
    for ch in children[:20]:
        try:
            print("  [%s] %r" % (ch.element_info.control_type, ch.window_text()[:50]), flush=True)
        except Exception as e:
            print("  child err:", e, flush=True)
except Exception as e:
    import traceback
    traceback.print_exc()
    print("FAIL", flush=True)
