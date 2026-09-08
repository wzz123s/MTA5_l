# -*- coding: utf-8 -*-
"""evaluate.backtest - Backtest engines (fixed-lot, equity-compounding, tier+3stage)

Three engines available, in increasing realism:

1. ``run_backtest(trades_df)``
   Fixed lot size. Simplest, useful for sanity checks.

2. ``run_backtest_equity(trades_df, risk_pct=3.0)``
   Equity-compounding (lot = risk_amount / (stop * pt_value)).
   ⚠️ REFERENCE COMPARISON ONLY — NOT the real 30m2H strategy.
   Kept for showing the contrast vs tier+3stage.

3. ``run_backtest_3stage(trades_df, tier_table=DEFAULT_TIER_TABLE, ...)``
   **Real strategy engine**: position tier matching + 3-stage split TP.
   Matches EA v3.10 behavior exactly.

The default tier table is the canonical $350 → 0.06 lots starting tier
documented in 30m2H策略/策略说明.md → 仓位管理：仓位档位匹配.
"""
import pandas as pd
import numpy as np


# ============================================================================
# Tier table (canonical, matches 策略说明.md)
# ============================================================================
# Each row: (equity_low_inclusive, equity_high_exclusive, lots_per_signal)
# Default tier_lots is the SUM of stage lots (3 × 0.02 = 0.06) — i.e. one signal
# opens 3 × 0.02 sub-orders, total exposure = tier_lots.
# Users can override tier_table via parameter (e.g. for single-stage testing).

DEFAULT_TIER_TABLE = [
    # (equity_low, equity_high, total_lots_for_one_signal)
    (0,     350,   0.03),    # 起步前, 1 stage × 0.03 = 0.03
    (350,   700,   0.06),    # 起步档: 3 × 0.02 = 0.06
    (700,   1400,  0.12),    # 3 × 0.04 = 0.12
    (1400,  2800,  0.24),    # 3 × 0.08 = 0.24
    (2800,  5600,  0.48),    # 3 × 0.16 = 0.48
    (5600,  np.inf, 0.96),   # 3 × 0.32 = 0.96
]


def get_tier_lots(equity, tier_table=None):
    """Look up tier lots for a given equity.

    Parameters
    ----------
    equity : float
        Current account equity in dollars.
    tier_table : list of tuples or None
        Custom tier table. If None, uses DEFAULT_TIER_TABLE.

    Returns
    -------
    float
        Total lots for one signal (sum across all stages).
    """
    if tier_table is None:
        tier_table = DEFAULT_TIER_TABLE
    for low, high, lots in tier_table:
        if low <= equity < high:
            return float(lots)
    # Past highest tier → use last row
    return float(tier_table[-1][2])


# ============================================================================
# Engine 1: fixed lot
# ============================================================================

def run_backtest(trades_df, initial_capital=350, lot_size=0.1, pt_value_per_lot=10):
    """Fixed lot size backtest. Returns trades_df with PnL_$ and Equity columns.

    Simplest engine — useful for quick sanity checks but NOT the real strategy.
    Real strategy uses tier+3stage (see run_backtest_3stage).
    """
    result = trades_df.copy()
    result['PnL_$'] = result['盈亏点数'] * lot_size * pt_value_per_lot
    result['Equity'] = initial_capital + result['PnL_$'].cumsum()
    result['手数'] = lot_size
    return result


# ============================================================================
# Engine 2: equity-compounding (REFERENCE ONLY)
# ============================================================================

def run_backtest_equity(trades_df, initial_capital=350, risk_pct=3.0,
                        pt_value_per_lot=10, min_lots=0.01, max_lots=100.0):
    """Equity-compounding position sizing backtest.

    ⚠️ REFERENCE COMPARISON ONLY — NOT the real 30m2H strategy.
    Real strategy uses tier+3stage (see run_backtest_3stage).

    Kept to show the contrast: compounding gives aggressive growth but assumes
    unbounded position sizing, which the real tier system rejects for safety.

    For each trade sequentially:
      1. Current equity -> risk_amount = equity * risk_pct / 100
      2. Lots = risk_amount / (stop_points * pt_value_per_lot)
      3. Lots clamped to [min_lots, max_lots]
      4. PnL_$ = points * lots * pt_value_per_lot
      5. Equity += PnL_$
    Returns trades_df with PnL_$, 手数, Equity, 风险金额 columns.
    """
    df = trades_df.copy()
    n = len(df)
    pnl_dollar = np.zeros(n)
    lots_arr = np.zeros(n)
    equity_arr = np.zeros(n)
    risk_arr = np.zeros(n)
    equity = float(initial_capital)
    for i in range(n):
        stop_pts = float(df.iloc[i]['止损点数'])
        pnl_pts = float(df.iloc[i]['盈亏点数'])
        risk_amount = equity * risk_pct / 100.0
        if stop_pts > 0:
            lots = risk_amount / (stop_pts * pt_value_per_lot)
        else:
            lots = 0
        lots = max(min_lots, min(lots, max_lots))
        pnl_dollar[i] = pnl_pts * lots * pt_value_per_lot
        equity += pnl_dollar[i]
        equity = max(equity, 0)
        lots_arr[i] = lots
        equity_arr[i] = equity
        risk_arr[i] = risk_amount
    df['PnL_$'] = pnl_dollar
    df['手数'] = np.round(lots_arr, 4)
    df['Equity'] = equity_arr
    df['风险金额'] = np.round(risk_arr, 2)
    return df


