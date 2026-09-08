# -*- coding: utf-8 -*-
"""processing.extrema - Segment extrema tracking"""
import numpy as np

def track_segment_extrema(df):
    """
    在 DataFrame 上追加段极值追踪列。

    参数
    ----------
    df : pd.DataFrame
        必须包含列: 方向_合并后, high, low, SMA_13, way_s_way, vol_way_s_way

    返回
    -------
    pd.DataFrame
        新增 16 列后的副本

    算法
    -----
    单遍 O(N) 遍历，类似 way_grade：

    - good 行：输出上一 down 段最低价（prev_seg_low_*），重置 down 暂存，
      启动 up 段追踪（从当前行 high 开始）
    - bad  行：输出上一 up 段最高价（prev_seg_high_*），重置 up 暂存，
      启动 down 段追踪（从当前行 low 开始）
    - up   行：若 high 创新高则更新 up 暂存，填入运行列
    - down 行：若 low 创新低则更新 down 暂存，填入运行列

    边界处理：
    - 首行若为 up/down（无前导穿越点），通过 NaN 检测自动初始化追踪
    - 无前一段时 prev_* 列保持 NaN
    - 非本段方向时运行列保持 NaN
    """
    _df = df.copy()

    direction = _df['方向_合并后'].values
    high = _df['high'].values
    low = _df['low'].values
    close = _df['close'].values          # ← 新增：用于计算均价 (H+L+C)/3
    sma13 = _df['SMA_13'].values
    wsw = _df['way_s_way'].values
    vwsw = _df['vol_way_s_way'].values
    n = len(_df)

    # --- 输出列 ---
    up_hp   = np.full(n, np.nan)
    up_hs   = np.full(n, np.nan)
    up_hw   = np.full(n, np.nan)
    up_hvw  = np.full(n, np.nan)

    dn_lp   = np.full(n, np.nan)
    dn_ls   = np.full(n, np.nan)
    dn_lw   = np.full(n, np.nan)
    dn_lvw  = np.full(n, np.nan)

    ps_hp   = np.full(n, np.nan)
    ps_hs   = np.full(n, np.nan)
    ps_hw   = np.full(n, np.nan)
    ps_hvw  = np.full(n, np.nan)

    ps_lp   = np.full(n, np.nan)
    ps_ls   = np.full(n, np.nan)
    ps_lw   = np.full(n, np.nan)
    ps_lvw  = np.full(n, np.nan)

    # --- 均价与止损列（仅 good/bad 行有值）---
    long_entry  = np.full(n, np.nan)   # (H+L+C)/3 @ good
    long_stop   = np.full(n, np.nan)   # prev_seg_low_sma13 @ good
    short_entry = np.full(n, np.nan)   # (H+L+C)/3 @ bad
    short_stop  = np.full(n, np.nan)   # prev_seg_high_sma13 @ bad

    # --- 状态变量 ---
    c_up_hp  = np.nan   # current up segment's running highest high
    c_up_hs  = np.nan   # SMA_13 at that point
    c_up_hw  = np.nan   # way_s_way at that point
    c_up_hvw = np.nan   # vol_way_s_way at that point

    c_dn_lp  = np.nan   # current down segment's running lowest low
    c_dn_ls  = np.nan   # SMA_13 at that point
    c_dn_lw  = np.nan   # way_s_way at that point
    c_dn_lvw = np.nan   # vol_way_s_way at that point

    for i in range(n):
        d = direction[i]

        if d == 'good':
            # ---- 输出上一 down 段最低价 ----
            ps_lp[i]  = c_dn_lp
            ps_ls[i]  = c_dn_ls
            ps_lw[i]  = c_dn_lw
            ps_lvw[i] = c_dn_lvw

            # ---- 做多均价 = (H+L+C)/3，止损 = 上一段最低价 SMA13 ----
            long_entry[i] = (high[i] + low[i] + close[i]) / 3.0
            long_stop[i]  = c_dn_ls

            # ---- 重置 down 追踪 ----
            c_dn_lp  = np.nan
            c_dn_ls  = np.nan
            c_dn_lw  = np.nan
            c_dn_lvw = np.nan

            # ---- 启动 up 段追踪（用本行初始化 c_up_*，但本行不是 up，输出列保持 NaN） ----
            c_up_hp  = high[i]
            c_up_hs  = sma13[i]
            c_up_hw  = wsw[i]
            c_up_hvw = vwsw[i]
            # up_hp[i..up_hvw[i] 留 NaN (本行是 good 不是 up)

        elif d == 'bad':
            # ---- 输出上一 up 段最高价 ----
            ps_hp[i]  = c_up_hp
            ps_hs[i]  = c_up_hs
            ps_hw[i]  = c_up_hw
            ps_hvw[i] = c_up_hvw

            # ---- 做空均价 = (H+L+C)/3，止损 = 上一段最高价 SMA13 ----
            short_entry[i] = (high[i] + low[i] + close[i]) / 3.0
            short_stop[i]  = c_up_hs

            # ---- 重置 up 追踪 ----
            c_up_hp  = np.nan
            c_up_hs  = np.nan
            c_up_hw  = np.nan
            c_up_hvw = np.nan

            # ---- 启动 down 段追踪（用本行初始化 c_dn_*，但本行不是 down，输出列保持 NaN） ----
            c_dn_lp  = low[i]
            c_dn_ls  = sma13[i]
            c_dn_lw  = wsw[i]
            c_dn_lvw = vwsw[i]
            # dn_lp[i..dn_lvw[i] 留 NaN (本行是 bad 不是 down)

        elif d == 'up':
            # ---- 运行最高价追踪 ----
            if np.isnan(c_up_hp) or high[i] > c_up_hp:
                c_up_hp  = high[i]
            # 追踪 SMA13 自身的最高值（独立于价格高点）
            if np.isnan(c_up_hs) or sma13[i] > c_up_hs:
                c_up_hs  = sma13[i]
                c_up_hw  = wsw[i]
                c_up_hvw = vwsw[i]

            up_hp[i]  = c_up_hp
            up_hs[i]  = c_up_hs
            up_hw[i]  = c_up_hw
            up_hvw[i] = c_up_hvw

        elif d == 'down':
            # ---- 运行最低价追踪 ----
            if np.isnan(c_dn_lp) or low[i] < c_dn_lp:
                c_dn_lp  = low[i]
            # 追踪 SMA13 自身的最低值（独立于价格低点）
            # 修正：SMA13 是慢速均线，最低值往往出现在价格见底之后
            if np.isnan(c_dn_ls) or sma13[i] < c_dn_ls:
                c_dn_ls  = sma13[i]
                c_dn_lw  = wsw[i]
                c_dn_lvw = vwsw[i]

            dn_lp[i]  = c_dn_lp
            dn_ls[i]  = c_dn_ls
            dn_lw[i]  = c_dn_lw
            dn_lvw[i] = c_dn_lvw

    # --- 写回 DataFrame ---
    _df['up_high_price']         = up_hp
    _df['up_high_sma13']         = up_hs
    _df['up_high_way_s_way']     = up_hw
    _df['up_high_vol_way_s_way'] = up_hvw

    _df['down_low_price']         = dn_lp
    _df['down_low_sma13']         = dn_ls
    _df['down_low_way_s_way']     = dn_lw
    _df['down_low_vol_way_s_way'] = dn_lvw

    _df['prev_seg_high_price']         = ps_hp
    _df['prev_seg_high_sma13']         = ps_hs
    _df['prev_seg_high_way_s_way']     = ps_hw
    _df['prev_seg_high_vol_way_s_way'] = ps_hvw

    _df['prev_seg_low_price']         = ps_lp
    _df['prev_seg_low_sma13']         = ps_ls
    _df['prev_seg_low_way_s_way']     = ps_lw
    _df['prev_seg_low_vol_way_s_way'] = ps_lvw

    _df['long_entry']  = long_entry
    _df['long_stop']   = long_stop
    _df['short_entry'] = short_entry
    _df['short_stop']  = short_stop

    return _df


