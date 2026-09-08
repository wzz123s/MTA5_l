# -*- coding: utf-8 -*-
"""v37: 读模式 ComboBox items + 尝试 select"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
from pywinauto import Desktop

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

mt5 = find_mt5()
if mt5 is None:
    print("FAIL"); sys.exit(1)

# 找模式 ComboBox（含 OHLC 或 开价 或 报价）
for c in mt5.descendants():
    try:
        if "ComboBox" in c.class_name():
            txt = c.window_text()
            if txt and any(k in txt for k in ["OHLC", "开价", "报价", "实时"]):
                r = c.rectangle()
                print("模式 ComboBox: %r rect=(%d,%d) visible=%s" % (txt, r.left, r.top, c.is_visible()))
                # 读 items
                try:
                    items = c.item_texts()
                    print("  items:", items)
                except Exception as e:
                    print("  item_texts FAIL:", e)
                # 尝试 select
                for target in ["仅使用开价", "仅开盘价", "Open prices only", "仅用开盘价"]:
                    try:
                        c.select(target)
                        time.sleep(0.4)
                        print("  select %r -> %r" % (target, c.window_text()))
                        break
                    except Exception as e:
                        print("  select %r FAIL: %s" % (target, str(e)[:60]))
    except Exception:
        pass
