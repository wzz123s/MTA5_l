#!/usr/bin/env python3
"""
全数据生成脚本 — 30m2H EA v3.18 (分级 H2) 数据准备
=================================================
读 M30 raw -> 算 SMMA5/13 -> 同步 H2 -> 算 cross/tier/decision -> 输出 CSV
"""
import csv
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent
SRC  = BASE_DIR / 'XAUUSDm30.csv'
OUT  = BASE_DIR / 'full_data_30m2h.csv'

# === v3.18 分级参数 ===
H2_TIER_HI      = 0.10   # T3 下限 (%)
H2_TIER_MID_POS = 0.03   # T2 下限 / T1 上限 (%)
H2_TIER_MID_NEG = -0.03  # T1 下限 (反向硬阻断)
LOT_MUL_T3 = 1.0
LOT_MUL_T2 = 0.6
LOT_MUL_T1 = 0.3


def smma(values, period):
    """MQL5 MODE_SMMA: SMMA[i] = (SMMA[i-1]*(p-1) + price[i]) / p"""
    if len(values) < period:
        return [None] * len(values)
    sma = sum(values[:period]) / period
    out = [None] * (period - 1) + [sma]
    for i in range(period, len(values)):
        out.append((out[-1] * (period - 1) + values[i]) / period)
    return out


def resample_h2(m30_rows):
    """把 M30 行聚合成 H2 行 (4 根 M30 = 1 根 H2),保留 OHLCV"""
    h2 = []
    for i in range(0, len(m30_rows), 4):
        chunk = m30_rows[i:i + 4]
        if not chunk:
            continue
        h2.append({
            'time':  chunk[0]['time'],
            'open':  chunk[0]['open'],
            'high':  max(r['high'] for r in chunk),
            'low':   min(r['low']  for r in chunk),
            'close': chunk[-1]['close'],
        })
    return h2


def h2_align_to_m30(m30_times, h2_rows):
    """每个 M30 bar 找到它所属 H2 bar 的索引 (last H2 bar with time <= m30_time)"""
    h2_times = [datetime.strptime(r['time'], '%Y-%m-%d %H:%M:%S') for r in h2_rows]
    m30_t = [datetime.strptime(t, '%Y-%m-%d %H:%M:%S') for t in m30_times]
    idx = []
    j = 0
    for t in m30_t:
        while j + 1 < len(h2_times) and h2_times[j + 1] <= t:
            j += 1
        idx.append(j if h2_times[j] <= t else -1)
    return idx


