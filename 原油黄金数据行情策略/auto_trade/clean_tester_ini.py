# -*- coding: utf-8 -*-
"""清理 terminal.ini 中重复的 [Tester] 段，仅保留 DataEvent 段。"""
import re
from pathlib import Path

INI = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\config\terminal.ini")
text = INI.read_text(encoding="ansi")
# 移除所有 [Tester] 段（含旧 USOIL4H 与 DataEvent 注释段）
text = re.sub(r"\[Tester\].*?(?=\n\[|\Z)", "", text, flags=re.S)
# 注入本工程 DataEvent 段
block = """;
; DataEvent EA Tester config (injected by M4)
[Tester]
Expert=Experts\Advisors\Gold_DataEvent_EA.ex5
Symbol=XAUUSDm
Period=16386
Model=1
FromDate=2023.01.01
ToDate=2024.12.31
ForwardMode=0
Deposit=500.00
Currency=USD
Leverage=2000
Optimization=0
Visual=0
Report=Gold_DataEvent_EA_tester_report
ShutdownTerminal=0
UseLocal=1
UseRemote=0
UseCloud=0
LastExpert=Experts\Advisors\Gold_DataEvent_EA.ex5
"""
text = text.rstrip() + "\n" + block
INI.write_text(text, encoding="ansi")
print("ini cleaned: Tester -> Gold_DataEvent_EA")
