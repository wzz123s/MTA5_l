# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
print("start", flush=True)
try:
    import comtypes
    print("comtypes OK", comtypes.__version__, flush=True)
except Exception as e:
    print("comtypes FAIL:", repr(e), flush=True)
try:
    from pywinauto import Desktop
    print("Desktop import OK", flush=True)
    import time
    t0 = time.time()
    d = Desktop(backend="uia")
    print("UIA Desktop init OK in %.1fs" % (time.time()-t0), flush=True)
    wins = d.windows()
    print("窗口数:", len(wins), flush=True)
    for w in list(wins)[:8]:
        try:
            print("  -", w.window_text()[:60], flush=True)
        except Exception as e:
            print("  - err", e, flush=True)
except Exception as e:
    import traceback
    traceback.print_exc()
    print("UIA FAIL", flush=True)
