# -*- coding: utf-8 -*-
"""Inject 30m2H_ABC_EA into chart08.chr (free slot) and restart MT5."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



import os
import shutil
import subprocess
import time


BASE = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65"
CHART = os.path.join(BASE, "MQL5", "Profiles", "Charts", "Default", "chart08.chr")
TERMINAL_EXE = r"F:\Program Files\MetaTrader 5\terminal64.exe"

EXPERT_ABC = """<expert>
name=30m2H_ABC_EA
path=Experts\\Advisors\\30m2H_ABC_EA.ex5
expertmode=1
<inputs>
=== Account ====
InpMagic=352036
InpSymbol=XAUUSDm
=== Risk ====
InpRiskPct=1.0
InpStopLoPt=5.0
InpStopHiPt=35.0
InpMaxOpenVirtual=10
InpMinLots=0.01
InpMaxLots=10.0
InpSimStartBalance=500.0
=== Layer 2 ====
InpPreCrossGapPct=0.300
InpPostNMin=2
InpPostNMax=6
InpMergedMinLen=8
=== H2 Gate ====
InpBias55Threshold=3.0
InpBias5MinPct=0.2
InpH2SMA5=5
InpH2SMA55=55
InpM30SMA5=5
InpM30SMA13=13
=== Split TP ====
InpStage1R=2.0
InpStage2TrailR=1.5
InpStage2ForceR=4.0
InpStage1Units=0.5
InpStage2Units=1.0
InpStage3Units=1.5
=== Runtime ====
InpHistoryBars=600
InpSimMode=true
InpAllowRealTrading=false
InpExportCSV=true
InpExportLedger=true
InpVerboseDiag=true
</inputs>
</expert>
"""


def read_utf16(path: str) -> str:
    with open(path, "rb") as f:
        return f.read().decode("utf-16")


def write_utf16(path: str, text: str) -> None:
    with open(path, "wb") as f:
        f.write(text.encode("utf-16"))


def patch_chart() -> None:
    backup = CHART + ".bak_20260815_30m2h_abc"
    if not os.path.exists(backup):
        shutil.copy2(CHART, backup)
        print("backup:", backup)

    text = read_utf16(CHART)
    if "<expert>" in text:
        print("chart08 already has an expert; aborting to avoid overwrite")
        raise SystemExit(1)
    sep = "\r\n" if "\r\n" in text else "\n"
    marker = "windows_total=1\r\n" if "\r\n" in text else "windows_total=1\n"
    idx = text.find(marker)
    if idx < 0:
        raise SystemExit("chart08.chr: windows_total marker not found")
    insert_at = idx + len(marker)
    new_block = EXPERT_ABC.replace("\n", sep).rstrip(sep)
    new_text = text[:insert_at] + new_block + text[insert_at:]
    write_utf16(CHART, new_text)
    print("chart08.chr patched: expert -> 30m2H_ABC_EA")


def restart_terminal() -> None:
    subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-Command",
            "Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Stop-Process -Force",
        ],
        check=False,
        timeout=60,
    )
    time.sleep(3)
    subprocess.Popen([TERMINAL_EXE], cwd=os.path.dirname(TERMINAL_EXE))
    print("terminal restarted:", TERMINAL_EXE)


if __name__ == "__main__":
    patch_chart()
    restart_terminal()
    print("done. wait ~45s then check Experts log for '30m2H ABC EA initialized'.")
