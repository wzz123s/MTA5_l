# -*- coding: utf-8 -*-
"""Read current MT5 Tester panel values and look for popup dialogs."""
from __future__ import annotations

import time

from pywinauto import Desktop


def find_mt5() -> object:
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        text = window.window_text()
        if "Exness" in text and "MetaTrader" not in text:
            return window
    return None


def main() -> None:
    desktop = Desktop(backend="uia")
    print("--- all top windows ---")
    for window in desktop.windows():
        print("win:", repr(window.window_text()[:70]))

    mt5 = find_mt5()
    if mt5 is None:
        print("MT5 not found")
        return

    tester = None
    for child in mt5.children():
        if child.window_text() == "策略测试":
            tester = child
            break
    if tester is None:
        print("tester panel not found")
        return

    for desc in tester.descendants():
        try:
            if desc.element_info.control_type == "TabItem" and desc.window_text() == "设置":
                desc.select()
                desc.click_input()
                break
        except Exception:  # noqa: BLE001
            continue
    time.sleep(1.5)

    print("--- tester combo/edit values ---")
    for desc in tester.descendants():
        try:
            ctype = desc.element_info.control_type
            if ctype not in ("ComboBox", "Edit", "CheckBox", "Button"):
                continue
            name = desc.window_text()
            rect = desc.rectangle()
            if rect.width() <= 0 or rect.height() <= 0:
                continue
            extra = ""
            if ctype == "Button" and name == "开始":
                try:
                    extra = "enabled=" + str(desc.is_enabled())
                except Exception:  # noqa: BLE001
                    extra = "enabled=?"
            print(ctype, repr(name[:40]), "auto_id=", desc.element_info.automation_id, extra)
        except Exception:  # noqa: BLE001
            continue


if __name__ == "__main__":
    main()
