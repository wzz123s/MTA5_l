# -*- coding: utf-8 -*-
"""factors.volatility - Return volatility (close pct_change rolling std)"""
from factors.base import BaseFactor

class Volatility(BaseFactor):
    """
    Volatility: rolling std of close-to-close percentage change over n bars.
    Low values = quiet/choppy market (SMA crossover signals noisy).
    High values = trending/volatile market.
    """
    def signal(self, df, n, factor_name):
        df[factor_name] = df['close'].pct_change().rolling(n, min_periods=1).std()
        return df

    @classmethod
    def get_parameter(cls):
        return [7, 14, 30]
