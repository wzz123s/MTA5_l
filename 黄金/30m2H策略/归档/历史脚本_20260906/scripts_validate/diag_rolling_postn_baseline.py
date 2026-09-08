# -*- coding: utf-8 -*-

"""验证: 滚动 merged post_n（EA 算法）重算 baseline → 交易数变化

对比:
  A) 全量合并 post_n（当前 expected ledger 用的, look-ahead）
  B) 滚动合并 post_n（EA 实时语义, 无 look-ahead）

输出: 两种口径下的 accepted 交易数 / 最终 picked 数
"""
import os
import sys
os.chdir(r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程\scripts")

import numpy as np
import pandas as pd
from processing.smma import calc_smma
from processing.direction import mark_direction, add_pre_cross_and_counter
from processing.segment_filter import filter_short_segments_v2

import _current_baseline as base
import _m15_early_entry_test as m15t

WINDOW = 500  # EA 当前窗口; 0 = 全量
MIN_LEN = 8


def ea_merged_dir_code(fast, slow, completed):
    """复刻 EA M30MergedDirectionCodeLastCompleted(窗口内全量合并)"""
    if completed <= 0:
        return 0
    dir_codes = np.zeros(completed, dtype=int)
    prev_above = fast[0] > slow[0]
    dir_codes[0] = 1 if prev_above else -1
    for i in range(1, completed):
        curr_above = fast[i] > slow[i]
        if curr_above and not prev_above:
            dir_codes[i] = 2
        elif not curr_above and prev_above:
            dir_codes[i] = -2
        elif curr_above and prev_above:
            dir_codes[i] = 1
        else:
            dir_codes[i] = -1
        prev_above = curr_above
    crossings = [i for i in range(completed) if abs(dir_codes[i]) == 2]
    if not crossings:
        return dir_codes[completed - 1]
    first_type = dir_codes[crossings[0]]
    state = -1 if first_type == 2 else 1
    i = 0
    while i < len(crossings):
        pos = crossings[i]
        type_ = dir_codes[pos]
        if i + 1 >= len(crossings):
            break
        next_pos = crossings[i + 1]
        region_count = 0
        for k in range(pos + 1, next_pos):
            if type_ == 2 and dir_codes[k] == 1:
                region_count += 1
            if type_ == -2 and dir_codes[k] == -1:
                region_count += 1
        if region_count < MIN_LEN:
            dir_codes[pos] = state
            for k in range(pos + 1, next_pos):
                dir_codes[k] = state
            dir_codes[next_pos] = state
            crossings.pop(i + 1)
            crossings.pop(i)
            if not crossings:
                break
            continue
        state = 1 if type_ == 2 else -1
        i += 1
    return dir_codes[completed - 1]


def rolling_merged_postn(fast, slow, window):
    """逐 bar 滚动: merged 方向（窗口内全量合并, 末段保留）+ 增量 counter。
    window=0 → 全量窗口（与 EA 窗口全量时一致）。返回 (merged_codes, post_n)"""
    n = len(fast)
    merged = np.zeros(n, dtype=int)
    post_n = np.zeros(n, dtype=int)
    last_dir = 0
    cnt = 0
    for i in range(n):
        if i < 1:
            continue
        start = 0 if window <= 0 else max(0, i - window)
        code = ea_merged_dir_code(fast[start:i], slow[start:i], i - start)
        m = 1 if code > 0 else -1
        if last_dir == 0:
            cnt = 1
        elif m != last_dir:
            cnt = 1 if m > 0 else -1
        else:
            cnt = cnt + 1 if cnt > 0 else (cnt - 1 if cnt < 0 else (1 if m > 0 else -1))
        last_dir = m
        merged[i - 1] = code
        post_n[i - 1] = cnt
    return merged, post_n


def build_with_postn(post_n_col):
    """用给定 post_n 列构建 accepted 候选, 返回交易表"""
    df, h2, m15 = base.load_market_context()
    df["merged_post_cross_n"] = post_n_col
    q2_pass_set, q2_factor_map, _, _ = base.h2t.early_precompute(h2, df, 2, False)
    raw_df, accepted = base.combo.build_candidate_frames(df, q2_pass_set, q2_factor_map)
    return df, accepted, raw_df


def main():
    m30 = pd.read_csv(r"F:\use_code\MTA5_l\黄金\30m2H策略\data\raw\mt5_history\30m2h_mt5_20260811\XAUUSDm_M30.csv",
                      encoding="utf-8-sig")
    m30["time"] = pd.to_datetime(m30["time"]).dt.tz_localize(None)
    df0 = m30[["time", "open", "high", "low", "close"]].reset_index(drop=True)
    df0["SMA_5"] = calc_smma(df0["close"], 5).values
    df0["SMA_13"] = calc_smma(df0["close"], 13).values
    df0 = df0.dropna(subset=["SMA_13"]).reset_index(drop=True)
    n = len(df0)
    fast = df0["SMA_5"].values
    slow = df0["SMA_13"].values

    # A) 全量合并（当前口径）
    raw = mark_direction(df0)
    merged, *_ = filter_short_segments_v2(raw, min_len=MIN_LEN)
    merged = add_pre_cross_and_counter(merged, fixed_thr=0.0005, atr_k=None,
                                       direction_col="方向_合并后", prefix="merged_")
    full_pn = merged["merged_post_cross_n"].values

    # B) 滚动合并（EA 语义）
    roll_codes, roll_pn = rolling_merged_postn(fast, slow, WINDOW)

    print(f"bars: {n}")
    print(f"full post_n 非零: {(full_pn != 0).sum()}  滚动非零: {(roll_pn != 0).sum()}")
    diff = (full_pn != roll_pn)
    print(f"post_n 不一致 bar: {diff.sum()} ({diff.sum()/n*100:.1f}%)")

    # 分别构建候选
    print("\n=== A) 全量合并口径 ===")
    dfA, accA, rawA = build_with_postn(full_pn)
    print(f"accepted: {len(accA)}  (模式: {accA['mode'].value_counts().to_dict()})")

    print("\n=== B) 滚动合并口径 (EA 语义) ===")
    dfB, accB, rawB = build_with_postn(roll_pn)
    print(f"accepted: {len(accB)}  (模式: {accB['mode'].value_counts().to_dict()})")


if __name__ == "__main__":
    main()
