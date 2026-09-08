# -*- coding: utf-8 -*-
"""Strategy Tester smoke run for 2H_M30_6H_ABC_EA (2025-2026).

Configures the tester panel on the DAD3B8CC terminal and starts a backtest
with "Open prices only". Writes the EA ledger to the tester Files folder.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



import os
import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys


BASE = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65"
LEDGER = os.path.join(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000\MQL5\Files",
    "2H_M30_6H_abc_trade_ledger.csv",
)
EANAME = "2H_M30_6H_ABC_EA"


def find_mt5():
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        text = window.window_text()
        if "Exness" in text and "MetaTrader" not in text:
            return window
    return None


def find_tester(mt5):
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        if "策略测试" in window.window_text():
            return window
    for child in mt5.children():
        if "策略测试" in child.window_text():
            return child
    return None


def ensure_tester(mt5) -> object:
    for _ in range(4):
        tester = find_tester(mt5)
        if tester is not None:
            return tester
        mt5.set_focus()
        send_keys("^r")
        time.sleep(3)
    return None


def dump_controls(tester):
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
            print(f"  {ctrl_type} | {text!r} | {auto!r}")
        except Exception:
            continue


def click_settings(tester) -> bool:
    for desc in tester.descendants():
        try:
            if desc.element_info.control_type == "TabItem" and desc.window_text() in ("设置", "Settings"):
                desc.select()
                desc.click_input()
                time.sleep(1.5)
                return True
        except Exception:
            continue
    return False


def main() -> bool:
    mt5 = find_mt5()
    if mt5 is None:
        print("no MT5 window")
        return False
    tester = ensure_tester(mt5)
    if tester is None:
        print("tester panel not found")
        return False
    print("tester found:", tester.window_text())
    if click_settings(tester):
        print("settings tab clicked")
    dump_controls(tester)
    return True


if __name__ == "__main__":
    main()
