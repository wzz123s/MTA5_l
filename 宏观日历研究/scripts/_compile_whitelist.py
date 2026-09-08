# -*- coding: utf-8 -*-
import shutil
import subprocess
import sys
import time
from pathlib import Path

METAEDITOR = r"F:\Program Files\MetaTrader 5\MetaEditor64.exe"
TERMINAL_EXE = r"F:\Program Files\MetaTrader 5\terminal64.exe"
BASE = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65")
ADVISORS = BASE / "MQL5" / "Experts" / "Advisors"
LOG_DIR = Path(r"F:\use_code\MTA5_l\宏观日历研究\logs")

EAS = [
    (Path(r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade\30m2H_ABC_EA.mq5"), "30m2H_ABC_EA.ex5"),
    (Path(r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_ABC_EA.mq5"), "2H_M30_6H_ABC_EA.ex5"),
    (Path(r"F:\use_code\MTA5_l\原油\原油4H门策略\auto_trade\USOIL4H_Gate_On2H_EA.mq5"), "USOIL4H_Gate_On2H_EA.ex5"),
]

for src, ex5name in EAS:
    log = LOG_DIR / f"compile_{ex5name}.log"
    subprocess.run([METAEDITOR, f"/compile:{src}", f"/log:{log}"], capture_output=True, text=True, timeout=120)
    ex5 = src.with_suffix(".ex5")
    if not ex5.exists():
        print(f"FATAL compile fail: {src.name}")
        print(log.read_text(encoding="utf-16", errors="replace")[-3000:])
        sys.exit(1)
    shutil.copy2(ex5, ADVISORS / ex5name)
    print(f"[OK] {ex5name} ({ex5.stat().st_size} bytes)")
    if log.exists():
        for line in log.read_text(encoding="utf-16", errors="replace").splitlines():
            if "error" in line.lower() or "Result" in line:
                print("   ", line.strip())

subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe"], capture_output=True)
time.sleep(4)
subprocess.Popen([TERMINAL_EXE], cwd=str(Path(TERMINAL_EXE).parent))
print("[OK] terminal restarted")