def main():
    print(f'Reading {SRC}...')
    rows = []
    with open(SRC, 'r', encoding='gbk') as f:
        reader = csv.reader(f)
        header = next(reader)
        for r in reader:
            rows.append({
                'time':  r[0],
                'open':  float(r[1]),
                'high':  float(r[2]),
                'low':   float(r[3]),
                'close': float(r[4]),
                'vol':   float(r[5]) if len(r) > 5 else 0,
            })
    print(f'  total M30 bars: {len(rows)}')
    print(f'  range: {rows[0]["time"]} -> {rows[-1]["time"]}')

    # H2 聚合
    print('Resampling to H2...')
    h2_rows = resample_h2(rows)
    print(f'  total H2 bars: {len(h2_rows)}')
    print(f'  range: {h2_rows[0]["time"]} -> {h2_rows[-1]["time"]}')

    # 计算 SMMA
    print('Computing SMAs...')
    m30_close = [r['close'] for r in rows]
    m30_sma5  = smma(m30_close, 5)
    m30_sma13 = smma(m30_close, 13)

    h2_close  = [r['close'] for r in h2_rows]
    h2_sma5   = smma(h2_close, 5)
    h2_sma13  = smma(h2_close, 13)

    # H2 -> M30 对齐
    m30_times = [r['time'] for r in rows]
    h2_idx = h2_align_to_m30(m30_times, h2_rows)

    # 写 CSV
    print(f'Writing {OUT}...')
    out_fields = [
        'bar_time', 'close',
        'm30_sma5', 'm30_sma13', 'm30_diff', 'm30_dist%',
        'm30_cross',
        'h2_time', 'h2_sma5', 'h2_sma13', 'h2_diff', 'h2_dist%', 'h2_score',
        'h2_dir', 'h2_cross', 'h2_tier',
        'decision', 'lot_mul', 'skip_reason',
    ]
    n = 0
    n_signal = 0
    n_skip = 0
    tier_counts = {'T3': 0, 'T2': 0, 'T1': 0, 'T0': 0, 'NA': 0}

    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, out_fields)
        w.writeheader()

        prev_m30_cross_state = None  # for cross detection (last completed bar)
        prev_h2_cross_state  = None

        for i in range(len(rows)):
            r = rows[i]
            s5 = m30_sma5[i]; s13 = m30_sma13[i]

            # ---- M30 cross (event-based, on completed bar i-1) ----
            m30_cross = 'NONE'
            if i >= 1 and s5 is not None and s13 is not None \
               and m30_sma5[i-1] is not None and m30_sma13[i-1] is not None:
                ca = s5 > s13; pa = m30_sma5[i-1] > m30_sma13[i-1]
                if not pa and ca: m30_cross = 'GOLDEN'
                elif pa and not ca: m30_cross = 'DEAD'

            # ---- H2 aligned ----
            j = h2_idx[i]
            h2_time  = h2_rows[j]['time'] if j >= 0 else ''
            h2_s5 = h2_sma5[j] if j >= 0 else None
            h2_s13 = h2_sma13[j] if j >= 0 else None

            h2_diff = None; h2_dist = None; h2_score = None
            h2_dir = 'NA'; h2_tier = 'NA'; h2_cross = 'NONE'
            if h2_s5 is not None and h2_s13 is not None:
                h2_diff  = h2_s5 - h2_s13
                h2_dist  = (r['close'] - h2_s5) / h2_s5 * 100.0  # close vs H2 SMA5
                h2_score = h2_diff / h2_s13 * 100.0
                h2_dir   = 'BULL' if h2_s5 > h2_s13 else ('BEAR' if h2_s5 < h2_s13 else 'NEUTRAL')

                # tier (BUY 视角的 tier 分类,用于判定 BUY 仓位乘数)
                if h2_score >= H2_TIER_HI:        h2_tier = 'T3'
                elif h2_score >= H2_TIER_MID_POS: h2_tier = 'T2'
                elif h2_score > H2_TIER_MID_NEG:  h2_tier = 'T1'
                else:                              h2_tier = 'T0'

                # H2 cross (event-based, on completed H2 bar j-1)
                if j >= 1 and h2_sma5[j-1] is not None and h2_sma13[j-1] is not None:
                    ca2 = h2_s5 > h2_s13
                    pa2 = h2_sma5[j-1] > h2_sma13[j-1]
                    if not pa2 and ca2: h2_cross = 'GOLDEN'
                    elif pa2 and not ca2: h2_cross = 'DEAD'

            # ---- Decision (assume BUY视角;SELL 对称可同样计算) ----
            decision = 'SKIP'
            lot_mul  = 0.0
            skip_rsn = ''
            if m30_cross == 'NONE':
                decision = 'SKIP'; skip_rsn = 'no_m30_cross'; lot_mul = 0.0
            elif h2_tier == 'NA':
                decision = 'SKIP'; skip_rsn = 'h2_warmup'; lot_mul = 0.0
            elif h2_tier == 'T0':
                decision = 'SKIP'; skip_rsn = 'h2_counter_trend'; lot_mul = 0.0
            elif m30_cross == 'GOLDEN':
                if h2_tier == 'T3': decision, lot_mul = 'BUY', LOT_MUL_T3
                elif h2_tier == 'T2': decision, lot_mul = 'BUY', LOT_MUL_T2
                elif h2_tier == 'T1': decision, lot_mul = 'BUY', LOT_MUL_T1
            elif m30_cross == 'DEAD':
                # SELL 对称: BUY 视角下 DEAD 是反向信号
                decision = 'SKIP'; skip_rsn = 'm30_dead_buy_view'; lot_mul = 0.0

            tier_counts[h2_tier] = tier_counts.get(h2_tier, 0) + 1
            if decision == 'BUY': n_signal += 1
            else: n_skip += 1

            w.writerow({
                'bar_time':  r['time'],
                'close':     f'{r["close"]:.5f}',
                'm30_sma5':  f'{s5:.5f}'   if s5   is not None else '',
                'm30_sma13': f'{s13:.5f}'  if s13  is not None else '',
                'm30_diff':  f'{s5 - s13:.5f}' if (s5 is not None and s13 is not None) else '',
                'm30_dist%': f'{(s5 - s13) / s13 * 100:.5f}' if (s5 is not None and s13 is not None) else '',
                'm30_cross': m30_cross,
                'h2_time':   h2_time,
                'h2_sma5':   f'{h2_s5:.5f}'  if h2_s5  is not None else '',
                'h2_sma13':  f'{h2_s13:.5f}' if h2_s13 is not None else '',
                'h2_diff':   f'{h2_diff:.5f}' if h2_diff is not None else '',
                'h2_dist%':  f'{h2_dist:.5f}' if h2_dist is not None else '',
                'h2_score':  f'{h2_score:.5f}' if h2_score is not None else '',
                'h2_dir':    h2_dir,
                'h2_cross':  h2_cross,
                'h2_tier':   h2_tier,
                'decision':  decision,
                'lot_mul':   f'{lot_mul:.2f}',
                'skip_reason': skip_rsn,
            })
            n += 1

    print(f'\nDone. Wrote {n} rows to {OUT}')
    print(f'  BUY signals: {n_signal}')
    print(f'  SKIP rows:   {n_skip}')
    print(f'  Tier counts: {tier_counts}')


if __name__ == '__main__':
    main()