# ============================================================================
# Engine 3: tier + 3-stage TP (REAL STRATEGY)
# ============================================================================
# Matches EA v3.10 (30m2H_Strategy_EA.mq5). Logic:
#
#   Per signal (entry):
#     Lots = tier_lots(equity) / InpStageCount    (e.g. 0.06/3 = 0.02 per stage)
#     Open InpStageCount sub-orders at same entry price with magic suffix.
#
#   Per stage exit (within bars from entry to next M30 opposite cross):
#     Stage 1 (0.02): close at 1.2R profit (active market close).
#       If price never reaches 1.2R before M30 opposite cross → close at next cross price.
#       If SL hit before → stage 1 exits at SL.
#     Stage 2 (0.02): after 2R, trail SL to 30m SMA13 (only ratchet up).
#       At 3R force-close. If M30 opposite cross before → close at cross.
#       If SL hit before → stage 2 exits at SL.
#     Stage 3 (0.02): passive, exits on 2H SMA5/13 reverse cross.
#       If 2H never flips before M30 opposite cross → close at M30 cross.
#       If SL hit before → stage 3 exits at SL.
#
# Output: original trades_df + per-stage PnL/exit columns + total PnL + Equity.

def run_backtest_3stage(trades_df, initial_capital=350,
                        tier_table=None,
                        stage1_r=1.2, stage2_trail_r=2.0, stage2_force_r=3.0,
                        stage_count=3, lots_per_stage=None,
                        pt_value_per_lot=10,
                        main_df=None, high_df=None,
                        use_2h_flip_for_stage3=True):
    """Tier-based position sizing + 3-stage TP backtest. Matches EA v3.10.

    Parameters
    ----------
    trades_df : DataFrame
        Output of Strategy30m2H.run() — must have 开仓时间, 方向, 开仓价,
        止损价, 止损点数, 平仓时间, 平仓价, 平仓信号, 盈亏点数.
    initial_capital : float
        Starting equity in dollars.
    tier_table : list or None
        Custom tier table. None → DEFAULT_TIER_TABLE.
    stage1_r, stage2_trail_r, stage2_force_r : float
        TP multipliers in R (R = stop distance in price units).
    stage_count : int
        Number of split stages (1, 2, or 3). 1 = single order (legacy).
    lots_per_stage : float or None
        Override lots per stage (e.g. 0.02). If None, derive from tier:
        lots_per_stage = tier_lots(equity_at_entry) / stage_count.
    pt_value_per_lot : float
        Dollar value per point per standard lot (XAUUSD = 10).
    main_df, high_df : DataFrame or None
        Optional: provide main (30m) and high (2H) data so stage 2/3 TP
        simulation can use 30m SMA13 trailing and 2H reverse-cross exit.
        If None, only stage 1 TP (1.2R) is fully simulated; stages 2/3
        fall back to M30 opposite cross exit (simpler, less realistic).
    use_2h_flip_for_stage3 : bool
        If True AND high_df provided: stage 3 waits for 2H SMA5/13 reverse cross.
        If False: stage 3 closes at next M30 opposite cross like stages 1/2.

    Returns
    -------
    trades_df copy with added columns:
        total_lots         — total lots for this entry (= tier_lots)
        stage1_lots        — lots in stage 1 sub-order
        stage2_lots        — lots in stage 2 sub-order (0 if stage_count < 2)
        stage3_lots        — lots in stage 3 sub-order (0 if stage_count < 3)
        stage1_pnl_points  — stage 1 PnL in price points
        stage2_pnl_points  — stage 2 PnL in price points
        stage3_pnl_points  — stage 3 PnL in price points
        total_pnl_points   — sum of stage PnLs (matches 盈亏点数 for single-stage)
        stage1_exit        — '1.2R TP' | 'M30 cross' | 'SL hit' | '2H flip' | 'still open'
        stage2_exit        — same vocabulary
        stage3_exit        — same vocabulary
        stage1_pnl_$       — stage 1 PnL in dollars
        stage2_pnl_$       — stage 2 PnL in dollars
        stage3_pnl_$       — stage 3 PnL in dollars
        total_pnl_$        — sum of stage PnLs in dollars
        Equity             — running equity after this entry
    """
    if tier_table is None:
        tier_table = DEFAULT_TIER_TABLE

    df = trades_df.copy()
    n = len(df)
    equity = float(initial_capital)

    # Allocate output arrays
    out = {
        'total_lots': np.zeros(n),
        'stage1_lots': np.zeros(n),
        'stage2_lots': np.zeros(n),
        'stage3_lots': np.zeros(n),
        'stage1_pnl_points': np.zeros(n),
        'stage2_pnl_points': np.zeros(n),
        'stage3_pnl_points': np.zeros(n),
        'total_pnl_points': np.zeros(n),
        'stage1_exit': [''] * n,
        'stage2_exit': [''] * n,
        'stage3_exit': [''] * n,
        'stage1_pnl_$': np.zeros(n),
        'stage2_pnl_$': np.zeros(n),
        'stage3_pnl_$': np.zeros(n),
        'total_pnl_$': np.zeros(n),
        'Equity': np.zeros(n),
    }

    # Pre-build main_df / high_df lookups if provided
    main_lookup = None
    high_lookup = None
    if main_df is not None:
        main_lookup = _build_ohlcv_lookup(main_df)
    if high_df is not None:
        high_lookup = _build_ohlcv_lookup(high_df)

    for i in range(n):
        row = df.iloc[i]
        ep       = float(row['开仓价'])
        stop     = float(row['止损价'])
        exit_p   = float(row['平仓价'])
        is_long  = '做多' in str(row.get('方向', ''))
        R        = abs(ep - stop)             # R = stop distance in price units
        if R <= 0:
            # Invalid entry — skip
            out['Equity'][i] = equity
            continue

        # Position sizing from tier table
        total_lots = get_tier_lots(equity, tier_table)
        if lots_per_stage is None:
            per = total_lots / max(stage_count, 1)
        else:
            per = float(lots_per_stage)
            total_lots = per * stage_count

        # Per-stage lots (round to 2 decimals = 0.01 step)
        s1_lots = round(per, 2) if stage_count >= 1 else 0.0
        s2_lots = round(per, 2) if stage_count >= 2 else 0.0
        s3_lots = round(per, 2) if stage_count >= 3 else 0.0

        # Compute per-stage exits
        entry_time = row.get('开仓时间')
        exit_time  = row.get('平仓时间')
        m30_cross_exit_p = exit_p     # default: M30 opposite cross exit price
        m30_cross_exit_t = exit_time

        # Stage 1: 1.2R TP (active market close), else exit at M30 cross / SL
        s1_exit, s1_exit_p, s1_exit_t = _stage1_outcome(
            ep, stop, R, is_long, m30_cross_exit_p, m30_cross_exit_t,
            stage1_r=stage1_r,
            main_lookup=main_lookup, entry_time=entry_time,
        )
        s1_pnl_pts = (s1_exit_p - ep) if is_long else (ep - s1_exit_p)

        # Stage 2: 2R SMA13 trail + 3R force, else exit at M30 cross / SL
        s2_exit, s2_exit_p, s2_exit_t = _stage2_outcome(
            ep, stop, R, is_long, m30_cross_exit_p, m30_cross_exit_t,
            stage2_trail_r=stage2_trail_r, stage2_force_r=stage2_force_r,
            main_lookup=main_lookup, entry_time=entry_time,
        )
        s2_pnl_pts = (s2_exit_p - ep) if is_long else (ep - s2_exit_p)

        # Stage 3: passive, exits on 2H flip (if use_2h_flip + high_df), else M30 cross
        s3_exit, s3_exit_p, s3_exit_t = _stage3_outcome(
            ep, stop, R, is_long, m30_cross_exit_p, m30_cross_exit_t,
            use_2h_flip=use_2h_flip_for_stage3 and high_lookup is not None,
            main_lookup=main_lookup, high_lookup=high_lookup,
            entry_time=entry_time,
        )
        s3_pnl_pts = (s3_exit_p - ep) if is_long else (ep - s3_exit_p)

        # Convert points → dollars
        s1_dollar = s1_pnl_pts * s1_lots * pt_value_per_lot
        s2_dollar = s2_pnl_pts * s2_lots * pt_value_per_lot
        s3_dollar = s3_pnl_pts * s3_lots * pt_value_per_lot
        total_dollar = s1_dollar + s2_dollar + s3_dollar
        total_pnl_pts = s1_pnl_pts + s2_pnl_pts + s3_pnl_pts

        # Update equity
        equity += total_dollar
        equity = max(equity, 0)

        out['total_lots'][i]        = round(s1_lots + s2_lots + s3_lots, 4)
        out['stage1_lots'][i]       = s1_lots
        out['stage2_lots'][i]       = s2_lots
        out['stage3_lots'][i]       = s3_lots
        out['stage1_pnl_points'][i] = round(s1_pnl_pts, 2)
        out['stage2_pnl_points'][i] = round(s2_pnl_pts, 2)
        out['stage3_pnl_points'][i] = round(s3_pnl_pts, 2)
        out['total_pnl_points'][i]  = round(total_pnl_pts, 2)
        out['stage1_exit'][i]       = s1_exit
        out['stage2_exit'][i]       = s2_exit
        out['stage3_exit'][i]       = s3_exit
        out['stage1_pnl_$'][i]      = round(s1_dollar, 2)
        out['stage2_pnl_$'][i]      = round(s2_dollar, 2)
        out['stage3_pnl_$'][i]      = round(s3_dollar, 2)
        out['total_pnl_$'][i]       = round(total_dollar, 2)
        out['Equity'][i]            = round(equity, 2)

    # Assign all output columns at once
    for col, arr in out.items():
        df[col] = arr

    # Keep legacy 'PnL_$' = total_pnl_$ for backward compat with old scripts
    if 'PnL_$' not in df.columns:
        df['PnL_$'] = out['total_pnl_$']
    return df


