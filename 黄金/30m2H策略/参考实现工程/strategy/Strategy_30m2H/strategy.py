# -*- coding: utf-8 -*-
"""strategy.Strategy_30m2H - 30-minute x 2-Hour cross-period strategy for XAUUSD

v3.17 sync (2026-06-22):
  - Stop-finding logic aligned with EA v3.17 FindStopSMA (rollback).
  - MIN_BARS=30 guard added (defends against array OOB when bar history too short).
  - InpStopLookback parameter exposed (default 200, mirrors EA input).
  - Spec range check (stop_lo=3.0 / stop_hi=35.0 spec 点 = $3-$35) is done by
    the caller (entry_signal), matching EA line ~1147
    `if(stop_pts < InpStopLo || stop_pts > InpStopHi)`.
  - No v3.16 4-guard (MAX_LOOKBACK / MIN_SEG_LEN / MAX_SEG_LEN / MAX_DIST_PTS)
    was ever present in Python — segment walk-back uses the prior `good`/`bad`
    marker as `k`, then np.nanmin/nanmax over [k, pos) — equivalent to EA's
    "search entire history for most recent cross → MathMin/MathMax".
"""
import pandas as pd
import numpy as np
from strategy.base import BaseStrategy


# v3.17: minimum bar history required for stop search (defends against OOB).
# Matches EA FindStopSMA MIN_BARS=30.
MIN_BARS_FOR_STOP = 30

# v3.17: InpStopLookback equivalent. Kept for parity with EA (200 M30 bars =
# ~100 hours of history). The Python `k = pos - 1` walk already searches back
# to the prior cross marker, so this is informational / used by tests.
INP_STOP_LOOKBACK = 200


