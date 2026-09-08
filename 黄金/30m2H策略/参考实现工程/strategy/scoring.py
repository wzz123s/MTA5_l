# -*- coding: utf-8 -*-
"""strategy.scoring - Multi-factor scoring system with configurable weights"""
import pandas as pd
import numpy as np
from factors.atr import ATR
from factors.di import DIPlus, DIMinus
from factors.sma_distance import SMADistance
from factors.bias import Bias
from factors.pct_change import PctChange
from factors.volatility import Volatility
from factors.bb_width import BBWidth


class MultiFactorScorer:
    """
    Multi-factor scoring system for trade filtering.

    Flow:
    1. Compute factors on 2H data
    2. Map factor values to each trade at entry time
    3. Compute percentile ranks (higher = better for all factors)
    4. Compute weighted composite score
    5. Filter by top-X% or score threshold

    Factor weights should be based on marginal contribution analysis.
    All factors are kept in config (even with zero weight) so weights
    can be adjusted when market conditions change.

    Default weights from marginal contribution analysis (2026-06):
        SMAdist_5:  0.335  (core - price deviation from SMA5)
        DIp_7:      0.302  (trend direction confirmation)
        PctChg_5:   0.277  (momentum alignment)
        ATR_14:     0.087  (volatility filter)
        Vol_7:      0.000  (redundant with SMAdist_5 + ATR_14)
        SMAdist_13: 0.000  (redundant with SMAdist_5)
        DIm_7:      0.000  (inverse of DIp_7, optional for shorts)
        BBWidth_13: 0.000  (not tested yet)

    v4.0 (2026-06-26) 三层分级新增 Bias 因子 (初始 weight=0,待 _factor_mining_v3.py MC 重定):
        Bias_5:     0.000  (H2 close - SMA5 偏离 %)
        Bias_13:    0.000
        Bias_55:    0.000  (Layer 1 大势判断,推荐关注)
        Bias_144:   0.000
        Bias_233:   0.000  (推荐关注)
    """

    # Default factor configuration
    # Format: {factor_key: {'class': factor_class, 'param': n, 'weight': w}}
    DEFAULT_CONFIG = {
        # v3.10 现 8 因子 (2026-06 MC 加权)
        'SMAdist_5':  {'class': SMADistance, 'param': 5,  'weight': 0.335},
        'DIp_7':      {'class': DIPlus,      'param': 7,  'weight': 0.302},
        'PctChg_5':   {'class': PctChange,   'param': 5,  'weight': 0.277},
        'ATR_14':     {'class': ATR,          'param': 14, 'weight': 0.087},
        'Vol_7':      {'class': Volatility,   'param': 7,  'weight': 0.000},
        'SMAdist_13': {'class': SMADistance,  'param': 13, 'weight': 0.000},
        'DIm_7':      {'class': DIMinus,      'param': 7,  'weight': 0.000},
        'BBWidth_13': {'class': BBWidth,      'param': 13, 'weight': 0.000},
        # v4.0 新增 5 个 Bias 因子 (初始 weight=0)
        'Bias_5':     {'class': Bias,         'param': 5,    'weight': 0.000},
        'Bias_13':    {'class': Bias,         'param': 13,   'weight': 0.000},
        'Bias_55':    {'class': Bias,         'param': 55,   'weight': 0.000},
        'Bias_144':   {'class': Bias,         'param': 144,  'weight': 0.000},
        'Bias_233':   {'class': Bias,         'param': 233,  'weight': 0.000},
    }

    def __init__(self, factor_config=None, top_pct=50):
        """
        Parameters
        ----------
        factor_config : dict or None
            Factor configuration. If None, uses DEFAULT_CONFIG.
        top_pct : float
            Top percentage of trades to keep by composite score (0-100).
            Default 50 = keep top 50%.
        """
        self.config = factor_config or self.DEFAULT_CONFIG.copy()
        self.top_pct = top_pct
        self._factor_cols = []
        self._weights = {}

    def compute_factors(self, high_df):
        """Compute all configured factors on high_df (2H data)."""
        for key, cfg in self.config.items():
            col = f"factor_{key}"
            cfg['class']().signal(high_df, cfg['param'], col)
            self._factor_cols.append(col)
            self._weights[col] = cfg['weight']
        return high_df

    def map_to_trades(self, trades_df, high_df):
        """
        Map 2H factor values to each trade at entry time.

        Parameters
        ----------
        trades_df : DataFrame
            Trade list with '开仓时间' column.
        high_df : DataFrame
            2H data with factor columns and 'date' column.

        Returns
        -------
        trades_df with added factor value columns.
        """
        if not self._factor_cols:
            raise ValueError("Call compute_factors() first")

        # Ensure high_df has date column
        if 'date' not in high_df.columns and isinstance(high_df.index, pd.DatetimeIndex):
            high_df = high_df.reset_index()

        hd = high_df['date'] if hasattr(high_df['date'], 'dt') else pd.to_datetime(high_df['date'])

        for col in self._factor_cols:
            trades_df[col] = np.nan

        for i, row in trades_df.iterrows():
            t = row['开仓时间']
            mask = hd <= t
            if not mask.any():
                continue
            hrow = high_df.iloc[high_df[mask].index[-1]]
            for col in self._factor_cols:
                trades_df.at[i, col] = hrow.get(col, np.nan)

        return trades_df

    def score(self, trades_df):
        """
        Compute composite score for each trade.

        For each factor: percentile rank across all trades (higher = better).
        Composite score = weighted average of ranks.

        Adds columns: score_{factor}, score_composite

        Returns
        -------
        trades_df with score columns added.
        """
        if not self._factor_cols:
            return trades_df

        rank_cols = []
        total_weight = sum(self._weights.values())
        if total_weight == 0:
            trades_df['score_composite'] = 0.5
            return trades_df

        trades_df['score_composite'] = 0.0
        for col in self._factor_cols:
            w = self._weights.get(col, 0)
            if w == 0:
                continue
            rank_col = f"score_{col.replace('factor_', '')}"
            # Percentile rank: higher value = higher rank (closer to 1.0)
            trades_df[rank_col] = trades_df[col].rank(pct=True)
            trades_df['score_composite'] += trades_df[rank_col] * w / total_weight
            rank_cols.append(rank_col)

        return trades_df

    def filter(self, trades_df):
        """
        Filter trades by composite score, keeping top top_pct%.

        Returns
        -------
        Filtered trades_df.
        """
        if 'score_composite' not in trades_df.columns:
            trades_df = self.score(trades_df)

        if self.top_pct >= 100:
            return trades_df

        threshold = trades_df['score_composite'].quantile(1 - self.top_pct / 100)
        filtered = trades_df[trades_df['score_composite'] >= threshold].copy()
        return filtered.reset_index(drop=True)

    def run(self, trades_df, high_df):
        """
        Full pipeline: compute factors, map, score, filter.

        Parameters
        ----------
        trades_df : DataFrame
            Trade list from strategy.
        high_df : DataFrame
            2H data (must have 'close', 'high', 'low' columns).

        Returns
        -------
        Filtered trades_df with factor and score columns.
        """
        high_df = self.compute_factors(high_df)
        trades_df = self.map_to_trades(trades_df, high_df)
        trades_df = self.score(trades_df)
        trades_df = self.filter(trades_df)
        return trades_df

    def summary(self):
        """Return current configuration summary."""
        active = {k: v['weight'] for k, v in self.config.items() if v['weight'] > 0}
        inactive = {k: v['weight'] for k, v in self.config.items() if v['weight'] == 0}
        return {
            'top_pct': self.top_pct,
            'active_factors': len(active),
            'active_weights': active,
            'inactive_factors': list(inactive.keys()),
        }
