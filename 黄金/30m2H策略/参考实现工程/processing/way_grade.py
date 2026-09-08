# -*- coding: utf-8 -*-
"""processing.way_grade - Segment strength evaluation"""
import numpy as np

def way_grade(df):
    """
    v4 段内信号强度评估 (与 v3 兼容)。
    输入 df 需含列: 方向, 方向_合并后, low, high, SMA_13, volume, vol_ma_120
    新增列: way, way_s, way_s_way, vol_way, vol_way_s_way

    关键规则 (v4 严格链式版):
    1. 段开始 (穿越点之后第一根 up/down):
       - 用 **方向_合并后** 判定 (而非 方向)
       - good 后第一根 up → y=1, x=1, z=1 if vol<=vol_ma else 0
       - bad 后第一根 down → y=-1, x=-1, z=-1 if vol<=vol_ma else 0
       — 用户反馈: "第一个 up 的 way_s 应该是 1, 不应该是 0"
    2. 段内 up/down: y += 1, 按规则累加 x, z
    3. 穿越点 (good/bad) 本身: y/x/z 重置, way_s_way=0

    v4 严格链式语义:
      v4 链式吸收后, good+up+next_bad 全部改成 state, 因此 方向_合并后 列里
      幸存 good 之后必然紧跟 up 段, 幸存 bad 之后必然紧跟 down 段.
      段开始判定不能再用 prev_raw == 'good' (位置错位), 必须用 prev_d (方向_合并后).
    """
    # 关键: 段开始判定基于 方向_合并后
    direction = df['方向_合并后'].values if '方向_合并后' in df.columns else df['方向'].values
    sma13 = df['SMA_13'].values
    low = df['low'].values
    high = df['high'].values
    vol = df['volume'].values
    vol_ma = df['vol_ma_120'].values
    n = len(df)

    way_vals = np.zeros(n)
    way_s_vals = np.zeros(n)
    way_s_way_vals = np.zeros(n)
    vol_way_vals = np.zeros(n)
    vol_way_s_way_vals = np.zeros(n)

    y = x = z = 0
    prev_d = None  # 上一根的方向_合并后 (up/down/good/bad)
    for i in range(n):
        d = direction[i]

        if d in ('good', 'bad'):
            # 穿越点: y/x/z 重置, way_s_way=0
            y = x = z = 0
            way_s_way = 0.0
            vol_way_s_way = 0.0

        elif d == 'up':
            # 段内 up:
            #   - 上一根是 good → 段第一根, 强制 x=1
            #   - 上一根是 down/bad → 状态翻转到 up, 新段开始
            #   - 上一根是 up → 段内延续
            if prev_d == 'good':
                # 段第一根 up: y=0→1, x 强制初始化为 1
                y = 1
                x = 1
                z = 1 if vol[i] <= vol_ma[i] else 0
            elif prev_d == 'up':
                # 段内延续
                y += 1
                if low[i] >= sma13[i] and high[i] >= high[i - 1]:
                    x += 1
                if vol[i] <= vol_ma[i]:
                    z += 1
            else:
                # 上一根是 down/bad/None → 翻转到 up = 新段开始
                # v4 严格链式后, 这种"down→up 翻转"等价于 v3 的 "good→up" 段开始
                y = 1
                x = 1  # 强制初始化为 1 (用户要求: 第一个 up 的 way_s 应该是 1)
                z = 1 if vol[i] <= vol_ma[i] else 0
            way_s_way = round(x / y, 2) if y != 0 else 0.0
            vol_way_s_way = round(z / y, 2) if y != 0 else 0.0

        elif d == 'down':
            if prev_d == 'bad':
                # 段第一根 down: y=0→-1, x 强制初始化为 -1
                y = -1
                x = -1
                z = -1 if vol[i] <= vol_ma[i] else 0
            elif prev_d == 'down':
                # 段内延续
                y -= 1
                if high[i] <= sma13[i] and low[i] <= low[i - 1]:
                    x -= 1
                if vol[i] <= vol_ma[i]:
                    z -= 1
            else:
                # 上一根是 up/good/None → 翻转到 down = 新段开始
                y = -1
                x = -1  # 强制初始化为 -1
                z = -1 if vol[i] <= vol_ma[i] else 0
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

        prev_d = d

    df['way'] = way_vals
    df['way_s'] = way_s_vals
    df['way_s_way'] = way_s_way_vals
    df['vol_way'] = vol_way_vals
    df['vol_way_s_way'] = vol_way_s_way_vals
    return df

