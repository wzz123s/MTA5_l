# -*- coding: utf-8 -*-
"""processing.prepare - Unified entry point: load -> process -> save"""
import pandas as pd
import numpy as np
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from processing.smma import calc_smma
from processing.direction import mark_direction, add_pre_cross_and_counter
from processing.segment_filter import filter_short_segments_v2
from processing.way_grade import way_grade

def prepare(csv_path, min_len=8, mt5_smma=None):
    """加载 + 计算 + 段合并 + 强度，返回 (df, meta)。
    
    mt5_smma: 可选，从 MT5 EA CSV 加载的原生 SMMA DataFrame。
              若提供，SMA_5/SMA_13 从 MT5 读取，不再用 Python calc_smma()。
    """
    # 1) 加载
    df_raw = pd.read_csv(csv_path, encoding='gbk')
    df_raw.columns = ['date', 'open', 'high', 'low', 'close', 'volume',
                      'spread', 'real_volume', 'symbol', 'time_diff']
    df_raw['date'] = pd.to_datetime(df_raw['date'])

    # ⭐ 时区偏移: MT5 服务器 → MT5 客户端, 整体 +2 小时。
    df_raw['date'] = df_raw['date'] + pd.Timedelta(hours=0)  # 服务器=UTC，无时区偏移

    df_raw = df_raw.set_index('date')

    # 2) 5/13 SMMA — 优先使用 MT5 原生值
    if mt5_smma is not None:
        # 对齐: MT5 CSV 的时间已经 +2h，和 df_raw 的 date 对齐
        common_idx = df_raw.index.intersection(mt5_smma.index)
        df_raw.loc[common_idx, 'SMA_5'] = mt5_smma.loc[common_idx, 'm30_sma5']
        df_raw.loc[common_idx, 'SMA_13'] = mt5_smma.loc[common_idx, 'm30_sma13']
        # 填充开头对齐不上的部分用 Python SMMA
        mask = df_raw['SMA_5'].isna()
        df_raw.loc[mask, 'SMA_5'] = calc_smma(df_raw['close'], 5).loc[mask]
        mask = df_raw['SMA_13'].isna()
        df_raw.loc[mask, 'SMA_13'] = calc_smma(df_raw['close'], 13).loc[mask]
    else:
        df_raw['SMA_5'] = calc_smma(df_raw['close'], 5)
        df_raw['SMA_13'] = calc_smma(df_raw['close'], 13)

    # 3) 方向（含首行纠正）
    df = mark_direction(df_raw)

    # 4) 120 根均量（way_grade 需要）
    df['vol_ma_120'] = df['volume'].rolling(120, min_periods=1).mean().round(2)

    # 5) v2 段合并
    (df, is_real_good, is_real_bad, seg_len, seg_starts, seg_ends,
     has_first, has_last, n_seg, good_pos, bad_pos) = filter_short_segments_v2(df, min_len=min_len)

    # 6) 段内强度（按 v2 后的 方向_合并后 算）
    df = way_grade(df)

    # 6.5) v4.0 Layer 2 状态机: pre_cross + post_cross_n
    #   第一次调用基于原始 '方向': pre_cross 在原始穿越前的 K 线检测
    #   第二次调用基于 '方向_合并后': post_cross_n 在段合并后重算(覆盖 post_cross_n)
    df = add_pre_cross_and_counter(df, fixed_thr=0.0005, atr_k=None,
                                    direction_col='方向', prefix='')
    df = add_pre_cross_and_counter(df, fixed_thr=0.0005, atr_k=None,
                                    direction_col='方向_合并后', prefix='merged_')

    # 7) meta：用于画图
    real_good_pos = good_pos[is_real_good]
    real_bad_pos = bad_pos[is_real_bad]
    reclassified_good_pos = good_pos[~is_real_good]
    reclassified_bad_pos = bad_pos[~is_real_bad]

    # 按 方向_合并后 重建段边界（供段色带使用）
    # v4 兼容: 幸存 good/bad 数量差可能 > 1, 按位置交替扫描重建
    direction_new = df['方向_合并后'].values
    new_good = np.where(direction_new == 'good')[0]
    new_bad = np.where(direction_new == 'bad')[0]
    n_new_good, n_new_bad = len(new_good), len(new_bad)
    n_total = len(df)

    # 决定首末段 (按方向序列交替: 谁先出现谁定首段, 最后剩余定末段)
    if n_new_good == 0 and n_new_bad == 0:
        # 无穿越点: 整段一段
        n_new_seg = 1
        new_seg_starts = np.array([0])
        new_seg_ends = np.array([n_total - 1])
    else:
        if n_new_good == 0:
            first_is_bad = True
        elif n_new_bad == 0:
            first_is_bad = False
        else:
            first_is_bad = new_bad[0] < new_good[0]
        # 末段 = 序列最长的那边最后剩的那段
        if n_new_good == n_new_bad:
            last_is_bad = not first_is_bad
        elif n_new_good > n_new_bad:
            last_is_bad = False
        else:
            last_is_bad = True

        # 按穿越点配对切分: 段 i = [穿越点[i], 穿越点[i+1]]
        # 首段特殊: 从 0 开始, 第一个穿越点之前
        # 末段特殊: 从最后一个穿越点开始, 到 n_total-1
        new_has_first = first_is_bad  # 首段 = down 段 (从 0 到首个 bad) 或 up 段
        new_has_last = last_is_bad    # 末段 = down 段 (从末个 bad 到 n-1) 或 up 段
        n_new_seg = n_new_good + n_new_bad + 1

        new_seg_starts = np.zeros(n_new_seg, dtype=int)
        new_seg_ends = np.zeros(n_new_seg, dtype=int)
        # 把所有穿越点按位置排序
        all_cross = sorted(
            [(p, 'good') for p in new_good] + [(p, 'bad') for p in new_bad],
            key=lambda x: x[0]
        )
        # 段 i 的范围:
        #   i = 0: [0, all_cross[0][0]]
        #   0 < i < n_new_seg - 1: [all_cross[i-1][0], all_cross[i][0]]
        #   i = n_new_seg - 1: [all_cross[-1][0], n_total - 1]
        for i in range(n_new_seg):
            if i == 0:
                new_seg_starts[i] = 0
                new_seg_ends[i] = all_cross[0][0]
            elif i == n_new_seg - 1:
                new_seg_starts[i] = all_cross[-1][0]
                new_seg_ends[i] = n_total - 1
            else:
                new_seg_starts[i] = all_cross[i - 1][0]
                new_seg_ends[i] = all_cross[i][0]

    # 每段类型 (up 段 / down 段) — 用整段多数方向, 不只看中点
    new_seg_type = []
    for i in range(n_new_seg):
        seg_range = direction_new[new_seg_starts[i]:new_seg_ends[i] + 1]
        n_up = ((seg_range == 'up') | (seg_range == 'good')).sum()
        n_down = ((seg_range == 'down') | (seg_range == 'bad')).sum()
        new_seg_type.append('up' if n_up >= n_down else 'down')

    meta = {
        'real_good_pos': real_good_pos,
        'real_bad_pos': real_bad_pos,
        'reclassified_good_pos': reclassified_good_pos,
        'reclassified_bad_pos': reclassified_bad_pos,
        'seg_starts': new_seg_starts,
        'seg_ends': new_seg_ends,
        'seg_type': np.array(new_seg_type),
        'n_seg': n_new_seg,
        'n_real_good': len(real_good_pos),
        'n_real_bad': len(real_bad_pos),
    }

    # ⭐ DatetimeIndex → RangeIndex(0..N-1)
    # 消除非交易时段的视觉留白: K线紧密排列, X 轴只显示整数 0..N-1
    # reset_index (无 drop) 把 DatetimeIndex 变成 'date' 普通列 + RangeIndex,
    # 'date' 列保留给 plotly 的 Candlestick customdata / hovertemplate 显示真实时间。
    df = df.reset_index()  # index → 'date' 列, 新 index = 0..N-1 的 RangeIndex
    if 'date' not in df.columns:
        # 防御: 如果原 index 没有 name, 自动用 'date' 命名
        df.columns = ['date'] + list(df.columns[:-1])

    return df, meta


