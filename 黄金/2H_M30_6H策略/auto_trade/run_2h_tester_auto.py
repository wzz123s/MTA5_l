# -*- coding: utf-8 -*-
"""Start the 2H_M30_6H current candidate backtest and watch for the ledger."""
from __future__ import annotations

import os
import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys


BASE = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"
LEDGER = os.path.join(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\B695BCB6C1E6864B6D96307B87B29F16\Agent-127.0.0.1-3000\MQL5\Files",
    "2H_M30_6H_current_candidate_trade_ledger.csv",
)


def find_mt5() -> object:
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        text = window.window_text()
        if "Exness" in text and "MetaTrader" not in text:
            for child in window.children():
                try:
                    if "策略测试" in child.window_text():
                        return window
                except Exception:  # noqa: BLE001
                    continue
    # Fall back to the XAUUSDm chart window, then any Exness window.
    for window in desktop.windows():
        text = window.window_text()
        if "Exness" in text and "MetaTrader" not in text and "XAUUSDm" in text:
            return window
    for window in desktop.windows():
        text = window.window_text()
        if "Exness" in text and "MetaTrader" not in text:
            return window
    return None


def main() -> bool:
    mt5 = find_mt5()
    if mt5 is None:
        print("MT5 Exness window not found")
        return False
    print("found MT5:", mt5.window_text()[:60])
    mt5.set_focus()
    time.sleep(1)

    send_keys("{ESC}")
    time.sleep(1)
    send_keys("^r")
    time.sleep(3)

    tester = None
    # Close the live-update welcome dialog if it is blocking the panel.
    for dialog in mt5.children():
        try:
            if dialog.friendly_class_name() == "Dialog":
                for button in dialog.descendants(control_type="Button"):
                    try:
                        name = button.window_text()
                        if any(key in name for key in ("关闭", "Close", "OK", "确定", "稍后", "Later")):
                            button.click_input()
                            print("closed dialog:", repr(name))
                            break
                    except Exception:  # noqa: BLE001
                        continue
        except Exception:  # noqa: BLE001
            continue

    for _ in range(5):
        for child in mt5.children():
            if "策略测试" in child.window_text():
                tester = child
                break
        if tester is not None:
            break
        send_keys("^r")
        time.sleep(3)
    if tester is None:
        desktop = Desktop(backend="uia")
        for window in desktop.windows():
            if "策略测试" in window.window_text():
                tester = window
                break
    if tester is None:
        print("tester panel not found")
        return False

    start = None
    for desc in tester.descendants():
        try:
            if desc.element_info.control_type == "Button" and desc.window_text() == "开始":
                start = desc
                break
        except Exception:  # noqa: BLE001
            continue
    if start is None:
        print("start button not found on current tab; switching to 设置")
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
                if desc.element_info.control_type == "Button" and desc.window_text() == "开始":
                    start = desc
                    break
            except Exception:  # noqa: BLE001
                continue
        if start is None:
            print("start button still not found")
            return False

    print("clicking Start at", start.rectangle())
    try:
        start.set_focus()
        time.sleep(0.5)
    except Exception:  # noqa: BLE001
        pass
    try:
        start.invoke()
        print("start invoked")
    except Exception:  # noqa: BLE001
        start.click_input()
        print("start clicked via mouse")
    print("start clicked; waiting for ledger")

    deadline = time.time() + 90
    while time.time() < deadline:
        if os.path.exists(LEDGER) and os.path.getsize(LEDGER) > 100:
            print("ledger ready:", LEDGER, os.path.getsize(LEDGER))
            with open(LEDGER, "r", errors="replace") as handle:
                lines = handle.read().strip().splitlines()
            print("rows:", len(lines) - 1)
            return True
        time.sleep(3)
    print("ledger not ready in time")
    return False


if __name__ == "__main__":
    main()
