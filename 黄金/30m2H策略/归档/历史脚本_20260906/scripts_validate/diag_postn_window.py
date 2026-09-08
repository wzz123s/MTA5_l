# -*- coding: utf-8 -*-

"""诊断: EA 500-bar 窗口段合并 vs Python 全量合并 → post_n 差异根因验证

复刻 EA M30MergedDirectionCodeLastCompleted (500-bar window) + UpdateMergedPostNState,
对比 Python processing.filter_short_segments_v2 全量 merged_post_cross_n。
"""
import sys
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程")

import numpy as np
import pandas as pd
from processing.smma import calc_smma

M30_PATH = r"F:\use_code\MTA5_l\黄金\30m2H策略\data\raw\mt5_history\30m2h_mt5_20260811\XAUUSDm_M30.csv"
WINDOW = 500
MIN_LEN = 8

# ---------- 1) 加载数据 + SMMA ----------
m30 = pd.read_csv(M30_PATH, encoding="utf-8-sig")
m30["time"] = pd.to_datetime(m30["time"]).dt.tz_localize(None)
df = m30[["time", "open", "high", "low", "close"]].reset_index(drop=True)
df["SMA_5"] = calc_smma(df["close"], 5).values
df["SMA_13"] = calc_smma(df["close"], 13).values
df = df.dropna(subset=["SMA_13"]).reset_index(drop=True)
n = len(df)
print(f"bars: {n}  ({df['time'].iloc[0]} ~ {df['time'].iloc[-1]})")

# ---------- 2) Python 全量 merged 方向 + post_n ----------
from processing.direction import mark_direction, add_pre_cross_and_counter
from processing.segment_filter import filter_short_segments_v2

df_raw = mark_direction(df)
df_merged, *_ = filter_short_segments_v2(df_raw, min_len=MIN_LEN)
df_merged = add_pre_cross_and_counter(df_merged, fixed_thr=0.0005, atr_k=None,
                                      direction_col="方向_合并后", prefix="merged_")
py_merged = df_merged["merged_post_cross_n"].values

# ---------- 3) 复刻 EA 逻辑 (500-bar 窗口 + 增量 counter) ----------
def ea_merged_dir_code(fast, slow, completed):
    """复刻 M30MergedDirectionCodeLastCompleted(窗口内)"""
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

# 逐 bar 复刻 EA: bar i 收盘后调用 → 窗口 [i-WINDOW, i) 重算 merged dir（=bar i-1 的）→ 增量 counter 记在 bar i-1
fast = df["SMA_5"].values
slow = df["SMA_13"].values
ea_counter = np.zeros(n, dtype=int)
last_dir = 0
cnt = 0
mismatch_pos = []
for i in range(1, n):
    start = max(0, i - WINDOW)
    w_fast = fast[start:i]      # 老→新, 不含 i
    w_slow = slow[start:i]
    if len(w_fast) < 2:
        continue
    merged_code = ea_merged_dir_code(w_fast, w_slow, len(w_fast))
    merged = 1 if merged_code > 0 else -1
    if last_dir == 0:
        cnt = 1
    elif merged != last_dir:
        cnt = 1 if merged > 0 else -1
    else:
        if cnt > 0:
            cnt += 1
        elif cnt < 0:
            cnt -= 1
        else:
            cnt = 1 if merged > 0 else -1
    last_dir = merged
    ea_counter[i - 1] = cnt
    if cnt != py_merged[i - 1]:
        mismatch_pos.append(i - 1)

mm = np.array(mismatch_pos)
print(f"\n=== 对比结果 ===")
print(f"total bars: {n}")
print(f"mismatch bars: {len(mm)} ({len(mm)/n*100:.2f}%)")
if len(mm) > 0:
    # 连续段统计
    gaps = np.diff(mm)
    seg_start = mm[0]
    runs = []
    for j in range(1, len(mm)):
        if gaps[j-1] > 1:
            runs.append((seg_start, mm[j-1]))
            seg_start = mm[j]
    runs.append((seg_start, mm[-1]))
    print(f"mismatch 连续段: {len(runs)} 段")
    for s, e in runs[:15]:
        span = e - s + 1
        print(f"  [{df['time'].iloc[s]} ~ {df['time'].iloc[e]}]  {span} bars  py={py_merged[s]} ea={ea_counter[s]}")
    # 差 1 分析: 第一个 mismatch 的详情
    i0 = mm[0]
    print(f"\n=== 首个 mismatch bar {df['time'].iloc[i0]} ===")
    for j in range(max(0, i0-6), min(n, i0+6)):
        mark = " <-- MISMATCH" if j in mismatch_pos else ""
        print(f"  idx {j} {df['time'].iloc[j]}  py_post_n={py_merged[j]}  ea_post_n={ea_counter[j]}{mark}")
