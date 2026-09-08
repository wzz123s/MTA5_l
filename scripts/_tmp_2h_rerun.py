# -*- coding: utf-8 -*-
"""切EA=2H + 起始日期2015->2025(自校验) + 开始 + 轮询."""
import ctypes,sys,time
sys.stdout.reconfigure(encoding="utf-8")
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception: pass
from pywinauto import Desktop
from pywinauto.keyboard import send_keys
u=ctypes.windll.user32; k=ctypes.windll.kernel32
CB=0x014F; BM_CLICK=0x00F5
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
fg(); send_keys("^r"); time.sleep(3.5)
# EA -> 2H
def cc(sub):
    for c in win.descendants():
        try:
            if "ComboBox" in c.class_name() and sub in c.window_text(): return c
        except Exception: pass
    return None
def set_via_type(ctrl,name):
    fg(); u.SendMessageW(ctrl.handle,CB,1,0); time.sleep(0.5)
    for ch in name: send_keys(ch); time.sleep(0.07)
    time.sleep(0.2); send_keys("{ENTER}"); time.sleep(0.9)
    try: return ctrl.window_text()
    except Exception: return ""
ea=cc("Advisors")
print("[EA]", ea.window_text()[:40] if ea else "none")
if ea and "2H_M30_6H_ABC_EA" not in ea.window_text():
    t=set_via_type(ea,"2H_M30_6H_ABC_EA"); print("  ->", t[:40])
# From 日期 2015->2025 (UP 10), 自校验
dtps=[]
for c in win.descendants():
    try:
        if "SysDateTimePick32" in c.class_name():
            r=c.rectangle()
            if r.width()>60: dtps.append(c)
    except Exception: pass
def rd(c):
    try: return c.window_text()
    except Exception: return ""
def set_year(ctrl,target):
    for _ in range(60):
        txt=rd(ctrl)
        try: cy=int(txt.split(".")[0])
        except Exception: return False
        if cy==target: return True
        fg(); ctrl.click_input(); time.sleep(0.4)
        send_keys("{LEFT 2}"); time.sleep(0.3)
        send_keys("{UP}" if target>cy else "{DOWN}"); time.sleep(0.5)
        send_keys("{ENTER}"); time.sleep(0.3)
    return False
if dtps:
    c0=dtps[0]
    print("[from now]", rd(c0))
    ok=set_year(c0,2025)
    print("[from after]", rd(c0), "ok", ok)
# 开始
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
