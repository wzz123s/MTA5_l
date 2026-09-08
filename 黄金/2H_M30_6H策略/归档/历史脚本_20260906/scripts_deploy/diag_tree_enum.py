# -*- coding: utf-8 -*-
"""展开 EA 目录树 + TVM 消息枚举 + 选择 ABC EA."""
import ctypes
from ctypes import wintypes
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

# TreeView 消息
TVM_GETNEXTITEM = 0x110A
TVM_GETITEMW = 0x110E  # 注意: TVM_GETITEMW 实际是 0x113E? 用 0x110C 是 A 版
TVM_SELECTITEM = 0x110B
TVM_EXPAND = 0x110E
TVGN_ROOT = 0x0
TVGN_NEXT = 0x1
TVGN_CHILD = 0x4
TVGN_CARET = 0x9
TVE_EXPAND = 0x2
TVIF_TEXT = 0x1
TVIF_CHILDREN = 0x40

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
if mt5 is None:
    print("FAIL"); sys.exit(1)
hwnd = mt5.handle
user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.5)
user32.SetForegroundWindow(hwnd); time.sleep(0.5)

# 展开 EA
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            c.click_input(); time.sleep(1.0)
    except Exception:
        pass

# 找可见的 SysTreeView32
tree = None
for c in mt5.descendants():
    try:
        if "SysTreeView32" in c.class_name():
            try:
                if c.is_visible():
                    tree = c
                    break
            except Exception:
                pass
    except Exception:
        pass

if tree is None:
    print("FAIL 未找到可见 TreeView"); sys.exit(1)
print("TreeView hwnd=%d" % tree.handle)

def get_text(h):
    buf = ctypes.create_unicode_buffer(512)
    it = TVITEM()
    it.mask = TVIF_TEXT
    it.hItem = h
    it.pszText = ctypes.cast(buf, ctypes.c_wchar_p)
    it.cchTextMax = 512
    user32.SendMessageW(tree.handle, TVM_GETITEMW, 0, ctypes.byref(it))
    return buf.value

def get_child(h):
    return user32.SendMessageW(tree.handle, TVM_GETNEXTITEM, TVGN_CHILD, h)

def get_next(h):
    return user32.SendMessageW(tree.handle, TVM_GETNEXTITEM, TVGN_NEXT, h)

# 递归枚举
target = None
def walk(h, depth):
    global target
    while h:
        txt = get_text(h)
        print("  " * depth + txt)
        if "2H_M30_6H_ABC_EA" in txt:
            target = h
        ch = get_child(h)
        if ch:
            walk(ch, depth + 1)
        h = get_next(h)

root = user32.SendMessageW(tree.handle, TVM_GETNEXTITEM, TVGN_ROOT, 0)
walk(root, 0)

if target:
    print("\n找到目标, 选择...")
    user32.SendMessageW(tree.handle, TVM_SELECTITEM, TVGN_CARET, target)
    time.sleep(0.5)
    send_keys("{ENTER}"); time.sleep(0.8)
    for c in mt5.descendants():
        try:
            if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
                print("[EA] 最终:", c.window_text()[:60])
        except Exception:
            pass
else:
    print("\n未找到 2H_M30_6H_ABC_EA 项")
