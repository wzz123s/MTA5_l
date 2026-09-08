# -*- coding: utf-8 -*-
"""Best-effort Strategy Tester automation for USOIL2H_CrossConfirm_EA."""
from __future__ import annotations

import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys


def find_mt5():
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        text = window.window_text()
        if "MetaTrader" in text or "Exness" in text:
            return window
    return None


def find_tester(mt5):
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        if "策略测试" in window.window_text() or "Strategy Tester" in window.window_text():
            return window
    for child in mt5.children():
        if "策略测试" in child.window_text() or "Strategy Tester" in child.window_text():
            return child
    return None


def ensure_tester(mt5):
    for _ in range(4):
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


def dump(tester):
    seen = set()
    for desc in tester.descendants():
        try:
            ctrl = desc.element_info.control_type
            text = desc.window_text()
            auto = desc.element_info.automation_id
            key = (ctrl, text, auto)
            if key in seen:
                continue
            seen.add(key)
            print(f"{ctrl} | {text!r} | {auto!r}")
        except Exception:
            continue


def main():
    mt5 = find_mt5()
    if mt5 is None:
        print("no MT5 window found")
        return
    print("MT5 window:", mt5.window_text())
    tester = ensure_tester(mt5)
    if tester is None:
        print("tester panel not found")
        return
    print("tester:", tester.window_text())
    dump(tester)


if __name__ == "__main__":
    main()
