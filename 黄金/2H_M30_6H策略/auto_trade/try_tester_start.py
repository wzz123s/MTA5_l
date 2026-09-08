# -*- coding: utf-8 -*-
"""Try to start the MT5 Strategy Tester through UIA and wait for the ledger.

The terminal keeps the last Tester panel settings in terminal.ini; this helper
only opens the panel and attempts to invoke the Start button.  It is a fallback
for the fully manual click that MT5 sometimes requires.
"""
from __future__ import annotations

import os
import time
from pywinauto import Desktop
from pywinauto.keyboard import send_keys


BASE = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"
LEDGER_PATHS = [
    os.path.join(BASE, "MQL5", "Files", "2H_M30_6H_current_candidate_trade_ledger.csv"),
    os.path.join(
        r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\Common\Files",
        "2H_M30_6H_current_candidate_trade_ledger.csv",
    ),
]


def find_mt5() -> object:
    desktop = Desktop(backend="uia")
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
    print("found MT5 window:", mt5.window_text()[:60])
    mt5.set_focus()
    time.sleep(1)

    print("opening Strategy Tester with Ctrl+R")
    send_keys("^r")
    time.sleep(4)

    buttons = []
    try:
        for desc in mt5.descendants(control_type="Button"):
            buttons.append((desc.window_text(), desc))
    except Exception as exc:  # noqa: BLE001
        print("button enumeration failed:", exc)
    print("buttons found:", len(buttons))
    for name, _ in buttons[:60]:
        print("  button:", repr(name))

    start = None
    for name, desc in buttons:
        if any(key in name for key in ("Start", "开始", "Run")):
            start = desc
            print("using start button:", repr(name))
            break

    clicked = False
    if start is not None:
        for method in ("invoke", "click", "click_input"):
            try:
                getattr(start, method)()
                print("start button", method, "ok")
                clicked = True
                break
            except Exception as exc:  # noqa: BLE001
                print("start button", method, "failed:", exc)
    if not clicked:
        print("fallback: pressing Enter")
        send_keys("{ENTER}")

    print("waiting up to 120s for ledger")
    deadline = time.time() + 120
    while time.time() < deadline:
        for path in LEDGER_PATHS:
            if os.path.exists(path) and os.path.getsize(path) > 100:
                print("ledger ready:", path, os.path.getsize(path))
                with open(path, "r", errors="replace") as handle:
                    lines = handle.read().strip().splitlines()
                print("rows:", len(lines) - 1)
                return True
        time.sleep(2)

    print("no ledger after 120s")
    return False


if __name__ == "__main__":
    main()
