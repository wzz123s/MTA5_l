# -*- coding: utf-8 -*-
"""UIA backend 探索 MT5 Tester 面板, 找参数表格 InpNanRegOn."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
from pywinauto import Desktop

def find_mt5():
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        text = window.window_text()
        if "Exness" in text and "MetaTrader" not in text:
            return window
    return None

mt5 = find_mt5()
if mt5 is None:
    print("FAIL 无 MT5"); sys.exit(1)
print("MT5:", mt5.window_text()[:60])

# 找策略测试面板
tester = None
for child in mt5.children():
    try:
        if "策略测试" in child.window_text():
            tester = child
            print("找到策略测试面板:", child.element_info.control_type)
            break
    except Exception:
        pass

if tester is None:
    # 尝试打开 Tester
    from pywinauto.keyboard import send_keys
    mt5.set_focus(); time.sleep(0.5)
    send_keys("^r"); time.sleep(2)
    for child in mt5.children():
        try:
            if "策略测试" in child.window_text():
                tester = child
                break
        except Exception:
            pass

if tester is None:
    print("无策略测试面板"); sys.exit(1)

# 递归找参数 (InpNanRegOn) 相关的控件
found = []
def walk(elem, depth=0):
    if depth > 6: return
    try:
        children = elem.children()
    except Exception:
        return
    for ch in children:
        try:
            name = ch.window_text()
            ctrl = ch.element_info.control_type
            if name and (('Inp' in name) or ('参数' in name) or ('设置' in name) or ctrl in ('Edit','ListItem','DataItem','Table','Custom')):
                found.append((ctrl, name[:60], depth))
        except Exception:
            pass
        walk(ch, depth+1)

walk(tester)
print("\n=== 含 Inp/参数的控件 ===")
for ctrl, name, d in found[:50]:
    print("  [%s] d=%d %r" % (ctrl, d, name))
