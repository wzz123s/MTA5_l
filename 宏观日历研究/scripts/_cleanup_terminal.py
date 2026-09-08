
import shutil
import subprocess
import time
from pathlib import Path

BASE = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65")
CHARTS = BASE / "MQL5" / "Profiles" / "Charts" / "Default"
TARGET = CHARTS / "chart10.chr"
BACKUP = Path(str(TARGET) + ".bak_calendar_probe")
TERMINAL_EXE = r"F:\Program Files\MetaTrader 5\terminal64.exe"

if BACKUP.exists():
    shutil.copy2(BACKUP, TARGET)
    print("chart10 restored from backup")
else:
    print("no backup; leaving chart10 as-is")
subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe"], capture_output=True)
time.sleep(4)
subprocess.Popen([TERMINAL_EXE], cwd=str(Path(TERMINAL_EXE).parent))
print("terminal restarted (clean state)")
