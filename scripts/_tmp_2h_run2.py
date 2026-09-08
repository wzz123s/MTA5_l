# -*- coding: utf-8 -*-
"""确认日期 → 开始 → 轮询."""
import ctypes,sys,time
sys.stdout.reconfigure(encoding="utf-8")
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception: pass
from pywinauto import Desktop
u=ctypes.windll.user32; k=ctypes.windll.kernel32
BM_CLICK=0x00F5
d=Desktop(backend="win32"); win=None
for w in d.windows():
    try:
        if w.window_text() and "Exness" in w.window_text() and w.class_name().startswith("MetaQuotes"): win=w; break
    except Exception: pass
if win is None: print("FAIL win"); sys.exit(1)
hwnd=win.handle
def fg():
    cur=k.GetCurrentThreadId(); f=u.GetForegroundWindow(); ft=u.GetWindowThreadProcessId(f,None) if f else 0
    u.AttachThreadInput(cur,ft,True); u.ShowWindow(hwnd,9); time.sleep(0.2); u.BringWindowToTop(hwnd); u.SetForegroundWindow(hwnd); u.SetActiveWindow(hwnd); time.sleep(0.3); u.AttachThreadInput(cur,ft,False)
fg()
dt=[]
for c in win.descendants():
    try:
        if c.class_name()=="SysDateTimePick32":
            r=c.rectangle()
            if r.width()>60: dt.append(c.window_text())
    except Exception: pass
print("dates:", dt[:2])
fg(); sh=None
for c in win.descendants():
    try:
        if "Button" in c.class_name() and c.window_text()=="开始": sh=c.handle
    except Exception: pass
if not sh: print("FAIL start"); sys.exit(1)
u.SendMessageW(sh,BM_CLICK,0,0); time.sleep(5.0)
def bs():
    for c in win.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始","停止"): return c.window_text()
        except Exception: pass
    return None
st=bs(); print("started:", st)
t0=time.time()
for i in range(50):
    time.sleep(15); st=bs()
    if st=="开始": print("DONE t=%.0fs"%(time.time()-t0)); break
    if i%4==0: print("t=%.0fs %r"%(time.time()-t0,st))
else: print("timeout")
print("final:", bs())
