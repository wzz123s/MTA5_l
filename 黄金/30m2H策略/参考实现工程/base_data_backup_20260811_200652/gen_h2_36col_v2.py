#!/usr/bin/env python3
"""
H2 数据生成 v2 — 修复版
========================
修复:
  1. 乱码问题 — 改用 ASCII 列名(原 '方向'/'方向_合并后' → 'direction'/'direction_merged')
  2. 数据偏移 — 按 2 小时时间桶重新采样 (而非按 index 每 4 根)
  3. 缺失 SMA55/144/233 — 加 3 列

输出: H2_XAUUSDm_39col.csv  (UTF-8 BOM,无中文字符)
"""
import csv
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent
SRC = BASE_DIR / 'XAUUSDm30.csv'
OUT = BASE_DIR / 'H2_XAUUSDm_39col.csv'

SMA_PERIODS = [5, 13, 55, 144, 233]   # v3.1 SMMA 周期
MIN_SEG_LEN = 8                        # 段合并最小长度
VOL_MA_N = 120                         # 成交量均线周期


def smma(values, period):
    """v3.1 SMMA: SMA(i) = price(i)/N + (N-1)/N × SMA(i-1)
    初值 = 前 N 根算术平均"""
    out = [None] * len(values)
    if len(values) < period:
        return out
    out[period - 1] = sum(values[:period]) / period
    for i in range(period, len(values)):
        out[i] = values[i] / period + (period - 1) / period * out[i - 1]
    return out


