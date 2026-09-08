# -*- coding: utf-8 -*-
"""optimize.grid_search - Parameter grid search for strategy optimization"""
import pandas as pd
import numpy as np


def grid_search(trades_csv, param_grid, metric='total_pnl', min_trades=5):
    """
    Grid search over parameter combinations.

    Parameters
    ----------
    trades_csv : str or DataFrame
        Path to trade list CSV, or DataFrame with columns:
        '止损点数', '盈亏点数'
    param_grid : dict
        Keys are column names in trades DataFrame, values are lists of thresholds.
        e.g. {'止损点数': [(1,100), (2,50), (3,35)]} for lo/hi bounds.
    metric : str
        'total_pnl' | 'ev' | 'pf' | 'wr'. What to rank by.
    min_trades : int
        Minimum trades required for a parameter combo to be valid.

    Returns
    -------
    DataFrame sorted by metric descending, with columns:
    param_cols..., Trades, WR%, PF, EV, TotalPnL
    """
    if isinstance(trades_csv, str):
        encodings = ['utf-8-sig', 'utf-8', 'gbk']
        df = None
        for enc in encodings:
            try:
                df = pd.read_csv(trades_csv, encoding=enc)
                break
            except (UnicodeDecodeError, TypeError):
                continue
        if df is None:
            raise ValueError(f"Failed to read {trades_csv} with any encoding")
    else:
        df = trades_csv.copy()

    results = []

    # Build all param combos from param_grid
    keys = list(param_grid.keys())
    value_lists = [param_grid[k] for k in keys]

    from itertools import product
    for combo in product(*value_lists):
        # Apply filters: each combo item is (lo, hi) for that column
        mask = pd.Series(True, index=df.index)
        params = {}
        for i, key in enumerate(keys):
            lo, hi = combo[i]
            mask &= (df[key] >= lo) & (df[key] <= hi)
            params[f'{key}_lo'] = lo
            params[f'{key}_hi'] = hi

        subset = df[mask]
        if len(subset) < min_trades:
            continue

        wins = (subset['盈亏点数'] > 0).sum()
        profit = subset[subset['盈亏点数'] > 0]['盈亏点数'].sum()
        loss = abs(subset[subset['盈亏点数'] <= 0]['盈亏点数'].sum())
        pf = profit / loss if loss > 0 else 999
        wr = wins / len(subset) * 100
        ev = (profit - loss) / len(subset)
        total_pnl = profit - loss

        row = {
            **params,
            'Trades': len(subset),
            'WR%': round(wr, 1),
            'PF': round(pf, 2),
            'EV': round(ev, 1),
            'TotalPnL': round(total_pnl, 0),
        }
        results.append(row)

    if not results:
        return pd.DataFrame()

    out = pd.DataFrame(results)
    metric_col = {'total_pnl': 'TotalPnL', 'ev': 'EV', 'pf': 'PF', 'wr': 'WR%'}.get(metric, 'TotalPnL')
    out = out.sort_values(metric_col, ascending=False).reset_index(drop=True)
    return out


def fine_grid(trades_csv, lo_values, hi_values, metric='total_pnl', min_trades=5):
    """
    Fine-grained 2D grid search for stop loss bounds.

    Parameters
    ----------
    trades_csv : str or DataFrame
    lo_values : list of int
        Lower bound values to test.
    hi_values : list of int
        Upper bound values to test.
    metric : str
        Ranking metric.
    min_trades : int
        Minimum trade count.

    Returns
    -------
    DataFrame with columns: Lo, Hi, Trades, WR%, PF, EV, TotalPnL, $1.0/pt
    """
    if isinstance(trades_csv, str):
        encodings = ['utf-8-sig', 'utf-8', 'gbk']
        df = None
        for enc in encodings:
            try:
                df = pd.read_csv(trades_csv, encoding=enc)
                break
            except (UnicodeDecodeError, TypeError):
                continue
        if df is None:
            raise ValueError(f"Failed to read {trades_csv}")
    else:
        df = trades_csv.copy()

    results = []
    for lo in lo_values:
        for hi in hi_values:
            f = df[(df['止损点数'] >= lo) & (df['止损点数'] <= hi)]
            if len(f) < min_trades:
                continue
            wins = (f['盈亏点数'] > 0).sum()
            profit = f[f['盈亏点数'] > 0]['盈亏点数'].sum()
            loss = abs(f[f['盈亏点数'] <= 0]['盈亏点数'].sum())
            pf = profit / loss if loss > 0 else 999
            wr = wins / len(f) * 100 if len(f) > 0 else 0
            ev = (profit - loss) / len(f)
            total_pnl = profit - loss

            results.append({
                'Lo': lo, 'Hi': hi,
                'Trades': len(f),
                'WR%': round(wr, 1),
                'PF': round(pf, 2),
                'EV': round(ev, 1),
                'TotalPnL': round(total_pnl, 0),
            })

    if not results:
        return pd.DataFrame()

    out = pd.DataFrame(results)
    metric_col = {'total_pnl': 'TotalPnL', 'ev': 'EV', 'pf': 'PF', 'wr': 'WR%'}.get(metric, 'TotalPnL')
    out = out.sort_values(metric_col, ascending=False).reset_index(drop=True)
    return out
