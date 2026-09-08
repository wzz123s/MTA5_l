# -*- coding: utf-8 -*-
"""Win32 control dump of the MT5 tester panel (find Start button etc.)."""
from __future__ import annotations

import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys


def main():
    def all_windows():
        return Desktop(backend="uia").windows()

    mt5 = None
    for w in all_windows():
        t = w.window_text()
        if "MetaTrader" in t or "Exness" in t:
            mt5 = w
            break
    if mt5 is None:
        print("no MT5 window")
        return
    print("MT5:", mt5.window_text())
    found = None
    for w in all_windows():
        t = w.window_text()
        if "策略测试" in t or "Strategy Tester" in t:
            found = w
            break
    if found is None:
        # search children of the MT5 main window
        for child in mt5.descendants():
            try:
                t = child.window_text()
                if "策略测试" in t or "Strategy Tester" in t:
                    found = child
                    break
            except Exception:
                continue
    if found is None:
        mt5.set_focus()
        send_keys("^r")
        time.sleep(3)
        for w in all_windows():
            t = w.window_text()
            if "策略测试" in t or "Strategy Tester" in t:
                found = w
                break
        if found is None:
            for child in mt5.descendants():
                try:
                    t = child.window_text()
                    if "策略测试" in t or "Strategy Tester" in t:
                        found = child
                        break
                except Exception:
                    continue
    if found is None:
        print("tester panel not found")
        return
    print("tester:", found.window_text())
    handle = found.handle
    print("tester handle:", handle)
    from pywinauto.application import Application
    app = Application(backend="win32").connect(handle=handle)
    wrapper = app.window(handle=handle)
    # ensure on-screen: restore + move main window into visible area
    try:
        main_rect = mt5.rectangle()
        print("main rect:", main_rect)
        if main_rect.right > 2040 or main_rect.bottom > 1140:
            from ctypes import windll
            windll.user32.ShowWindow(mt5.handle, 9)  # SW_RESTORE
            time.sleep(1)
            windll.user32.MoveWindow(mt5.handle, 0, 0, 2048, 1152, True)
            time.sleep(2)
            print("moved main window on-screen")
    except Exception as e:
        print("move err:", e)

    print("descendants (win32):")
    seen = set()
    for child in wrapper.descendants():
        try:
            txt = child.window_text()
            cls = child.class_name()
            cid = child.control_id()
            key = (cls, cid, txt)
            if key in seen:
                continue
            seen.add(key)
            try:
                r = child.rectangle()
                rect = f"({r.left},{r.top},{r.right},{r.bottom})"
            except Exception:
                rect = "?"
            print(f"  class={cls} cid={cid} rect={rect} text={txt!r}")
        except Exception:
            continue


if __name__ == "__main__":
    main()
