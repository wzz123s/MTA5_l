# -*- coding: utf-8 -*-
"""evaluate.visualize - Equity curve and analysis charts"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt, numpy as np, pandas as pd

def equity_curve(trades_df, initial_capital=350, title='Equity Curve', save_path=None):
    """Plot equity curve from trade list."""
    trades_df['Equity'] = initial_capital + trades_df['PnL_$'].cumsum()
    
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(range(len(trades_df)), trades_df['Equity'].values, linewidth=1.2, color='#1a73e8')
    ax.axhline(y=initial_capital, color='gray', linestyle='--', alpha=0.5)
    ax.fill_between(range(len(trades_df)), initial_capital, trades_df['Equity'].values,
                    where=(trades_df['Equity'].values >= initial_capital), color='green', alpha=0.15)
    ax.fill_between(range(len(trades_df)), initial_capital, trades_df['Equity'].values,
                    where=(trades_df['Equity'].values < initial_capital), color='red', alpha=0.15)
    ax.set_xlabel('Trade #'); ax.set_ylabel('Equity ($)')
    ax.set_title(title); ax.grid(True, alpha=0.3)
    plt.tight_layout()
    if save_path: plt.savefig(save_path, dpi=150)
    return fig
