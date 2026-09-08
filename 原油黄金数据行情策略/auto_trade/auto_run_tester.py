# -*- coding: utf-8 -*-
"""M4.3 Tester 自动化：配置策略测试面板并运行 Gold/Oil DataEvent EA，收集 ledger。
用法: python auto_run_tester.py --ea Gold_DataEvent_EA --symbol XAUUSDm --period H4 [--from 2021-01-01 --to 2026-08-30]
"""
from __future__ import annotations
import argparse
import datetime
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from pywinauto import Desktop
from pywinauto.application import Application
from pywinauto.keyboard import send_keys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "auto_trade"
LOG = OUT / "tester_auto_run.log"
TDIR = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65")
TROOT = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65")
TERM_EXE = r"F:\Program Files\MetaTrader 5\terminal64.exe"


def log(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def term_alive():
    return any(p.info["name"] == "terminal64.exe" for p in psutil.process_iter(["name"]))


def meta_count():
    return sum(1 for p in psutil.process_iter(["name"]) if "metatester" in str(p.info["name"]).lower())


def find_mt5():
    # 沙箱内 uia 后端不可用，改用 win32 后端（M4 记录的环境限制，2026-08-30 修复）
    for w in Desktop(backend="win32").windows():
        if "MetaTrader" in w.window_text() or "Exness" in w.window_text():
            return w
    return None


def find_tester(mt5):
    cands = []
    for w in Desktop(backend="win32").windows():
        if "策略测试" in w.window_text() or "Strategy Tester" in w.window_text():
            cands.append(w)
    if mt5 is not None:
        try:
            for c in mt5.children():
                if "策略测试" in c.window_text() or "Strategy Tester" in c.window_text():
                    cands.append(c)
        except Exception:
            pass
    # 面板存在多个同名窗口（Afx:ControlBar 真面板 + AfxWnd 包装窗），
    # 优先选择包含 EA 组合框(10485)的那个
    for w in cands:
        try:
            if w.descendants(control_id=10485):
                return w
        except Exception:
            continue
    return cands[0] if cands else None


def find_start_button(tester):
    # win32 后端：MT5 开始按钮 control_id=16790（class 可能为 Button/TButton）
    try:
        for b in tester.descendants(control_id=16790):
            return b
    except Exception:
        pass
    return None


def click_start_button(tester):
    """点击开始按钮：优先 BM_CLICK 消息（ElementNotVisible 时 .click() 不可靠）"""
    import ctypes
    btn = find_start_button(tester)
    if btn is None:
        log("start button not found")
        return False
    try:
        hwnd = btn.handle
        # BM_CLICK = 0x00F5；先激活面板确保消息被处理
        try:
            tester.set_focus()
        except Exception:
            pass
        ctypes.windll.user32.SendMessageW(hwnd, 0x00F5, 0, 0)
        log("BM_CLICK sent to start button hwnd=%d" % hwnd)
        return True
    except Exception as e:
        log("BM_CLICK err: %r" % e)
        try:
            btn.click()
            log("fallback .click() sent")
            return True
        except Exception as e2:
            log("fallback click err: %r" % e2)
            return False


def find_ledger(name: str):
    if not TROOT.exists():
        return None
    for p in TROOT.rglob(name):
        return p
    return None


def cget(w, cls, cid):
    try:
        return w.child_window(class_name=cls, control_id=cid).window_text()
    except Exception:
        return ""


def set_combo(w, cls, cid, value):
    """设置 ComboBox 值（键盘选择）；控件为嵌套子窗口，用 descendants 查找"""
    try:
        found = w.descendants(control_id=cid)
        if not found:
            log("set_combo err: combo id %s not found" % cid)
            return False
        cb = found[0]
        cb.set_focus()
        cb.type_keys(value + "{ENTER}")
        time.sleep(0.5)
        return True
    except Exception as e:
        log("set_combo err: %r" % e)
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ea", default="Gold_DataEvent_EA")
    ap.add_argument("--symbol", default="XAUUSDm")
    ap.add_argument("--period", default="H4")
    ap.add_argument("--from", dest="from_d", default="2021-01-01")
    ap.add_argument("--to", dest="to_d", default="2026-08-30")
    args = ap.parse_args()

    ledger_name = {"Gold_DataEvent_EA": "Gold_DataEvent_trade_ledger.csv",
                   "Oil_DataEvent_EA": "Oil_DataEvent_trade_ledger.csv"}.get(args.ea, args.ea + "_trade_ledger.csv")

    log("=== auto run start: %s %s %s %s~%s ===" % (args.ea, args.symbol, args.period, args.from_d, args.to_d))
    # 1) 确保终端运行
    if not term_alive():
        subprocess.Popen([TERM_EXE])
        log("MT5 launched")
    mt5 = None
    for _ in range(15):
        time.sleep(3)
        mt5 = find_mt5()
        if mt5 is not None:
            break
    if mt5 is None:
        log("FATAL: no MT5 window")
        return 1
    # 2) 打开策略测试
    tester = None
    for _ in range(5):
        tester = find_tester(mt5)
        if tester is not None:
            break
        try:
            mt5.set_focus()
        except Exception:
            pass
        send_keys("^r")
        time.sleep(4)
    if tester is None:
        log("FATAL: no tester panel")
        return 2
    time.sleep(2)
    app = Application(backend="win32").connect(handle=tester.handle)
    w = app.window(handle=tester.handle)
    # 3) 设置 EA / 品种 / 周期 / 日期（尽力而为，若已有配置则跳过）
    set_combo(w, "ComboBox", 10485, args.ea)     # EA
    set_combo(w, "ComboBox", 10486, args.symbol) # symbol
    set_combo(w, "ComboBox", 10487, args.period) # period
    time.sleep(1)
    # 4) 删除旧 ledger
    led = find_ledger(ledger_name)
    if led is not None:
        led.unlink()
        log("removed old ledger: %s" % led)
    # 5) 点击开始
    started = False
    for attempt in range(3):
        if not click_start_button(tester):
            log("start button click failed (attempt %d)" % (attempt + 1))
            time.sleep(2)
            continue
        log("Start clicked (attempt %d)" % (attempt + 1))
        time.sleep(6)
        mc = meta_count()
        b2 = find_start_button(tester)
        txt = ""
        if b2 is not None:
            try:
                txt = b2.window_text()
            except Exception:
                pass
        log("after click: metatester=%d button=%r" % (mc, txt))
        if mc > 0 or "停止" in txt:
            started = True
            break
        time.sleep(4)
    if not started:
        log("FATAL: test did not start after 3 attempts")
        return 3
    # 6) 等待完成（全量 2019-2026 M30 回测较慢，放宽到 3 小时）
    deadline = time.time() + 10800
    last_rows = -1
    stable_since = None
    while time.time() < deadline:
        time.sleep(15)
        led = find_ledger(ledger_name)
        rows = -1
        if led is not None:
            try:
                rows = sum(1 for _ in open(led, "rb")) - 1
            except Exception:
                rows = -1
        mc = meta_count()
        log("watch rows=%d metatester=%d" % (rows, mc))
        if not term_alive():
            log("MT5 died mid-run")
            return 4
        if mc == 0 and rows > 0:
            if rows == last_rows:
                if stable_since is None:
                    stable_since = time.time()
                elif time.time() - stable_since > 45:
                    log("done: ledger stable %d rows" % rows)
                    break
            else:
                stable_since = None
        else:
            stable_since = None
        last_rows = rows
    time.sleep(4)
    led = find_ledger(ledger_name)
    if led is None:
        log("FATAL: ledger not found")
        return 5
    copied = OUT / ("tester_" + ledger_name)
    shutil.copy2(led, copied)
    rows = sum(1 for _ in open(led, "rb")) - 1
    log("ledger copied: %s rows=%d" % (copied, rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
