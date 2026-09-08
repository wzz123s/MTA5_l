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
ea.click_input(); time.sleep(2.0)

def walk(node, depth):
    try:
        txt = node.text() or ""
    except Exception:
        txt = "?"
    print("  " * depth + repr(txt[:60]))
    try:
        kids = node.children()
    except Exception:
        return
    for k in kids:
        try:
            walk(k, depth + 1)
        except Exception:
            pass

for c in win.descendants():
    try:
        if "SysTreeView32" in c.class_name() and c.is_visible():
            print("TREE hwnd=", c.handle, "rect=", c.rectangle())
            t = c.tree_root() if hasattr(c, "tree_root") else None
            try:
                roots = c.roots() if hasattr(c, "roots") else []
            except Exception:
                roots = []
            for r in roots:
                walk(r, 0)
            break
    except Exception as e:
        print("tree iter exc", e)
