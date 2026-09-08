# -*- coding: utf-8 -*-
"""乖离反转 Tester 面板探测: 打开 Strategy Tester, 转储关键控件文本 + 截图."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding="utf-8")
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

OUT = r"F:\use_code\MTA5_l\黄金\乖离反转策略\scripts\deploy"
user32 = ctypes.windll.user32

d = Desktop(backend="win32")
win = None
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t:
            win = w
            break
    except Exception:
        pass
if win is None:
    print("FAIL MT5")
    sys.exit(1)
hwnd = win.handle
print("hwnd", hwnd, "title:", win.window_text()[:80])
user32.ShowWindow(hwnd, 9)
time.sleep(1.0)
user32.SetWindowPos(ctypes.c_void_p(hwnd), ctypes.c_void_p(0), 0, 0, 1700, 950, 0x0040)
time.sleep(0.5)
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)
send_keys("^r")
time.sleep(4.0)

lines = []
def log(s):
    print(s)
    lines.append(s)

log("=== ComboBox 列表(前40) ===")
cnt = 0
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name():
            txt = (c.window_text() or "")[:70]
            log("#%d %r" % (cnt, txt))
            cnt += 1
            if cnt >= 40:
                break
    except Exception:
        pass

log("=== SysDateTimePick32 ===")
for c in win.descendants():
    try:
        if "SysDateTimePick32" in c.class_name():
            r = c.rectangle()
            if r.width() > 60:
                log("%r w=%d h=%d" % ((c.window_text() or ""), r.width(), r.height()))
    except Exception:
        pass

log("=== Button 文本(全部) ===")
for c in win.descendants():
    try:
        if "Button" in c.class_name():
            t = (c.window_text() or "").strip()
            if t:
                log(repr(t[:40]))
    except Exception:
        pass

with open(OUT + r"\_probe_tester_dump.txt", "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

try:
    img = win.capture_as_image()
    p = OUT + r"\_probe_tester.png"
    img.save(p)
    print("shot saved", p)
except Exception as e:
    print("shot fail", e)
print("done")
