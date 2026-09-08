# -*- coding: utf-8 -*-
"""简单枚举树: 根+子项, 加保护."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
d = Desktop(backend="win32")
MT5_HWND = 17306644

TVM_GETNEXTITEM = 0x110A
TVM_GETITEMW = 0x113E
TVGN_ROOT = 0x0
TVGN_NEXT = 0x1
TVGN_CHILD = 0x4
TVIF_TEXT = 0x1

class TVITEM(ctypes.Structure):
    _fields_ = [
        ("mask", ctypes.c_uint),
        ("hItem", ctypes.c_void_p),
        ("state", ctypes.c_uint),
        ("stateMask", ctypes.c_uint),
        ("pszText", ctypes.c_wchar_p),
        ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int),
        ("iSelectedImage", ctypes.c_int),
        ("cChildren", ctypes.c_int),
        ("lParam", ctypes.c_void_p),
    ]

mt5 = None
for w in d.windows():
    if w.handle == MT5_HWND:
        mt5 = w
hwnd = mt5.handle
user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.4)
user32.SetForegroundWindow(hwnd); time.sleep(0.4)

for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            c.click_input(); time.sleep(1.0)
    except Exception:
        pass

tree = None
for c in mt5.descendants():
    try:
        if "SysTreeView32" in c.class_name():
            try:
                if c.is_visible():
                    tree = c
            except Exception:
                pass
    except Exception:
        pass
if tree is None:
    print("FAIL 无可见树"); sys.exit(1)
print("TreeView hwnd=%d" % tree.handle)

def get_text(h):
    buf = ctypes.create_unicode_buffer(256)
    it = TVITEM()
    it.mask = TVIF_TEXT
    it.hItem = h
    it.pszText = ctypes.cast(buf, ctypes.c_wchar_p)
    it.cchTextMax = 256
    user32.SendMessageW(tree.handle, TVM_GETITEMW, 0, ctypes.byref(it))
    return buf.value

# 只枚举两层
root = user32.SendMessageW(tree.handle, TVM_GETNEXTITEM, TVGN_ROOT, 0)
print("root:", root, "text:", repr(get_text(root)))
if root:
    child = user32.SendMessageW(tree.handle, TVM_GETNEXTITEM, TVGN_CHILD, root)
    n = 0
    while child and n < 60:
        txt = get_text(child)
        print("  child[%d] hItem=%d text=%r" % (n, child, txt))
        child = user32.SendMessageW(tree.handle, TVM_GETNEXTITEM, TVGN_NEXT, child)
        n += 1