if __name__ == '__main__':
    df, meta = prepare('F:/use_code/MTA5/data/原始行情/XAUUSDm16388.csv')
    print(f"数据形状: {df.shape}")
    print(f"首根时间 (北京时间): {df['date'].iloc[0]}")
    print(f"末根时间 (北京时间): {df['date'].iloc[-1]}")
    print(f"index 类型: {type(df.index).__name__} (应为 RangeIndex)")
    print(f"段数 (合并后): {meta['n_seg']}")
    print(f"真实 good: {meta['n_real_good']}")
    print(f"真实 bad : {meta['n_real_bad']}")
    print(f"差值     : {meta['n_real_good'] - meta['n_real_bad']}")
    print(f"\n列: {list(df.columns)}")
    print(f"\n前 3 行:")
    print(df[['date', 'close', 'SMA_5', 'SMA_13', '方向', '方向_合并后',
             'way', 'way_s', 'way_s_way', 'vol_way']].head(3).to_string())

    # ========== v4 验证断言 ==========
    # 1) 反例 1: 2017-04-10 14:00 (北京时间) bad + 1 根 down → 应被链式吸收, 全部改成 up
    sub1 = df[(df['date'] >= '2017-04-10 14:00') & (df['date'] < '2017-04-10 22:00')]
    assert len(sub1) >= 2, f"反例1 数据范围异常, 找到 {len(sub1)} 行"
    assert (sub1['方向_合并后'] == 'up').all(), (
        f"反例1 失败: 2017-04-10 14:00 后续 K线应全部 up, 实际 {sub1['方向_合并后'].tolist()}"
    )
    print(f"\n✓ 反例 1 通过: 2017-04-10 14:00 区域 {len(sub1)} 根全 up")

    # 2) 反例 2: 2017-04-20 06:00 bad + 8 根 down → 不应被吸收
    sub2 = df[(df['date'] >= '2017-04-20 06:00') & (df['date'] < '2017-04-21 18:00')]
    assert len(sub2) >= 9, f"反例2 数据范围异常, 找到 {len(sub2)} 行"
    assert sub2.iloc[0]['方向_合并后'] == 'bad', (
        f"反例2 失败: 2017-04-20 06:00 应保持 bad, 实际 {sub2.iloc[0]['方向_合并后']}"
    )
    assert (sub2.iloc[1:9]['方向_合并后'] == 'down').all(), (
        f"反例2 失败: 2017-04-20 06:00 后续 8 根 down 应保持, 实际 {sub2.iloc[1:9]['方向_合并后'].tolist()}"
    )
    print(f"✓ 反例 2 通过: 2017-04-20 06:00 bad 保持, 后续 8 根 down 保持")

    # 3) ⭐ 核心新断言: 幸存 good/bad 数量差 ≤ 1 (走势是严格循环)
    n_good, n_bad = meta['n_real_good'], meta['n_real_bad']
    diff = n_good - n_bad
    assert abs(diff) <= 1, (
        f"v4 平衡约束违反: n_good={n_good}, n_bad={n_bad}, 差={diff} "
        f"(应 ≤ 1, 因为走势是严格循环 down→good→up→bad→down)"
    )
    print(f"✓ 平衡约束通过: n_good={n_good}, n_bad={n_bad}, 差={diff} (≤ 1)")

    # 4) 末段保持原始行情: 2026/6/2 22:00 末尾 bad 之后数据未走完
    #    → 应当保留 bad 为 real crossing, tail 1 根 down 应保持为 down
    last_date = df['date'].max()
    # 找最后一个 bad 穿越点
    last_bad_idx = df[df['方向'] == 'bad'].index[-1]
    last_bad_date = df.loc[last_bad_idx, 'date']
    tail_after_last_bad = df.iloc[last_bad_idx:]
    print(f"  最后 bad 穿越点: {last_bad_date}, tail {len(tail_after_last_bad) - 1} 根")
    assert tail_after_last_bad.iloc[0]['方向_合并后'] == 'bad', (
        f"末段失败: {last_bad_date} 应保持 bad, 实际 {tail_after_last_bad.iloc[0]['方向_合并后']}"
    )
    # tail 的 down 应当保持 (按原始行情)
    tail_dn = tail_after_last_bad[tail_after_last_bad['方向'] == 'down']
    if len(tail_dn) > 0:
        assert (tail_dn['方向_合并后'] == 'down').all(), (
            f"末段 tail down 失败: 末尾原始 down 应当保持, 实际 "
            f"{tail_dn['方向_合并后'].tolist()}"
        )
    print(f"✓ 末段保持原始行情: 末尾 {last_bad_date.strftime('%Y/%m/%d %H:%M')} bad 保留, "
          f"tail {len(tail_dn)} 根 down 保持")

    print(f"\n{'='*60}")
    print(f"✓ v4 严格链式吸收 — 全部验证通过")
    print(f"{'='*60}")
