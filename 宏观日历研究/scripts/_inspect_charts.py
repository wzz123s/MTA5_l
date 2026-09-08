# -*- coding: utf-8 -*-
from pathlib import Path
charts = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Profiles\Charts\Default")
for n in ["chart03.chr", "chart04.chr", "chart08.chr", "chart09.chr", "chart10.chr"]:
    f = charts / n
    if not f.exists():
        print(f"--- {n}: MISSING ---")
        continue
    text = f.read_bytes().decode("utf-16")
    print(f"--- {n} ---")
    for line in text.splitlines():
        t = line.strip()
        if any(k in t for k in ["name=", "InpPostNMax", "InpPostNMin", "InpEventFilter", "InpEnableShort", "InpSimMode", "InpAllowRealTrading", "InpMagicShort", "InpMagic"]):
            print("  ", t)
