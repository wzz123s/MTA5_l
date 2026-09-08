# -*- coding: utf-8 -*-
"""验证 .ex5 字符串搜索: 对比旧参数 vs 新参数."""
import sys
sys.stdout.reconfigure(encoding='utf-8')

path = r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\DAD3B8CC3EAC09C0C9725021DF0C7A65\MQL5\Experts\Advisors\2H_M30_6H_ABC_EA.ex5"
data = open(path, 'rb').read()
print("ex5 大小:", len(data), "字节")

# 旧参数 vs 新参数
for kw in ['InpMagic', 'InpRiskPct', 'InpStopLoPt', 'InpMaxOpenVirtual', 'InpStage1R', 'InpM30SMA13', 'InpNanRegOn', 'InpM30SMA55', 'InpNanRegPct', 'InpHistoryBars']:
    a = kw.encode('ascii') in data
    u = kw.encode('utf-16-le') in data
    print("  %s: ascii=%s utf16=%s" % (kw, a, u))

# 检查是否是压缩文件 (MQL5 ex5 通常有特定 header)
print("\n头部 16 字节:", data[:16].hex())
