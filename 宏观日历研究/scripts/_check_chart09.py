# -*- coding: utf-8 -*-
from pathlib import Path
charts = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Profiles\Charts\Default")
# chart09 inputs 验证
text = charts.joinpath("chart09.chr").read_bytes().decode("utf-16")
in_expert = False
for line in text.splitlines():
    t = line.strip()
    if t.startswith("<expert>"):
        in_expert = True
    if t.startswith("</expert>"):
        in_expert = False
    if in_expert and (t.startswith("name=") or t.startswith("Inp")):
        print(" ", t)
