# -*- coding: utf-8 -*-
"""processing.smma - SMMA (Smoothed Moving Average) calculation"""

import pandas as pd
import numpy as np

def calc_smma(series, n, m=1):
    """
    SMMA(X, N, M) - 平滑移动平均
    第一步(初始化): 前N个周期的算术平均
    第二步(递推): SMA(i) = (M*CLOSE(i) + (N-M)*SMA(i-1)) / N
    """
    sma = pd.Series(index=series.index, dtype=float)
    sma.iloc[:n - 1] = pd.NA
    if len(series) >= n:
        sma.iloc[n - 1] = series.iloc[:n].mean()
        for i in range(n, len(series)):
            sma.iloc[i] = (m * series.iloc[i] + (n - m) * sma.iloc[i - 1]) / n
    return sma
