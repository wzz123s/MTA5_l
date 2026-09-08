# -*- coding: utf-8 -*-
"""Switch all 7 attached EAs from SimMode virtual to REAL trading on the demo account.
Changes: InpSimMode=true->false, InpAllowRealTrading=false->true in chart .chr files."""
import shutil
import subprocess
import time
from pathlib import Path

BASE = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65")
CHARTS = BASE / "MQL5" / "Profiles" / "Charts" / "Default"
TERMINAL_EXE = r"F:\Program Files\MetaTrader 5\terminal64.exe"

TARGETS = ["chart02.chr", "chart03.chr", "chart04.chr", "chart05.chr",
           "chart07.chr", "chart08.chr", "chart09.chr"]


def read_utf16(p):
    return p.read_bytes().decode("utf-16")


def write_utf16(p, t):
    p.write_bytes(t.encode("utf-16"))


def main():
    for name in TARGETS:
        p = CHARTS / name
        text = read_utf16(p)
        if "InpSimMode=true" not in text or "InpAllowRealTrading=false" not in text:
            print("SKIP %s: switches not found (already switched?)" % name)
            continue
        backup = Path(str(p) + ".bak_20260820_sim")
        if not backup.exists():
            shutil.copy2(p, backup)
        text = text.replace("InpSimMode=true", "InpSimMode=false")
        text = text.replace("InpAllowRealTrading=false", "InpAllowRealTrading=true")
        write_utf16(p, text)
        print("SWITCHED %s -> SimMode=false AllowRealTrading=true" % name)
    subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe"], capture_output=True)
    time.sleep(4)
    subprocess.Popen([TERMINAL_EXE], cwd=str(Path(TERMINAL_EXE).parent))
    print("terminal restarted")
    time.sleep(24)
    logdir = BASE / "logs"
    logs = sorted(logdir.glob("2026*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if logs:
        content = logs[0].read_text(encoding="utf-8", errors="ignore")
        lines = [ln for ln in content.splitlines()
                 if ("initialized" in ln and "SimMode" in ln) or "loaded successfully" in ln]
        for ln in lines[-14:]:
            print("  ", ln[:150])


if __name__ == "__main__":
    main()
