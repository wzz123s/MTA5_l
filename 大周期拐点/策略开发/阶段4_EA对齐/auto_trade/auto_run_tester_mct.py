# -*- coding: utf-8 -*-
"""auto_run_tester_mct.py —— MCT_EA Tester 自动化（复用 M4 v2 已验证方法，v2 修复强前台）。
用法: python auto_trade/auto_run_tester_mct.py --ea MCT_EA --symbol USOILm --period H4
       --from 2021.07.01 --to 2026.09.01
"""
from __future__ import annotations
import argparse
import ctypes
import ctypes.wintypes as wt
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil

sys.stdout.reconfigure(encoding="utf-8")
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

TERM_EXE = r"F:\Program Files\MetaTrader 5\terminal64.exe"
TROOT = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65")
WM_SETTEXT = 0x000C
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D
TCM_GETITEMCOUNT = 0x1304
TCM_SETCURSEL = 0x1330


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def launch_terminal_via_explorer():
    for p in psutil.process_iter(["name"]):
        if p.info["name"] == "terminal64.exe":
            log("terminal already running")
            return
    subprocess.Popen(["explorer.exe", TERM_EXE])
    log("terminal launched via explorer")
    for _ in range(40):
        time.sleep(3)
        if any(p.info["name"] == "terminal64.exe" for p in psutil.process_iter(["name"])):
            log("terminal up")
            return
    raise RuntimeError("terminal failed to start")


def find_mt5():
    EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    result = [None]

    @EnumWindowsProc
    def cb(hwnd, lparam):
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, buf, 256)
        if "Exness" in buf.value or "MetaTrader" in buf.value:
            result[0] = hwnd
            return False
        return True

    user32.EnumWindows(cb, 0)
    return result[0]


def find_by_cid(parent, cid):
    found = [None]

    def walk(p, d):
        if found[0] is not None or d > 16:
            return
        child = user32.GetWindow(p, 5)
        while child and found[0] is None:
            if user32.GetDlgCtrlID(child) == cid:
                found[0] = child
                return
            walk(child, d + 1)
            child = user32.GetWindow(child, 2)

    walk(parent, 0)
    return found[0]


def set_combo_text(mt5, cid, value):
    h = find_by_cid(mt5, cid)
    if not h:
        log("combo %d not found" % cid)
        return False
    edit = user32.GetWindow(h, 5) or h
    user32.SetFocus(edit)
    time.sleep(0.2)
    user32.SendMessageW(edit, WM_SETTEXT, 0, value)
    time.sleep(0.3)
    user32.SendMessageW(h, WM_KEYDOWN, VK_RETURN, 0)
    user32.SendMessageW(h, WM_KEYUP, VK_RETURN, 0)
    time.sleep(0.4)
    # 回读校验（编辑子控件文本）
    buf = ctypes.create_unicode_buffer(256)
    user32.GetWindowTextW(edit, buf, 256)
    log("combo %d -> %s (readback=%r)" % (cid, value, buf.value))
    return True


def activate_settings_tab(mt5):
    strips = []

    def find_strips(parent, depth):
        if depth > 10:
            return
        child = user32.GetWindow(parent, 5)
        while child:
            cls = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(child, cls, 64)
            if cls.value == "SysTabControl32":
                strips.append(child)
            find_strips(child, depth + 1)
            child = user32.GetWindow(child, 2)

    find_strips(mt5, 0)
    for strip in strips:
        n = user32.SendMessageW(strip, TCM_GETITEMCOUNT, 0, 0)
        if n == 5:
            user32.SendMessageW(strip, TCM_SETCURSEL, 1, 0)
            log("settings tab activated")
            return True
    return False


def click_button(btn_hwnd, mt5_hwnd):
    # BM_CLICK 直发（比真实鼠标可靠，M4 验证可用）
    user32.SendMessageW(btn_hwnd, 0x00F5, 0, 0)
    log("BM_CLICK sent")
    return True