# ============================================================================
# Stage outcome simulators (pure OHLCV scans)
# ============================================================================

def _build_ohlcv_lookup(df):
    """Convert OHLCV df to a list of (timestamp, O, H, L, C, sma13) sorted by time.

    Strategy_30m2H.mark_direction adds SMA_13 column for 30m data;
    for 2H data the same column is added when mark_direction is called.
    Returns a list of dicts so binary search can find bars after entry_time.
    """
    rows = []
    if 'date' in df.columns:
        ts = pd.to_datetime(df['date'])
    else:
        ts = df.index
    for i, (_, r) in enumerate(df.iterrows()):
        rows.append({
            'i': i,
            't': ts.iloc[i] if hasattr(ts, 'iloc') else ts[i],
            'O': float(r['open']),
            'H': float(r['high']),
            'L': float(r['low']),
            'C': float(r['close']),
            'sma13': float(r['SMA_13']) if 'SMA_13' in df.columns else 0.0,
            'dir': str(r['方向_合并后']) if '方向_合并后' in df.columns else '',
        })
    return rows


def _bars_after(lookup, t):
    """Return list of bars whose timestamp >= t (assumes sorted lookup)."""
    if not lookup:
        return []
    # Binary search for first bar >= t
    lo, hi = 0, len(lookup)
    while lo < hi:
        mid = (lo + hi) // 2
        if lookup[mid]['t'] < t:
            lo = mid + 1
        else:
            hi = mid
    return lookup[lo:]


