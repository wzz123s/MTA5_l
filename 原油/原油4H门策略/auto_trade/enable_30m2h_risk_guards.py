# -*- coding: utf-8 -*-
"""Enable 30m2H_Strategy_EA live risk guards (chart07.chr)."""
import shutil
import subprocess
import time
from pathlib import Path

BASE = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65")
P = BASE / "MQL5" / "Profiles" / "Charts" / "Default" / "chart07.chr"
TERMINAL_EXE = r"F:\Program Files\MetaTrader 5\terminal64.exe"

text = P.read_bytes().decode("utf-16")
if "InpEnableLiveRiskGuards=false" not in text:
    print("SKIP: InpEnableLiveRiskGuards=false not found (already enabled?)")
else:
    backup = Path(str(P) + ".bak_20260820_sim")
    if not backup.exists():
        shutil.copy2(P, backup)
    text = text.replace("InpEnableLiveRiskGuards=false", "InpEnableLiveRiskGuards=true")
    P.write_bytes(text.encode("utf-16"))
    print("chart07.chr: InpEnableLiveRiskGuards -> true")

subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe"], capture_output=True)
time.sleep(4)
subprocess.Popen([TERMINAL_EXE], cwd=str(Path(TERMINAL_EXE).parent))
print("terminal restarted")
time.sleep(22)
logdir = BASE / "logs"
logs = sorted(logdir.glob("2026*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
if logs:
    content = logs[0].read_text(encoding="utf-8", errors="ignore")
    for ln in content.splitlines():
        if "loaded successfully" in ln and "30m2H_Strategy_EA" in ln:
            print("  ", ln[:140])