class Strategy30m2H(BaseStrategy):
    """
    30m x 2H cross-period strategy.
    Rules:
    1. 2H direction confirms: up/good -> long only, down/bad -> short only
    2. 2H close distance from SMA13 > sma13_threshold (0.5%)
    3. 30m SMA5/13 crossover generates entry signal (good=long, bad=short)
    4. Stop = prev_seg SMA13 extreme (min for long, max for short)
       [v3.17] Search walks back to prior cross marker (k), finds MathMin/MathMax
       over sma13_arr[k:pos]. Equivalent to EA FindStopSMA v3.17.
    5. Exit = next opposite crossover or stop hit
    6. Stop range filter: lo <= stop_pts <= hi (caller check, line 172)
    """

    def __init__(self, name='30mx2H', main_tf='30m', high_tf='2H',
                 stop_lo=3.0, stop_hi=35.0, sma13_threshold=0.5,
                 use_prev_way_filter=False, prev_way_threshold=0.7,
                 pt_value_per_lot=10.0,
                 # v3.17: stop search params (mirrors EA inputs)
                 stop_lookback=INP_STOP_LOOKBACK, min_bars_for_stop=MIN_BARS_FOR_STOP,
                 # v3.10 split TP params (match EA inputs)
                 stage_count=3, lots_per_stage=0.02,
                 stage1_r=1.2, stage2_trail_r=2.0, stage2_force_r=3.0,
                 stage3_use_2h_flip=True,
                 **kwargs):
        super().__init__(name=name, main_tf=main_tf, high_tf=high_tf, params=kwargs)
        self.stop_lo = stop_lo
        self.stop_hi = stop_hi
        self.sma13_threshold = sma13_threshold
        self.use_prev_way_filter = use_prev_way_filter
        self.prev_way_threshold = prev_way_threshold
        self.pt_value_per_lot = pt_value_per_lot
        # v3.17: stop search params (mirror EA FindStopSMA)
        self.stop_lookback = int(stop_lookback)
        self.min_bars_for_stop = int(min_bars_for_stop)
        # v3.10 split TP
        self.stage_count = stage_count
        self.lots_per_stage = lots_per_stage
        self.stage1_r = stage1_r
        self.stage2_trail_r = stage2_trail_r
        self.stage2_force_r = stage2_force_r
        self.stage3_use_2h_flip = stage3_use_2h_flip

    def mark_direction(self, df):
        """Mark SMA5/13 crossover direction on a DataFrame."""
        df = df.copy()
        close = df['close'].values
        n = len(df)
        sma5 = self.smma(close, 5)
        sma13 = self.smma(close, 13)
        df['SMA_5'] = sma5
        df['SMA_13'] = sma13
        s5g = sma5 > sma13
        s5p = np.roll(s5g, 1)
        s5p[0] = s5g[0]
        direction = np.full(n, '', dtype=object)
        for i in range(n):
            if s5g[i] and not s5p[i]:
                direction[i] = 'good'
            elif not s5g[i] and s5p[i]:
                direction[i] = 'bad'
            elif s5g[i]:
                direction[i] = 'up'
            else:
                direction[i] = 'down'
        df['方向'] = direction
        # Merge short segments (< 8 bars) via chain absorption
        merged = direction.copy()
        crossings = [(i, direction[i]) for i in range(n) if direction[i] in ('good', 'bad')]
        if len(crossings) > 0:
            state = 'down' if crossings[0][1] == 'good' else 'up'
            surv = []
            i = 0
            while i < len(crossings):
                pos, tp = crossings[i]
                if i + 1 >= len(crossings):
                    surv.append(pos)
                    break
                npos, ntp = crossings[i + 1]
                cnt = sum(1 for j in range(pos + 1, npos)
                          if direction[j] == ('up' if tp == 'good' else 'down'))
                if cnt < 8:
                    merged[pos:npos] = state
                    crossings.pop(i + 1)
                    crossings.pop(i)
                else:
                    surv.append(pos)
                    state = 'up' if tp == 'good' else 'down'
                    i += 1
            for pos in surv:
                merged[pos] = 'good' if direction[pos] == 'good' else 'bad'
        df['方向_合并后'] = merged
        return df

    def get_high_direction_at(self, high_df, time):
        """Get merged direction of higher TF at a given time."""
        if 'date' not in high_df.columns and isinstance(high_df.index, pd.DatetimeIndex):
            high_df = high_df.reset_index()
        if 'date' not in high_df.columns:
            return None, None, None, None
        hd = high_df['date'] if hasattr(high_df['date'], 'dt') else pd.to_datetime(high_df['date'])
        m = hd <= time
        if not m.any():
            return None, None, None, None
        row = high_df.iloc[high_df[m].index[-1]]
        direction = row.get('方向_合并后', row.get('dir', ''))
        sma13 = row.get('SMA_13', 0)
        close = row.get('close', 0)
        return direction, sma13, close, row.name

    def check_sma13_distance(self, high_df_entry):
        """Check if 2H close distance from SMA13 exceeds threshold."""
        _, sma13, close, _ = high_df_entry
        if close is None or sma13 is None or sma13 == 0:
            return False
        dist_pct = abs(close - sma13) / sma13 * 100
        return dist_pct >= self.sma13_threshold

    def entry_signal(self, main_df, high_df):
        """Generate all entry signals. Returns list of dicts."""
        if '方向_合并后' not in main_df.columns:
            main_df = self.mark_direction(main_df)
        if '方向_合并后' not in high_df.columns:
            high_df = self.mark_direction(high_df)
        mdir = main_df['方向_合并后'].values
        n = len(main_df)
        # v3.17: MIN_BARS guard (mirrors EA FindStopSMA MIN_BARS=30).
        # Skip signal generation when bar history is too short for a
        # meaningful stop search (defends against array OOB / degenerate segs).
        if n < self.min_bars_for_stop:
            return []
        entries = []
        for is_long in [True, False]:
            entry_type = 'good' if is_long else 'bad'
            opp_type = 'bad' if is_long else 'good'
            for pos in np.where(mdir == entry_type)[0]:
                j = pos + 1
                while j < n and mdir[j] != opp_type:
                    j += 1
                if j >= n:
                    continue
                row = main_df.iloc[pos]
                t = row['date'] if 'date' in main_df.columns else main_df.index[pos]
                h_entry = self.get_high_direction_at(high_df, t)
                hd, _, _, _ = h_entry
                if hd is None:
                    continue
                aligned = (hd in ('up', 'good')) if is_long else (hd in ('down', 'bad'))
                if not aligned:
                    continue
                if not self.check_sma13_distance(h_entry):
                    continue
                k = pos - 1
                while k >= 0 and mdir[k] not in ('good', 'bad'):
                    k -= 1
                if k < 0:
                    continue
                sma13_arr = main_df['SMA_13'].values
                # v3.17: stop is the SMA13 extreme of the prior segment (no v3.16
                # 4-guard). For LONG, prior segment was DOWN → np.nanmin gives
                # the lowest SMA13 = natural stop below entry. For SHORT, prior
                # segment was UP → np.nanmax gives the highest SMA13 = stop above.
                # This is equivalent to EA FindStopSMA's "search entire history
                # for most recent cross → MathMin/MathMax".
                if is_long:
                    seg_sma = sma13_arr[max(0, k):pos]
                    stop_price = np.nanmin(seg_sma) if len(seg_sma) > 0 else np.nan
                    if self.nn(stop_price):
                        continue
                    ep = (row['high'] + row['low'] + row['close']) / 3.0
                    if self.nn(ep) or stop_price >= ep:
                        continue
                    stop_pts = ep - stop_price
                else:
                    seg_sma = sma13_arr[max(0, k):pos]
                    stop_price = np.nanmax(seg_sma) if len(seg_sma) > 0 else np.nan
                    if self.nn(stop_price):
                        continue
                    ep = (row['high'] + row['low'] + row['close']) / 3.0
                    if self.nn(ep) or stop_price <= ep:
                        continue
                    stop_pts = stop_price - ep
                # v3.17: spec range check at caller (matches EA line ~1147).
                # stop_lo/stop_hi are in spec 点 (= USD price for XAUUSD).
                # EA equivalent uses MQL5 points (×1000) but Python uses spec 点.
                if stop_pts < self.stop_lo or stop_pts > self.stop_hi:
                    continue
                prev_seg_way_val = None
                if self.use_prev_way_filter:
                    if is_long and 'prev_seg_low_way_s_way' in main_df.columns:
                        prev_seg_way_val = main_df.iloc[pos].get('prev_seg_low_way_s_way', None)
                        if not self.nn(prev_seg_way_val) and prev_seg_way_val >= self.prev_way_threshold:
                            continue
                    elif not is_long and 'prev_seg_high_way_s_way' in main_df.columns:
                        prev_seg_way_val = main_df.iloc[pos].get('prev_seg_high_way_s_way', None)
                        if not self.nn(prev_seg_way_val) and prev_seg_way_val >= self.prev_way_threshold:
                            continue
                entries.append({
                    '开仓时间': t, '方向': '做多' if is_long else '做空',
                    '开仓价': round(ep, 2), '止损价': round(stop_price, 2),
                    '止损点数': round(stop_pts, 2),
                    'is_long': is_long, 'entry_idx': pos, 'exit_idx': j,
                    'prev_seg_low_way': prev_seg_way_val if is_long else None,
                    'prev_seg_high_way': prev_seg_way_val if not is_long else None,
                })
        return entries

    def exit_signal(self, main_df, entry_row, position_idx):
        """Not used directly; entry_signal contains exit info."""
        pass

    def run(self, main_df, high_df, stage_aware=True):
        """Run full strategy: generate entries, determine exits, calculate PnL.

        Parameters
        ----------
        main_df, high_df : DataFrame
            30m and 2H OHLCV with '方向_合并后' and 'SMA_13' columns.
        stage_aware : bool
            True (v3.10 default): single-row output with stage columns
            (stage1_pnl_points, stage2_pnl_points, stage3_pnl_points, etc.).
            Set False for legacy single-row output (no stage columns).

        Returns
        -------
        DataFrame with one row per entry. If stage_aware=True, columns include:
            - stage1_pnl_points, stage2_pnl_points, stage3_pnl_points
            - stage1_exit, stage2_exit, stage3_exit (label strings)
            - stage1_lots, stage2_lots, stage3_lots
            - total_lots, total_pnl_points
        Always includes: 开仓时间, 方向, 开仓价, 止损价, 止损点数, 平仓时间,
        平仓价, 平仓信号, 盈亏点数, 触及止损.
        """
        entries = self.entry_signal(main_df, high_df)
        if not entries:
            return pd.DataFrame()
        mdir = main_df['方向_合并后'].values
        rows = []
        for entry in entries:
            pos = entry['entry_idx']
            j = entry['exit_idx']
            is_long = entry['is_long']
            stop_price = entry['止损价']
            ep = entry['开仓价']
            opp_type = 'bad' if is_long else 'good'
            seg = main_df.iloc[pos + 1:j + 1]
            if is_long:
                hit_mask = seg['low'].values <= stop_price
            else:
                hit_mask = seg['high'].values >= stop_price
            hit = hit_mask.any() if len(hit_mask) > 0 else False
            if hit:
                hit_rel = hit_mask.argmax()
                exit_time = seg.iloc[hit_rel]['date'] if 'date' in seg.columns else seg.index[hit_rel]
                exit_price = stop_price
                exit_reason = 'stop'
                exit_pnl = -(ep - stop_price) if is_long else -(stop_price - ep)
            else:
                exit_time = main_df.iloc[j]['date'] if 'date' in main_df.columns else main_df.index[j]
                exit_price = main_df.iloc[j]['close']
                exit_reason = opp_type + '(平仓)'
                exit_pnl = exit_price - ep if is_long else ep - exit_price

            row = {
                **{k: v for k, v in entry.items() if k not in ('is_long', 'entry_idx', 'exit_idx')},
                '触及止损': '是' if hit else '否',
                '平仓时间': exit_time, '平仓价': round(exit_price, 2),
                '平仓信号': exit_reason, '盈亏点数': round(exit_pnl, 2),
            }

            if stage_aware:
                # Add per-stage PnL + exit columns.
                # In entry_signal-only mode (no bar-by-bar simulation),
                # treat the whole position as stage 1 (single-stage proxy).
                # For full bar-level simulation, call run_backtest_3stage()
                # from evaluate/backtest.py AFTER this run().
                s1 = round(self.lots_per_stage, 2) if self.stage_count >= 1 else 0
                s2 = round(self.lots_per_stage, 2) if self.stage_count >= 2 else 0
                s3 = round(self.lots_per_stage, 2) if self.stage_count >= 3 else 0
                row.update({
                    'total_lots':        round(s1 + s2 + s3, 4),
                    'stage1_lots':       s1,
                    'stage2_lots':       s2,
                    'stage3_lots':       s3,
                    'stage1_pnl_points': round(exit_pnl, 2) if self.stage_count >= 1 else 0,
                    'stage2_pnl_points': 0.0,   # filled by run_backtest_3stage
                    'stage3_pnl_points': 0.0,   # filled by run_backtest_3stage
                    'total_pnl_points':  round(exit_pnl, 2),
                    'stage1_exit':       exit_reason,
                    'stage2_exit':       '(待 run_backtest_3stage)',
                    'stage3_exit':       '(待 run_backtest_3stage)',
                    'stage1_pnl_$':      round(exit_pnl * s1 * self.pt_value_per_lot, 2),
                    'stage2_pnl_$':      0.0,
                    'stage3_pnl_$':      0.0,
                    'total_pnl_$':       round(exit_pnl * (s1 + s2 + s3) * self.pt_value_per_lot, 2),
                })
            rows.append(row)

        result = pd.DataFrame(rows)
        if len(result) > 0:
            result = result.sort_values('开仓时间').reset_index(drop=True)
        return result

    def summary(self, trades_df, lot_size=0.1):
        """Print strategy summary statistics."""
        if len(trades_df) == 0:
            return {'name': self.name, 'total_trades': 0}
        wins = (trades_df['盈亏点数'] > 0).sum()
        profit = trades_df[trades_df['盈亏点数'] > 0]['盈亏点数'].sum()
        loss = abs(trades_df[trades_df['盈亏点数'] <= 0]['盈亏点数'].sum())
        pf = profit / loss if loss > 0 else 999
        wr = wins / len(trades_df) * 100
        ev = (profit - loss) / len(trades_df)
        pts_per_lot = self.pt_value_per_lot
        dollar_pnl = (profit - loss) * lot_size * pts_per_lot
        return {
            'name': self.name, 'total_trades': len(trades_df),
            'wins': wins, 'losses': len(trades_df) - wins,
            'wr': f'{wr:.1f}%', 'pf': f'{pf:.2f}',
            'ev_pts': f'{ev:.1f}', 'total_pnl_pts': round(profit - loss, 0),
            'total_pnl_$': round(dollar_pnl, 0),
            'avg_stop': f'{trades_df["止损点数"].mean():.1f}',
        }
