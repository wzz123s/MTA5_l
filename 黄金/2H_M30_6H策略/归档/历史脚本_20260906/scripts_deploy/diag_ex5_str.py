# -*- coding: utf-8 -*-
"""搜 .ex5 二进制是否含 InpNanRegOn 字符串."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

for path in [
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Experts\Advisors\2H_M30_6H_ABC_EA.ex5",
    r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_ABC_EA.ex5",
]:
    try:
        data = open(path, 'rb').read()
        # ex5 可能压缩, 搜 utf-16 和 ascii
        for kw in ['InpNanRegOn', 'InpNanRegPct', 'InpM30SMA55']:
            a = kw.encode('ascii') in data
            u = kw.encode('utf-16-le') in data
            print("%s | %s: ascii=%s utf16=%s" % (path.split('\\')[-1], kw, a, u))
    except Exception as e:
        print(path, "读取失败", e)
