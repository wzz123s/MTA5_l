# -*- coding: utf-8 -*-
"""
segment_analysis.py —— 难论段分析核心库（MCT 大周期拐点策略 · 阶段0）

实现规范：F:\\use_code\\MTA5\\交易规则\\SMA均线参数配置_v3.1.md + 段的定义与方向标记.md
功能：
  1. calc_sma          SMMA 计算（N=5/13/55/144/233, M=1）
  2. mark_direction    good/up/bad/down 状态机（向量化）
  3. filter_short_segments_v2  v4 严格链式吸收 + 末段保持原始行情
  4. way_grade         段内强度（way/way_s/vol_way）
  5. track_extremes    段内极值追踪（价格极值 + SMA13 极值）
  6. mark_crossings    穿越点前段极值标记 + 开仓/止损价
  7. analyze           一站式入口

列名约定（与 MTA5 一致）：
  输入: open/high/low/close/tick_volume（或 vol）
  输出: SMA_5/SMA_13/SMA_55/方向/方向_合并后/vol_ma_120/
        way/way_s/way_s_way/vol_way/vol_way_s_way/
        up_high_price/up_high_sma13/down_low_price/down_low_sma13/
        prev_seg_low_price/prev_seg_low_sma13/prev_seg_high_price/prev_seg_high_sma13/
        long_entry/long_stop/short_entry/short_stop
"""
from __future__ import annotations

import numpy as np
import pandas as pd

pd.set_option("future.no_silent_downcasting", True)


# ============================================================
# 1. SMMA 计算（SMA 加权移动平均, N 为周期, M=1）
# ============================================================
def calc_sma(series, n, m=1):
    """加权移动平均 SMA(X, N, M)；前 n-1 行返回 NaN。"""
    s = series.astype(float)
    out = pd.Series(np.nan, index=series.index)
    if len(s) < n:
        return out
    vals = s.values
    sma = np.full(len(vals), np.nan)
    sma[n - 1] = vals[:n].mean()
    for i in range(n, len(vals)):
        sma[i] = (m * vals[i] + (n - m) * sma[i - 1]) / n
    out.iloc[:] = sma
    return out


# ============================================================
# 2. 方向标记（good/up/bad/down）
# ============================================================
def mark_direction(df):
    """
    5SMA 与 13SMA 的位置关系状态机：
      good = 上穿瞬间（5 从下方穿越到 13 上方）
      bad  = 下穿瞬间（5 从上方穿越到 13 下方）
      up   = 5 持续在 13 上方；down = 5 持续在 13 下方
    首行单独纠正（不可能为穿越点）。
    """
    _df = df.dropna(subset=['SMA_13']).copy()
    sma5_gt_sma13 = _df['SMA_5'] > _df['SMA_13']
    sma5_gt_sma13_prev = sma5_gt_sma13.shift(1).fillna(False).astype(bool)

    conditions = [
        sma5_gt_sma13 & ~sma5_gt_sma13_prev,   # good
        ~sma5_gt_sma13 & sma5_gt_sma13_prev,   # bad
        sma5_gt_sma13 & sma5_gt_sma13_prev,    # up
        ~sma5_gt_sma13 & ~sma5_gt_sma13_prev,  # down
    ]
    _df['方向'] = np.select(conditions, ['good', 'bad', 'up', 'down'], default=None)
    _df.loc[_df.index[0], '方向'] = 'up' if sma5_gt_sma13.iloc[0] else 'down'
    return _df