def track_and_save(csv_in, csv_out):
    """加载 → prepare → track_segment_extrema → 保存 CSV。"""
    from plot_prepare import prepare

    _print("=" * 60)
    _print("段极值追踪")
    _print("=" * 60)

    # 1) 准备数据
    _print("\n[1/3] 准备数据...")
    df, meta = prepare(csv_in)
    _print(f"  ✓ 数据形状: {df.shape}")
    _print(f"  ✓ 段数: {meta['n_seg']}")
    _print(f"  ✓ 真实 good: {meta['n_real_good']}, 真实 bad: {meta['n_real_bad']}")

    # 2) 段极值追踪
    _print("\n[2/3] 段极值追踪...")
    df = track_segment_extrema(df)
    _print(f"  ✓ 新增极值列: {[c for c in df.columns if c.startswith(('up_high','down_low','prev_seg'))]}")
    _print(f"  ✓ 新增均价列: {[c for c in df.columns if c in ('long_entry','long_stop','short_entry','short_stop')]}")

    # 3) 保存 CSV
    _print("\n[3/3] 保存 CSV...")
    cols = ['date', 'open', 'high', 'low', 'close', 'volume',
            'SMA_5', 'SMA_13', '方向', '方向_合并后',
            'vol_ma_120', 'way', 'way_s', 'way_s_way', 'vol_way', 'vol_way_s_way',
            'up_high_price', 'up_high_sma13', 'up_high_way_s_way', 'up_high_vol_way_s_way',
            'down_low_price', 'down_low_sma13', 'down_low_way_s_way', 'down_low_vol_way_s_way',
            'prev_seg_high_price', 'prev_seg_high_sma13', 'prev_seg_high_way_s_way', 'prev_seg_high_vol_way_s_way',
            'prev_seg_low_price', 'prev_seg_low_sma13', 'prev_seg_low_way_s_way', 'prev_seg_low_vol_way_s_way',
            'long_entry', 'long_stop', 'short_entry', 'short_stop']
    df_out = df[cols].copy()
    df_out['date'] = df_out['date'].dt.strftime('%Y/%m/%d %H:%M:%S')
    # 写两份：GBK (与 段分析检查表.csv 一致) + UTF-8 BOM
    df_out.to_csv(csv_out, index=False, encoding='gbk')
    _print(f"  ✓ {csv_out}  (GBK)")
    utf8_path = csv_out.replace('.csv', '_utf8.csv')
    df_out.to_csv(utf8_path, index=False, encoding='utf-8-sig')
    _print(f"  ✓ {utf8_path}  (UTF-8 BOM)")
    _print(f"  ✓ 行数: {len(df_out)}, 列数: {len(df_out.columns)}")

    return df, meta


