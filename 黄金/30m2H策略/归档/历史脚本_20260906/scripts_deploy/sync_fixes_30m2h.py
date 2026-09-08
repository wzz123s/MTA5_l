# -*- coding: utf-8 -*-
"""同步 2H 对齐修复(BUG-12/13/15)到 30m2H EA."""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

ea2h = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\auto_trade\2H_M30_6H_ABC_EA.mq5"
ea30 = r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade\30m2H_ABC_EA.mq5"

src2h = open(ea2h, encoding='utf-8').read()
src30 = open(ea30, encoding='utf-8').read()

def extract_func(src, name):
    """提取函数: name( 到花括号匹配结束."""
    start = src.index(name)
    brace_start = src.index('{', start)
    depth = 0
    for i in range(brace_start, len(src)):
        if src[i] == '{': depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                return src[start:i+1]
    return None

# 1) BuildMergedCodes
func_2h = extract_func(src2h, 'void BuildMergedCodes(')
func_30_old = extract_func(src30, 'void BuildMergedCodes(')
print("2H BuildMergedCodes len:", len(func_2h), "| 30m2H len:", len(func_30_old))
src30 = src30.replace(func_30_old, func_2h)
print("BuildMergedCodes 已替换")

# 2) DetectSignal
func_2h_ds = extract_func(src2h, 'bool DetectSignal(')
func_30_ds = extract_func(src30, 'bool DetectSignal(')
print("2H DetectSignal len:", len(func_2h_ds), "| 30m2H len:", len(func_30_ds))
src30 = src30.replace(func_30_ds, func_2h_ds)
print("DetectSignal 已替换")

# 3) OnTick: DetectSignal 调用加 raw_codes
# 30m2H 现在是 2H 签名(含 raw), 调用处需要传 raw_codes
# 找 DetectSignal( 调用 (非定义)
import re
src30 = re.sub(
    r'DetectSignal\(rates, n, sma5, sma13, merged, sig_idx, dir, mode, stop\)',
    'DetectSignal(rates, n, sma5, sma13, raw_codes, merged, sig_idx, dir, mode, stop)',
    src30
)
print("OnTick DetectSignal 调用已改")

open(ea30, 'w', encoding='utf-8').write(src30)
print("30m2H EA 已写回")
