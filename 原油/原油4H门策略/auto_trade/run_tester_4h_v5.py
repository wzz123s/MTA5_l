# -*- coding: utf-8 -*-
"""v5: resilient full run - relaunch, verify, UIA-invoke Start, verify started, watch, collect."""
import datetime, shutil, subprocess, time, os
from pathlib import Path
import psutil
from pywinauto import Desktop
from pywinauto.application import Application
from pywinauto.keyboard import send_keys

OUT_DIR = Path(r"F:\use_code\MTA5_l\原油\原油4H门策略\auto_trade")
LOG = OUT_DIR / "tester_auto_run_4h.log"
TDIR = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65")
INI = TDIR / "config" / "terminal.ini"
TROOT = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65")
COPIED = OUT_DIR / "tester_ledger_4h_gate.csv"
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
    for w in Desktop(backend="uia").windows():
        if "MetaTrader" in w.window_text() or "Exness" in w.window_text():
            return w
    return None

def find_tester(mt5):
    for w in Desktop(backend="uia").windows():
        if "策略测试" in w.window_text() or "Strategy Tester" in w.window_text():
            return w
    if mt5 is not None:
        try:
            for c in mt5.children():
                if "策略测试" in c.window_text() or "Strategy Tester" in c.window_text():
                    return c
        except Exception:
            pass
    return None

def find_start_button(tester):
    for d in tester.descendants():
        try:
            if d.element_info.control_type == "Button" and d.element_info.automation_id == "16790":
                return d
        except Exception:
            continue
    return None

def find_ledger():
    if not TROOT.exists():
        return None
    for p in TROOT.rglob("USOIL4H_gate_trade_ledger.csv"):
        return p
    return None

def cget(w, cls, cid):
    try:
        return w.child_window(class_name=cls, control_id=cid).window_text()
    except Exception:
        return ""

def verify_panel(w):
    checks = [
        ("EA", cget(w, "ComboBox", 10485), "USOIL4H_Gate_On2H_EA"),
        ("symbol", cget(w, "ComboBox", 10486), "USOILm"),
        ("period", cget(w, "ComboBox", 10487), "H2"),
        ("model", cget(w, "ComboBox", 10515), "1分钟 OHLC"),
        ("deposit", cget(w, "ComboBox", 10489), "500"),
        ("from", cget(w, "SysDateTimePick32", 10550), "2021.01.01"),
        ("to", cget(w, "SysDateTimePick32", 10551), "2026.08.15"),
    ]
    ok = True
    for name, got, want in checks:
        good = want in (got or "")
        if not good:
            ok = False
        log("check %-8s want=%r got=%r %s" % (name, want, got, "OK" if good else "MISMATCH"))
    return ok

def main():
    log("=== v5 auto run start ===")
    # ensure terminal up
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
        return 1
    time.sleep(2)
    app = Application(backend="win32").connect(handle=tester.handle)
    w = app.window(handle=tester.handle)
    if not verify_panel(w):
        log("FATAL: panel mismatch")
        return 2
    led = find_ledger()
    if led is not None:
        led.unlink()
        log("removed old ledger: %s" % led)
    # start via UIA invoke
    started = False
    for attempt in range(3):
        btn = find_start_button(tester)
        if btn is None:
            log("start button not found (attempt %d)" % (attempt + 1))
            time.sleep(2)
            continue
        try:
            btn.click()
            log("Start clicked via UIA (attempt %d)" % (attempt + 1))
        except Exception as e:
            log("uia click err: %r" % e)
        time.sleep(6)
        mc = meta_count()
        txt = ""
        b2 = find_start_button(tester)
        if b2 is not None:
            try:
                txt = b2.window_text()
            except Exception:
                pass
        log("after click: metatester=%d button=%r" % (mc, txt))
        if mc > 0 or "停止" in txt:
            started = True
            break
        # maybe tester needs focus; click once more via uia invoke
        time.sleep(4)
    if not started:
        log("FATAL: test did not start after 3 attempts")
        return 3
    # watch until done
    deadline = time.time() + 2400
    last_rows = -1
    stable_since = None
    while time.time() < deadline:
        time.sleep(15)
        led = find_ledger()
        rows = -1
        if led is not None:
            try:
                rows = sum(1 for _ in open(led, "rb")) - 1
            except Exception:
                rows = -1
        mc = meta_count()
        alive = term_alive()
        log("watch rows=%d metatester=%d term_alive=%s" % (rows, mc, alive))
        if not alive:
            log("MT5 died mid-run; aborting watch (ledger rows=%d)" % rows)
            return 4
        if mc == 0 and rows > 0:
            if rows == last_rows:
                if stable_since is None:
                    stable_since = time.time()
                elif time.time() - stable_since > 45:
                    log("done: agents idle + ledger stable %d rows" % rows)
                    break
            else:
                stable_since = None
        else:
            stable_since = None
        last_rows = rows
    else:
        log("TIMEOUT watching")
    time.sleep(4)
    led = find_ledger()
    if led is None:
        log("FATAL: ledger not found at end")
        return 5
    shutil.copy2(led, COPIED)
    rows = sum(1 for _ in open(led, "rb")) - 1
    log("ledger copied: %s rows=%d (source %s)" % (COPIED, rows, led))
    log("=== v5 done ===")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
