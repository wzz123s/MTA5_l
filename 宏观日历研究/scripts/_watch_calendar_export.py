
import sys, time
from pathlib import Path
DONE = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Files\calendar_export_done.txt")
OUT = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Files\calendar_export.csv")
deadline = time.time() + 900
while time.time() < deadline:
    if DONE.exists():
        print("DONE:", DONE.read_text(encoding="utf-8", errors="replace").strip())
        print("csv size:", OUT.stat().st_size if OUT.exists() else 0)
        sys.exit(0)
    if OUT.exists():
        size = OUT.stat().st_size
        if size > 0 and time.time() % 60 < 5:
            print("csv size now:", size, flush=True)
    time.sleep(15)
print("TIMEOUT after 900s")
sys.exit(3)
