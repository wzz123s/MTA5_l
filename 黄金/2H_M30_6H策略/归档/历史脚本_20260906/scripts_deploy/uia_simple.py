# -*- coding: utf-8 -*-
"""简化 UIA: 找 MT5 + 策略测试面板 + 参数控件."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
from pywinauto import Desktop
from pywinauto.keyboard import send_keys

desktop = Desktop(backend="uia")
mt5 = None
for window in desktop.windows():
    text = window.window_text()
    if "Exness" in text and "MetaTrader" not in text:
        mt5 = window
        break

if mt5 is None:
    print("FAIL 无 MT5"); sys.exit(1)
print("MT5:", mt5.window_text()[:50])

# 找策略测试面板
tester = None
try:
    for child in mt5.children():
        if "策略测试" in child.window_text():
            tester = child
            break
except Exception:
    pass
if tester is None:
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
print("策略测试面板:", tester.window_text()[:30])

# 打印面板的直接子控件
print("\n=== 面板子控件 ===")
try:
    for child in tester.children():
        try:
            t = child.window_text()
            ct = child.element_info.control_type
            if t:
                print("  [%s] %r" % (ct, t[:50]))
        except Exception:
            pass
except Exception as e:
    print("children err:", e)
