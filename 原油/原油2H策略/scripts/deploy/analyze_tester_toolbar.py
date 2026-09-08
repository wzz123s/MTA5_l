# -*- coding: utf-8 -*-
"""Capture + analyze the MT5 tester toolbar strip to locate Start button & fields."""
from __future__ import annotations

import struct
import sys
import time

from pywinauto import Desktop
from pywinauto.keyboard import send_keys

import ctypes


def grab(x, y, w, h):
    import ctypes.wintypes
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    hwnd = user32.GetDesktopWindow()
    hdc = user32.GetWindowDC(hwnd)
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mem, bmp)
    gdi32.BitBlt(mem, 0, 0, w, h, hdc, x, y, 0x00CC0020)
    class BH(ctypes.Structure):
        _fields_ = [
            ("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
            ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
            ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
            ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
            ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
            ("biClrImportant", ctypes.c_uint32),
        ]
    bih = BH()
    bih.biSize = ctypes.sizeof(BH)
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
    return buf.raw


def pixels(raw, w, h):
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            o = (y * w + x) * 4
            b = raw[o]; g = raw[o + 1]; r = raw[o + 2]
            row.append((r, g, b))
        out.append(row)
    return out


def main():
    mt5 = None
    for w in Desktop(backend="uia").windows():
        if "MetaTrader" in w.window_text() or "Exness" in w.window_text():
            mt5 = w
            break
    if mt5 is None:
        print("no MT5")
        return
    r = mt5.rectangle()
    print("main rect:", r)
    # toolbar strip: assume tester panel top around y=469; strip y=410..480
    y0 = 405
    h = 90
    x0 = 40
    w = min(r.width(), 2000)
    raw = grab(x0, y0, w, h)
    px = pixels(raw, w, h)

    # scan rows 30..60 for green (Start button) and structure
    print("=== green pixels (Start button candidate) ===")
    greens = []
    for y in range(20, 70):
        for x in range(w):
            rr, gg, bb = px[y][x]
            if gg > 90 and gg > rr + 30 and gg > bb + 30:
                greens.append((x, y))
    if greens:
        xs = [g[0] for g in greens]
        ys = [g[1] for g in greens]
        print(f"green cluster x=[{min(xs)},{max(xs)}] y=[{min(ys)},{max(ys)}] n={len(greens)} screen_x=[{x0+min(xs)},{x0+max(xs)}]")
    else:
        print("no green pixels found in strip")

    # vertical edges: count strong horizontal color transitions per column
    print("=== column edge profile (y=30..60) ===")
    edges = []
    for x in range(1, w):
        diff = 0
        for y in range(30, 60):
            a = px[y][x - 1]; b = px[y][x]
            diff += abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2])
        if diff > 400:
            edges.append(x)
    # merge consecutive
    groups = []
    for e in edges:
        if groups and e - groups[-1][-1] <= 2:
            groups[-1].append(e)
        else:
            groups.append([e])
    for g in groups:
        if len(g) >= 2:
            print(f"  edge group x=[{g[0]},{g[-1]}] -> screen x=[{x0+g[0]},{x0+g[-1]}]")
    print("edges:", edges[:120])

    # coarse ASCII map of green density per 20px column bucket in strip y=410..460
    print("=== green density map (strip y=410..460, bucket 20px) ===")
    for y in range(0, 50, 5):
        line = []
        for x in range(0, w, 10):
            rr, gg, bb = px[y][x]
            if gg > 70 and gg > rr + 20 and gg > bb + 20:
                line.append("#")
            else:
                line.append(".")
        print(f"y={y0+y}: " + "".join(line))


if __name__ == "__main__":
    main()
