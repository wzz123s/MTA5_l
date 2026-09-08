# -*- coding: utf-8 -*-
"""油冒烟 FINAL: 全自动 EA/USOILm/H2/开价/日期/开始 (强前台)."""
import ctypes,sys,time
sys.stdout.reconfigure(encoding="utf-8")
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception: pass
from collections import defaultdict
from pywinauto import Desktop
from pywinauto.keyboard import send_keys
from ctypes import wintypes as wt
u=ctypes.windll.user32; k=ctypes.windll.kernel32
CB=0x014F; CB_SETCURSEL=0x014E; BM_CLICK=0x00F5
DTM_FIRST=0x1000; DTM_SETSYSTEMTIME=DTM_FIRST+2; GDT_VALID=0
class SYSTEMTIME(ctypes.Structure):
    _fields_=[("wYear",wt.WORD),("wMonth",wt.WORD),("wDayOfWeek",wt.WORD),("wDay",wt.WORD),
              ("wHour",wt.WORD),("wMinute",wt.WORD),("wSecond",wt.WORD),("wMilliseconds",wt.WORD)]
# 找窗口(带重试)
win=None
for attempt in range(8):
    d=Desktop(backend="win32")
    for w in d.windows():
        try:
            if w.window_text() and "Exness" in w.window_text() and w.class_name().startswith("MetaQuotes"):
                win=w; break
        except Exception: pass
    if win is not None: break
    time.sleep(3)
if win is None: print("FAIL win"); sys.exit(1)
hwnd=win.handle
print("MT5 hwnd", hwnd)
def fg():
    cur=k.GetCurrentThreadId(); f=u.GetForegroundWindow(); ft=u.GetWindowThreadProcessId(f,None) if f else 0
    u.AttachThreadInput(cur,ft,True); u.ShowWindow(hwnd,9); time.sleep(0.2); u.BringWindowToTop(hwnd); u.SetForegroundWindow(hwnd); u.SetActiveWindow(hwnd); time.sleep(0.3); u.AttachThreadInput(cur,ft,False)
fg()
send_keys("^r"); time.sleep(4.0)
def combos():
    out=[]
    for c in win.descendants():
        try:
            if "ComboBox" in c.class_name():
                t=c.window_text()
                if t: out.append(c)
        except Exception: pass
    return out
def cc(sub):
    for c in combos():
        try:
            if sub in c.window_text(): return c
        except Exception: pass
    return None
def set_via_type(ctrl,name):
    fg(); u.SendMessageW(ctrl.handle,CB,1,0); time.sleep(0.5)
    for ch in name: send_keys(ch); time.sleep(0.07)
    time.sleep(0.2); send_keys("{ENTER}"); time.sleep(0.9)
    try: return ctrl.window_text()
    except Exception: return ""
# EA
ea=cc("Advisors")
print("[EA]", ea.window_text()[:40] if ea else "none")
if ea and "CrossConfirm" not in ea.window_text():
    t=set_via_type(ea,"USOIL2H_CrossConfirm_EA"); print("  ->", t[:40])
# symbol
sym=cc("XAUUSDm")
if sym is None: sym=cc("USOILm")
print("[sym]", sym.window_text()[:16] if sym else "none")
if sym and "USOILm" not in sym.window_text():
    t=set_via_type(sym,"USOILm"); print("  ->", t[:16])
# period
per=cc("M30")
if per is None: per=cc("H2")
print("[per]", per.window_text()[:10] if per else "none")
if per and "H2" not in per.window_text():
    t=set_via_type(per,"H2"); print("  ->", t[:10])
# mode
fg()
for c in combos():
    if c.window_text() in ("每次报价","仅使用开价","1分钟OHLC"):
        u.SendMessageW(c.handle,CB_SETCURSEL,3,0); time.sleep(0.3); break
# dates
dtps=[]
for c in win.descendants():
    try:
        if "SysDateTimePick32" in c.class_name():
            r=c.rectangle()
            if r.width()>60: dtps.append(c)
    except Exception: pass
print("dates before:")
for i,c in enumerate(dtps):
    try: print(" ", i, c.window_text())
    except Exception: pass
def setdt(ctrl,y,m,dd):
    st=SYSTEMTIME(y,m,0,dd,0,0,0,0)
    return u.SendMessageW(ctrl.handle,DTM_SETSYSTEMTIME,GDT_VALID,ctypes.byref(st))
targets=[(2020,1,1),(2026,12,31)]
cur=0
for i,c in enumerate(dtps):
    if cur>=2: break
    try: txt=c.window_text()
    except Exception: continue
    try: yv=int(txt.split(".")[0])
    except Exception: continue
    if yv<2019 or yv>2026 or (i==1 and False):
        yy,mm,dd=targets[cur]
        res=setdt(c,yy,mm,dd); time.sleep(0.3)
        try: after=c.window_text()
        except Exception: after=""
        print("  DTM set", i, txt, "->", after, "res", res)
        cur+=1
print("dates after:")
for i,c in enumerate(dtps):
    try: print(" ", i, c.window_text())
    except Exception: pass
# start
fg()
sh=None
for c in win.descendants():
    try:
        if "Button" in c.class_name() and c.window_text()=="开始": sh=c.handle
    except Exception: pass
if not sh: print("FAIL start btn"); sys.exit(1)
u.SendMessageW(sh,BM_CLICK,0,0); time.sleep(5.0)
def bs():
    for c in win.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始","停止"): return c.window_text()
        except Exception: pass
    return None
st=bs(); print("started:", st)
t0=time.time()
for i in range(36):
    time.sleep(15); st=bs()
    if st=="开始": print("DONE t=%.0fs"%(time.time()-t0)); break
    if i%4==0: print("t=%.0fs %r"%(time.time()-t0,st))
else: print("timeout")
print("final:", bs())
