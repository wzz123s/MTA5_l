import sys, ctypes, os
from ctypes import wintypes
kernel32 = ctypes.windll.kernel32
ntdll = ctypes.windll.ntdll
class PBI(ctypes.Structure):
    _fields_ = [('ExitStatus', ctypes.c_int), ('PebBaseAddress', ctypes.c_void_p), ('AffinityMask', ctypes.c_void_p), ('BasePriority', ctypes.c_void_p), ('UniqueProcessId', ctypes.c_void_p), ('InheritedFromUniqueProcessId', ctypes.c_void_p)]
class US(ctypes.Structure):
    _fields_ = [('Length', ctypes.c_ushort), ('MaximumLength', ctypes.c_ushort), ('Buffer', ctypes.c_void_p)]
class CD(ctypes.Structure):
    _fields_ = [('DosPath', US), ('Handle', ctypes.c_void_p)]
class UPP(ctypes.Structure):
    _fields_ = [('MaximumLength', ctypes.c_uint), ('Length', ctypes.c_uint), ('Flags', ctypes.c_uint), ('DebugFlags', ctypes.c_uint), ('ConsoleHandle', ctypes.c_void_p), ('ConsoleFlags', ctypes.c_uint), ('StandardInput', ctypes.c_void_p), ('StandardOutput', ctypes.c_void_p), ('StandardError', ctypes.c_void_p), ('CurrentDirectory', CD)]
def gus(h, us):
    if us.Length == 0 or not us.Buffer: return ''
    n = us.Length // 2
    buf = ctypes.create_unicode_buffer(n + 1)
    ok = kernel32.ReadProcessMemory(h, ctypes.c_void_p(us.Buffer), buf, (n + 1) * 2, None)
    return buf.value if ok else ''
def ftps():
    pids = []
    nr = wintypes.DWORD()
    buf = (ctypes.c_uint * 4096)()
    kernel32.K32EnumProcesses(ctypes.byref(buf), ctypes.sizeof(buf), ctypes.byref(nr))
    for i in range(nr.value // 4):
        pid = buf[i]
        if not pid: continue
        h = kernel32.OpenProcess(0x1000, False, pid)
        if not h: continue
        name = ctypes.create_unicode_buffer(260)
        sz = wintypes.DWORD(260)
        if kernel32.QueryFullProcessImageNameW(h, 0, name, ctypes.byref(sz)):
            if name.value.lower().endswith('terminal64.exe'):
                pids.append((pid, name.value))
        kernel32.CloseHandle(h)
    return pids
def gcwd(pid):
    h = kernel32.OpenProcess(0x0410, False, pid)
    if not h: return None
    pbi = PBI()
    ret = ntdll.NtQueryInformationProcess(h, 0, ctypes.byref(pbi), ctypes.sizeof(pbi), None)
    if ret != 0: kernel32.CloseHandle(h); return None
    ppa = ctypes.c_void_p()
    ok = kernel32.ReadProcessMemory(h, ctypes.c_void_p(pbi.PebBaseAddress + 0x20), ctypes.byref(ppa), 8, None)
    if not ok: kernel32.CloseHandle(h); return None
    upp = UPP()
    ok = kernel32.ReadProcessMemory(h, ppa, ctypes.byref(upp), ctypes.sizeof(upp), None)
    if not ok: kernel32.CloseHandle(h); return None
    cwd = gus(h, upp.CurrentDirectory.DosPath)
    kernel32.CloseHandle(h)
    return cwd
if __name__ == '__main__':
    for pid, exe in ftps():
        cwd = gcwd(pid)
        print('PID=' + str(pid) + ' EXE=' + exe + ' CWD=' + str(cwd))
        if cwd:
            experts = os.path.join(cwd, 'MQL5', 'Experts')
            print('  Experts=' + experts + ' exists=' + str(os.path.exists(experts)))