# ============================================================
# 3. 短段过滤 v4（严格链式吸收 + 末段保持原始行情）
# ============================================================
def filter_short_segments_v2(df, min_len=8):
    """
    v4 段合并：good 后 up < min_len → good+up+next_bad 一起吸收（趋势延续）；
    bad 后 down < min_len → bad+down+next_good 一起吸收。
    强制链式：每次吸收连带移除下一个穿越点；末段穿越点永远保留。
    返回 (df, is_real_good, is_real_bad, seg_len, seg_starts, seg_ends,
          has_first, has_last, n_seg, good_pos_all, bad_pos_all)
    """
    _df = df.copy()
    direction = _df['方向'].values.astype(object)
    n = len(_df)
    good_pos_all = np.where(direction == 'good')[0]
    bad_pos_all = np.where(direction == 'bad')[0]

    all_crossings = sorted(
        [(int(p), 'good') for p in good_pos_all] +
        [(int(p), 'bad') for p in bad_pos_all],
        key=lambda x: x[0],
    )

    if len(all_crossings) == 0:
        _df['方向_合并后'] = direction
        return (_df, np.array([], dtype=bool), np.array([], dtype=bool),
                np.array([n], dtype=int), np.array([0]), np.array([n - 1]),
                True, True, 1, good_pos_all, bad_pos_all)

    first_pos, first_type = all_crossings[0]
    state = 'down' if first_type == 'good' else 'up'
    surviving_good = []
    surviving_bad = []

    i = 0
    while i < len(all_crossings):
        pos, type_ = all_crossings[i]

        # 末段：无下一个穿越点 → 永远保留为 real crossing
        if i + 1 >= len(all_crossings):
            if type_ == 'good':
                surviving_good.append(pos)
            else:
                surviving_bad.append(pos)
            break

        next_pos, next_type = all_crossings[i + 1]
        region = (direction[pos + 1:next_pos]
                  if pos + 1 < next_pos else np.array([], dtype=object))
        if type_ == 'good':
            region_count = int(np.sum(region == 'up'))
        else:
            region_count = int(np.sum(region == 'down'))

        if region_count < min_len:
            # 严格链式吸收：current + region + next 全部改为 state
            direction[pos] = state
            for k in range(pos + 1, next_pos):
                direction[k] = state
            direction[next_pos] = state
            all_crossings.pop(i + 1)
            all_crossings.pop(i)
        else:
            if type_ == 'good':
                surviving_good.append(pos)
                state = 'up'
            else:
                surviving_bad.append(pos)
                state = 'down'
            i += 1

    _df['方向_合并后'] = direction
    surviving_good_set = set(surviving_good)
    surviving_bad_set = set(surviving_bad)
    is_real_good = np.array([(int(p) in surviving_good_set) for p in good_pos_all], dtype=bool)
    is_real_bad = np.array([(int(p) in surviving_bad_set) for p in bad_pos_all], dtype=bool)

    # 段边界重建
    new_good = good_pos_all[is_real_good]
    new_bad = bad_pos_all[is_real_bad]
    n_ng, n_nb = len(new_good), len(new_bad)
    if n_ng == 0 and n_nb == 0:
        n_seg = 1
        seg_starts = np.array([0])
        seg_ends = np.array([n - 1])
        has_first = has_last = True
    else:
        if n_ng == 0:
            first_is_bad = True
        elif n_nb == 0:
            first_is_bad = False
        else:
            first_is_bad = int(new_bad[0]) < int(new_good[0])
        n_seg = n_ng + n_nb + 1
        if n_ng > n_nb:
            last_is_bad = False
        elif n_nb > n_ng:
            last_is_bad = True
        else:
            last_is_bad = not first_is_bad
        has_first, has_last = first_is_bad, last_is_bad

        all_cross_sorted = sorted(
            [(int(p), 'good') for p in new_good] +
            [(int(p), 'bad') for p in new_bad],
            key=lambda x: x[0],
        )
        seg_starts = np.zeros(n_seg, dtype=int)
        seg_ends = np.zeros(n_seg, dtype=int)
        for k in range(n_seg):
            if k == 0:
                seg_starts[k] = 0
                seg_ends[k] = all_cross_sorted[0][0]
            elif k == n_seg - 1:
                seg_starts[k] = all_cross_sorted[-1][0]
                seg_ends[k] = n - 1
            else:
                seg_starts[k] = all_cross_sorted[k - 1][0]
                seg_ends[k] = all_cross_sorted[k][0]

    seg_len_out = np.array([
        int(np.sum((direction[s:e + 1] == 'up') | (direction[s:e + 1] == 'down')))
        for s, e in zip(seg_starts, seg_ends)
    ])
    return (_df, is_real_good, is_real_bad, seg_len_out,
            seg_starts, seg_ends, has_first, has_last, n_seg,
            good_pos_all, bad_pos_all)


