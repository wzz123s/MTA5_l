# -*- coding: utf-8 -*-
"""部署 BiasReversal_Combo_EA：复制 ex5 + 生成 chart10.chr + 重启"""
import shutil, subprocess, time
from pathlib import Path

BASE = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65")
DST = BASE / "MQL5" / "Experts" / "Advisors"
CHARTS = BASE / "MQL5" / "Profiles" / "Charts" / "Default"
TEMPLATE = CHARTS / "chart09.chr"
TARGET = CHARTS / "chart10.chr"
CRLF = "\r\n"

EXPERT = ("<expert>" + CRLF +
          "name=BiasReversal_Combo_EA" + CRLF +
          "path=Experts\\Advisors\\BiasReversal_Combo_EA.ex5" + CRLF +
          "expertmode=1" + CRLF +
          "<inputs>" + CRLF +
          "=== Account ====" + CRLF +
          "InpMagicLong=372036" + CRLF +
          "InpMagicShort=372037" + CRLF +
          "InpSymbol=XAUUSDm" + CRLF +
          "=== Short (bias reversal) ====" + CRLF +
          "InpShortGateThr=3.5" + CRLF +
          "InpRiseThr=3.0" + CRLF +
          "InpWThr=0.5" + CRLF +
          "=== Long (mode) ====" + CRLF +
          "InpLongMode=0" + CRLF +
          "InpLongGateThr=0.0" + CRLF +
          "=== Risk ====" + CRLF +
          "InpRiskPct=1.0" + CRLF +
          "InpStopPct=1.2" + CRLF +
          "InpTpR=3.0" + CRLF +
          "InpMinLots=0.01" + CRLF +
          "InpMaxLots=10.0" + CRLF +
          "=== Runtime ====" + CRLF +
          "InpSimMode=false" + CRLF +
          "InpAllowRealTrading=true" + CRLF +
          "InpExportLedger=true" + CRLF +
          "InpVerboseDiag=true" + CRLF +
          "InpHistoryBars=600" + CRLF +
          "</inputs>" + CRLF +
          "</expert>")

# 1) copy ex5
shutil.copy2(r"F:\use_code\MTA5_l\黄金\乖离反转策略\auto_trade\BiasReversal_Combo_EA.ex5", DST / "BiasReversal_Combo_EA.ex5")
print("ex5 copied")

# 2) chart10.chr from chart09 template
text = TEMPLATE.read_bytes().decode("utf-16")
sep = CRLF if CRLF in text else "\n"
lines = text.split(sep)
for i, ln in enumerate(lines):
    if ln.startswith("id="):
        lines[i] = "id=%d" % (int(time.time() * 1000) % 10**18)
    elif ln.startswith("symbol="):
        lines[i] = "symbol=XAUUSDm"
    elif ln.startswith("description="):
        lines[i] = "description=Gold vs US Dollar"
    elif ln.startswith("period_type="):
        lines[i] = "period_type=0"
    elif ln.startswith("period_size="):
        lines[i] = "period_size=30"
    elif ln.startswith("window_left="):
        lines[i] = "window_left=%d" % (int(ln.split("=")[1]) + 60)
    elif ln.startswith("window_top="):
        lines[i] = "window_top=%d" % (int(ln.split("=")[1]) + 60)
    elif ln.startswith("window_right="):
        lines[i] = "window_right=%d" % (int(ln.split("=")[1]) + 60)
    elif ln.startswith("window_bottom="):
        lines[i] = "window_bottom=%d" % (int(ln.split("=")[1]) + 60)
text = sep.join(lines)
start = text.find("<expert>")
end = text.find("</expert>")
if start >= 0 and end >= 0:
    end += len("</expert>")
    text = text[:start] + EXPERT + text[end:]
else:
    # no expert in template; insert after windows_total
    marker = "windows_total=1" + sep
    idx = text.find(marker)
    if idx < 0:
        raise SystemExit("marker not found")
    insert_at = idx + len(marker)
    text = text[:insert_at] + EXPERT + text[insert_at:]
backup = Path(str(TARGET) + ".bak_20260821")
if not TARGET.exists() and not backup.exists():
    pass
if backup.exists():
    shutil.copy2(backup, TARGET) if False else None
TARGET.write_bytes(text.encode("utf-16"))
print("chart10.chr written")

# 3) restart terminal
subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe"], capture_output=True)
time.sleep(4)
subprocess.Popen([r"F:\Program Files\MetaTrader 5\terminal64.exe"], cwd=r"F:\Program Files\MetaTrader 5")
print("terminal restarted")
time.sleep(25)
logdir = BASE / "logs"
logs = sorted(logdir.glob("2026*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
if logs:
    content = logs[0].read_text(encoding="utf-8", errors="ignore")
    hits = [ln for ln in content.splitlines() if "BiasReversal" in ln]
    print("log hits:", len(hits))
    for h in hits[-4:]:
        print("  ", h[:150])
