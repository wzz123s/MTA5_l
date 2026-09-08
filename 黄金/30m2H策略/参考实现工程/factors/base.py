# -*- coding: utf-8 -*-
"""factors.base - Factor base class with get_parameter() support"""
import numpy as np

def rolling_mean(arr, window):
    r = np.full(len(arr), np.nan)
    cs = np.cumsum(np.nan_to_num(arr, 0))
    for i in range(window - 1, len(arr)):
        r[i] = (cs[i] - (cs[i - window] if i >= window else 0)) / window
    return r

class BaseFactor:
    """
    Base factor class with signal(df, n, factor_name) interface.
    Subclasses must implement signal().
    Optionally override get_parameter() to declare preferred parameter list
    (used by grid search / parameter optimization).
    """
    def signal(self, df, n, factor_name):
        raise NotImplementedError

    @classmethod
    def get_parameter(cls):
        """Return list of preferred parameter values for this factor.
        Override in subclass to declare custom parameter list.
        Default: [5, 8, 13, 55, 168, 233] (Fibonacci-like common periods)."""
        return [5, 8, 13, 55, 168, 233]
