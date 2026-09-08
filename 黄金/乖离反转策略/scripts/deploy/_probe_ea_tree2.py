# -*- coding: utf-8 -*-
import ctypes, sys, time
sys.stdout.reconfigure(encoding="utf-8")
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from pywinauto import Desktop
from pywinauto.keyboard import send_keys
user32 = ctypes.windll.user32

d = Desktop(backend="win32")
win = None
for w in d.windows():
    try:
        t = w.window_text()
        if t and "Exness" in t:
            win = w; break
    except Exception:
        pass
hwnd = win.handle
user32.ShowWindow(hwnd, 9); time.sleep(1.0)
user32.SetWindowPos(ctypes.c_void_p(hwnd), ctypes.c_void_p(0), 0, 0, 1700, 950, 0x0040)
time.sleep(0.4)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)
send_keys("^r"); time.sleep(3.0)

ea = None
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name() and ("Advisors" in (c.window_text() or "")):
            ea = c; break
    except Exception:
        pass
print("combo rect", ea.rectangle())
ea.click_input(); time.sleep(2.0)

def walk(node, depth, lines):
    try:
        txt = node.text() or ""
    except Exception:
        txt = "?"
    lines.append("  " * depth + repr(txt[:70]))
    try:
        kids = node.children()
    except Exception:
        return
    for k in kids:
        try:
            walk(k, depth + 1, lines)
        except Exception:
            pass

lines = []
seen = set()
for w in d.windows():
    try:
        cls = w.class_name()
        rect = w.rectangle()
        if "TreeView" in cls or "ListBox" in cls or "ComboBox" in cls:
            key = (cls, w.handle)
            if key in seen: continue
            seen.add(key)
            lines.append("WINDOW cls=%s hwnd=%d rect=(%d,%d,%d,%d) text=%r" % (
                cls, w.handle, rect.left, rect.top, rect.right, rect.bottom, (w.window_text() or "")[:40]))
            try:
                for r in w.roots():
                    walk(r, 1, lines)
            except Exception as e:
                lines.append("  roots exc " + str(e)[:80])
    except Exception:
        pass
print("\n".join(lines))
