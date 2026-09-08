# -*- coding: utf-8 -*-
"""evaluate.metrics - Strategy evaluation metrics"""
import pandas as pd, numpy as np

def calc_metrics(equity_df, pnl_column='PnL_$', initial_capital=350):
    """Calculate comprehensive strategy metrics."""
    pnl = equity_df[pnl_column].values
    wins = pnl[pnl > 0]; losses = pnl[pnl < 0]
    n_total = len(pnl); n_wins = len(wins); n_losses = len(losses)
    
    total_profit = wins.sum(); total_loss = abs(losses.sum())
    pf = total_profit / total_loss if total_loss > 0 else 999
    wr = n_wins / n_total * 100 if n_total > 0 else 0
    ev = pnl.sum() / n_total if n_total > 0 else 0
    avg_win = wins.mean() if n_wins > 0 else 0
    avg_loss = losses.mean() if n_losses > 0 else 0
    rr = abs(avg_win / avg_loss) if avg_loss != 0 else 999
    
    # Max consecutive loss
    cl, ml = 0, 0
    for p in pnl:
        if p > 0: cl = 0
        else: cl += 1; ml = max(ml, cl)
    
    # Equity curve
    equity = initial_capital + np.cumsum(pnl)
    max_equity = equity.max()
    dd = np.maximum.accumulate(equity) - equity
    max_dd = dd.max()
    max_dd_pct = max_dd / (max_equity - max_dd + 0.01) * 100
    
    return {
        '交易总数': n_total, '盈利笔数': n_wins, '亏损笔数': n_losses,
        '胜率': f'{wr:.1f}%', '盈利因子': f'{pf:.2f}',
        '平均盈利': f'{avg_win:.1f}', '平均亏损': f'{avg_loss:.1f}',
        '盈亏比': f'{rr:.1f}:1', '期望值': f'{ev:.1f}',
        '总净盈亏': f'{pnl.sum():.0f}',
        '最大连续亏损': ml,
        '最大回撤': f'{max_dd:.0f}({max_dd_pct:.1f}%)',
        '初始资金': initial_capital, '最终权益': f'{equity[-1]:.0f}',
        '最大权益': f'{max_equity:.0f}',
    }

def calc_metrics_long_short(long_df, short_df, initial_capital=350):
    """Calculate metrics separately for long and short trades."""
    lm = calc_metrics(long_df, 'PnL_$', initial_capital) if len(long_df) > 0 else {}
    sm = calc_metrics(short_df, 'PnL_$', initial_capital) if len(short_df) > 0 else {}
    combined = pd.concat([long_df, short_df]) if len(long_df) > 0 and len(short_df) > 0 else (long_df if len(long_df) > 0 else short_df)
    cm = calc_metrics(combined, 'PnL_$', initial_capital)
    return {'多头': lm, '空头': sm, '合并': cm}
