
# -*- coding: utf-8 -*-
"""_watch_mct.py —— 等待 MCT Tester 账本稳定 → 拷贝 → 对齐"""
import shutil, sys, time
from pathlib import Path
import psutil

sys.stdout.reconfigure(encoding="utf-8")
TROOT = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\DAD3B8CC3EAC09C0C9725021DF0C7A65")
SRC = Path(__file__).resolve().parent
DST = SRC.parent / "data" / "validation" / "tester_actual_mct.csv"

deadline = time.time() + 3600
last_rows = -1
stable_since = None
while time.time() < deadline:
    time.sleep(20)
    led = None
    if TROOT.exists():
        for p in TROOT.rglob("MCT_trade_ledger.csv"):
            led = p
            break
    if led is None:
        print("[%s] no ledger yet" % time.strftime("%H:%M:%S"), flush=True)
        continue
    try:
        rows = sum(1 for _ in open(led, "rb")) - 1
    except Exception:
        rows = -1
    agents = sum(1 for p in psutil.process_iter(["name"])
                 if "metatester" in str(p.info["name"]).lower())
    print("[%s] rows=%d agents=%d ledger=%s" % (time.strftime("%H:%M:%S"), rows, agents, led), flush=True)
    if agents == 0 and rows > 0:
        if rows == last_rows:
            if stable_since is None:
                stable_since = time.time()
            elif time.time() - stable_since > 60:
                shutil.copy2(led, DST)
                print("DONE rows=%d copied -> %s" % (rows, DST), flush=True)
                break
        else:
            stable_since = None
    else:
        stable_since = None
    last_rows = rows
else:
    print("TIMEOUT", flush=True)