def wait_ledger_stable(timeout_s=30000):
    ledger_name = "MCT_trade_ledger.csv"
    deadline = time.time() + timeout_s
    last_rows = -1
    stable_since = None
    while time.time() < deadline:
        time.sleep(15)
        led = None
        if TROOT.exists():
            for p in TROOT.rglob(ledger_name):
                led = p
                break
        if led is None:
            log("no ledger yet")
            continue
        try:
            rows = sum(1 for _ in open(led, "rb")) - 1
        except Exception:
            rows = -1
        agents = sum(1 for p in psutil.process_iter(["name"])
                     if "metatester" in str(p.info["name"]).lower())
        log("watch rows=%d agents=%d" % (rows, agents))
        if agents == 0 and rows > 0:
            if rows == last_rows:
                if stable_since is None:
                    stable_since = time.time()
                elif time.time() - stable_since > 60:
                    log("test done: %d rows" % rows)
                    return led
            else:
                stable_since = None
        else:
            stable_since = None
        last_rows = rows
    log("TIMEOUT waiting for ledger")
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ea", default="MCT_EA")
    ap.add_argument("--symbol", default="USOILm")
    ap.add_argument("--period", default="H4")
    ap.add_argument("--from", dest="from_d", default="2021.07.01")
    ap.add_argument("--to", dest="to_d", default="2026.09.01")
    args = ap.parse_args()

    launch_terminal_via_explorer()
    time.sleep(30)
    mt5 = find_mt5()
    if mt5 is None:
        log("FATAL: no MT5 window")
        return 1
    user32.MoveWindow(mt5, 0, -57, 2048, 1157, True)
    time.sleep(2)

    # 强前台
    tid = user32.GetWindowThreadProcessId(mt5, None)
    cur = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(cur, tid, True)
    user32.BringWindowToTop(mt5)
    user32.SetForegroundWindow(mt5)
    user32.AttachThreadInput(cur, tid, False)
    time.sleep(1)

    VK_CONTROL, VK_R = 0x11, 0x52

    def send_ctrl_r():
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_R, 0, 0, 0)
        user32.keybd_event(VK_R, 0, 2, 0)
        user32.keybd_event(VK_CONTROL, 0, 2, 0)
        time.sleep(8)

    # 面板开关循环（最多 3 次）
    opened = False
    for _ in range(3):
        send_ctrl_r()
        if find_by_cid(mt5, 10485) is not None and find_by_cid(mt5, 16790) is not None:
            log("panel open")
            opened = True
            break
    if not opened:
        log("FATAL: panel did not open")
        return 6

    set_combo_text(mt5, 10485, "Experts\\Advisors\\%s.ex5" % args.ea)
    set_combo_text(mt5, 10486, args.symbol)
    set_combo_text(mt5, 10487, args.period)
    set_combo_text(mt5, 10550, args.from_d)
    set_combo_text(mt5, 10551, args.to_d)
    activate_settings_tab(mt5)
    time.sleep(2)
    btn = find_by_cid(mt5, 16790)
    if btn is None:
        log("FATAL: start button not found")
        return 2
    # 恢复窗口再点击（窗口可能被最小化）
    clicked = False
    for attempt in range(3):
        user32.ShowWindow(mt5, 9)          # SW_RESTORE
        user32.MoveWindow(mt5, 0, -57, 2048, 1157, True)
        time.sleep(1.5)
        tid = user32.GetWindowThreadProcessId(mt5, None)
        cur = kernel32.GetCurrentThreadId()
        user32.AttachThreadInput(cur, tid, True)
        user32.BringWindowToTop(mt5)
        user32.SetForegroundWindow(mt5)
        user32.AttachThreadInput(cur, tid, False)
        time.sleep(1)
        btn = find_by_cid(mt5, 16790)
        if btn is None:
            log("retry %d: button gone" % attempt)
            continue
        if click_button(btn, mt5):
            clicked = True
            break
        log("retry %d: button covered" % attempt)
    if not clicked:
        log("FATAL: button click failed after retries")
        return 3
    time.sleep(4)
    buf = ctypes.create_unicode_buffer(64)
    user32.GetWindowTextW(btn, buf, 64)
    log("button now: %r" % buf.value)
    if "停止" not in buf.value:
        log("FATAL: test did not start")
        return 4
    log("TEST STARTED")
    led = wait_ledger_stable()
    if led is None:
        return 5
    dst = Path(__file__).resolve().parents[1] / "data" / "validation" / "tester_actual_mct.csv"
    shutil.copy2(led, dst)
    log("ledger copied: %s -> %s" % (led, dst))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
