# -*- coding: utf-8 -*-
"""对比 .ini 里 bool 参数格式."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

ini = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Profiles\Tester\2H_M30_6H_ABC_EA.XAUUSDm.M30.20250101_20260814.200.ini"

raw = None
for enc in ['utf-16', 'utf-8']:
    try:
        with open(ini, 'r', encoding=enc) as f:
            raw = f.read()
        print("编码:", enc)
        break
    except Exception as e:
        print(enc, "失败", e)

for line in raw.split(chr(10)):
    if any(k in line for k in ['InpSimMode', 'InpNanRegOn', 'InpExportCSV', 'InpAllowRealTrading', 'InpVerboseDiag', 'InpEventFilterOn']):
        print(repr(line))