# ============================================================
# 4. way_grade 段内强度
# ============================================================
def way_grade(data):
    """
    段内强度指标：
      way        段持续 K 线数（good/bad 归零，up+1，down-1）
      way_s      强势信号计数（up: 低≥13SMA且高≥前高；down: 高≤13SMA且低≤前低）
      way_s_way  way_s/way 比值
      vol_way    缩量信号计数（vol ≤ 120 均量）
      vol_way_s_way vol_way/way 比值
    需要列：方向、最低价、最高价、SMA_13、vol、成交量均线
    """
    direction = data['方向'].values
    sma13 = data['SMA_13'].values
    low = data['最低价'].values
    high = data['最高价'].values
    vol = data['vol'].values
    vol_ma = data['成交量均线'].values
    n = len(data)

    y = x = z = 0
    way_vals = np.zeros(n)
    way_s_vals = np.zeros(n)
    way_s_way_vals = np.zeros(n)
    vol_way_vals = np.zeros(n)
    vol_way_s_way_vals = np.zeros(n)

    for i in range(n):
        dir_i = direction[i]
        if dir_i in ('good', 'bad'):
            y = x = z = 0
            way_s_way = 0.0
            vol_way_s_way = 0.0
        elif dir_i == 'up':
            y += 1
            if low[i] >= sma13[i] and (i == 0 or high[i] >= high[i - 1]):
                x += 1
            if vol[i] <= vol_ma[i]:
                z += 1
            way_s_way = round(x / y, 2) if y != 0 else 0.0
            vol_way_s_way = round(z / y, 2) if y != 0 else 0.0
        elif dir_i == 'down':
            y -= 1
            if high[i] <= sma13[i] and (i == 0 or low[i] <= low[i - 1]):
                x -= 1
            if vol[i] <= vol_ma[i]:
                z -= 1
            way_s_way = round(x / y, 2) if y != 0 else 0.0
            vol_way_s_way = round(z / y, 2) if y != 0 else 0.0
        else:
            way_s_way = 0.0
            vol_way_s_way = 0.0

        way_vals[i] = y
        way_s_vals[i] = x
        way_s_way_vals[i] = way_s_way
        vol_way_vals[i] = z
        vol_way_s_way_vals[i] = vol_way_s_way

    data['way'] = way_vals
    data['way_s'] = way_s_vals
    data['way_s_way'] = way_s_way_vals
    data['vol_way'] = vol_way_vals
    data['vol_way_s_way'] = vol_way_s_way_vals
    return data


# ============================================================
# 5. 段内极值追踪（v3.1 第八节）
# ============================================================
def track_extremes(df):
    """
    段内极值追踪（基于 方向_合并后）：
      up 段:   up_high_price（段内最高价）、up_high_sma13（最高价K线对应的 SMA_13）
      down 段: down_low_price（段内最低价）、down_low_sma13（最低价K线对应的 SMA_13）
    SMA13 极值独立追踪（慢速均线极值通常晚于价格极值）。
    """
    direction = df['方向_合并后'].values
    high = df['high'].values
    low = df['low'].values
    sma13 = df['SMA_13'].values
    n = len(df)

    up_hp = up_hs = np.nan
    dn_lp = dn_ls = np.nan
    up_high_price = np.full(n, np.nan)
    up_high_sma13 = np.full(n, np.nan)
    down_low_price = np.full(n, np.nan)
    down_low_sma13 = np.full(n, np.nan)

    for i in range(n):
        d = direction[i]
        if d == 'up':
            if not np.isnan(up_hp):
                if high[i] > up_hp:
                    up_hp = high[i]
                if sma13[i] > up_hs:
                    up_hs = sma13[i]
            else:
                up_hp, up_hs = high[i], sma13[i]
            up_high_price[i] = up_hp
            up_high_sma13[i] = up_hs
        elif d == 'down':
            if not np.isnan(dn_lp):
                if low[i] < dn_lp:
                    dn_lp = low[i]
                if sma13[i] < dn_ls:
                    dn_ls = sma13[i]
            else:
                dn_lp, dn_ls = low[i], sma13[i]
            down_low_price[i] = dn_lp
            down_low_sma13[i] = dn_ls
        else:
            # good/bad 穿越点：重置极值（下一段重新累计）
            up_hp = up_hs = np.nan
            dn_lp = dn_ls = np.nan

    df['up_high_price'] = up_high_price
    df['up_high_sma13'] = up_high_sma13
    df['down_low_price'] = down_low_price
    df['down_low_sma13'] = down_low_sma13
    return df


