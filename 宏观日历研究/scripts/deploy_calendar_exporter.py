# -*- coding: utf-8 -*-
"""Deploy ExportCalendar_EA: copy to terminal, compile, patch scratch chart, restart terminal."""
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65")
CHARTS = BASE / "MQL5" / "Profiles" / "Charts" / "Default"
TEMPLATE = CHARTS / "chart05.chr"
TARGET = CHARTS / "chart10.chr"
TERMINAL_EXE = r"F:\Program Files\MetaTrader 5\terminal64.exe"
METAEDITOR = r"F:\Program Files\MetaTrader 5\MetaEditor64.exe"
SRC_MQ5 = Path(r"F:\use_code\MTA5_l\宏观日历研究\mql5\ExportCalendar_EA.mq5")
DST_MQ5 = BASE / "MQL5" / "Experts" / "Advisors" / "ExportCalendar_EA.mq5"
LOG = Path(r"F:\use_code\MTA5_l\宏观日历研究\logs\compile_calendar.log")
CRLF = "\r\n"

EXPERT_BLOCK = ("<expert>" + CRLF +
                "name=ExportCalendar_EA" + CRLF +
                "path=Experts\\Advisors\\ExportCalendar_EA.ex5" + CRLF +
                "expertmode=1" + CRLF +
                "<inputs>" + CRLF +
                "InpDateFrom=2019.01.01" + CRLF +
                "InpDateTo=2027.01.01" + CRLF +
                "InpOutFile=calendar_export.csv" + CRLF +
                "InpDoneFile=calendar_export_done.txt" + CRLF +
                "</inputs>" + CRLF +
                "</expert>")


def read_utf16(path):
    return path.read_bytes().decode("utf-16")


def write_utf16(path, text):
    path.write_bytes(text.encode("utf-16"))


def main():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC_MQ5, DST_MQ5)
    print("copied mq5 ->", DST_MQ5)
    res = subprocess.run([METAEDITOR, f"/compile:{DST_MQ5}", f"/log:{LOG}"],
                         capture_output=True, text=True, timeout=120)
    print("metaeditor rc:", res.returncode)
    ex5 = DST_MQ5.with_suffix(".ex5")
    if not ex5.exists():
        print("FATAL: ex5 not produced; log tail:")
        print(LOG.read_text(encoding="utf-8", errors="replace")[-2000:])
        sys.exit(1)
    print("compiled:", ex5)

    # patch scratch chart
    backup = Path(str(TARGET) + ".bak_calendar_probe")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
        print("backup:", backup.name)
    text = read_utf16(TEMPLATE)
    sep = CRLF if CRLF in text else "\n"
    lines = text.split(sep)
    for i, ln in enumerate(lines):
        if ln.startswith("id="):
            lines[i] = "id=%d" % random.randrange(10**17, 10**18)
        elif ln.startswith("symbol="):
            lines[i] = "symbol=EURUSD"
        elif ln.startswith("description="):
            lines[i] = "description=Euro"
    text = sep.join(lines)
    start = text.find("<expert>")
    end = text.find("</expert>")
    if start < 0 or end < 0:
        print("FATAL: template expert block not found")
        sys.exit(1)
    end += len("</expert>")
    text = text[:start] + EXPERT_BLOCK + text[end:]
    write_utf16(TARGET, text)
    print("chart10.chr patched with ExportCalendar_EA")

    # restart terminal
    subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe"], capture_output=True)
    time.sleep(4)
    subprocess.Popen([TERMINAL_EXE], cwd=str(Path(TERMINAL_EXE).parent))
    print("terminal restarted; waiting for EA load + export ...")


if __name__ == "__main__":
    main()
