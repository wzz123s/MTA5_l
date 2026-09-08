# -*- coding: utf-8 -*-
"""Open the MT5 Strategy Tester panel via the View menu."""
from __future__ import annotations

import time

from pywinauto import Desktop


def find_exness() -> object:
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        text = window.window_text()
        if "Exness" in text and "MetaTrader" not in text:
            return window
    return None


def has_panel(window: object) -> bool:
    for child in window.children():
        try:
            if "策略测试" in child.window_text():
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def main() -> bool:
    window = find_exness()
    if window is None:
        print("no Exness window")
        return False
    window.set_focus()
    time.sleep(1)
    if has_panel(window):
        print("panel already open")
        return True

    # Open the View menu via keyboard (Alt+V is the localized View menu).
    from pywinauto.keyboard import send_keys

    send_keys("%v")
    time.sleep(1.5)
    items = []
    for desc in window.descendants(control_type="MenuItem"):
        try:
            name = desc.window_text()
            items.append((name, desc))
            if "策略测试" in name or "Strategy Tester" in name:
                desc.click_input()
                print("clicked menu item:", repr(name))
                time.sleep(2)
                return has_panel(window)
        except Exception:  # noqa: BLE001
            continue
    print("view menu items seen:", [name for name, _ in items[:40]])
    # Fallback: toggle with Ctrl+R a few times, checking each time.
    for _ in range(4):
        send_keys("^r")
        time.sleep(4)
        if has_panel(window):
            print("panel opened via Ctrl+R")
            return True
    print("panel not opened")
    return False


if __name__ == "__main__":
    main()
