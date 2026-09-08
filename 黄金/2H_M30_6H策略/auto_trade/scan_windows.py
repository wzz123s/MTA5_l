# -*- coding: utf-8 -*-
"""Scan MT5-related windows to find the Strategy Tester panel."""
from __future__ import annotations

from pywinauto import Desktop


def main() -> None:
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        text = window.window_text()
        if "Exness" not in text:
            continue
        print("==", repr(text[:90]))
        for child in window.children():
            try:
                print("   child:", repr(child.window_text()[:60]), child.friendly_class_name())
            except Exception:  # noqa: BLE001
                continue


if __name__ == "__main__":
    main()
