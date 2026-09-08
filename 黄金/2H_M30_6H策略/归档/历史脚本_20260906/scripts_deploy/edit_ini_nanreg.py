# -*- coding: utf-8 -*-
"""修正: 用 utf-16 写回 .ini."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

ini = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Profiles\Tester\2H_M30_6H_ABC_EA.XAUUSDm.M30.20250101_20260814.200.ini"

# 读 (先 utf-16, 后 utf-8)
raw = None
for enc in ['utf-16', 'utf-8']:
    try:
        with open(ini, 'r', encoding=enc) as f:
            raw = f.read()
        print("读取编码:", enc)
        break
    except Exception as e:
        print("编码", enc, "失败:", e)

if raw is None:
    print("无法读取"); sys.exit(1)

import re
# 确保三个参数存在
lines = raw.split(chr(10))
has55 = any('InpM30SMA55' in l for l in lines)
hasOn = any('InpNanRegOn' in l for l in lines)
hasPct = any('InpNanRegPct' in l for l in lines)
print("has55=%s hasOn=%s hasPct=%s" % (has55, hasOn, hasPct))

if not hasOn:
    anchor = [l for l in lines if 'InpM30SMA13' in l]
    if anchor:
        idx = lines.index(anchor[0])
        lines[idx:idx+1] = [
            anchor[0],
            "InpM30SMA55=55||55||1||550||N",
            "InpNanRegOn=true||false||0||true||N",
            "InpNanRegPct=0.5||0.5||0.050000||5.000000||N",
        ]
    raw = chr(10).join(lines)
else:
    # 已有, 确保值为 true
    raw = re.sub(r'InpNanRegOn=.*', 'InpNanRegOn=true||false||0||true||N', raw)

# 用 utf-16 写回
with open(ini, 'w', encoding='utf-16', newline='') as f:
    f.write(raw)
print("已用 utf-16 写回")

# 验证
with open(ini, 'r', encoding='utf-16') as f:
    txt = f.read()
for l in txt.split(chr(10)):
    if 'InpNanRegOn' in l or 'InpM30SMA55' in l or 'InpNanRegPct' in l:
        print("  验证:", l.strip())
