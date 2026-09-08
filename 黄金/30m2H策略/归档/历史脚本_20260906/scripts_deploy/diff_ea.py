# -*- coding: utf-8 -*-
"""diff 30m2H vs 2H EA 逻辑差异."""
import sys, difflib
sys.stdout.reconfigure(encoding='utf-8')
a = open(r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_ABC_EA.mq5", encoding='utf-8').readlines()
b = open(r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade\30m2H_ABC_EA.mq5", encoding='utf-8').readlines()
diff = list(difflib.unified_diff(a, b, '2H', '30m2H', lineterm=''))
# 打印 diff 的行号范围 + 内容 (跳过 input 段大段)
print("diff 总行数:", len(diff))
out = []
for i, line in enumerate(diff):
    out.append(line)
# 写到文件分析
open(r"F:\use_code\MTA5_l\黄金\30m2H策略\scripts\deploy\ea_diff.txt", 'w', encoding='utf-8').write(''.join(out))
print("diff 已保存 ea_diff.txt, 共", len(out), "行")
# 打印 @@ 块标题 (定位差异区域)
for line in diff:
    if line.startswith('@@'):
        print(line.strip())
