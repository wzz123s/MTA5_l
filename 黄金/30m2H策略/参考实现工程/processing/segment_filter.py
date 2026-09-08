# -*- coding: utf-8 -*-
"""processing.segment_filter - Short segment filtering V4 (strict chain absorption)"""
import numpy as np

def filter_short_segments_v2(df, min_len=8):
    """
    v4 段合并 — **严格链式吸收** (v3 的修正版)。

    核心规则 (用户原话, 2026-06-04 明确):
      - good 之后 up < min_len → good + 整段 up + 下一个 bad 一起吸收
        (趋势延续为 good 之前的方向, 通常是 down)
      - bad 之后 down < min_len → bad + 整段 down + 下一个 good 一起吸收
        (趋势延续为 bad 之前的方向, 通常是 up)
      - **强制链式**: 每次吸收必然连带移除下一个穿越点, 不论其后续段长
      - 这样保证幸存 good 和 bad 数量差严格 ≤ 1 (走势是循环)

    关键修正 (vs 错版 v4):
      1. 移除 while 循环 + 双列表结构 → 改用单次严格链式遍历
      2. 链式吸收 = 一次移除 1 good + 1 bad, 差值严格不变
      3. 首段 [0, first_crossing-1] 不参与吸收, 作为初始趋势保留
      4. 末段无 next_crossing 可链, 可能差 1 (但 ≤ 1 满足约束)
      5. 段边界切分容错: n_seg = n_good + n_bad + 1, 任意差值都正确

    返回 (df, is_real_good, is_real_bad, seg_len, seg_starts, seg_ends,
          has_first, has_last, n_seg, good_pos, bad_pos)
    — 接口与 v3 兼容, prepare() 调用方不需改。
    """
    _df = df.copy()
    direction = _df['方向'].values.astype(object)
    n = len(_df)
    good_pos_all = np.where(direction == 'good')[0]
    bad_pos_all = np.where(direction == 'bad')[0]

    # ---------- 1) 合并所有穿越点, 按位置排序 ----------
    all_crossings = sorted(
        [(int(p), 'good') for p in good_pos_all] +
        [(int(p), 'bad')  for p in bad_pos_all],
        key=lambda x: x[0],
    )

    if len(all_crossings) == 0:
        # 极端: 无穿越点, 整段一段
        _df['方向_合并后'] = direction
        return (_df, np.array([], dtype=bool), np.array([], dtype=bool),
                np.array([n], dtype=int), np.array([0]), np.array([n - 1]),
                True, True, 1, good_pos_all, bad_pos_all)

    # ---------- 2) 初始 state = 第一个穿越点之前的趋势 ----------
    #    good (上穿) 前是 down, bad (下穿) 前是 up
    first_pos, first_type = all_crossings[0]
    state = 'down' if first_type == 'good' else 'up'

    surviving_good = []
    surviving_bad = []

    # ---------- 3) 严格链式吸收 (单次遍历, O(N)) ----------
    i = 0
    while i < len(all_crossings):
        pos, type_ = all_crossings[i]

        # 3.1) 末段: 没有下一个穿越点
        # ⭐ 数据末尾行情可能未走完, 永远保留最后一个穿越点为 real crossing
        # 按原始行情安排: tail 的 up/down 保持原状 (不改成 state)
        if i + 1 >= len(all_crossings):
            if type_ == 'good':
                surviving_good.append(pos)
            else:
                surviving_bad.append(pos)
            break

        # 3.2) 区域内同向数量 (good 后数 up, bad 后数 down)
        next_pos, next_type = all_crossings[i + 1]
        region = (direction[pos + 1:next_pos]
                  if pos + 1 < next_pos else np.array([], dtype=object))
        if type_ == 'good':
            region_count = int(np.sum(region == 'up'))
        else:
            region_count = int(np.sum(region == 'down'))

        if region_count < min_len:
            # ⭐ 严格链式吸收: current + region + next 全部改成 state
            # 趋势延续 (state 不变)
            direction[pos] = state
            for k in range(pos + 1, next_pos):
                direction[k] = state
            direction[next_pos] = state

            # 移除当前和下一个穿越点 (强制, 不论 next 后续段长)
            all_crossings.pop(i + 1)
            all_crossings.pop(i)
            # i 不变, state 不变 → 下次处理 next_crossing 之后的那个
        else:
            # 保留当前穿越点, 趋势翻转为新方向
            if type_ == 'good':
                surviving_good.append(pos)
                state = 'up'
            else:
                surviving_bad.append(pos)
                state = 'down'
            i += 1

    # ---------- 4) 写回 方向_合并后, 构造幸存穿越点掩码 ----------
    _df['方向_合并后'] = direction
    surviving_good_set = set(surviving_good)
    surviving_bad_set = set(surviving_bad)
    is_real_good = np.array([(int(p) in surviving_good_set) for p in good_pos_all], dtype=bool)
    is_real_bad = np.array([(int(p) in surviving_bad_set) for p in bad_pos_all], dtype=bool)

    # ---------- 5) 段边界完全重建 (按幸存 good/bad 交替扫描) ----------
    new_good = good_pos_all[is_real_good]
    new_bad = bad_pos_all[is_real_bad]
    n_ng, n_nb = len(new_good), len(new_bad)
    if n_ng == 0 and n_nb == 0:
        n_seg = 1
        has_first = True
        has_last = True
        seg_starts = np.array([0])
        seg_ends = np.array([n - 1])
    else:
        # 决定首段类型: 由位置最靠前的穿越点决定
        if n_ng == 0:
            first_is_bad = True
        elif n_nb == 0:
            first_is_bad = False
        else:
            first_is_bad = int(new_bad[0]) < int(new_good[0])
        # 段数 = 幸存穿越点数 + 1 (任意差值都正确)
        n_seg = n_ng + n_nb + 1
        # 末段: 由数量多的一边决定 (与首段相反或同)
        if n_ng > n_nb:
            last_is_bad = False
        elif n_nb > n_ng:
            last_is_bad = True
        else:
            last_is_bad = not first_is_bad
        has_first = first_is_bad
        has_last = last_is_bad
        # 配对切分: 段 i = [穿越点[i], 穿越点[i+1]] (i > 0)
        all_cross_sorted = sorted(
            [(int(p), 'good') for p in new_good] +
            [(int(p), 'bad')  for p in new_bad],
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

