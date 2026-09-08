# -*- coding: utf-8 -*-
"""Patch chart04.chr to load 2H_M30_6H_ABC_EA, then restart MT5.

Run deploy_abc_ea.ps1 first (copies ex5/set into DAD3B8CC), then this script:
  1. backup chart04.chr
  2. replace the <expert>...</expert> block with the ABC EA section
  3. restart the MT5 terminal (DAD3B8CC data folder)
"""
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
CHART = os.path.join(BASE, "MQL5", "Profiles", "Charts", "Default", "chart04.chr")
TERMINAL_EXE = r"F:\Program Files\MetaTrader 5\terminal64.exe"

EXPERT_ABC = """<expert>
name=2H_M30_6H_ABC_EA
path=Experts\\Advisors\\2H_M30_6H_ABC_EA.ex5
expertmode=1
<inputs>
=== Account ====
InpMagic=342036
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
=== 6H Gate ====
InpH6SMA5=5
InpH6SMA55=55
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
    backup = CHART + ".bak_20260815_2h_abc"
    if not os.path.exists(backup):
        shutil.copy2(CHART, backup)
        print("backup:", backup)

    text = read_utf16(CHART)
    sep = "\r\n" if "\r\n" in text else "\n"
    start = text.find("<expert>")
    end = text.find("</expert>")
    if start < 0 or end < 0:
        raise SystemExit("chart04.chr: expert block not found")
    end += len("</expert>")
    new_block = EXPERT_ABC.replace("\n", sep).rstrip(sep)
    new_text = text[:start] + new_block + text[end:]
    write_utf16(CHART, new_text)
    print("chart04.chr patched: expert -> 2H_M30_6H_ABC_EA")


def restart_terminal() -> None:
    # stop existing terminal processes for this data folder
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
    print("done. wait ~30s then check Experts log for '2H_M30_6H ABC EA initialized'.")
