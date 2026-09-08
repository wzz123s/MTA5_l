
import shutil, subprocess, sys
from pathlib import Path
METAEDITOR = r"F:\Program Files\MetaTrader 5\MetaEditor64.exe"
SRC = Path(r"F:\use_code\MTA5_l\宏观日历研究\mql5\ProbeCalendar_EA.mq5")
DST = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Experts\Advisors\ProbeCalendar_EA.mq5")
LOG = Path(r"F:\use_code\MTA5_l\宏观日历研究\logs\compile_probe.log")
shutil.copy2(SRC, DST)
print("copied")
try:
    res = subprocess.run([METAEDITOR, f"/compile:{DST}", f"/log:{LOG}"],
                         capture_output=True, text=True, timeout=90)
    print("rc:", res.returncode)
    print("ex5 exists:", DST.with_suffix(".ex5").exists())
    if LOG.exists():
        txt = LOG.read_text(encoding="utf-16", errors="replace")
        for line in txt.splitlines():
            print(line)
    else:
        print("no log file")
except subprocess.TimeoutExpired:
    print("COMPILE TIMEOUT")
    sys.exit(2)
