# -*- coding: utf-8 -*-
"""factors.pct_change - Price momentum (close pct_change)"""
from factors.base import BaseFactor

class PctChange(BaseFactor):
    """PctChange: close.pct_change(n) - simple price momentum over n bars."""
    def signal(self, df, n, factor_name):
        df[factor_name] = df['close'].pct_change(n)
        return df
