# -*- coding: utf-8 -*-
"""factors.atr - Average True Range"""
from factors.base import BaseFactor, rolling_mean
import numpy as np

class ATR(BaseFactor):
    """ATR(n): Average True Range"""
    def signal(self, df, n, factor_name):
        high, low, close = df['high'].values, df['low'].values, df['close'].values
        tr = np.maximum(high - low, np.maximum(
            np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
        tr[0] = high[0] - low[0]
        df[factor_name] = rolling_mean(tr, n)
        return df