def _stage1_outcome(ep, stop, R, is_long, m30_cross_exit_p, m30_cross_exit_t,
                    stage1_r, main_lookup, entry_time):
    """Stage 1: close at 1.2R profit if reached before M30 cross / SL.

    Returns (exit_label, exit_price, exit_time).
    """
    target_p = ep + stage1_r * R if is_long else ep - stage1_r * R

    if main_lookup is None or entry_time is None:
        # No bar data — fall back to M30 cross exit
        if m30_cross_exit_t is not None and _price_reached(m30_cross_exit_p, ep, target_p, is_long):
            return '1.2R TP (fallback)', m30_cross_exit_p, m30_cross_exit_t
        if (is_long and m30_cross_exit_p <= stop) or (not is_long and m30_cross_exit_p >= stop):
            return 'SL hit (fallback)', stop, m30_cross_exit_t
        return 'M30 cross', m30_cross_exit_p, m30_cross_exit_t

    # Scan bars after entry
    bars = _bars_after(main_lookup, entry_time)
    for bar in bars:
        # Check SL first (conservative)
        if is_long and bar['L'] <= stop:
            return 'SL hit', stop, bar['t']
        if not is_long and bar['H'] >= stop:
            return 'SL hit', stop, bar['t']
        # Check 1.2R target reached (use High for long, Low for short)
        if is_long and bar['H'] >= target_p:
            return f'{stage1_r}R TP', target_p, bar['t']
        if not is_long and bar['L'] <= target_p:
            return f'{stage1_r}R TP', target_p, bar['t']
    # Never reached → exit at M30 cross
    return 'M30 cross', m30_cross_exit_p, m30_cross_exit_t


