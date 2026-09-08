# -*- coding: utf-8 -*-
"""Open the Strategy Tester panel on the DAD3B8CC terminal and dump controls."""
from __future__ import annotations

import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys


def find_mt5():
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        text = window.window_text()
        if "Exness" in text and "MetaTrader" not in text:
            return window
    return None


def main() -> None:
    mt5 = find_mt5()
    if mt5 is None:
        print("no MT5 window")
        return
    print("found:", mt5.window_text()[:60])
    mt5.set_focus()
    time.sleep(1)
    send_keys("^r")
    time.sleep(4)
    tester = None
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        if "策略测试" in window.window_text():
            tester = window
            break
    if tester is None:
        for child in mt5.children():
            if "策略测试" in child.window_text():
                tester = child
                break
    if tester is None:
        print("tester panel not found")
        print("---- all windows ----")
        for window in desktop.windows():
            try:
                t = window.window_text()
                if t:
                    print(repr(t), "|", window.friendly_class_name())
            except Exception:
                pass
        print("---- mt5 children ----")
        for child in mt5.children():
            try:
                print(repr(child.window_text()), "|", child.friendly_class_name())
            except Exception:
                pass
        return
    print("tester:", tester.window_text())
    seen = set()
    for desc in tester.descendants():
        try:
            ctrl_type = desc.element_info.control_type
            text = desc.window_text()
            auto = desc.element_info.automation_id
            key = (ctrl_type, text, auto)
            if key in seen:
                continue
            seen.add(key)
            print(f"{ctrl_type} | text={text!r} | auto={auto!r}")
        except Exception:
            continue


if __name__ == "__main__":
    main()
