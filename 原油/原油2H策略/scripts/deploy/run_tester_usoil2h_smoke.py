# -*- coding: utf-8 -*-
"""原油 TODO-4 冒烟 v2: 强前台 + EA/USOILm/H2/开价/日期 + 开始."""
import ctypes, sys, time
sys.stdout.reconfigure(encoding='utf-8')
try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception: pass
from collections import defaultdict
from pywinauto import Desktop
from pywinauto.keyboard import send_keys
u=ctypes.windll.user32; k=ctypes.windll.kernel32
BM_CLICK=0x00F5; CB_SETCURSEL=0x014E

def foreground(hwnd):
    cur=k.GetCurrentThreadId(); fg=u.GetForegroundWindow(); ft=u.GetWindowThreadProcessId(fg,None) if fg else 0
    u.AttachThreadInput(cur,ft,True)
    u.ShowWindow(hwnd,9); time.sleep(0.3); u.BringWindowToTop(hwnd); u.SetForegroundWindow(hwnd); u.SetActiveWindow(hwnd); time.sleep(0.5)
    u.AttachThreadInput(cur,ft,False)

d=Desktop(backend="win32"); win=None
for w in d.windows():
    try:
        if w.window_text() and "Exness" in w.window_text() and w.class_name().startswith("MetaQuotes"): win=w; break
    except Exception: pass
if win is None: print("FAIL win"); sys.exit(1)
hwnd=win.handle
foreground(hwnd)
send_keys("^r"); time.sleep(3.0)

def ea_combo():
    for c in win.descendants():
        try:
            if "ComboBox" in c.class_name() and "Advisors" in c.window_text(): return c
        except Exception: pass
    return None
ea=ea_combo()
if ea is None: print("FAIL ea combo"); sys.exit(1)
etxt=ea.window_text(); print("[EA]", etxt[:60])
if "USOIL2H_CrossConfirm_EA" not in etxt:
    # 尝试再切一次
    foreground(hwnd); u.SendMessageW(ea.handle, 0x014F, 1, 0); time.sleep(0.6)
    for ch in "USOIL2H_CrossConfirm_EA": send_keys(ch); time.sleep(0.07)
    time.sleep(0.3); send_keys("{ENTER}"); time.sleep(0.9)
    etxt=ea.window_text(); print("[EA] retry:", etxt[:60])
    if "USOIL2H_CrossConfirm_EA" not in etxt: print("仍非目标, 中止"); sys.exit(1)

def find_combo(m):
    for c in win.descendants():
        try:
            if "ComboBox" in c.class_name() and m in c.window_text(): return c
        except Exception: pass
    return None
def set_combo_keys(combo, value):
    try:
        foreground(hwnd); combo.click_input(); time.sleep(0.5)
        send_keys(value, with_spaces=True); time.sleep(0.4); send_keys("{ENTER}"); time.sleep(0.6)
    except Exception as e: print("setcombofail", e)

# symbol USOILm
sym=find_combo("USOILm")
if sym is None: sym=find_combo("XAUUSDm")
if sym and "USOILm" not in sym.window_text():
    print("[sym]", sym.window_text()[:30]); set_combo_keys(sym, "USOILm"); print("  ->", sym.window_text()[:30])
else: print("[sym] ok", sym.window_text()[:30] if sym else "none")
# period H2
per=find_combo("H2")
if per is None: per=find_combo("M30")
if per and "H2" not in per.window_text():
    print("[period]", per.window_text()[:30])
    foreground(hwnd)
    try: per.select("H2"); time.sleep(0.5)
    except Exception as e: print("  selectfail", e); set_combo_keys(per, "H2")
    print("  ->", per.window_text()[:30])
else: print("[period] ok", per.window_text()[:30] if per else "none")
# mode
foreground(hwnd)
for c in win.descendants():
    try:
        if "ComboBox" in c.class_name() and c.window_text() in ("每次报价","仅使用开价","1分钟OHLC"):
            u.SendMessageW(c.handle, CB_SETCURSEL, 3, 0); time.sleep(0.3); break
    except Exception: pass

def dtp_pairs(m):
    groups=defaultdict(list)
    for c in m.descendants():
        try:
            if "SysDateTimePick32" in c.class_name():
                r=c.rectangle()
                if r.width()>60: groups[r.top].append((c,r))
        except Exception: pass
    out=[]
    for top,items in groups.items():
        if len(items)>=2:
            items.sort(key=lambda x:x[1].left); out.append((items[0][0],items[1][0]))
    return out
def cur(ctrl):
    try: return ctrl.window_text()
    except Exception: return ""
def fix_seg(ctrl, field, want):
    fi={"year":0,"month":1,"day":2}[field]; want=int(want)
    for _ in range(80):
        try: parts=cur(ctrl).split("."); v=int(parts[fi])
        except Exception: return False
        if v==want: return True
        foreground(hwnd); ctrl.set_focus(); time.sleep(0.35)
        if fi==0: send_keys("{LEFT 2}"); time.sleep(0.35)
        elif fi==2: send_keys("{RIGHT 1}"); time.sleep(0.35)
        send_keys("{UP}" if want>v else "{DOWN}"); time.sleep(0.45)
    return False
def fix_date(ctrl,ty,tm,td):
    ok=fix_seg(ctrl,"year",ty); ok=fix_seg(ctrl,"month",tm) and ok; ok=fix_seg(ctrl,"day",td) and ok
    return ok
pairs=dtp_pairs(win)
if not pairs: print("FAIL dtp"); sys.exit(1)
start,stop=pairs[0]
print("start now",cur(start),"stop now",cur(stop))
fix_date(start,2020,1,1); fix_date(stop,2026,7,31)
print("after fix start",cur(start),"stop",cur(stop))

foreground(hwnd)
sh=None
for c in win.descendants():
    try:
        if "Button" in c.class_name() and c.window_text()=="开始": sh=c.handle
    except Exception: pass
if not sh: print("FAIL start btn"); sys.exit(1)
u.SendMessageW(sh,BM_CLICK,0,0); time.sleep(4.0)
def bs():
    for c in win.descendants():
        try:
            if "Button" in c.class_name() and c.window_text() in ("开始","停止"): return c.window_text()
        except Exception: pass
    return None
st=bs(); print("started",st)
t0=time.time()
for i in range(60):
    time.sleep(15); st=bs()
    if st=="开始": print("done t=%.0fs"%(time.time()-t0)); break
    if i%4==0: print("t=%.0fs %r"%(time.time()-t0,st))
else: print("timeout")
print("final",bs())
