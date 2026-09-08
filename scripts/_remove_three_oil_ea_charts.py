# -*- coding: utf-8 -*-
"""从 DAD3B8 Default profile 摘除三个原油 EA（USOIL2H / USOIL4H / Oil_DataEvent）

用法：先正常退出 MT5（File→Exit），再运行本脚本，然后重新启动 MT5。
摘除的是 chart05 / chart08 / chart11 上的 <expert> 段（图表本身保留）。
运行前自动备份 .chr 到 backup_20260907/mt5_ea/重启前Default_profile快照_20260907/。
"""
import os, re, shutil, datetime, sys

TERM = r"C:/Users/3762/AppData/Roaming/MetaQuotes/Terminal/DAD3B8CC3EAC09C0C9725021DF0C7A65"
CHDIR = os.path.join(TERM, "MQL5", "Profiles", "Charts", "Default")
BAK = r"F:/use_code/MTA5_l/archive/backup_20260907/mt5_ea/摘除三原油EA前chr备份_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
TARGETS = {  # chart -> 要摘除的 EA 名
    "chart05.chr": "USOIL2H_CrossConfirm_EA",
    "chart08.chr": "USOIL4H_Gate_On2H_EA",
    "chart11.chr": "Oil_DataEvent_EA",
}

def rd(p):
    b = open(p, "rb").read()
    return b.decode("utf-16")

def wr(p, s):
    open(p, "wb").write(s.encode("utf-16"))

def main():
    # 检查 MT5 是否仍在运行（必须关闭后执行）
    import ctypes
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32
    class PE32(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)), ("th32ModuleID", wintypes.DWORD),
                    ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", wintypes.DWORD),
                    ("szExeFile", ctypes.c_char * 260)]
    snap = k32.CreateToolhelp32Snapshot(0x2, 0); pe = PE32(); pe.dwSize = ctypes.sizeof(PE32)
    running = False
    if k32.Process32First(snap, ctypes.byref(pe)):
        while True:
            if pe.szExeFile.decode().lower() == "terminal64.exe":
                running = True; break
            if not k32.Process32Next(snap, ctypes.byref(pe)): break
    k32.CloseHandle(snap)
    if running:
        print("[!] MT5 terminal64 仍在运行。请先 File→Exit 正常关闭 MT5，再运行本脚本。")
        sys.exit(1)
    os.makedirs(BAK, exist_ok=True)
    for fn, ea in TARGETS.items():
        p = os.path.join(CHDIR, fn)
        if not os.path.exists(p):
            print(f"  跳过 {fn}: 不存在"); continue
        s = rd(p)
        # 删除匹配该 EA 的 <expert>...</expert> 段
        pat = re.compile(r"<expert>\r?\n.*?name=%s\r?\n.*?\r?\n</expert>\r?\n" % re.escape(ea), re.S)
        n = len(pat.findall(s))
        if n == 0:
            print(f"  {fn}: 未找到 {ea} 的 expert 段（可能已摘除）"); continue
        shutil.copy2(p, os.path.join(BAK, fn))
        s2 = pat.sub("", s)
        wr(p, s2)
        print(f"  {fn}: 已移除 {n} 个 {ea} expert 段（备份 -> {os.path.join(BAK, fn)}）")
    print("完成。现在可以重新启动 MT5。")

if __name__ == "__main__":
    main()