def h2_bucket_start(t_str):
    """返回 M30 bar 所属 H2 桶起点时间
    桶对齐到整点 2h 倍数 (00:00, 02:00, 04:00, ..., 22:00)"""
    t = datetime.strptime(t_str, '%Y-%m-%d %H:%M:%S')
    epoch = int(t.timestamp())
    bucket = (epoch // 7200) * 7200
    return datetime.fromtimestamp(bucket)


def resample_m30_to_h2(m30):
    """按 2h 时间桶聚合 M30 → H2
    每个桶起点 = floor(t/2h)*2h
    OHLCV: open=first, high=max, low=min, close=last, vol=sum"""
    buckets = defaultdict(list)
    for bar in m30:
        bs = h2_bucket_start(bar['time'])
        buckets[bs].append(bar)

    h2 = []
    for bs in sorted(buckets.keys()):
        bars = sorted(buckets[bs], key=lambda b: b['time'])
        if not bars:
            continue
        h2.append({
            'time':  bs.strftime('%Y-%m-%d %H:%M:%S'),
            'open':  bars[0]['open'],
            'high':  max(b['high'] for b in bars),
            'low':   min(b['low']  for b in bars),
            'close': bars[-1]['close'],
            'vol':   sum(b['vol']  for b in bars),
            'n_m30': len(bars),       # 子 bar 数 (调试用)
        })
    return h2


def mark_direction(sma5, sma13):
    """段的定义与方向标记.md 第六节"""
    n = len(sma5)
    direction = [''] * n
    prev_above = None
    for i in range(n):
        if sma5[i] is None or sma13[i] is None:
            continue
        curr_above = sma5[i] > sma13[i]
        if prev_above is None:
            direction[i] = 'up' if curr_above else 'down'
        else:
            if not prev_above and curr_above: direction[i] = 'good'
            elif prev_above and not curr_above: direction[i] = 'bad'
            elif curr_above: direction[i] = 'up'
            else: direction[i] = 'down'
        prev_above = curr_above
    return direction


def filter_short_segments(direction, min_len=8):
    """段的定义与方向标记.md 第九节: 短段链式吸收"""
    n = len(direction)
    merged = list(direction)
    for _ in range(50):  # 最多迭代 50 次防死循环
        breaks = [i for i in range(n) if merged[i] in ('good', 'bad')]
        if not breaks:
            break
        segs = []
        for k in range(len(breaks)):
            start = breaks[k]
            end_excl = breaks[k + 1] if k + 1 < len(breaks) else n
            length = end_excl - start - 1
            segs.append((start, end_excl, length))
        short = [length < min_len for (_, _, length) in segs]
        new_reclass = [False] * n
        for k in range(len(segs) - 1):
            if short[k] and k > 0:
                start, _, _ = segs[k]
                new_reclass[start] = True
                if k + 1 < len(breaks):
                    new_reclass[breaks[k + 1]] = True
        any_change = False
        for i in range(n):
            if new_reclass[i]:
                if merged[i] == 'bad':
                    merged[i] = 'up' if i > 0 and merged[i-1] == 'up' else 'down'
                elif merged[i] == 'good':
                    merged[i] = 'down' if i > 0 and merged[i-1] == 'down' else 'up'
                any_change = True
        if not any_change:
            break
    return merged


def compute_way_grade(direction, sma13, low, high, vol, vol_ma):
    """段的定义与方向标记.md 第八节"""
    n = len(direction)
    way = [0]*n; way_s = [0]*n; way_s_way = [0.0]*n
    vol_way = [0]*n; vol_way_s_way = [0.0]*n
    y = x = z = 0
    for i in range(n):
        d = direction[i]
        if d in ('good', 'bad'):
            y = x = z = 0
            wsw = vwsw = 0.0
        elif d == 'up':
            y += 1
            if low[i] >= sma13[i] and (i == 0 or high[i] >= high[i-1]):
                x += 1
            if vol[i] <= vol_ma[i]:
                z += 1
            wsw = round(x/y, 2) if y else 0.0
            vwsw = round(z/y, 2) if y else 0.0
        elif d == 'down':
            y -= 1
            if high[i] <= sma13[i] and (i == 0 or low[i] <= low[i-1]):
                x -= 1
            if vol[i] <= vol_ma[i]:
                z -= 1
            wsw = round(x/y, 2) if y else 0.0
            vwsw = round(z/y, 2) if y else 0.0
        else:
            wsw = vwsw = 0.0
        way[i] = y; way_s[i] = x
        way_s_way[i] = wsw; vol_way[i] = z; vol_way_s_way[i] = vwsw
    return way, way_s, way_s_way, vol_way, vol_way_s_way


def track_extrema(direction, high, low, close, sma13, wsw, vwsw):
    """v3.1 第八/九/十节"""
    n = len(direction)
    up_hp = [None]*n; up_hs = [None]*n; up_hw = [None]*n; up_hvw = [None]*n
    dn_lp = [None]*n; dn_ls = [None]*n; dn_lw = [None]*n; dn_lvw = [None]*n
    ps_hp = [None]*n; ps_hs = [None]*n; ps_hw = [None]*n; ps_hvw = [None]*n
    ps_lp = [None]*n; ps_ls = [None]*n; ps_lw = [None]*n; ps_lvw = [None]*n
    long_entry = [None]*n; long_stop = [None]*n
    short_entry = [None]*n; short_stop = [None]*n

    c_up_hp = c_up_hs = c_up_hw = c_up_hvw = None
    c_dn_lp = c_dn_ls = c_dn_lw = c_dn_lvw = None

    for i in range(n):
        d = direction[i]
        if d == 'good':
            ps_lp[i] = c_dn_lp; ps_ls[i] = c_dn_ls
            ps_lw[i] = c_dn_lw; ps_lvw[i] = c_dn_lvw
            long_entry[i] = (high[i] + low[i] + close[i]) / 3.0
            long_stop[i] = c_dn_ls
            c_dn_lp = c_dn_ls = c_dn_lw = c_dn_lvw = None
            c_up_hp = high[i]; c_up_hs = sma13[i]
            c_up_hw = wsw[i]; c_up_hvw = vwsw[i]
        elif d == 'bad':
            ps_hp[i] = c_up_hp; ps_hs[i] = c_up_hs
            ps_hw[i] = c_up_hw; ps_hvw[i] = c_up_hvw
            short_entry[i] = (high[i] + low[i] + close[i]) / 3.0
            short_stop[i] = c_up_hs
            c_up_hp = c_up_hs = c_up_hw = c_up_hvw = None
            c_dn_lp = low[i]; c_dn_ls = sma13[i]
            c_dn_lw = wsw[i]; c_dn_lvw = vwsw[i]
        elif d == 'up':
            if c_up_hp is None or high[i] > c_up_hp:
                c_up_hp = high[i]
            if c_up_hs is None or sma13[i] > c_up_hs:
                c_up_hs = sma13[i]; c_up_hw = wsw[i]; c_up_hvw = vwsw[i]
            up_hp[i] = c_up_hp; up_hs[i] = c_up_hs
            up_hw[i] = c_up_hw; up_hvw[i] = c_up_hvw
        elif d == 'down':
            if c_dn_lp is None or low[i] < c_dn_lp:
                c_dn_lp = low[i]
            if c_dn_ls is None or sma13[i] < c_dn_ls:
                c_dn_ls = sma13[i]; c_dn_lw = wsw[i]; c_dn_lvw = vwsw[i]
            dn_lp[i] = c_dn_lp; dn_ls[i] = c_dn_ls
            dn_lw[i] = c_dn_lw; dn_lvw[i] = c_dn_lvw

    return {
        'up_high_price': up_hp, 'up_high_sma13': up_hs,
        'up_high_way_s_way': up_hw, 'up_high_vol_way_s_way': up_hvw,
        'down_low_price': dn_lp, 'down_low_sma13': dn_ls,
        'down_low_way_s_way': dn_lw, 'down_low_vol_way_s_way': dn_lvw,
        'prev_seg_high_price': ps_hp, 'prev_seg_high_sma13': ps_hs,
        'prev_seg_high_way_s_way': ps_hw, 'prev_seg_high_vol_way_s_way': ps_hvw,
        'prev_seg_low_price': ps_lp, 'prev_seg_low_sma13': ps_ls,
        'prev_seg_low_way_s_way': ps_lw, 'prev_seg_low_vol_way_s_way': ps_lvw,
        'long_entry': long_entry, 'long_stop': long_stop,
        'short_entry': short_entry, 'short_stop': short_stop,
    }


def fmt(v, nd=5):
    if v is None: return ''
    if isinstance(v, float):
        return f'{v:.2f}' if nd == 2 else f'{v:.5f}'
    return str(v)


def main():
    print(f'Reading {SRC} (GBK)...')
    m30 = []
    with open(SRC, 'r', encoding='gbk') as f:
        reader = csv.reader(f)
        next(reader)
        for r in reader:
            m30.append({
                'time':  r[0],
                'open':  float(r[1]),
                'high':  float(r[2]),
                'low':   float(r[3]),
                'close': float(r[4]),
                'vol':   float(r[5]) if len(r) > 5 else 0.0,
            })
    print(f'  M30 bars: {len(m30)}')

    print('Resampling to H2 (2h time-bucket, NOT index)...')
    h2 = resample_m30_to_h2(m30)
    print(f'  H2 bars:  {len(h2)} (was 24,410 with index grouping)')

    # 调试: 显示前几个不完整桶
    print('\n  First 10 H2 bars (n_m30 = M30 bars aggregated):')
    for i in range(min(10, len(h2))):
        r = h2[i]
        print(f'    H2[{i}] {r["time"]}  n_m30={r["n_m30"]}  O={r["open"]} H={r["high"]} L={r["low"]} C={r["close"]} V={int(r["vol"])}')
    print()

    closes = [r['close'] for r in h2]
    sma = {p: smma(closes, p) for p in SMA_PERIODS}

    vol_ma_120 = []
    window = []
    for r in h2:
        window.append(r['vol'])
        if len(window) > VOL_MA_N:
            window.pop(0)
        vol_ma_120.append(sum(window) / len(window))

    from collections import Counter
    direction_raw = mark_direction(sma[5], sma[13])
    direction_merged = filter_short_segments(direction_raw, min_len=MIN_SEG_LEN)
    print(f'  direction raw:    {Counter(direction_raw)}')
    print(f'  direction merged: {Counter(direction_merged)}')

    way, way_s, way_s_way, vol_way, vol_way_s_way = compute_way_grade(
        direction_merged, sma[13],
        [r['low'] for r in h2], [r['high'] for r in h2],
        [r['vol'] for r in h2], vol_ma_120,
    )

    extr = track_extrema(
        direction_merged,
        [r['high'] for r in h2], [r['low'] for r in h2], [r['close'] for r in h2],
        sma[13], way_s_way, vol_way_s_way,
    )

    # 列定义 — 全 ASCII,无中文
    fields = [
        'date', 'open', 'high', 'low', 'close', 'volume',
        'SMA_5', 'SMA_13', 'SMA_55', 'SMA_144', 'SMA_233',     # 5 个 SMMA
        'direction', 'direction_merged',
        'vol_ma_120', 'way', 'way_s', 'way_s_way', 'vol_way', 'vol_way_s_way',
        'up_high_price', 'up_high_sma13', 'up_high_way_s_way', 'up_high_vol_way_s_way',
        'down_low_price', 'down_low_sma13', 'down_low_way_s_way', 'down_low_vol_way_s_way',
        'prev_seg_high_price', 'prev_seg_high_sma13', 'prev_seg_high_way_s_way', 'prev_seg_high_vol_way_s_way',
        'prev_seg_low_price', 'prev_seg_low_sma13', 'prev_seg_low_way_s_way', 'prev_seg_low_vol_way_s_way',
        'long_entry', 'long_stop', 'short_entry', 'short_stop',
    ]
    print(f'\n  Total columns: {len(fields)}')

    print(f'\nWriting {OUT} (UTF-8 with BOM, ASCII-only headers)...')
    with open(OUT, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(fields)
        for i in range(len(h2)):
            r = h2[i]
            w.writerow([
                r['time'],
                fmt(r['open']), fmt(r['high']), fmt(r['low']),
                fmt(r['close']), f'{r["vol"]:.0f}',
                fmt(sma[5][i]), fmt(sma[13][i]),
                fmt(sma[55][i]), fmt(sma[144][i]), fmt(sma[233][i]),
                direction_raw[i], direction_merged[i],
                f'{vol_ma_120[i]:.5f}',
                int(way[i]), int(way_s[i]),
                f'{way_s_way[i]:.2f}', int(vol_way[i]), f'{vol_way_s_way[i]:.2f}',
                fmt(extr['up_high_price'][i]), fmt(extr['up_high_sma13'][i]),
                fmt(extr['up_high_way_s_way'][i], 2), fmt(extr['up_high_vol_way_s_way'][i], 2),
                fmt(extr['down_low_price'][i]), fmt(extr['down_low_sma13'][i]),
                fmt(extr['down_low_way_s_way'][i], 2), fmt(extr['down_low_vol_way_s_way'][i], 2),
                fmt(extr['prev_seg_high_price'][i]), fmt(extr['prev_seg_high_sma13'][i]),
                fmt(extr['prev_seg_high_way_s_way'][i], 2), fmt(extr['prev_seg_high_vol_way_s_way'][i], 2),
                fmt(extr['prev_seg_low_price'][i]), fmt(extr['prev_seg_low_sma13'][i]),
                fmt(extr['prev_seg_low_way_s_way'][i], 2), fmt(extr['prev_seg_low_vol_way_s_way'][i], 2),
                fmt(extr['long_entry'][i]), fmt(extr['long_stop'][i]),
                fmt(extr['short_entry'][i]), fmt(extr['short_stop'][i]),
            ])

    # 自检
    print('\n--- Self-check ---')
    test = [10, 12, 11, 13, 9, 14, 13, 12, 15, 11]
    ts = smma(test, 5)
    expected = [11.0, 11.6, 11.88, 11.9, 12.52, 12.22]
    ok = all(abs(ts[i+5] - expected[i]) < 0.01 for i in range(5))
    print(f'  v3.1 formula test (N=5): {"PASS" if ok else "FAIL"}')

    # H2 桶验证
    print(f'\n  H2 bar at first M30[0] time (12:00):')
    h2_at_12 = next(r for r in h2 if r['time'] == '2018-01-04 12:00:00')
    print(f'    open={h2_at_12["open"]}  high={h2_at_12["high"]}  low={h2_at_12["low"]}  close={h2_at_12["close"]}  vol={h2_at_12["vol"]}  n_m30={h2_at_12["n_m30"]}')

    # 关键时间点验证
    print(f'\n  H2 bar at 22:00 on 2018-01-04 (should now exist from lone 23:30 M30):')
    h2_at_22 = next((r for r in h2 if r['time'] == '2018-01-04 22:00:00'), None)
    if h2_at_22:
        print(f'    found: open={h2_at_22["open"]} high={h2_at_22["high"]} low={h2_at_22["low"]} close={h2_at_22["close"]} vol={h2_at_22["vol"]} n_m30={h2_at_22["n_m30"]}')
    else:
        print(f'    NOT FOUND - check bucket logic')

    n_long_entry = sum(1 for v in extr['long_entry'] if v is not None)
    n_short_entry = sum(1 for v in extr['short_entry'] if v is not None)
    n_good = sum(1 for d in direction_merged if d == 'good')
    n_bad = sum(1 for d in direction_merged if d == 'bad')
    print(f'\n  good rows={n_good}  long_entry filled={n_long_entry}  match={n_good == n_long_entry}')
    print(f'  bad  rows={n_bad}   short_entry filled={n_short_entry}  match={n_bad == n_short_entry}')

    print(f'\nDone. Wrote {len(h2)} rows x {len(fields)} cols to {OUT}')


if __name__ == '__main__':
    main()
