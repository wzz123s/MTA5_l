# -*- coding: utf-8 -*-
"""查 .ini 换行符 + InpNanRegOn 行的原始字节."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

ini = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Profiles\Tester\2H_M30_6H_ABC_EA.XAUUSDm.M30.20250101_20260814.200.ini"
data = open(ini, 'rb').read()
print("文件大小:", len(data))

# 检查换行符
crlf = data.count(b'\r\n')
lf = data.count(b'\n')
print("CRLF 数量:", crlf, " | LF 数量:", lf)

# 找 InpNanRegOn 的字节位置
for kw in [b'InpM30SMA55', b'InpNanRegOn', b'InpNanRegPct', b'InpSimMode']:
    idx = data.find(kw)
    if idx >= 0:
        # 打印该行前后 60 字节 hex
        s = max(0, idx-10)
        e = min(len(data), idx+60)
        chunk = data[s:e]
        print("\n%s @%d:" % (kw.decode(), idx))
        print("  hex:", chunk.hex(' '))
        # 尝试 utf-16-le 解码该 chunk
        try:
            print("  utf16:", chunk.decode('utf-16-le', errors='replace'))
        except Exception:
            pass
