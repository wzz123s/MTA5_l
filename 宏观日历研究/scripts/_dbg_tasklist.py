# -*- coding: utf-8 -*-
import subprocess
from pathlib import Path
tmp = Path(r"F:\use_code\MTA5_l\observation_dashboard\监测报告\_tasklist_dbg.txt")
with tmp.open("w", encoding="utf-8", errors="ignore") as fh:
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq terminal64.exe"], stdout=fh, stderr=fh)
print("rc:", r.returncode)
raw = tmp.read_bytes()
print("bytes:", raw[:300])
print("utf8:", tmp.read_text(encoding="utf-8", errors="replace")[:300])
print("match:", "terminal64.exe" in tmp.read_text(encoding="utf-8", errors="ignore"))
