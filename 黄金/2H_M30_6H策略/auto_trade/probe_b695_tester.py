# -*- coding: utf-8 -*-
"""Probe the EXNESS (B695, PID 10436) Strategy Tester panel values."""
from __future__ import annotations

import time

from pywinauto import Desktop


def main() -> None:
    desktop = Desktop(backend="uia")
    target = None
    for window in desktop.windows():
        try:
            if window.element_info.process_id == 10436:
                target = window
                break
        except Exception:  # noqa: BLE001
            continue
    if target is None:
        print("B695 window not found")
        return
    print("window:", target.window_text()[:70])

    tester = None
    for child in target.children():
        if "策略测试" in child.window_text():
            tester = child
            break
    if tester is None:
        print("tester panel not found in B695")
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

    for desc in tester.descendants():
        try:
            ctype = desc.element_info.control_type
            if ctype not in ("ComboBox", "Button", "Edit"):
                continue
            name = desc.window_text()
            auto_id = desc.element_info.automation_id
            if auto_id in ("10485", "10486", "10123", "10489", "10559", "10473", "16790"):
                try:
                    value = desc.selected_text() if ctype == "ComboBox" else desc.get_value()
                except Exception:  # noqa: BLE001
                    value = "?"
                print(ctype, auto_id, repr(name[:30]), "=>", repr(str(value)[:80]))
        except Exception:  # noqa: BLE001
            continue


if __name__ == "__main__":
    main()
