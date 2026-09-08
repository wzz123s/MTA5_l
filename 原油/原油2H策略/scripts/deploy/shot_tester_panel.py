# -*- coding: utf-8 -*-
"""Capture the MT5 tester panel region to PNG for visual inspection."""
from __future__ import annotations

import sys
import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys

import ctypes


def grab(x, y, w, h, path):
    import ctypes.wintypes
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    hwnd = user32.GetDesktopWindow()
    hdc = user32.GetWindowDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    gdi32.BitBlt(mem, 0, 0, w, h, hdc, x, y, 0x00CC0020)
    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", ctypes.c_uint32),
            ("biWidth", ctypes.c_int32),
            ("biHeight", ctypes.c_int32),
            ("biPlanes", ctypes.c_uint16),
            ("biBitCount", ctypes.c_uint16),
            ("biCompression", ctypes.c_uint32),
            ("biSizeImage", ctypes.c_uint32),
            ("biXPelsPerMeter", ctypes.c_int32),
            ("biYPelsPerMeter", ctypes.c_int32),
            ("biClrUsed", ctypes.c_uint32),
            ("biClrImportant", ctypes.c_uint32),
        ]
    bih = BITMAPINFOHEADER()
    bih.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bih.biWidth = w
    bih.biHeight = -h
    bih.biPlanes = 1
    bih.biBitCount = 32
    bufsize = w * h * 4
    buf = ctypes.create_string_buffer(bufsize)
    gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bih), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mem)
    user32.ReleaseDC(hwnd, hdc)
    # write BMP (54-byte header + pixel data)
    import struct
    header = b"BM" + struct.pack("<IHHI", 54 + bufsize, 0, 0, 54)
    header += struct.pack("<IiiHHIIiiII", 40, w, h, 1, 32, 0, bufsize, 2835, 2835, 0, 0)
    with open(path, "wb") as f:
        f.write(header + buf.raw)
    print("saved", path)


def main():
    mt5 = None
    for w in Desktop(backend="uia").windows():
        t = w.window_text()
        if "MetaTrader" in t or "Exness" in t:
            mt5 = w
            break
    if mt5 is None:
        print("no MT5")
        return
    def find_tester():
        for w in Desktop(backend="uia").windows():
            if "策略测试" in w.window_text() or "Strategy Tester" in w.window_text():
                return w
        for child in mt5.descendants():
            try:
                if "策略测试" in child.window_text() or "Strategy Tester" in child.window_text():
                    return child
            except Exception:
                continue
        return None

    found = find_tester()
    if found is None:
        mt5.set_focus()
        send_keys("^r")
        time.sleep(3)
        found = find_tester()
    if found is None:
        print("tester window not found; capturing main window bottom strip anyway")
        rect = mt5.rectangle()
        w = min(rect.width(), 2560)
        y0 = max(0, rect.bottom - 260)
        h = min(260, 1536 - y0)
        grab(max(0, rect.left), y0, w, h, sys.argv[1] if len(sys.argv) > 1 else r"F:\use_code\MTA5_l\原油\原油2H策略\scripts\deploy\tester_panel_shot.bmp")
        return
    rect = found.rectangle()
    print("tester rect:", rect)
    if rect.width() <= 0 or rect.height() <= 0:
        rect = mt5.rectangle()
        y0 = max(0, rect.bottom - 260)
        w = min(rect.width(), 2560)
        h = min(260, 1536 - y0)
        grab(max(0, rect.left), y0, w, h, sys.argv[1] if len(sys.argv) > 1 else r"F:\use_code\MTA5_l\原油\原油2H策略\scripts\deploy\tester_panel_shot.bmp")
        return
    y0 = max(0, rect.top - 60)
    x0 = max(0, rect.left)
    w = min(rect.width(), 2560)
    h = min(rect.height() + 60, 1536 - y0)
    grab(x0, y0, w, h, sys.argv[1] if len(sys.argv) > 1 else r"F:\use_code\MTA5_l\原油\原油2H策略\scripts\deploy\tester_panel_shot.bmp")


if __name__ == "__main__":
    main()
