# -*- coding: utf-8 -*-
"""optimize.stability - Year-by-year parameter stability analysis"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def stability_by_year(trades_df, param_config, year_col='开仓时间', pnl_col='盈亏点数', pt_value=1.0, initial_capital=350):
    """
    Analyze strategy stability year by year.

    Parameters
    ----------
    trades_df : DataFrame
        Trade list with datetime column and PnL column.
    param_config : dict
        Filter configuration: {'止损点数': (lo, hi)} or additional column filters.
    year_col : str
        Column name for trade open time.
    pnl_col : str
        Column name for profit/loss in points.
    pt_value : float
        Dollar value per point (lot_size * 10).
    initial_capital : float
        Starting equity.

    Returns
    -------
    DataFrame with yearly metrics: Trades, Wins, WR%, PF, EV, TotalPnL, Equity, MaxDD
    """
    df = trades_df.copy()
    if year_col in df.columns:
        df = df.dropna(subset=[year_col])
    else:
        raise KeyError(f"Column '{year_col}' not found. Available: {list(df.columns)}")

    df['Year'] = pd.to_datetime(df[year_col]).dt.year

    # Apply filters
    mask = pd.Series(True, index=df.index)
    for col, (lo, hi) in param_config.items():
        if col in df.columns:
            mask &= (df[col] >= lo) & (df[col] <= hi)

    filtered = df[mask].copy()
    if len(filtered) == 0:
        return pd.DataFrame()

    yearly_stats = []
    for year, group in filtered.groupby('Year'):
        n = len(group)
        wins = (group[pnl_col] > 0).sum()
        profit = group[group[pnl_col] > 0][pnl_col].sum()
        loss = abs(group[group[pnl_col] <= 0][pnl_col].sum())
        pf = profit / loss if loss > 0 else 999
        wr = wins / n * 100 if n > 0 else 0
        ev = (profit - loss) / n if n > 0 else 0
        total = profit - loss
        dollar_pnl = total * pt_value

        yearly_stats.append({
            'Year': int(year),
            'Trades': n,
            'Wins': wins,
            'WR%': round(wr, 1),
            'PF': round(pf, 2),
            'EV_pt': round(ev, 1),
            'TotalPnL_pt': round(total, 0),
            'TotalPnL_$': round(dollar_pnl, 0),
        })

    out = pd.DataFrame(yearly_stats).sort_values('Year')

    # Cumulative equity
    pt_values = []
    for _, row in filtered.iterrows():
        pt_values.append(row[pnl_col] * pt_value)

    cumulative = initial_capital + np.cumsum(pt_values)
    max_peaks = np.maximum.accumulate(cumulative)
    dd = max_peaks - cumulative

    return out, {
        'final_equity': cumulative[-1] if len(cumulative) > 0 else initial_capital,
        'max_equity': cumulative.max() if len(cumulative) > 0 else initial_capital,
        'max_dd': dd.max() if len(dd) > 0 else 0,
        'max_dd_pct': (dd.max() / (max_peaks[-1] + 0.01) * 100) if len(dd) > 0 else 0,
    }


def plot_stability(yearly_df, save_path=None):
    """
    Plot year-by-year bar chart of PnL.

    Parameters
    ----------
    yearly_df : DataFrame
        Output from stability_by_year() with Year and TotalPnL_$ columns.
    save_path : str or None
        Path to save the chart.

    Returns
    -------
    matplotlib Figure
    """
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # Bar: yearly PnL $
    ax1 = axes[0]
    years = yearly_df['Year'].values
    pnl = yearly_df['TotalPnL_$'].values
    colors = ['#2ecc71' if p > 0 else '#e74c3c' for p in pnl]
    ax1.bar(range(len(yearly_df)), pnl, color=colors, width=0.6)
    ax1.set_xticks(range(len(yearly_df)))
    ax1.set_xticklabels([str(int(y)) for y in years])
    ax1.set_ylabel('PnL ($)', fontsize=11)
    ax1.set_title('Year-by-Year PnL', fontsize=13)
    ax1.axhline(y=0, color='black', linewidth=0.5)
    ax1.grid(True, alpha=0.3)
    for i, (y, p, t) in enumerate(zip(years, pnl, yearly_df['Trades'].values)):
        ax1.text(i, p + (max(abs(pnl))*0.03), f'{t} trades', ha='center', fontsize=8)

    # Line: WR% and EV
    ax2 = axes[1]
    ax2.plot(range(len(yearly_df)), yearly_df['WR%'].values, 'o-', color='#3498db', linewidth=1.5, label='WR%')
    ax2.set_xticks(range(len(yearly_df)))
    ax2.set_xticklabels([str(int(y)) for y in years])
    ax2.set_ylabel('WR%', color='#3498db', fontsize=11)

    ax2b = ax2.twinx()
    ax2b.plot(range(len(yearly_df)), yearly_df['EV_pt'].values, 's-', color='#e67e22', linewidth=1.5, label='EV (pt)')
    ax2b.set_ylabel('EV (pt)', color='#e67e22', fontsize=11)

    ax2.set_title('Year-by-Year Win Rate & Expected Value', fontsize=13)
    ax2.grid(True, alpha=0.3)

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2b.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=9)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150)
    return fig
