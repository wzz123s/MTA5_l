# -*- coding: utf-8 -*-
"""Deploy USOIL2H_CrossConfirm_EA to DAD3B8CC terminal SimMode (chart05 USOILm)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

from pathlib import Path


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY = ROOT / "原油" / "原油2H策略"
AUTO = STRATEGY / "auto_trade"
EA_NAME = "USOIL2H_CrossConfirm_EA"
SET_NAME = "USOIL2H_CrossConfirm_SimDeployment_EA"
BASE = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65"
CHART = os.path.join(BASE, "MQL5", "Profiles", "Charts", "Default", "chart05.chr")
METAEDITOR = r"F:\Program Files\MetaTrader 5\metaeditor64.exe"
TERMINAL_EXE = r"F:\Program Files\MetaTrader 5\terminal64.exe"

EXPERT = """<expert>
name=USOIL2H_CrossConfirm_EA
path=Experts\\Advisors\\USOIL2H_CrossConfirm_EA.ex5
expertmode=1
<inputs>
=== Account ====
InpMagic=362036
InpSymbol=USOILm
=== Risk ====
InpRiskPct=1.0
InpStopLoPct=0.1
InpStopHiPct=1.0
InpMaxOpenVirtual=20
InpMinLots=0.01
InpMaxLots=10.0
InpSimStartBalance=500.0
=== Strategy ====
InpSMA5=5
InpSMA13=13
InpMergedMinLen=8
InpConfirmThr=0.5
InpVolMaPeriod=120
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


def compile_ea() -> None:
    mq5 = AUTO / f"{EA_NAME}.mq5"
    log = AUTO / "compile_usoil2h_v1.log"
    cmd = [METAEDITOR, f"/compile:{mq5}", f"/log:{log}"]
    print("compile:", " ".join(cmd))
    subprocess.run(cmd, timeout=120)
    time.sleep(2)
    if not (AUTO / f"{EA_NAME}.ex5").exists():
        print("COMPILE FAILED - no .ex5 produced")
        sys.exit(1)
    print("compile OK ->", AUTO / f"{EA_NAME}.ex5")


def copy_to_terminal() -> None:
    experts = os.path.join(BASE, "MQL5", "Experts", "Advisors")
    presets = os.path.join(BASE, "MQL5", "Presets")
    os.makedirs(experts, exist_ok=True)
    os.makedirs(presets, exist_ok=True)
    shutil.copy2(AUTO / f"{EA_NAME}.mq5", os.path.join(experts, f"{EA_NAME}.mq5"))
    shutil.copy2(AUTO / f"{EA_NAME}.ex5", os.path.join(experts, f"{EA_NAME}.ex5"))
    shutil.copy2(AUTO / f"{SET_NAME}.set", os.path.join(presets, f"{SET_NAME}.set"))
    print("copied mq5/ex5/set to terminal")


def patch_chart() -> None:
    backup = CHART + ".bak_20260816_usoil2h"
    if not os.path.exists(backup):
        shutil.copy2(CHART, backup)
        print("backup:", backup)
    text = read_utf16(CHART)
    if "<expert>" in text:
        print("chart05 already has an expert; aborting")
        sys.exit(1)
    sep = "\r\n" if "\r\n" in text else "\n"
    marker = "windows_total=1" + sep
    idx = text.find(marker)
    if idx < 0:
        sys.exit("chart05.chr: windows_total marker not found")
    insert_at = idx + len(marker)
    new_block = EXPERT.replace("\n", sep).rstrip(sep)
    write_utf16(CHART, text[:insert_at] + new_block + text[insert_at:])
    print("chart05.chr patched: expert -> USOIL2H_CrossConfirm_EA")


def restart_terminal() -> None:
    subprocess.run(["taskkill", "/IM", "terminal64.exe", "/F"], capture_output=True)
    time.sleep(3)
    subprocess.Popen([TERMINAL_EXE], cwd=os.path.dirname(TERMINAL_EXE))
    print("terminal restarted")


def main() -> None:
    compile_ea()
    copy_to_terminal()
    patch_chart()
    restart_terminal()
    print("done. wait ~60s then check Experts log for 'USOIL2H CrossConfirm EA initialized'")


if __name__ == "__main__":
    main()
