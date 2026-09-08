# -*- coding: utf-8 -*-
"""VirtualAllocEx 跨进程枚举 EA 树 + 选择 30m2H_ABC_EA."""
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
TVM_SELECTITEMW = 0x113D
TVGN_ROOT = 0
TVGN_NEXT = 1
TVGN_CHILD = 4
TVGN_CARET = 9
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

# 展开 EA
ea = None
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name() and "Advisors" in c.window_text():
            ea = c
    except Exception:
        pass
ea.click_input(); time.sleep(1.2)

# 找树
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

# MT5 进程
pid = user32.GetWindowThreadProcessId(hwnd, None)
print("需要 pid... 用 GetWindowThreadProcessId 2参数")
# 重新取 pid
pid = ctypes.c_uint()
user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
pid = pid.value
print("MT5 PID:", pid)

ph = kernel32.OpenProcess(PROCESS_VM_OPERATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_QUERY_INFORMATION, False, pid)
if not ph:
    print("OpenProcess 失败"); sys.exit(1)
print("OpenProcess OK")

# 分配远程内存: TVITEM + 文本缓冲区
tv_mem = kernel32.VirtualAllocEx(ph, None, ctypes.sizeof(TVITEM), MEM_COMMIT, PAGE_READWRITE)
buf_mem = kernel32.VirtualAllocEx(ph, None, 512, MEM_COMMIT, PAGE_READWRITE)
print("TVITEM mem:", tv_mem, "buf mem:", buf_mem)

def get_item_text(hItem):
    # 写 TVITEM 到远程
    it = TVITEM()
    it.mask = TVIF_TEXT
    it.hItem = hItem
    it.pszText = buf_mem
    it.cchTextMax = 512
    written = ctypes.c_ulong()
    kernel32.WriteProcessMemory(ph, tv_mem, ctypes.byref(it), ctypes.sizeof(TVITEM), ctypes.byref(written))
    # SendMessage
    user32.SendMessageW(tree_hwnd, TVM_GETITEMW, 0, tv_mem)
    # 读回文本
    buf = ctypes.create_string_buffer(512)
    kernel32.ReadProcessMemory(ph, buf_mem, buf, 512, ctypes.byref(written))
    return buf.value.decode('utf-16-le', errors='replace').split('\x00')[0]

# 枚举树 (root + 遍历)
target = None
def walk(hItem, depth, limit):
    global target
    while hItem and limit[0] > 0:
        txt = get_item_text(hItem)
        print("  "*depth + txt)
        if "30m2H_ABC_EA" in txt:
            target = hItem
        child = user32.SendMessageW(tree_hwnd, TVM_GETNEXTITEM, TVGN_CHILD, hItem)
        if child:
            walk(child, depth+1, limit)
        hItem = user32.SendMessageW(tree_hwnd, TVM_GETNEXTITEM, TVGN_NEXT, hItem)
        limit[0] -= 1

root = user32.SendMessageW(tree_hwnd, TVM_GETNEXTITEM, TVGN_ROOT, 0)
print("root hItem:", root)
limit = [200]
walk(root, 0, limit)

if target:
    print("\n找到目标 hItem:", target)
    user32.SendMessageW(tree_hwnd, TVM_SELECTITEMW, TVGN_CARET, target)
    time.sleep(0.5)
    from pywinauto.keyboard import send_keys
    send_keys("{ENTER}"); time.sleep(0.8)
    print("EA 结果:", ea.window_text()[:50])
else:
    print("未找到 30m2H_ABC_EA")

kernel32.VirtualFreeEx(ph, tv_mem, 0, MEM_RELEASE)
kernel32.VirtualFreeEx(ph, buf_mem, 0, MEM_RELEASE)
kernel32.CloseHandle(ph)
