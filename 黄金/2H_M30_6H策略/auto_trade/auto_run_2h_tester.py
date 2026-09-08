# -*- coding: utf-8 -*-
"""Open the Strategy Tester panel, click Start, and wait for the 2H ledger."""
from __future__ import annotations

import os
import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys


AGENT_ROOTS = [
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\B695BCB6C1E6864B6D96307B87B29F16\Agent-127.0.0.1-3000\MQL5\Files",
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\B695BCB6C1E6864B6D96307B87B29F16\Agent-127.0.0.1-3001\MQL5\Files",
]
LEDGERS = [os.path.join(root, "2H_M30_6H_current_candidate_trade_ledger.csv") for root in AGENT_ROOTS]
TERMINAL_PID = 10436


def find_window_with_panel() -> object:
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        try:
            if window.element_info.process_id != TERMINAL_PID:
                continue
        except Exception:  # noqa: BLE001
            continue
        text = window.window_text()
        if "Exness" not in text or "MetaTrader" in text:
            continue
        for child in window.children():
            try:
                if "策略测试" in child.window_text():
                    return window
            except Exception:  # noqa: BLE001
                continue
    return None


def find_terminal_window() -> object:
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        try:
            if window.element_info.process_id == TERMINAL_PID:
                return window
        except Exception:  # noqa: BLE001
            continue
    return None


def open_via_menu(window: object) -> bool:
    window.set_focus()
    time.sleep(1)
    send_keys("%v")
    time.sleep(1.5)
    for desc in window.descendants(control_type="MenuItem"):
        try:
            if "策略测试" in desc.window_text():
                desc.click_input()
                time.sleep(3)
                return True
        except Exception:  # noqa: BLE001
            continue
    return False


def main() -> bool:
    for ledger in LEDGERS:
        if os.path.exists(ledger):
            try:
                os.remove(ledger)
            except OSError:
                pass

    window = find_window_with_panel()
    if window is None:
        print("panel not open; opening via View menu")
        any_window = find_terminal_window()
        if any_window is None:
            print("no Exness window")
            return False
        open_via_menu(any_window)
        window = find_window_with_panel()
        if window is None:
            print("panel still not open after menu")
            return False

    print("panel window:", window.window_text()[:60])
    tester = None
    for child in window.children():
        if "策略测试" in child.window_text():
            tester = child
            break

    start = None
    for desc in tester.descendants():
        try:
            if desc.element_info.control_type == "Button" and desc.window_text() == "开始":
                start = desc
                break
            if desc.element_info.control_type == "Button" and desc.window_text() == "停止":
                print("tester is in running/stopped state; clicking 停止 first")
                desc.click_input()
                time.sleep(3)
        except Exception:  # noqa: BLE001
            continue
    if start is None:
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
        print("start button not found")
        return False

    print("clicking Start")
    try:
        start.set_focus()
        time.sleep(0.3)
    except Exception:  # noqa: BLE001
        pass
    try:
        start.invoke()
        print("start invoked")
    except Exception:  # noqa: BLE001
        start.click_input()
        print("start clicked via mouse")

    deadline = time.time() + 120
    while time.time() < deadline:
        for ledger in LEDGERS:
            if os.path.exists(ledger) and os.path.getsize(ledger) > 100:
                print("ledger ready:", ledger, os.path.getsize(ledger))
                with open(ledger, "r", errors="replace") as handle:
                    lines = handle.read().strip().splitlines()
                print("rows:", len(lines) - 1)
                return True
        time.sleep(2)
    print("ledger not ready in time")
    return False


if __name__ == "__main__":
    main()