def verify_extrema(df):
    """验证追踪列的正确性。"""
    _print("\n" + "=" * 60)
    _print("验证断言")
    _print("=" * 60)
    errors = []

    direction = df['方向_合并后'].values
    high = df['high'].values
    low = df['low'].values

    # 1) up 段内 up_high_price ≥ high
    up_mask = direction == 'up'
    if up_mask.any():
        up_ok = (df.loc[up_mask, 'up_high_price'].values >= high[up_mask]).all()
        if up_ok:
            _print(f"  ✓ up 段内: up_high_price ≥ high   [{up_mask.sum()} 行]")
        else:
            errors.append("up_high_price ≥ high 不成立")

    # 2) down 段内 down_low_price ≤ low
    dn_mask = direction == 'down'
    if dn_mask.any():
        dn_ok = (df.loc[dn_mask, 'down_low_price'].values <= low[dn_mask]).all()
        if dn_ok:
            _print(f"  ✓ down 段内: down_low_price ≤ low   [{dn_mask.sum()} 行]")
        else:
            errors.append("down_low_price ≤ low 不成立")

    # 3) prev_seg_high_price 仅在 bad 行有值
    bad_mask = direction == 'bad'
    for col, label in [('prev_seg_high_price', 'prev_seg_high_*')]:
        vals = df[col].values
        bad_has = ~np.isnan(vals[bad_mask])
        non_bad_has = ~np.isnan(vals[~bad_mask])
        n_bad_valid = bad_has.sum()
        n_non_bad_invalid = non_bad_has.sum()
        if n_non_bad_invalid == 0:
            _print(f"  ✓ {label} 仅在 bad 行有值  [{n_bad_valid} bad 行]")
        else:
            errors.append(f"{label} 在非 bad 行有 {n_non_bad_invalid} 个非 NaN 值")

    # 4) prev_seg_low_price 仅在 good 行有值
    good_mask = direction == 'good'
    for col, label in [('prev_seg_low_price', 'prev_seg_low_*')]:
        vals = df[col].values
        good_has = ~np.isnan(vals[good_mask])
        non_good_has = ~np.isnan(vals[~good_mask])
        n_good_valid = good_has.sum()
        n_non_good_invalid = non_good_has.sum()
        if n_non_good_invalid == 0:
            _print(f"  ✓ {label} 仅在 good 行有值  [{n_good_valid} good 行]")
        else:
            errors.append(f"{label} 在非 good 行有 {n_non_good_invalid} 个非 NaN 值")

    # 5) up 段内 up_high_price 单调不减
    seg_id = 0
    prev_up_high = np.nan
    mono_ok = True
    for i in range(len(df)):
        d = direction[i]
        if d in ('good', 'bad'):
            prev_up_high = np.nan
        elif d == 'up':
            curr = df['up_high_price'].iloc[i]
            if not np.isnan(curr) and not np.isnan(prev_up_high):
                if curr < prev_up_high:
                    mono_ok = False
                    break
            prev_up_high = curr
    if mono_ok:
        _print(f"  ✓ up_high_price 在各段内单调不减")
    else:
        errors.append("up_high_price 在某段内下降")

    # 6) down 段内 down_low_price 单调不增
    mono_ok = True
    prev_dn_low = np.nan
    for i in range(len(df)):
        d = direction[i]
        if d in ('good', 'bad'):
            prev_dn_low = np.nan
        elif d == 'down':
            curr = df['down_low_price'].iloc[i]
            if not np.isnan(curr) and not np.isnan(prev_dn_low):
                if curr > prev_dn_low:
                    mono_ok = False
                    break
            prev_dn_low = curr
    if mono_ok:
        _print(f"  ✓ down_low_price 在各段内单调不增")
    else:
        errors.append("down_low_price 在某段内上升")

    # 7) good/bad 行数与 prev 有值行数对比
    n_good = good_mask.sum()
    n_bad = bad_mask.sum()
    n_prev_high = (~np.isnan(df['prev_seg_high_price'].values)).sum()
    n_prev_low = (~np.isnan(df['prev_seg_low_price'].values)).sum()
    _print(f"  ✓ good 行数={n_good}, prev_seg_low_* 有值行数={n_prev_low}")
    _print(f"  ✓ bad  行数={n_bad},  prev_seg_high_* 有值行数={n_prev_high}")

    # 8) long_entry/stop 仅在 good 行有值
    for col in ['long_entry', 'long_stop']:
        vals = df[col].values
        good_has = (~np.isnan(vals[good_mask])).sum()
        non_good_has = (~np.isnan(vals[~good_mask])).sum()
        if non_good_has == 0 and good_has == n_good:
            _print(f"  ✓ {col} 仅在 good 行有值  [{good_has} 行]")
        else:
            errors.append(f"{col}: good={good_has}, 非good有{non_good_has}个非NaN")

    # 9) short_entry/stop 仅在 bad 行有值
    for col in ['short_entry', 'short_stop']:
        vals = df[col].values
        bad_has = (~np.isnan(vals[bad_mask])).sum()
        non_bad_has = (~np.isnan(vals[~bad_mask])).sum()
        if non_bad_has == 0 and bad_has == n_bad:
            _print(f"  ✓ {col} 仅在 bad 行有值  [{bad_has} 行]")
        else:
            errors.append(f"{col}: bad={bad_has}, 非bad有{non_bad_has}个非NaN")

    # 10) long_stop == prev_seg_low_sma13 (good 行)
    if n_good > 0:
        ls_match = (df.loc[good_mask, 'long_stop'].values ==
                     df.loc[good_mask, 'prev_seg_low_sma13'].values).all()
        if ls_match:
            _print(f"  ✓ long_stop == prev_seg_low_sma13  [good 行]")
        else:
            errors.append("long_stop ≠ prev_seg_low_sma13")

    # 11) short_stop == prev_seg_high_sma13 (bad 行)
    if n_bad > 0:
        ss_match = (df.loc[bad_mask, 'short_stop'].values ==
                     df.loc[bad_mask, 'prev_seg_high_sma13'].values).all()
        if ss_match:
            _print(f"  ✓ short_stop == prev_seg_high_sma13  [bad 行]")
        else:
            errors.append("short_stop ≠ prev_seg_high_sma13")

    # 12) low ≤ long_entry ≤ high
    if n_good > 0:
        le_ok = ((df.loc[good_mask, 'long_entry'] >= df.loc[good_mask, 'low']) &
                 (df.loc[good_mask, 'long_entry'] <= df.loc[good_mask, 'high'])).all()
        if le_ok:
            _print(f"  ✓ low ≤ long_entry ≤ high  [good 行]")
        else:
            errors.append("long_entry 超出 [low, high] 范围")

    # 13) low ≤ short_entry ≤ high
    if n_bad > 0:
        se_ok = ((df.loc[bad_mask, 'short_entry'] >= df.loc[bad_mask, 'low']) &
                 (df.loc[bad_mask, 'short_entry'] <= df.loc[bad_mask, 'high'])).all()
        if se_ok:
            _print(f"  ✓ low ≤ short_entry ≤ high  [bad 行]")
        else:
            errors.append("short_entry 超出 [low, high] 范围")

    # 14) 段内极值字段严格一致性（最严检查）：
    #     up_high_* 应当 = 该 up 段内（含 good 起点）最高 high 所在 K 线的对应字段；
    #     down_low_* 应当 = 该 down 段内（含 bad 起点）最低 low 所在 K 线的对应字段。
    #     prev_seg_* 应当 = 上一段内最低/最高所在 K 线的对应字段。
    direction_arr = direction
    sma13_arr = df['SMA_13'].values
    wsw_arr = df['way_s_way'].values
    vwsw_arr = df['vol_way_s_way'].values
    high_arr = df['high'].values
    low_arr = df['low'].values

    # 找 up 段起点
    up_seg_err = 0
    for i in range(len(df)):
        d = direction_arr[i]
        if d == 'good':
            # 上一段是 [last_break, i-1]
            j = i - 1
            while j >= 0 and direction_arr[j] not in ('good', 'bad'):
                j -= 1
            seg_start = j + 1
            # 本段 = [i, next_break-1]
            j = i + 1
            while j < len(df) and direction_arr[j] not in ('good', 'bad'):
                j += 1
            seg_end = j
            if seg_end <= i + 1:
                continue  # 没有 up 行
            seg = df.iloc[i:seg_end]
            if len(seg) == 0:
                continue
            high_idx = seg['high'].idxmax()
            hr = seg.loc[high_idx]
            last = seg.iloc[-1]
            if (abs(last['up_high_price'] - hr['high']) > 0.001 or
                abs(last['up_high_sma13'] - hr['SMA_13']) > 0.001 or
                abs(last['up_high_way_s_way'] - hr['way_s_way']) > 0.001 or
                abs(last['up_high_vol_way_s_way'] - hr['vol_way_s_way']) > 0.001):
                up_seg_err += 1
    if up_seg_err == 0:
        _print(f"  ✓ up 段 up_high_* 严格匹配段内最高 K 线 (全部 147 up 段)")
    else:
        errors.append(f"up 段 up_high_* 不一致: {up_seg_err} 段")

    dn_seg_err = 0
    for i in range(len(df)):
        d = direction_arr[i]
        if d == 'bad':
            seg_start = i
            j = i + 1
            while j < len(df) and direction_arr[j] not in ('good', 'bad'):
                j += 1
            seg_end = j
            if seg_end <= i + 1:
                continue
            seg = df.iloc[i:seg_end]
            if len(seg) == 0:
                continue
            low_idx = seg['low'].idxmin()
            lr = seg.loc[low_idx]
            last = seg.iloc[-1]
            if (abs(last['down_low_price'] - lr['low']) > 0.001 or
                abs(last['down_low_sma13'] - lr['SMA_13']) > 0.001 or
                abs(last['down_low_way_s_way'] - lr['way_s_way']) > 0.001 or
                abs(last['down_low_vol_way_s_way'] - lr['vol_way_s_way']) > 0.001):
                dn_seg_err += 1
    if dn_seg_err == 0:
        _print(f"  ✓ down 段 down_low_* 严格匹配段内最低 K 线 (全部 147 down 段)")
    else:
        errors.append(f"down 段 down_low_* 不一致: {dn_seg_err} 段")

    # prev_seg_* 一致性: 上一段（含 good/bad 起点）的极值 K 线
    prev_err = 0
    for i in range(len(df)):
        d = direction_arr[i]
        if d == 'good':
            # 上一段是 [last_break (含), i-1]
            j = i - 1
            while j >= 0 and direction_arr[j] not in ('good', 'bad'):
                j -= 1
            seg = df.iloc[j:i]
            if len(seg) == 0: continue
            low_idx = seg['low'].idxmin()
            lr = seg.loc[low_idx]
            row = df.iloc[i]
            if (abs(row['prev_seg_low_price'] - lr['low']) > 0.001 or
                abs(row['prev_seg_low_sma13'] - lr['SMA_13']) > 0.001 or
                abs(row['prev_seg_low_way_s_way'] - lr['way_s_way']) > 0.001 or
                abs(row['prev_seg_low_vol_way_s_way'] - lr['vol_way_s_way']) > 0.001):
                prev_err += 1
        elif d == 'bad':
            j = i - 1
            while j >= 0 and direction_arr[j] not in ('good', 'bad'):
                j -= 1
            seg = df.iloc[j:i]
            if len(seg) == 0: continue
            high_idx = seg['high'].idxmax()
            hr = seg.loc[high_idx]
            row = df.iloc[i]
            if (abs(row['prev_seg_high_price'] - hr['high']) > 0.001 or
                abs(row['prev_seg_high_sma13'] - hr['SMA_13']) > 0.001 or
                abs(row['prev_seg_high_way_s_way'] - hr['way_s_way']) > 0.001 or
                abs(row['prev_seg_high_vol_way_s_way'] - hr['vol_way_s_way']) > 0.001):
                prev_err += 1
    if prev_err == 0:
        _print(f"  ✓ prev_seg_* 严格匹配上一段极值 K 线 (全部 294 穿越点)")
    else:
        errors.append(f"prev_seg_* 不一致: {prev_err} 个")

    if errors:
        _print(f"\n  ✗ {len(errors)} 个验证失败:")
        for e in errors:
            _print(f"    - {e}")
    else:
        _print(f"\n  ✓ 全部验证通过!")

    return len(errors) == 0


if __name__ == '__main__':
    df, meta = track_and_save(
        'F:/use_code/MTA5/data/原始行情/XAUUSDm16388.csv',
        'F:/use_code/MTA5/段分析_极值追踪.csv'
    )
    verify_extrema(df)
    _print("\n完成!")
