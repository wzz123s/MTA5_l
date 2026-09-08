# -*- coding: utf-8 -*-
"""strategy.base - Abstract base class for all strategies"""
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.

    Subclasses must implement:
        - entry_signal(): Return list of entry dicts (开仓时间, 方向, 开仓价, 止损价...)
        - exit_signal(): Return exit signal for each position
        - run(): Compose entry + exit into a trades DataFrame

    For v3.10+ strategies, ``run()`` should return stage-aware output with
    columns like stage1_pnl_points, stage2_pnl_points, stage3_pnl_points,
    stage1_exit, stage2_exit, stage3_exit, total_lots. Then call
    ``evaluate.backtest.run_backtest_3stage()`` to fill in per-stage PnL
    using bar-level simulation (1.2R TP, 30m SMA13 trail, 2H flip exit).

    Inherited attributes:
        name : str         Strategy name
        main_tf : str      Main timeframe (e.g. '30m')
        high_tf : str      Higher timeframe for direction filter
        params : dict      Strategy parameters
    """

    def __init__(self, name='BaseStrategy', main_tf='30m', high_tf='2H', params=None):
        self.name = name
        self.main_tf = main_tf
        self.high_tf = high_tf
        self.params = params or {}

    @abstractmethod
    def entry_signal(self, main_df, high_df):
        """
        Generate entry signals.

        Parameters
        ----------
        main_df : DataFrame
            Main timeframe OHLCV + processed columns (dir, SMA_13, etc.)
        high_df : DataFrame
            Higher timeframe OHLCV + processed columns

        Returns
        -------
        DataFrame with columns: 开仓时间, 方向, 开仓价, 止损价, 止损点数
        """
        pass

    @abstractmethod
    def exit_signal(self, main_df, entry_row, position_idx):
        """
        Determine exit for a position.

        Parameters
        ----------
        main_df : DataFrame
            Main timeframe data.
        entry_row : Series
            The entry signal row.
        position_idx : int
            Row index of the entry in main_df.

        Returns
        -------
        dict with: 平仓时间, 平仓价, 平仓信号, 盈亏点数
        """
        pass

    @staticmethod
    def smma(series, n, m=1):
        """Smoothed Moving Average"""
        r = np.full(len(series), np.nan)
        r[n-1] = series[:n].mean()
        for i in range(n, len(series)):
            r[i] = (m * series[i] + (n - m) * r[i-1]) / n
        return r

    @staticmethod
    def rolling_mean(arr, window):
        """Fast rolling mean using cumsum"""
        r = np.full(len(arr), np.nan)
        cs = np.cumsum(np.nan_to_num(arr, 0))
        for i in range(window - 1, len(arr)):
            r[i] = (cs[i] - (cs[i - window] if i >= window else 0)) / window
        return r

    @staticmethod
    def nn(v):
        """Check if value is NaN float"""
        return isinstance(v, (float, np.floating)) and np.isnan(v)

    def __repr__(self):
        return f"{self.name}({self.main_tf}x{self.high_tf})"
