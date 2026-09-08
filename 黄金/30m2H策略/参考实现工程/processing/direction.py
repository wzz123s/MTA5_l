# -*- coding: utf-8 -*-
"""processing.direction - Direction marking based on SMA5/SMA13 crossover"""

import numpy as np
import pandas as pd

def mark_direction(df):
    """
    根据 5SMA 与 13SMA 的位置关系标记方向
    返回: good(上穿) / up(持续在上) / bad(下穿) / down(持续在下)
    首行: 只可能是 up 或 down(不是穿越点)
    """
    _df = df.dropna(subset=['SMA_13']).copy()
    sma5_gt_sma13 = _df['SMA_5'] > _df['SMA_13']
    sma5_gt_sma13_prev = sma5_gt_sma13.shift(1).fillna(False)

    conditions = [
        sma5_gt_sma13 & ~sma5_gt_sma13_prev,          # good: 从下穿越到上
        ~sma5_gt_sma13 & sma5_gt_sma13_prev,          # bad:  从上穿越到下
        sma5_gt_sma13 & sma5_gt_sma13_prev,           # up:   持续在上
        ~sma5_gt_sma13 & ~sma5_gt_sma13_prev          # down: 持续在下
    ]
    _df['方向'] = np.select(conditions, ['good', 'bad', 'up', 'down'], default=None)
    _df.iloc[0, _df.columns.get_loc('方向')] = 'up' if sma5_gt_sma13.iloc[0] else 'down'
    return _df


def add_pre_cross_and_counter(df, fixed_thr=0.0005, atr_k=None,
                               direction_col='方向', prefix=''):
    """
    v4.0 三层分级策略 Layer 2 状态机扩展。

    在 mark_direction 输出的 df 上追加两列:
      - <prefix>pre_cross:  bool, True 表示当前 K 线处于 pre_cross 状态
        (价已穿越 SMA13 + SMA5 还在原侧 + |SMA5-SMA13|/SMA13 < 阈值)
      - <prefix>post_cross_n: int, 穿越后第 N 根 K 线
        (good 后 up 段 → +1, +2, +3...; bad 后 down 段 → -1, -2, -3...)

    参数
    ----
    df : pd.DataFrame
        必须包含列: SMA_5, SMA_13, high, low, close (ATR 计算需要),
        以及 direction_col (默认 '方向' 或 '方向_合并后')
    fixed_thr : float
        方案1: 固定阈值 (默认 0.0005 = 0.05%)
    atr_k : float 或 None
        方案2: ATR(14) × k 动态阈值;若 None 则只用 fixed_thr (二者取并集)
    direction_col : str
        基于哪一列方向 ('方向' 原始 / '方向_合并后' 段合并后)
    prefix : str
        列名前缀 (用于区分两次调用,如 '' vs 'merged_')

    返回
    ----
    df 副本,新增两列 <prefix>pre_cross 和 <prefix>post_cross_n
    """
    df = df.copy()
    n = len(df)

    sma5 = df['SMA_5'].values
    sma13 = df['SMA_13'].values
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    direction = df[direction_col].values

    pre_col = f'{prefix}pre_cross'
    post_col = f'{prefix}post_cross_n'

    # === 1) pre_cross 计算 ===
    # 价 vs SMA13 距离
    price_ratio = np.full(n, np.nan)
    valid = ~np.isnan(sma13) & (sma13 != 0)
    price_ratio[valid] = np.abs(close[valid] - sma13[valid]) / sma13[valid]

    # SMA5 vs SMA13 距离
    sma_ratio = np.full(n, np.nan)
    valid5 = ~np.isnan(sma5) & ~np.isnan(sma13) & (sma13 != 0)
    sma_ratio[valid5] = np.abs(sma5[valid5] - sma13[valid5]) / sma13[valid5]

    # 条件 A: 价在 SMA13 一侧 (穿越)
    # long setup: close > SMA13 (价在 SMA13 上方)
    # short setup: close < SMA13 (价在 SMA13 下方)
    cond_price_long = close > sma13
    cond_price_short = close < sma13

    # 条件 B: SMA5 在 SMA13 另一侧 (还没追上)
    cond_sma_long = sma5 < sma13   # SMA5 在 SMA13 下方 (long 还没金叉)
    cond_sma_short = sma5 > sma13  # SMA5 在 SMA13 上方 (short 还没死叉)

    # 条件 C: SMA5/SMA13 距离接近阈值
    cond_thr_fixed = sma_ratio < fixed_thr
    cond_thr_atr = np.zeros(n, dtype=bool)
    if atr_k is not None:
        # ATR(14)
        prev_close = np.roll(close, 1)
        prev_close[0] = close[0]
        tr = np.maximum(high - low,
                np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))
        atr14 = _rolling_mean(tr, 14)
        # ATR(14) × k / SMA13 作为比率阈值
        atr_thr_ratio = np.where(valid, atr_k * atr14 / sma13, np.inf)
        cond_thr_atr = sma_ratio < atr_thr_ratio

    cond_thr = cond_thr_fixed | cond_thr_atr

    # 排除 SMA13 未 warmup 的行
    warmup_ok = ~np.isnan(sma13) & ~np.isnan(sma5)

    # 排除穿越点本身 (good/bad 那根不算 pre_cross)
    not_cross = ~np.isin(direction, ['good', 'bad'])

    pre_cross = (
        warmup_ok & not_cross & cond_thr &
        ((cond_price_long & cond_sma_long) | (cond_price_short & cond_sma_short))
    )
    df[pre_col] = pre_cross

    # === 2) post_cross_n 计算 ===
    # 基于 direction_col (通常是 '方向_合并后')
    post_n = np.zeros(n, dtype=int)
    counter = 0
    last_cross = None  # 'good' / 'bad' / None

    for i in range(n):
        d = direction[i]
        if d == 'good':
            counter = 1
            last_cross = 'good'
            post_n[i] = counter
        elif d == 'bad':
            counter = -1
            last_cross = 'bad'
            post_n[i] = counter
        elif d == 'up' and last_cross == 'good':
            counter += 1
            post_n[i] = counter
        elif d == 'down' and last_cross == 'bad':
            counter -= 1
            post_n[i] = counter
        else:
            # up 但 last_cross 是 bad (段翻转),或 down 但 last_cross 是 good
            # 或首行(无前导穿越) → post_n = 0
            counter = 0
            last_cross = None
            post_n[i] = 0

    df[post_col] = post_n
    return df


def _rolling_mean(arr, w):
    """简单滚动均值(局部实现,避免与 factors.base 循环引用)"""
    r = np.full(len(arr), np.nan)
    cs = np.cumsum(np.nan_to_num(arr, 0.0))
    for i in range(w - 1, len(arr)):
        s = cs[i] - (cs[i - w] if i >= w else 0.0)
        r[i] = s / w
    return r
