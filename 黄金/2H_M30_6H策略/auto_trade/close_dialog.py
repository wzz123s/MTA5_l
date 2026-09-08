# -*- coding: utf-8 -*-
"""Close stray top-level dialogs that may block MT5 automation."""
from __future__ import annotations

from pywinauto import Desktop


def main() -> None:
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        text = window.window_text()
        if text in ("快速设置", "欢迎来到实时更新") or "实时更新" in text:
            print("closing dialog:", repr(text))
            for button in window.descendants(control_type="Button"):
                try:
                    name = button.window_text()
                    if name in ("关闭", "Close", "OK", "确定", "稍后", "Later"):
                        button.click_input()
                        print("clicked:", repr(name))
                        break
                except Exception:  # noqa: BLE001
                    continue


if __name__ == "__main__":
    main()
