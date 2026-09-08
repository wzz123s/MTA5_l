# -*- coding: utf-8 -*-
"""factors.bb_width - Bollinger Band width"""
from factors.base import BaseFactor, rolling_mean
import numpy as np

class BBWidth(BaseFactor):
    """BB Width: 2 * std(n) / SMA(n) * 100"""
    def signal(self, df, n, factor_name):
        close = df['close'].values
        sma = rolling_mean(close, n)
        std = np.array([np.std(close[max(0, i-n+1):i+1]) for i in range(len(close))])
        df[factor_name] = std * 2 / (sma + 0.01) * 100
        return df
