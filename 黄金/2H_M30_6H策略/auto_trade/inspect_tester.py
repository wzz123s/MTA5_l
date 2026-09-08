# -*- coding: utf-8 -*-
"""Inspect MT5 Strategy Tester controls to locate the Start button."""
from __future__ import annotations

from pywinauto import Desktop


def find_mt5() -> object:
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        text = window.window_text()
        if "Exness" in text and "MetaTrader" not in text:
            return window
    return None


def main() -> None:
    mt5 = find_mt5()
    if mt5 is None:
        print("MT5 window not found")
        return
    print("main window:", mt5.window_text()[:80])

    print("--- top-level children ---")
    for child in mt5.children():
        try:
            rect = child.rectangle()
            print(
                repr(child.window_text()[:50]),
                child.friendly_class_name(),
                child.element_info.automation_id,
                rect.left,
                rect.top,
                rect.width(),
                rect.height(),
            )
        except Exception:  # noqa: BLE001
            continue

    tester = None
    for child in mt5.children():
        text = child.window_text()
        if any(key in text for key in ("Tester", "测试", "Strategy")):
            tester = child
            break
    if tester is None:
        print("tester panel child not found")
        return
    print("tester panel:", tester.window_text()[:60], tester.friendly_class_name())

    print("--- tester descendants (name / auto_id / rect) ---")
    seen = 0
    for desc in tester.descendants():
        try:
            ctype = desc.element_info.control_type
            if ctype not in ("Button", "SplitButton", "TabItem", "Edit", "ComboBox", "Custom", "ToolBar"):
                continue
            rect = desc.rectangle()
            if rect.width() <= 0 or rect.height() <= 0:
                continue
            print(
                ctype,
                repr(desc.window_text()[:40]),
                "auto_id=",
                desc.element_info.automation_id,
                "rect=",
                rect.left,
                rect.top,
                rect.width(),
                rect.height(),
            )
            seen += 1
            if seen > 120:
                break
        except Exception:  # noqa: BLE001
            continue
    print("printed controls:", seen)

    print("--- toolbar 1421 descendants ---")
    for desc in tester.descendants():
        try:
            if desc.element_info.automation_id == "1421":
                for item in desc.descendants():
                    rect = item.rectangle()
                    print(
                        item.element_info.control_type,
                        repr(item.window_text()[:40]),
                        "auto_id=",
                        item.element_info.automation_id,
                        "rect=",
                        rect.left,
                        rect.top,
                        rect.width(),
                        rect.height(),
                    )
        except Exception:  # noqa: BLE001
            continue

    print("--- switch to settings tab ---")
    for tab in tester.descendants():
        try:
            if tab.element_info.control_type == "TabItem" and tab.window_text() == "设置":
                tab.select()
                tab.click_input()
                print("selected 设置 tab")
                break
        except Exception:  # noqa: BLE001
            continue
    import time

    time.sleep(1.5)
    print("--- settings tab controls ---")
    seen2 = 0
    for desc in tester.descendants():
        try:
            ctype = desc.element_info.control_type
            if ctype not in ("Button", "SplitButton", "Edit", "ComboBox", "Custom", "ToolBar", "CheckBox"):
                continue
            rect = desc.rectangle()
            if rect.width() <= 0 or rect.height() <= 0:
                continue
            print(
                ctype,
                repr(desc.window_text()[:50]),
                "auto_id=",
                desc.element_info.automation_id,
                "rect=",
                rect.left,
                rect.top,
                rect.width(),
                rect.height(),
            )
            seen2 += 1
            if seen2 > 150:
                break
        except Exception:  # noqa: BLE001
            continue
    print("settings controls:", seen2)


if __name__ == "__main__":
    main()
