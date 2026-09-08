# -*- coding: utf-8 -*-
"""factors.prev_seg_way - Previous segment way_s_way / vol_way_s_way at price extreme"""
import numpy as np

def prev_seg_way(df, direction_col='方向_合并后'):
    """
    Extract prev_seg way_s_way and vol_way_s_way at PRICE extreme.

    For longs (good crossing):
      - prev_low_way: way_s_way at the lowest LOW of the preceding down segment
      - prev_low_vol_way: vol_way_s_way at that same bar

    For shorts (bad crossing):
      - prev_high_way: way_s_way at the highest HIGH of the preceding up segment
      - prev_high_vol_way: vol_way_s_way at that same bar

    Adds columns: factor_prev_low_way, factor_prev_low_vol_way,
                  factor_prev_high_way, factor_prev_high_vol_way
    """
    d = df[direction_col].values
    n = len(df)
    low = df['low'].values
    high = df['high'].values
    wsw = df['way_s_way'].values if 'way_s_way' in df.columns else np.zeros(n)
    vws = df['vol_way_s_way'].values if 'vol_way_s_way' in df.columns else np.zeros(n)

    prev_low_way = np.full(n, np.nan)
    prev_low_vol = np.full(n, np.nan)
    prev_high_way = np.full(n, np.nan)
    prev_high_vol = np.full(n, np.nan)

    dn_low_price = np.inf
    dn_low_way_val = np.nan
    dn_low_vol_val = np.nan
    up_high_price = -np.inf
    up_high_way_val = np.nan
    up_high_vol_val = np.nan

    for i in range(n):
        if d[i] == 'down':
            if np.isnan(low[i]):
                continue
            if low[i] < dn_low_price:
                dn_low_price = low[i]
                dn_low_way_val = wsw[i] if not np.isnan(wsw[i]) else 0
                dn_low_vol_val = vws[i] if not np.isnan(vws[i]) else 0
        elif d[i] == 'good':
            prev_low_way[i] = dn_low_way_val
            prev_low_vol[i] = dn_low_vol_val
            dn_low_price = np.inf
            dn_low_way_val = np.nan
            dn_low_vol_val = np.nan
        elif d[i] == 'up':
            if np.isnan(high[i]):
                continue
            if high[i] > up_high_price:
                up_high_price = high[i]
                up_high_way_val = wsw[i] if not np.isnan(wsw[i]) else 0
                up_high_vol_val = vws[i] if not np.isnan(vws[i]) else 0
        elif d[i] == 'bad':
            prev_high_way[i] = up_high_way_val
            prev_high_vol[i] = up_high_vol_val
            up_high_price = -np.inf
            up_high_way_val = np.nan
            up_high_vol_val = np.nan

    df['factor_prev_low_way'] = prev_low_way
    df['factor_prev_low_vol_way'] = prev_low_vol
    df['factor_prev_high_way'] = prev_high_way
    df['factor_prev_high_vol_way'] = prev_high_vol
    return df
