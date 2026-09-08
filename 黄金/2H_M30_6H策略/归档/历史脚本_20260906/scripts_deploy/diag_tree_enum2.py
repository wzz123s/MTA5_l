# -*- coding: utf-8 -*-
"""修正消息号: TVM_GETITEMW=0x113E 枚举树."""
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
d = Desktop(backend="win32")
MT5_HWND = 17306644

TVM_GETNEXTITEM = 0x110A
TVM_GETITEMW = 0x113E
TVM_SELECTITEMW = 0x113D
TVM_EXPAND = 0x110E
TVM_GETCOUNT = 0x1105
TVGN_ROOT = 0x0
TVGN_NEXT = 0x1
TVGN_CHILD = 0x4
TVGN_CARET = 0x9
TVE_EXPAND = 0x2
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
time.sleep(0.5)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)

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

count = user32.SendMessageW(tree.handle, TVM_GETCOUNT, 0, 0)
print("树项数(顶层): %d" % count)

def get_text(h):
    buf = ctypes.create_unicode_buffer(512)
    it = TVITEM()
    it.mask = TVIF_TEXT
    it.hItem = h
    it.pszText = ctypes.cast(buf, ctypes.c_wchar_p)
    it.cchTextMax = 512
    user32.SendMessageW(tree.handle, TVM_GETITEMW, 0, ctypes.byref(it))
    return buf.value

target = None
def walk(h, depth):
    global target
    while h:
        txt = get_text(h)
        print("  "*depth + txt)
        if "2H_M30_6H_ABC_EA" in txt:
            target = h
        ch = user32.SendMessageW(tree.handle, TVM_GETNEXTITEM, TVGN_CHILD, h)
        if ch:
            walk(ch, depth+1)
        h = user32.SendMessageW(tree.handle, TVM_GETNEXTITEM, TVGN_NEXT, h)

root = user32.SendMessageW(tree.handle, TVM_GETNEXTITEM, TVGN_ROOT, 0)
walk(root, 0)

if target:
    print("\n选择目标...")
    user32.SendMessageW(tree.handle, TVM_SELECTITEMW, TVGN_CARET, target)
    time.sleep(0.5)
    send_keys("{ENTER}"); time.sleep(0.8)
    for c in mt5.descendants():
        try:
            if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
                print("[EA] 最终:", c.window_text()[:60])
        except Exception:
            pass
else:
    print("\n未找到目标项")
