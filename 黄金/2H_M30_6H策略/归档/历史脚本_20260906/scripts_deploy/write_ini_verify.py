# -*- coding: utf-8 -*-
"""写 InpNanRegOn=true + 立即读回验证."""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

ini = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Profiles\Tester\2H_M30_6H_ABC_EA.XAUUSDm.M30.20250101_20260814.200.ini"

# 读
raw = open(ini, 'r', encoding='utf-16').read()
print("读到 InpNanRegOn 行:")
for l in raw.split('\n'):
    if 'InpNanRegOn' in l:
        print("  改前:", repr(l))

# 改
raw2 = re.sub(r'InpNanRegOn=[^\r\n]*', 'InpNanRegOn=true||false||0||true||N', raw)

# 写回 utf-16 (明确 LE)
open(ini, 'w', encoding='utf-16-le', newline='').write(raw2)

# 读回验证
raw3 = open(ini, 'r', encoding='utf-16-le').read()
print("写回后 InpNanRegOn 行:")
for l in raw3.split('\n'):
    if 'InpNanRegOn' in l or 'InpM30SMA55' in l or 'InpNanRegPct' in l:
        print("  改后:", repr(l))
