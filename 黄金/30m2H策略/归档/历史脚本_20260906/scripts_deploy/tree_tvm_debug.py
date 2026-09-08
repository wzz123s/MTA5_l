# -*- coding: utf-8 -*-
"""调试: 树项读取."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8')
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass
from pywinauto import Desktop

kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32
user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
HWND_TOPMOST = ctypes.c_void_p(-1)
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
TVM_GETNEXTITEM = 0x110A
TVM_GETITEMW = 0x113E
TVM_GETCOUNT = 0x1105
TVGN_ROOT = 0
TVGN_NEXT = 1
TVGN_CHILD = 4
TVIF_TEXT = 0x1
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04

class TVITEM(ctypes.Structure):
    _fields_ = [
        ("mask", ctypes.c_uint),
        ("hItem", ctypes.c_void_p),
        ("state", ctypes.c_uint),
        ("stateMask", ctypes.c_uint),
        ("pszText", ctypes.c_void_p),
        ("cchTextMax", ctypes.c_int),
        ("iImage", ctypes.c_int),
        ("iSelectedImage", ctypes.c_int),
        ("cChildren", ctypes.c_int),
        ("lParam", ctypes.c_void_p),
    ]

d = Desktop(backend="win32")
mt5 = None
for w in d.windows():
    try:
        if w.handle == 4654538:
            mt5 = w
    except Exception:
        pass
hwnd = mt5.handle
user32.SetWindowPos(ctypes.c_void_p(hwnd), HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE)
time.sleep(0.4)
user32.SetForegroundWindow(hwnd); time.sleep(0.4)

ea = None
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c
    except Exception:
        pass
ea.click_input(); time.sleep(3.0)  # 等树加载

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
    print("无树"); sys.exit(1)
tree_hwnd = tree.handle
print("Tree hwnd:", tree_hwnd)

pid = ctypes.c_uint()
user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
pid = pid.value
ph = kernel32.OpenProcess(PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_QUERY_INFORMATION, False, pid)
tv_mem = kernel32.VirtualAllocEx(ph, None, ctypes.sizeof(TVITEM), MEM_COMMIT, PAGE_READWRITE)
buf_mem = kernel32.VirtualAllocEx(ph, None, 512, MEM_COMMIT, PAGE_READWRITE)

count = user32.SendMessageW(tree_hwnd, TVM_GETCOUNT, 0, 0)
print("TVM_GETCOUNT:", count)

def get_item_text(hItem):
    it = TVITEM()
    it.mask = TVIF_TEXT
    it.hItem = hItem
    it.pszText = buf_mem
    it.cchTextMax = 512
    written = ctypes.c_ulong()
    kernel32.WriteProcessMemory(ph, tv_mem, ctypes.byref(it), ctypes.sizeof(TVITEM), ctypes.byref(written))
    ret = user32.SendMessageW(tree_hwnd, TVM_GETITEMW, 0, tv_mem)
    buf = ctypes.create_string_buffer(512)
    kernel32.ReadProcessMemory(ph, buf_mem, buf, 512, ctypes.byref(written))
    raw = buf.raw[:written.value]
    # 尝试多种解码
    txt = ""
    for enc in ['utf-16-le', 'utf-8']:
        try:
            txt = raw.decode(enc, errors='ignore').split('\x00')[0]
            if txt:
                break
        except Exception:
            pass
    return txt

root = user32.SendMessageW(tree_hwnd, TVM_GETNEXTITEM, TVGN_ROOT, 0)
print("root hItem:", root)
if root:
    print("root text:", repr(get_item_text(root)))
    child = user32.SendMessageW(tree_hwnd, TVM_GETNEXTITEM, TVGN_CHILD, root)
    print("root child:", child)
    n = 0
    while child and n < 40:
        print("  [%d] text=%r" % (n, get_item_text(child)))
        child = user32.SendMessageW(tree_hwnd, TVM_GETNEXTITEM, TVGN_NEXT, child)
        n += 1

kernel32.CloseHandle(ph)
