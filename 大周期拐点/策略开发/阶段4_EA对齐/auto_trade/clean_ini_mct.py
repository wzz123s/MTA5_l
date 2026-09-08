
# -*- coding: utf-8 -*-
"""清理 terminal.ini 所有 [Tester] 段，只写入 MCT_EA 一个干净块。"""
import datetime, re
from pathlib import Path

INI = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\config\terminal.ini")
text = INI.read_text(encoding="ansi")

# 移除所有 [Tester] 段（从 [Tester] 行到下一个 [ 段或文件尾）
text = re.sub(r"(?m)^\[Tester\].*?(?=^\[|\Z)", "", text, flags=re.S)
text = text.rstrip() + "\n"

def epoch(d):
    return int(datetime.datetime.strptime(d, "%Y.%m.%d").replace(tzinfo=datetime.timezone.utc).timestamp())

block = """;
; MCT EA Tester config (stage4)
[Tester]
Expert=Experts\\Advisors\\MCT_EA.ex5
Symbol=USOILm
Period=16388
Model=1
FromDate=2021.07.01
ToDate=2026.09.01
ForwardMode=0
Deposit=500.00
Currency=USD
Leverage=2000
Optimization=0
Visual=0
Report=MCT_EA_tester_report
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
LastExpert=Experts\\Advisors\\MCT_EA.ex5
LastIndicator=
LastTicksMode=0
LastCriterion=0
LastForward=2
LastDelay=91
LastOptimization=0
DateRange=3
DateFrom=%d
DateTo=%d
Visualization=0
Execution=0
CheckCurrencyDigits=8
PipsCalculation=0
TicksMode=1
ProgramType=0
OptMode=-1
OptForward=0
OptCrit=0
OptFwdDate=1693785600
""" % (epoch("2021.07.01"), epoch("2026.09.01"))

INI.write_text(text + block, encoding="ansi")
# 校验：应只有一个 [Tester] 且 Expert=MCT_EA
txt = INI.read_text(encoding="ansi")
print("Tester blocks:", len(re.findall(r"(?m)^\[Tester\]", txt)))
m = re.search(r"Expert=([^\r\n]+)", txt)
print("Expert:", m.group(1) if m else None)