# ============================================================
# 6. 穿越点前段极值标记 + 开仓/止损价（v3.1 第九、十节）
# ============================================================
def mark_crossings(df):
    """
    good 行：标记上一 down 段的最低价 K 线四元组 → 做多开仓+止损
    bad 行： 标记上一 up 段的最高价 K 线四元组 → 做空开仓+止损
    开仓价 = (H+L+C)/3；止损 = 前段 SMA13 极值（prev_seg_low_sma13 / prev_seg_high_sma13）
    """
    direction = df['方向_合并后'].values
    n = len(df)
    low_vals = df['low'].values
    high_vals = df['high'].values
    sma13_vals = df['SMA_13'].values

    prev_seg_low_price = np.full(n, np.nan)
    prev_seg_low_sma13 = np.full(n, np.nan)
    prev_seg_high_price = np.full(n, np.nan)
    prev_seg_high_sma13 = np.full(n, np.nan)

    cur_down_low_price = cur_down_low_sma13 = np.nan
    cur_up_high_price = cur_up_high_sma13 = np.nan

    for i in range(n):
        d = direction[i]
        if d == 'down':
            # 价格极值与 SMA13 极值独立追踪（v3.1：SMA13 自身最低值）
            if np.isnan(cur_down_low_price) or low_vals[i] < cur_down_low_price:
                cur_down_low_price = low_vals[i]
            if np.isnan(cur_down_low_sma13) or sma13_vals[i] < cur_down_low_sma13:
                cur_down_low_sma13 = sma13_vals[i]
        elif d == 'up':
            if np.isnan(cur_up_high_price) or high_vals[i] > cur_up_high_price:
                cur_up_high_price = high_vals[i]
            if np.isnan(cur_up_high_sma13) or sma13_vals[i] > cur_up_high_sma13:
                cur_up_high_sma13 = sma13_vals[i]
        elif d == 'good':
            prev_seg_low_price[i] = cur_down_low_price
            prev_seg_low_sma13[i] = cur_down_low_sma13
            cur_up_high_price = cur_up_high_sma13 = np.nan
        elif d == 'bad':
            prev_seg_high_price[i] = cur_up_high_price
            prev_seg_high_sma13[i] = cur_up_high_sma13
            cur_down_low_price = cur_down_low_sma13 = np.nan

    df['prev_seg_low_price'] = prev_seg_low_price
    df['prev_seg_low_sma13'] = prev_seg_low_sma13
    df['prev_seg_high_price'] = prev_seg_high_price
    df['prev_seg_high_sma13'] = prev_seg_high_sma13

    hl2 = (df['high'] + df['low'] + df['close']) / 3.0
    df['long_entry'] = np.where(direction == 'good', hl2, np.nan)
    df['long_stop'] = np.where(direction == 'good', prev_seg_low_sma13, np.nan)
    df['short_entry'] = np.where(direction == 'bad', hl2, np.nan)
    df['short_stop'] = np.where(direction == 'bad', prev_seg_high_sma13, np.nan)
    return df


# ============================================================
# 7. 一站式入口
# ============================================================
def analyze(df, min_len=8, calc_55=True, calc_144=False, calc_233=False):
    """
    完整段分析流水线：
      raw OHLCV(+tick_volume) → SMA → 方向 → v4 合并 → way_grade → 极值 → 穿越标记
    输入必需列：open/high/low/close（vol 可来自 tick_volume 或 vol）
    """
    out = df.copy()
    if 'vol' not in out.columns:
        out['vol'] = out.get('tick_volume', 0)
    out['vol'] = out['vol'].fillna(0).astype(float)

    out['SMA_5'] = calc_sma(out['close'], 5)
    out['SMA_13'] = calc_sma(out['close'], 13)
    if calc_55:
        out['SMA_55'] = calc_sma(out['close'], 55)
    if calc_144:
        out['SMA_144'] = calc_sma(out['close'], 144)
    if calc_233:
        out['SMA_233'] = calc_sma(out['close'], 233)

    out['最低价'] = out['low']
    out['最高价'] = out['high']
    out['成交量均线'] = out['vol'].rolling(120, min_periods=1).mean()

    out = mark_direction(out)

    (out, is_real_good, is_real_bad, seg_len,
     seg_starts, seg_ends, has_first, has_last, n_seg,
     good_pos, bad_pos) = filter_short_segments_v2(out, min_len=min_len)

    out = way_grade(out)
    out = track_extremes(out)
    out = mark_crossings(out)

    out.attrs['n_seg'] = n_seg
    out.attrs['seg_len'] = seg_len
    out.attrs['seg_starts'] = seg_starts
    out.attrs['seg_ends'] = seg_ends
    out.attrs['is_real_good'] = is_real_good
    out.attrs['is_real_bad'] = is_real_bad
    return out


if __name__ == '__main__':
    print("segment_analysis.py 自检…")
    df_test = pd.DataFrame({
        'open': [11, 12, 11, 10, 11, 12],
        'high': [13, 14, 12, 11, 13, 14],
        'low': [10, 11, 9, 9, 10, 11],
        'close': [12, 13, 10, 9, 12, 13],
        'tick_volume': [100, 100, 100, 100, 100, 100],
    })
    df_test['SMA_5'] = [12, 13, 10, 9, 12, 13]
    df_test['SMA_13'] = [11, 11, 11, 11, 11, 11]
    r = mark_direction(df_test)
    expect = ['up', 'up', 'bad', 'down', 'good', 'up']
    got = r['方向'].tolist()
    assert got == expect, f"mark_direction 验证失败: {got} != {expect}"
    print("mark_direction 验证用例通过:", got)
    print("全部自检通过 OK")
