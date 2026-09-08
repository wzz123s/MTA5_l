
# -*- coding: utf-8 -*-
"""Deploy + run ExportCalendar_EA v2: copy, compile, patch chart10, restart terminal, watch progress."""
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
LOG = Path(r"F:\use_code\MTA5_l\宏观日历研究\logs\compile_calendar_v2.log")
FILES_DIR = BASE / "MQL5" / "Files"
DONE = FILES_DIR / "calendar_export_done.txt"
OUT = FILES_DIR / "calendar_export.csv"
PROG = FILES_DIR / "calendar_export_progress.txt"
CRLF = "\r\n"

EXPERT_BLOCK = ("<expert>" + CRLF +
                "name=ExportCalendar_EA" + CRLF +
                "path=Experts\\Advisors\\ExportCalendar_EA.ex5" + CRLF +
                "expertmode=1" + CRLF +
                "</expert>")


def read_utf16(path):
    return path.read_bytes().decode("utf-16")


def write_utf16(path, text):
    path.write_bytes(text.encode("utf-16"))


def main():
    LOG.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SRC_MQ5, DST_MQ5)
    print("[1] copied mq5")
    res = subprocess.run([METAEDITOR, f"/compile:{DST_MQ5}", f"/log:{LOG}"],
                         capture_output=True, text=True, timeout=120)
    print("[2] metaeditor rc:", res.returncode)
    ex5 = DST_MQ5.with_suffix(".ex5")
    if not ex5.exists():
        print("FATAL: ex5 not produced; log tail:")
        print(LOG.read_text(encoding="utf-16", errors="replace")[-3000:])
        sys.exit(1)
    print("[3] compiled:", ex5.name)

    for f in (DONE, OUT, PROG):
        if f.exists():
            f.unlink()
    print("[4] old outputs cleaned")

    backup = Path(str(TARGET) + ".bak_calendar_probe")
    if not backup.exists():
        shutil.copy2(TARGET, backup)
        print("[5] chart10 backup:", backup.name)
    text = read_utf16(TEMPLATE)
    sep = CRLF if CRLF in text else "\n"
    lines = text.split(sep)
    for i, ln in enumerate(lines):
        if ln.startswith("id="):
            lines[i] = "id=%d" % random.randrange(10**17, 10**18)
        elif ln.startswith("symbol="):
            lines[i] = "symbol=XAUUSDm"
        elif ln.startswith("description="):
            lines[i] = "description=Gold"
    text = sep.join(lines)
    start = text.find("<expert>")
    end = text.find("</expert>")
    if start < 0 or end < 0:
        print("FATAL: template expert block not found")
        sys.exit(1)
    end += len("</expert>")
    text = text[:start] + EXPERT_BLOCK + text[end:]
    write_utf16(TARGET, text)
    print("[6] chart10 patched (XAUUSDm)")

    subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe"], capture_output=True)
    time.sleep(4)
    subprocess.Popen([TERMINAL_EXE], cwd=str(Path(TERMINAL_EXE).parent))
    print("[7] terminal restarted; watching progress ...")

    deadline = time.time() + 600
    last_prog = ""
    while time.time() < deadline:
        if DONE.exists():
            print("[8] DONE:", DONE.read_text(encoding="utf-8", errors="replace").strip())
            print("[9] csv size:", OUT.stat().st_size if OUT.exists() else 0)
            sys.exit(0)
        if PROG.exists():
            prog = PROG.read_text(encoding="utf-8", errors="replace").strip()
            if prog != last_prog:
                print("  prog:", prog)
                last_prog = prog
        time.sleep(5)
    print("FATAL: export not finished within 600s; last prog:", last_prog)
    sys.exit(3)


if __name__ == "__main__":
    main()
