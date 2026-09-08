# -*- coding: utf-8 -*-
"""evaluate - Backtest evaluation module (v3.10 tier+3stage)"""
from evaluate.metrics import calc_metrics, calc_metrics_long_short
from evaluate.visualize import equity_curve
from evaluate.backtest import (
    run_backtest,
    run_backtest_equity,         # reference comparison only, NOT real strategy
    run_backtest_3stage,         # v3.10 real strategy: tier + 3-stage TP
    DEFAULT_TIER_TABLE,
    get_tier_lots,
)