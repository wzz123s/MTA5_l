# -*- coding: utf-8 -*-
"""注入 terminal.ini [Tester] 段指向本工程 EA（MTA5_l 同款方法）。"""
import sys
from pathlib import Path

TDIR = Path(r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65")
INI = TDIR / "config" / "terminal.ini"

TEMPLATE = """;
; DataEvent EA Tester config (injected by M4)
[Tester]
Expert=Experts\\Advisors\\{ea}.ex5
Symbol={symbol}
Period={period}
Model=1
FromDate={from_d}
ToDate={to_d}
ForwardMode=0
Deposit=500.00
Currency=USD
Leverage=2000
Optimization=0
Visual=0
Report={ea}_tester_report
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
LastExpert=Experts\\Advisors\\{ea}.ex5
LastIndicator=
LastTicksMode=0
LastCriterion=0
LastForward=2
LastDelay=91
LastOptimization=0
DateRange=3
DateFrom={date_from_epoch}
DateTo={date_to_epoch}
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
"""


def _epoch(date_str: str) -> int:
    import datetime
    return int(datetime.datetime.strptime(date_str, "%Y.%m.%d").replace(tzinfo=datetime.timezone.utc).timestamp())


def inject(ea: str, symbol: str, period: str, from_d: str, to_d: str) -> None:
    text = INI.read_text(encoding="ansi")
    # 移除旧 DataEvent Tester 段
    import re
    text = re.sub(r"; DataEvent EA Tester config.*?\n\[Tester\].*?(?=\n\[|\Z)", "", text, flags=re.S)
    block = TEMPLATE.format(ea=ea, symbol=symbol, period=period, from_d=from_d, to_d=to_d,
                            date_from_epoch=_epoch(from_d), date_to_epoch=_epoch(to_d))
    text = text.rstrip() + "\n" + block
    INI.write_text(text, encoding="ansi")
    print(f"[ini] injected Tester block for {ea} ({symbol} {period} {from_d}~{to_d})")


if __name__ == "__main__":
    ea = sys.argv[1]
    symbol = sys.argv[2] if len(sys.argv) > 2 else "XAUUSDm"
    period = sys.argv[3] if len(sys.argv) > 3 else "16386"  # H4=16386, H1=16385
    from_d = sys.argv[4] if len(sys.argv) > 4 else "2021.01.01"
    to_d = sys.argv[5] if len(sys.argv) > 5 else "2026.08.30"
    inject(ea, symbol, period, from_d, to_d)
