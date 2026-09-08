# -*- coding: utf-8 -*-
"""Attach USOIL4H_Gate_On2H_EA to a live chart (chart09.chr, USOILm H1) in DAD3B8CC terminal."""
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65")
CHARTS = BASE / "MQL5" / "Profiles" / "Charts" / "Default"
TEMPLATE = CHARTS / "chart05.chr"
TARGET = CHARTS / "chart09.chr"
TERMINAL_EXE = r"F:\Program Files\MetaTrader 5\terminal64.exe"
CRLF = "\r\n"

EXPERT_BLOCK = ("<expert>" + CRLF +
                "name=USOIL4H_Gate_On2H_EA" + CRLF +
                "path=Experts\\Advisors\\USOIL4H_Gate_On2H_EA.ex5" + CRLF +
                "expertmode=1" + CRLF +
                "<inputs>" + CRLF +
                "=== Account ====" + CRLF +
                "InpMagic=362137" + CRLF +
                "InpSymbol=USOILm" + CRLF +
                "=== Risk & Virtual Position ====" + CRLF +
                "InpRiskPct=1.0" + CRLF +
                "InpStopLoPct=0.1" + CRLF +
                "InpStopHiPct=1.0" + CRLF +
                "InpMaxOpenVirtual=10" + CRLF +
                "InpMinLots=0.01" + CRLF +
                "InpMaxLots=10.0" + CRLF +
                "InpSimStartBalance=500.0" + CRLF +
                "=== Strategy ====" + CRLF +
                "InpSMA5=5" + CRLF +
                "InpSMA13=13" + CRLF +
                "InpPreGap=0.003" + CRLF +
                "InpHistoryBars2H=20000" + CRLF +
                "InpGateSMA5=5" + CRLF +
                "InpGateSMA13=13" + CRLF +
                "InpMergedMinLen=8" + CRLF +
                "InpVolMaPeriod=120" + CRLF +
                "InpGateThr=0.5" + CRLF +
                "InpGateAmpLo=0.5" + CRLF +
                "InpGateAmpHi=5.0" + CRLF +
                "InpHistoryBars4H=10000" + CRLF +
                "=== Runtime ====" + CRLF +
                "InpSimMode=true" + CRLF +
                "InpAllowRealTrading=false" + CRLF +
                "InpExportCSV=true" + CRLF +
                "InpExportLedger=true" + CRLF +
                "InpVerboseDiag=true" + CRLF +
                "</inputs>" + CRLF +
                "</expert>")


def read_utf16(path):
    return path.read_bytes().decode("utf-16")


def write_utf16(path, text):
    path.write_bytes(text.encode("utf-16"))


def main():
    backup = Path(str(TARGET) + ".bak_20260820_eth")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
        print("backup:", backup.name)
    text = read_utf16(TEMPLATE)
    sep = CRLF if CRLF in text else "\n"
    lines = text.split(sep)
    for i, ln in enumerate(lines):
        if ln.startswith("id="):
            lines[i] = "id=%d" % random.randrange(10**17, 10**18)
        elif ln.startswith("window_left="):
            lines[i] = "window_left=%d" % (int(ln.split("=")[1]) + 40)
        elif ln.startswith("window_top="):
            lines[i] = "window_top=%d" % (int(ln.split("=")[1]) + 40)
        elif ln.startswith("window_right="):
            lines[i] = "window_right=%d" % (int(ln.split("=")[1]) + 40)
        elif ln.startswith("window_bottom="):
            lines[i] = "window_bottom=%d" % (int(ln.split("=")[1]) + 40)
    text = sep.join(lines)
    start = text.find("<expert>")
    end = text.find("</expert>")
    if start < 0 or end < 0:
        print("FATAL: template expert block not found")
        sys.exit(1)
    end += len("</expert>")
    text = text[:start] + EXPERT_BLOCK + text[end:]
    write_utf16(TARGET, text)
    print("chart09.chr patched: USOILm H1 + USOIL4H_Gate_On2H_EA")
    subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe"], capture_output=True)
    time.sleep(4)
    subprocess.Popen([TERMINAL_EXE], cwd=str(Path(TERMINAL_EXE).parent))
    print("terminal restarted; waiting for EA load")
    time.sleep(22)
    logdir = BASE / "logs"
    logs = sorted(logdir.glob("2026*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if logs:
        content = logs[0].read_text(encoding="utf-8", errors="ignore")
        hits = [ln for ln in content.splitlines() if "USOIL4H_Gate_On2H_EA" in ln]
        print("log hits:", len(hits))
        for h in hits[-3:]:
            print("  ", h[:140])
    else:
        print("no log file found")


if __name__ == "__main__":
    main()
