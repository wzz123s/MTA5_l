
import re
src = open(r'F:\use_code\MTA5_l\黄金\30m2H策略\scripts\deploy\run_exness_full2.py', encoding='utf-8').read()
# 在 find_exness 结果前优先用固定 handle
src = src.replace("found = find_exness()", "found = find_exness()\nFIXED = [h for h in found if True]  # noop")
open(r'F:\use_code\MTA5_l\黄金\30m2H策略\scripts\deploy\run_exness_full2.py', 'w', encoding='utf-8').write(src)
print('patched placeholder')
