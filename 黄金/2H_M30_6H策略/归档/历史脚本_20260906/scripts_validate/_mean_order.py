# -*- coding: utf-8 -*-
"""对比 pandas mean vs 顺序求和 vs numpy sum（period=5/13）"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import numpy as np
import pandas as pd

F = r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\data\raw\mt5_history\2h_m30_6h_live\XAUUSDm_M30.csv"
df = pd.read_csv(F)
close = df['close'].values[:20]  # 前 20 个 close

for n in [5, 13]:
    chunk = close[:n]
    pm = pd.Series(chunk).mean()
    seq = sum(chunk) / n
    nps = np.sum(chunk) / n
    print("n=%d  pandas.mean=%.17g  顺序sum=%.17g  numpy.sum=%.17g" % (n, pm, seq, nps))
    print("   pandas vs 顺序 差异: %.3g" % abs(pm - seq))
    print("   pandas vs numpy 差异: %.3g" % abs(pm - nps))

# 也看 numpy 的 sum 是否 pairwise（对更大数组）
big = close[:13]
print("\n13个元素 顺序求和 vs numpy.sum:")
print("  顺序: %.17g" % sum(big))
print("  numpy: %.17g" % np.sum(big))
print("  差异: %.3g" % abs(sum(big) - np.sum(big)))
