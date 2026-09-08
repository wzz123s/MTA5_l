# -*- coding: utf-8 -*-
"""EXNESS TVM 枚举树 + 选择 30m2H_ABC_EA."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8')
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from pywinauto import Application
from pywinauto.keyboard import send_keys

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
MT5_HWND = 5114106
TVM_GETNEXTITEM = 0x110A
TVM_GETITEMW = 0x113E
TVM_SELECTITEMW = 0x113D
TVM_EXPAND = 0x110E
TVGN_ROOT = 0
TVGN_NEXT = 1
TVGN_CHILD = 4
TVGN_CARET = 9
TVE_EXPAND = 0x2
TVE_EXPANDPARTIAL = 0x40000000
TVIF_TEXT = 0x1
PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x1000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04

class TVITEM(ctypes.Structure):
    _fields_ = [
        ("mask", ctypes.c_uint), ("hItem", ctypes.c_void_p),
        ("state", ctypes.c_uint), ("stateMask", ctypes.c_uint),
        ("pszText", ctypes.c_void_p), ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int), ("iSelectedImage", ctypes.c_int),
        ("cChildren", ctypes.c_int), ("lParam", ctypes.c_void_p),
    ]

app = Application(backend="win32").connect(handle=MT5_HWND)
win = app.window(handle=MT5_HWND)
user32.SetForegroundWindow(MT5_HWND); time.sleep(0.5)

# 展开 EA
ea = None
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c
    except Exception:
        pass
ea.click_input(); time.sleep(2.0)

tree = None
for c in win.descendants():
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
    print("无树"); sys.exit(1)
tree_hwnd = tree.handle
print("Tree hwnd:", tree_hwnd)

pid = ctypes.c_uint()
user32.GetWindowThreadProcessId(MT5_HWND, ctypes.byref(pid))
ph = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid.value)
if not ph:
    print("OpenProcess 失败 pid:", pid.value); sys.exit(1)
print("OpenProcess OK pid:", pid.value)
tv_mem = kernel32.VirtualAllocEx(ph, None, ctypes.sizeof(TVITEM), MEM_COMMIT, PAGE_READWRITE)
buf_mem = kernel32.VirtualAllocEx(ph, None, 512, MEM_COMMIT, PAGE_READWRITE)

def get_text(hItem):
    it = TVITEM(); it.mask = TVIF_TEXT; it.hItem = hItem
    it.pszText = buf_mem; it.cchTextMax = 512
    w = ctypes.c_ulong()
    kernel32.WriteProcessMemory(ph, tv_mem, ctypes.byref(it), ctypes.sizeof(TVITEM), ctypes.byref(w))
    user32.SendMessageW(tree_hwnd, TVM_GETITEMW, 0, tv_mem)
    buf = ctypes.create_string_buffer(512)
    kernel32.ReadProcessMemory(ph, buf_mem, buf, 512, ctypes.byref(w))
    try:
        return buf.raw[:w.value].decode('utf-16-le', errors='ignore').split('\x00')[0]
    except Exception:
        return ""

target = None
def walk(h, depth, lmt):
    global target
    while h and lmt[0] > 0:
        txt = get_text(h)
        if txt:
            print("  "*depth + txt[:60])
        if "30m2H_ABC_EA" in txt:
            target = h
            return
        ch = user32.SendMessageW(tree_hwnd, TVM_GETNEXTITEM, TVGN_CHILD, h)
        if ch:
            # 展开目录
            user32.SendMessageW(tree_hwnd, TVM_EXPAND, TVE_EXPAND, h)
            walk(ch, depth+1, lmt)
        h = user32.SendMessageW(tree_hwnd, TVM_GETNEXTITEM, TVGN_NEXT, h)
        lmt[0] -= 1

root = user32.SendMessageW(tree_hwnd, TVM_GETNEXTITEM, TVGN_ROOT, 0)
print("root:", root)
walk(root, 0, [300])

if target:
    print("\n找到 target:", target)
    user32.SendMessageW(tree_hwnd, TVM_SELECTITEMW, TVGN_CARET, target)
    time.sleep(0.5)
    send_keys("{ENTER}"); time.sleep(1.0)
    print("EA 结果:", ea.window_text()[:50])
else:
    print("未找到 30m2H_ABC_EA")
