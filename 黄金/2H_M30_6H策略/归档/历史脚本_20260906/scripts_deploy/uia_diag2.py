# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
print("step0", flush=True)
try:
    from pywinauto import Desktop, Application
    print("step1 import ok", flush=True)
    d32 = Desktop(backend="win32")
    print("step2 win32 desktop ok", flush=True)
    found = []
    for w in d32.windows():
        try:
            t = w.window_text()
            if t and "Exness" in t:
                found.append((w.handle, t[:50]))
        except Exception:
            pass
    print("step3 Exness windows:", len(found), flush=True)
    for h, t in found[:5]:
        print("   hwnd=%d %r" % (h, t), flush=True)
except Exception as e:
    import traceback
    traceback.print_exc()
    print("FAIL", flush=True)
