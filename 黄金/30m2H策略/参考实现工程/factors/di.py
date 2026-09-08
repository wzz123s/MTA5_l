# -*- coding: utf-8 -*-
"""factors.di - Directional Indicators DI+ and DI-"""
from factors.base import BaseFactor, rolling_mean
import numpy as np

class DIPlus(BaseFactor):
    """DI+(n): Positive Directional Indicator"""
    def signal(self, df, n, factor_name):
        high, low, close = df['high'].values, df['low'].values, df['close'].values
        tr = np.maximum(high - low, np.maximum(
            np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
        tr[0] = high[0] - low[0]
        dm_p = np.where((high - np.roll(high, 1)) > (np.roll(low, 1) - low),
                        np.maximum(high - np.roll(high, 1), 0), 0)
        atr_n = rolling_mean(tr, n)
        df[factor_name] = rolling_mean(dm_p, n) / (atr_n + 0.0001) * 100
        return df

class DIMinus(BaseFactor):
    """DI-(n): Negative Directional Indicator"""
    def signal(self, df, n, factor_name):
        high, low, close = df['high'].values, df['low'].values, df['close'].values
        tr = np.maximum(high - low, np.maximum(
            np.abs(high - np.roll(close, 1)), np.abs(low - np.roll(close, 1))))
        tr[0] = high[0] - low[0]
        dm_m = np.where((np.roll(low, 1) - low) > (high - np.roll(high, 1)),
                        np.maximum(np.roll(low, 1) - low, 0), 0)
        atr_n = rolling_mean(tr, n)
        df[factor_name] = rolling_mean(dm_m, n) / (atr_n + 0.0001) * 100
        return df
