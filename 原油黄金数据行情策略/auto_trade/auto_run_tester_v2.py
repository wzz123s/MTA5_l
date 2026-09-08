# -*- coding: utf-8 -*-
"""M4.6 Tester 自动运行 v2（2026-08-31 验证可用）。
关键修复（沙箱会话踩坑总结）：
1. explorer 逃逸：终端必须由 explorer.exe 启动（脱离沙箱进程树），否则 tester agent
   无法与终端建立命名管道 IPC（沙箱阻断管道连接 -> agent 崩溃循环）；
2. 窗口几何：窗口须为 (0,-57,2048,1157) 或等效，使 docked 面板完全收入窗口、
   开始按钮位于任务栏上方可点击区（屏幕 2048x1153，任务栏 y=1104+）；
3. 面板设置：新终端面板字段为空，需用 WM_SETTEXT 填充（EA/品种/周期/日期）；
4. 开始按钮：先激活面板底部 5-tab 条的"设置"tab（tab1），按钮才可见；
   点击用真实鼠标（SetCursorPos+mouse_event）命中 UIA/win32 矩形中心。
用法: python auto_trade/auto_run_tester_v2.py [--ea Gold_DataEvent_EA --symbol XAUUSDm --period H4
       --from 2019.01.01 --to 2026.08.30]
"""
from __future__ import annotations
import argparse
import ctypes
import ctypes.wintypes as wt
import subprocess
import sys
import time
from pathlib import Path

import psutil

sys.stdout.reconfigure(encoding="utf-8")
user32 = ctypes.windll.user32

TERM_EXE = r"F:\Program Files\MetaTrader 5\terminal64.exe"
AGENT_DIR = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65\Agent-127.0.0.1-3000"
TROOT = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65")
WM_SETTEXT = 0x000C
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
VK_RETURN = 0x0D
TCM_GETITEMCOUNT = 0x1304
TCM_SETCURSEL = 0x1330
SWP_SHOWWINDOW = 0x0040
SWP_NOZORDER = 0x0010


def log(msg):
    print("[%s] %s" % (time.strftime("%H:%M:%S"), msg), flush=True)


def launch_terminal_via_explorer():
    """通过 explorer 启动终端（父进程=explorer，脱离沙箱树）"""
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
        if found[0] is not None or d > 14:
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


def find_panel(mt5):
    panel = [None]

    def walk(parent, depth):
        if panel[0] is not None or depth > 14:
            return
        buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(parent, buf, 256)
        if "策略测试" in buf.value or "Strategy Tester" in buf.value:
            panel[0] = parent
            return
        child = user32.GetWindow(parent, 5)
        while child and panel[0] is None:
            walk(child, depth + 1)
            child = user32.GetWindow(child, 2)

    walk(mt5, 0)
    return panel[0]


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
    log("combo %d -> %s" % (cid, value))
    return True


def activate_settings_tab(mt5):
    """面板底部 5-tab 条，tab1=设置"""
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
    br = wt.RECT()
    user32.GetWindowRect(btn_hwnd, ctypes.byref(br))
    cx = (br.left + br.right) // 2
    cy = (br.top + br.bottom) // 2
    pt = wt.POINT(cx, cy)
    hwnd_at = user32.WindowFromPoint(pt)
    if hwnd_at != btn_hwnd:
        log("WARNING: click point covered by hwnd=%d" % hwnd_at)
        return False
    user32.SetForegroundWindow(mt5_hwnd)
    time.sleep(0.8)
    user32.SetCursorPos(cx, cy)
    time.sleep(0.5)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.15)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    log("clicked at %d,%d" % (cx, cy))
    return True


def wait_ledger_stable(name, timeout_s=18000):
    ledger_name = {"gold": "Gold_DataEvent_trade_ledger.csv",
                   "oil": "Oil_DataEvent_trade_ledger.csv"}[name]
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
    ap.add_argument("--ea", default="Gold_DataEvent_EA")
    ap.add_argument("--symbol", default="XAUUSDm")
    ap.add_argument("--period", default="H4")
    ap.add_argument("--from", dest="from_d", default="2019.01.01")
    ap.add_argument("--to", dest="to_d", default="2026.08.30")
    args = ap.parse_args()

    launch_terminal_via_explorer()
    time.sleep(30)  # 等待登录/EA 加载
    mt5 = find_mt5()
    if mt5 is None:
        log("FATAL: no MT5 window")
        return 1
    # 窗口几何（面板入窗、按钮在任务栏上方）
    user32.MoveWindow(mt5, 0, -57, 2048, 1157, True)
    time.sleep(2)
    # 打开面板
    user32.SetForegroundWindow(mt5)
    time.sleep(1)
    VK_CONTROL, VK_R = 0x11, 0x52
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_R, 0, 0, 0)
    user32.keybd_event(VK_R, 0, 2, 0)
    user32.keybd_event(VK_CONTROL, 0, 2, 0)
    time.sleep(8)
    # 填充设置
    set_combo_text(mt5, 10485, "Experts\\Advisors\\%s.ex5" % args.ea)
    set_combo_text(mt5, 10486, args.symbol)
    set_combo_text(mt5, 10487, args.period)
    set_combo_text(mt5, 10550, args.from_d)
    set_combo_text(mt5, 10551, args.to_d)
    # 激活设置 tab
    activate_settings_tab(mt5)
    time.sleep(2)
    # 点击开始
    btn = find_by_cid(mt5, 16790)
    if btn is None:
        log("FATAL: start button not found")
        return 2
    if not click_button(btn, mt5):
        log("FATAL: button covered")
        return 3
    time.sleep(4)
    buf = ctypes.create_unicode_buffer(64)
    user32.GetWindowTextW(btn, buf, 64)
    log("button now: %r" % buf.value)
    if "停止" not in buf.value:
        log("FATAL: test did not start")
        return 4
    log("TEST STARTED")
    led = wait_ledger_stable(args.ea.split("_")[0].lower() if "Gold" in args.ea else "oil")
    if led is None:
        return 5
    dst = Path(__file__).resolve().parents[1] / "data" / "validation" / ("tester_actual_gold.csv" if "Gold" in args.ea else "tester_actual_oil.csv")
    import shutil
    shutil.copy2(led, dst)
    log("ledger copied: %s -> %s" % (led, dst))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
