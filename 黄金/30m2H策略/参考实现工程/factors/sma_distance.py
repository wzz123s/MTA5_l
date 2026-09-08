# -*- coding: utf-8 -*-
"""factors.sma_distance - Distance from SMA as percentage"""
from factors.base import BaseFactor, rolling_mean
import numpy as np

class SMADistance(BaseFactor):
    """SMA Distance: |close - SMA(n)| / SMA(n) * 100"""
    def signal(self, df, n, factor_name):
        close = df['close'].values
        sma = rolling_mean(close, n)
        df[factor_name] = np.abs(close - sma) / (sma + 0.01) * 100
        return df
