# -*- coding: utf-8 -*-
"""Full control dump of the MT5 Strategy Tester panel (both UIA + win32)."""
from __future__ import annotations

import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys


def find_mt5():
    for w in Desktop(backend="uia").windows():
        if "MetaTrader" in w.window_text() or "Exness" in w.window_text():
            return w
    return None


def find_tester(mt5):
    for w in Desktop(backend="uia").windows():
        t = w.window_text()
        if "策略测试" in t or "Strategy Tester" in t:
            return w
    for c in mt5.children():
        t = c.window_text()
        if "策略测试" in t or "Strategy Tester" in t:
            return c
    return None


def ensure_tester(mt5):
    for _ in range(5):
        t = find_tester(mt5)
        if t is not None:
            return t
        try:
            mt5.set_focus()
        except Exception:
            pass
        send_keys("^r")
        time.sleep(3)
    return None


def main():
    mt5 = find_mt5()
    print("MT5:", mt5.window_text() if mt5 else None)
    tester = ensure_tester(mt5)
    print("tester:", tester.window_text() if tester else None)
    if tester is None:
        return
    # move to visible position if off-screen
    try:
        rect = tester.rectangle()
        print("tester rect:", rect)
        if rect.right <= 0 or rect.bottom <= 0:
            tester.move_window(x=200, y=100, width=1200, height=800)
            print("moved tester window on-screen")
    except Exception as e:
        print("rect/move err:", e)

    seen = set()
    out = []
    for desc in tester.descendants():
        try:
            ctrl = desc.element_info.control_type
            text = desc.window_text()
            auto = desc.element_info.automation_id
            key = (ctrl, text, auto)
            if key in seen:
                continue
            seen.add(key)
            out.append(f"{ctrl} | {text!r} | {auto!r}")
        except Exception:
            continue
    print(f"controls: {len(out)}")
    for line in out:
        print(line)


if __name__ == "__main__":
    main()
