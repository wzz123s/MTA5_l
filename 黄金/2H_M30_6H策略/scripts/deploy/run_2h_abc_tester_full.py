# -*- coding: utf-8 -*-
"""v34: 完整配置 EA/品种/周期/模式 + 点开始"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

def find_mt5():
    d = Desktop(backend="win32")
    for w in d.windows():
        try:
            t = w.window_text()
            if t and "Exness" in t and "[" in t:
                return w
        except Exception:
            pass
    return None

def find_combo(mt5, text_match):
    for c in mt5.descendants():
        try:
            if "ComboBox" in c.class_name():
                txt = c.window_text()
                if text_match in txt:
                    return c
        except Exception:
            pass
    return None

def set_combo_keys(combo, value):
    try:
        combo.click_input()
        time.sleep(0.5)
        send_keys(value, with_spaces=True)
        time.sleep(0.5)
        send_keys("{ENTER}")
        time.sleep(0.5)
        return True
    except Exception as e:
        print("  set FAIL:", e)
        return False

mt5 = find_mt5()
if mt5 is None:
    print("FAIL"); sys.exit(1)

# 1. EA: MCT_EA -> 2H_M30_6H_ABC_EA
ea = find_combo(mt5, "Advisors")
if ea:
    print("[EA] 当前: %r" % ea.window_text())
    set_combo_keys(ea, "2H_M30_6H_ABC_EA")
    print("  -> %r" % ea.window_text())
else:
    print("[EA] 未找到")

# 2. 品种: USOILm -> XAUUSDm
sym = find_combo(mt5, "USOILm")
if sym is None:
    sym = find_combo(mt5, "XAUUSDm")
if sym:
    print("[品种] 当前: %r" % sym.window_text())
    set_combo_keys(sym, "XAUUSDm")
    print("  -> %r" % sym.window_text())
else:
    print("[品种] 未找到")

# 3. 周期: H4 -> M30 (用 select)
per = find_combo(mt5, "H4")
if per is None:
    per = find_combo(mt5, "M30")
if per:
    print("[周期] 当前: %r" % per.window_text())
    try:
        per.select("M30")
        time.sleep(0.5)
        print("  select -> %r" % per.window_text())
    except Exception as e:
        print("  select FAIL:", e, "改用 keys")
        set_combo_keys(per, "M30")
        print("  -> %r" % per.window_text())
else:
    print("[周期] 未找到")

# 4. 模式: 每次报价 -> 仅使用开价
mode = find_combo(mt5, "每次报价")
if mode is None:
    mode = find_combo(mt5, "仅使用开价")
if mode:
    print("[模式] 当前: %r" % mode.window_text())
    try:
        mode.select("仅使用开价")
        time.sleep(0.5)
        print("  select -> %r" % mode.window_text())
    except Exception as e:
        print("  select FAIL:", e)
else:
    print("[模式] 未找到")

# 5. 读回全部关键配置
print("\n=== 最终配置 ===")
for c in mt5.descendants():
    try:
        cls = c.class_name()
        txt = c.window_text()
        if "ComboBox" in cls and txt and any(k in txt for k in ["Advisors", "XAUUSDm", "USOILm", "M30", "H4", "仅使用开价", "每次报价"]):
            r = c.rectangle()
            print("  ComboBox %r (%d,%d)" % (txt, r.left, r.top))
        if "SysDateTimePick32" in cls:
            r = c.rectangle()
            print("  DateTime %r (%d,%d)" % (txt, r.left, r.top))
    except Exception:
        pass
