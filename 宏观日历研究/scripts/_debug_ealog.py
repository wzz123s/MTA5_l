# -*- coding: utf-8 -*-
from pathlib import Path
TERMINAL_LOG = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\logs")
logs = sorted(TERMINAL_LOG.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
print("log files:", [p.name for p in logs[:3]])
for log in logs[:1]:
    text = log.read_text(encoding="utf-8", errors="ignore")
    hits = [ln for ln in text.splitlines() if "expert " in ln and "loaded successfully" in ln]
    print("hits:", len(hits))
    if hits:
        print("sample:", hits[-1][:120])
        print("parsed:", hits[-1].split("expert ")[1].split(" (")[0])