def _stage2_outcome(ep, stop, R, is_long, m30_cross_exit_p, m30_cross_exit_t,
                    stage2_trail_r, stage2_force_r,
                    main_lookup, entry_time):
    """Stage 2: 30m SMA13 trail after 2R, force close at 3R, else M30 cross / SL."""
    target_2r_p = ep + stage2_trail_r * R if is_long else ep - stage2_trail_r * R
    target_3r_p = ep + stage2_force_r * R if is_long else ep - stage2_force_r * R
    # Trailing SL starts at the original stop, then only ratchets favorably
    trail_sl = stop

    if main_lookup is None or entry_time is None:
        # Fallback: assume best case 3R hit (we have no bar data)
        return '3R forced (fallback)', target_3r_p, m30_cross_exit_t

    bars = _bars_after(main_lookup, entry_time)
    for bar in bars:
        # Check 3R force first (highest priority)
        if is_long and bar['H'] >= target_3r_p:
            return f'{stage2_force_r}R forced', target_3r_p, bar['t']
        if not is_long and bar['L'] <= target_3r_p:
            return f'{stage2_force_r}R forced', target_3r_p, bar['t']
        # Check original/trailing SL
        if is_long and bar['L'] <= trail_sl:
            return 'SL hit', trail_sl, bar['t']
        if not is_long and bar['H'] >= trail_sl:
            return 'SL hit', trail_sl, bar['t']
        # Once 2R reached, ratchet SL to 30m SMA13 (only favorable direction)
        if is_long and bar['H'] >= target_2r_p:
            # Long: ratchet SL UP only
            if bar['sma13'] > trail_sl:
                trail_sl = bar['sma13']
        if not is_long and bar['L'] <= target_2r_p:
            # Short: ratchet SL DOWN only
            if bar['sma13'] < trail_sl or trail_sl == stop:
                if bar['sma13'] > 0:
                    trail_sl = bar['sma13']
    # Never reached 3R → exit at M30 cross
    return 'M30 cross', m30_cross_exit_p, m30_cross_exit_t


def _stage3_outcome(ep, stop, R, is_long, m30_cross_exit_p, m30_cross_exit_t,
                    use_2h_flip, main_lookup, high_lookup, entry_time):
    """Stage 3: passive, exit on 2H SMA5/13 reverse cross OR M30 cross (fallback).

    2H flip detection: compare current 2H close vs 2H SMA13. When 2H close
    crosses SMA13 opposite to position direction, that's the exit.
    Approximation: since we don't have SMA5 on 2H here, use the same logic
    the MQL5 EA uses (2H SMA5/13 reverse cross) — implemented in mark_direction
    via 'good'/'bad' labels. We use 方向_合并后 column for direction.
    """
    if not use_2h_flip or high_lookup is None or entry_time is None:
        # No 2H data — fall back to M30 cross (or SL if hit first)
        if main_lookup is not None and entry_time is not None:
            bars = _bars_after(main_lookup, entry_time)
            for bar in bars:
                if is_long and bar['L'] <= stop:
                    return 'SL hit', stop, bar['t']
                if not is_long and bar['H'] >= stop:
                    return 'SL hit', stop, bar['t']
        return 'M30 cross', m30_cross_exit_p, m30_cross_exit_t

    # Scan 2H bars after entry; check each for direction flip opposite to position
    hbars = _bars_after(high_lookup, entry_time)
    flipped_bar = None
    for hbar in hbars:
        d = hbar['dir']
        if is_long and d == 'bad':       # up-trend broken on 2H
            flipped_bar = hbar
            break
        if not is_long and d == 'good':  # down-trend broken on 2H
            flipped_bar = hbar
            break

    if flipped_bar is not None:
        return '2H flip', flipped_bar['C'], flipped_bar['t']

    # Also check SL via main_df
    if main_lookup is not None:
        bars = _bars_after(main_lookup, entry_time)
        for bar in bars:
            if is_long and bar['L'] <= stop:
                return 'SL hit', stop, bar['t']
            if not is_long and bar['H'] >= stop:
                return 'SL hit', stop, bar['t']

    # Never flipped 2H → exit at M30 cross
    return 'M30 cross', m30_cross_exit_p, m30_cross_exit_t


def _price_reached(cross_price, entry, target, is_long):
    """Did price reach target before M30 cross exit?"""
    if is_long:
        return max(cross_price, target) == target and target >= entry
    else:
        return min(cross_price, target) == target and target <= entry