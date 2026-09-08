# -*- coding: utf-8 -*-
"""Shared helpers for the current 30m x 2H mainline strategy baseline."""
import bisect
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from processing.prepare import prepare
import _stage12_combo_test as s12
import _m15_h2_combo_test as combo
import _m15_early_entry_test as m15t
import _h2_early_gate_test as h2t
from _h2_context import load_h2_context
import _pre_cross_range_test as pct


DEFAULT_SPEC_LO = 5
DEFAULT_SPEC_HI = 35
DEFAULT_TOP_PCT = 34
DEFAULT_BIAS55_THRESHOLD = 3.0
DEFAULT_STAGE1_R = 2.0
DEFAULT_STAGE2_TRAIL_R = 1.5
DEFAULT_STAGE2_FORCE_R = 4.0
EA_DIAG_H2_LOOKBACK = 500
EA_DIAG_M30_LAYER3_SHIFT_MINUTES = 30


def load_market_context(h2_shift_hours=0):
    df, _ = prepare("base_data/XAUUSDm30.csv", min_len=8)
    h2 = load_h2_context(extra_shift_hours=h2_shift_hours)
    m15 = m15t.load_m15()
    m15t.df_global = df
    h2t.df_global = df
    return df, h2, m15


# ---------------------------------------------------------------------------
# 滚动段合并 (EA 实时语义, 无 look-ahead)
# ---------------------------------------------------------------------------
MERGED_MIN_LEN = 8
MERGED_WINDOW = 500  # EA M30MergedDirectionCodeLastCompleted 的窗口


def _ea_merged_dir_code(fast, slow, completed):
    """复刻 EA M30MergedDirectionCodeLastCompleted(窗口内) 的段合并。
    返回窗口最后一根已完成 bar 的合并方向码 (±1/±2)。"""
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
            break  # 末段穿越点永远保留 (EA 语义)
        next_pos = crossings[i + 1]
        region_count = 0
        for k in range(pos + 1, next_pos):
            if type_ == 2 and dir_codes[k] == 1:
                region_count += 1
            if type_ == -2 and dir_codes[k] == -1:
                region_count += 1
        if region_count < MERGED_MIN_LEN:
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


def rolling_merged_postn(df, window=MERGED_WINDOW):
    """逐 bar 滚动: 复刻 EA 的 UpdateMergedPostNState 增量 counter + merged 方向。
    df 需含 SMA_5/SMA_13 (行序 = 时间序)。返回 (merged_code_series, post_n_series)。"""
    fast = df["SMA_5"].values
    slow = df["SMA_13"].values
    n = len(df)
    merged_codes = np.zeros(n, dtype=int)
    post_n = np.zeros(n, dtype=int)
    last_dir = 0
    cnt = 0
    for i in range(1, n):
        start = max(0, i - window)
        code = _ea_merged_dir_code(fast[start:i], slow[start:i], i - start)
        m = 1 if code > 0 else -1
        if last_dir == 0:
            cnt = 1
        elif m != last_dir:
            cnt = 1 if m > 0 else -1
        else:
            if cnt > 0:
                cnt += 1
            elif cnt < 0:
                cnt -= 1
            else:
                cnt = 1 if m > 0 else -1
        last_dir = m
        merged_codes[i - 1] = code
        post_n[i - 1] = cnt
    return merged_codes, post_n


def build_final_accepted(
    spec_lo=DEFAULT_SPEC_LO,
    spec_hi=DEFAULT_SPEC_HI,
    bias55_threshold=DEFAULT_BIAS55_THRESHOLD,
    h2_shift_hours=0,
    ea_executable_diag=False,
    rolling_merged=False,
):
    df, h2, m15 = load_market_context(h2_shift_hours=h2_shift_hours)

    if rolling_merged:
        # 滚动段合并 (EA 实时语义, 无 look-ahead): 覆盖 merged_post_cross_n 与 方向_合并后
        merged_codes, roll_pn = rolling_merged_postn(df)
        df["merged_post_cross_n"] = roll_pn
        df["merged_dir_code"] = merged_codes
        # ±1/±2 → up/down/good/bad (EA dir_codes 语义, 吸收后为 state 延续)
        df["方向_合并后"] = [
            "good" if c == 2 else ("bad" if c == -2 else ("up" if c == 1 else "down"))
            for c in merged_codes
        ]

    old_pct_lo, old_pct_hi = pct.SPEC_LO, pct.SPEC_HI
    old_bias55 = pct.BIAS_55_THRESHOLD
    old_m15_lo, old_m15_hi = m15t.SPEC_LO, m15t.SPEC_HI
    try:
        pct.SPEC_LO, pct.SPEC_HI = spec_lo, spec_hi
        pct.BIAS_55_THRESHOLD = bias55_threshold
        m15t.SPEC_LO, m15t.SPEC_HI = spec_lo, spec_hi

        q2_pass_set, q2_factor_map, _, _ = h2t.early_precompute(h2, df, 2, False)
        raw_df, accepted = combo.build_candidate_frames(
            df, q2_pass_set, q2_factor_map, ea_mode=ea_executable_diag,
        )

        m15_start = pd.Timestamp(m15["date"].min())
        pre_cov = accepted[pd.to_datetime(accepted["date"]) < m15_start].reset_index(drop=True)
        cov = accepted[pd.to_datetime(accepted["date"]) >= m15_start].reset_index(drop=True)
        if ea_executable_diag:
            cov_mod, _ = m15t.apply_replace_variant(
                cov,
                m15,
                m15t.choose_slot1_by_distance,
                "ea_slot1_replace",
                require_earlier=True,
                reanchor_stop_by_distance=True,
            )
            rejected_runtime = raw_df[
                (~raw_df["spec_pass"])
                & m15t.coverage_mask(raw_df, m15_start)
            ].copy()
            rescued, _ = m15t.build_rescued_trades(
                rejected_runtime,
                m15,
                m15t.choose_slot1_by_distance,
                variant_name="ea_slot1_runtime_rescue",
                reanchor_stop_by_distance=True,
            )
        else:
            cov_mod, _ = m15t.apply_replace_variant(cov, m15, m15t.choose_any, "combo")
            rejected_wide = raw_df[
                (~raw_df["spec_pass"])
                & (raw_df["spec_reason"] == "too_wide")
                & m15t.coverage_mask(raw_df, m15_start)
            ].copy()
            rescued, _ = m15t.build_rescued_trades(rejected_wide, m15, m15t.choose_any)
        cov_merged = m15t.dedupe_anchor(cov_mod.to_dict("records") + rescued.to_dict("records"))
        final_acc = combo.combine_full_sample(pre_cov, cov_merged).sort_values("date").reset_index(drop=True)
        if ea_executable_diag:
            final_acc = apply_m30_close_proxy(final_acc, df)
        final_acc["year"] = pd.to_datetime(final_acc["date"]).dt.year
        return df, final_acc
    finally:
        pct.SPEC_LO, pct.SPEC_HI = old_pct_lo, old_pct_hi
        pct.BIAS_55_THRESHOLD = old_bias55
        m15t.SPEC_LO, m15t.SPEC_HI = old_m15_lo, old_m15_hi


def apply_layer3(final_acc, top_pct=DEFAULT_TOP_PCT):
    threshold = float(final_acc["Bias_5"].quantile(1 - top_pct / 100.0))
    picked = final_acc[final_acc["Bias_5"] >= threshold].reset_index(drop=True)
    return threshold, picked


def annotate_trigger_type(final_acc):
    out = final_acc.copy()
    out["date"] = pd.to_datetime(out["date"])
    out["entry_time"] = pd.to_datetime(out["entry_time"])
    out["trigger"] = np.where(out["entry_time"] < out["date"], "M15 SLOT1", "M30 CLOSE")
    return out


def apply_m30_close_proxy(final_acc, df):
    if len(final_acc) == 0:
        return final_acc.copy()

    out = annotate_trigger_type(final_acc)
    price_map = (
        df[["date", "close"]]
        .copy()
        .assign(date=lambda x: pd.to_datetime(x["date"]))
        .drop_duplicates(subset=["date"], keep="last")
        .set_index("date")["close"]
        .astype(float)
    )
    mask = out["trigger"] == "M30 CLOSE"
    if not mask.any():
        return out.drop(columns=["trigger"])

    close_vals = out.loc[mask, "date"].map(price_map)
    valid_idx = close_vals[close_vals.notna()].index
    if len(valid_idx) == 0:
        return out.drop(columns=["trigger"])

    out.loc[valid_idx, "entry"] = close_vals.loc[valid_idx].astype(float).values
    out.loc[valid_idx, "entry_time"] = out.loc[valid_idx, "date"].values
    out.loc[valid_idx, "sd"] = (
        out.loc[valid_idx, "entry"].astype(float) - out.loc[valid_idx, "stop"].astype(float)
    ).abs().values
    return out.drop(columns=["trigger"])


def _build_h2_bias5_lookup(h2):
    out = h2.copy()
    out["date"] = pd.to_datetime(out["date"])
    out = out[(out["SMA_5"].notna()) & (out["SMA_5"] != 0)].reset_index(drop=True)
    out["Bias_5_calc"] = ((out["close"] - out["SMA_5"]).abs() / out["SMA_5"] * 100.0).astype(float)
    return out


def _rolling_top_threshold(values, top_pct):
    if len(values) < 10:
        return np.nan
    arr = np.sort(np.asarray(values, dtype=float))
    idx = int(np.floor(len(arr) * (1.0 - top_pct / 100.0)))
    idx = max(0, min(idx, len(arr) - 1))
    return float(arr[idx])


def apply_layer3_ea_executable(final_acc, h2, top_pct=DEFAULT_TOP_PCT, lookback=EA_DIAG_H2_LOOKBACK):
    if len(final_acc) == 0:
        out = final_acc.copy()
        out["layer3_eval_time"] = pd.NaT
        out["Bias_5_ea"] = np.nan
        out["layer3_threshold_ea"] = np.nan
        out["layer3_pass_ea"] = False
        return np.nan, out

    h2_bias = _build_h2_bias5_lookup(h2)
    h2_times = pd.to_datetime(h2_bias["date"]).tolist()
    h2_bias_values = h2_bias["Bias_5_calc"].tolist()

    out = annotate_trigger_type(final_acc)
    eval_times = []
    bias5_vals = []
    threshold_vals = []
    pass_flags = []

    for _, row in out.iterrows():
        # v3.36: Layer3 eval_time 统一 = date + 30min (bar close 判定时刻)。
        # EA 的所有信号 (含旧版 M15 SLOT1) 都在 bar close 的 new_m30_bar tick 判定
        # Layer3, 用当时的 H2 数据。旧版 M15 SLOT1 不加 shift → bias5 取错时刻
        # (例: 2025-10-07 13:30 post_n5, EA 用 14:00 H2 数据 PASS, Python 用 13:30 FAIL)。
        eval_time = pd.Timestamp(row["date"]) + pd.Timedelta(minutes=EA_DIAG_M30_LAYER3_SHIFT_MINUTES)
        eval_times.append(eval_time)

        idx = bisect.bisect_right(h2_times, eval_time) - 1
        if idx < 0:
            bias5_vals.append(np.nan)
            threshold_vals.append(np.nan)
            pass_flags.append(False)
            continue

        start = max(0, idx - lookback)
        # v3.36: 阈值样本不含当前 H2 bar — EA IsBias5TopPct 用 CopyClose(H2, 1, n)
        # (shift 1..500, 不含刚收盘的当前 bar); 旧版含当前 bar → 阈值差 1 个样本 → 边界翻转
        hist = h2_bias_values[start:idx]
        current_bias5 = float(h2_bias_values[idx])
        threshold = _rolling_top_threshold(hist, top_pct)
        bias5_vals.append(current_bias5)
        threshold_vals.append(threshold)
        if pd.isna(threshold):
            pass_flags.append(True)
        else:
            pass_flags.append(current_bias5 >= threshold)

    out["layer3_eval_time"] = eval_times
    out["Bias_5_ea"] = bias5_vals
    out["layer3_threshold_ea"] = threshold_vals
    out["layer3_pass_ea"] = pass_flags
    picked = out[out["layer3_pass_ea"]].reset_index(drop=True)
    threshold_series = out["layer3_threshold_ea"].dropna()
    threshold = float(threshold_series.median()) if not threshold_series.empty else np.nan
    return threshold, picked


def summarize_strategy(
    spec_lo=DEFAULT_SPEC_LO,
    spec_hi=DEFAULT_SPEC_HI,
    top_pct=DEFAULT_TOP_PCT,
    bias55_threshold=DEFAULT_BIAS55_THRESHOLD,
    stage1_r=DEFAULT_STAGE1_R,
    stage2_trail_r=DEFAULT_STAGE2_TRAIL_R,
    stage2_force_r=DEFAULT_STAGE2_FORCE_R,
    h2_shift_hours=0,
    ea_executable_diag=False,
):
    df, final_acc = build_final_accepted(
        spec_lo=spec_lo,
        spec_hi=spec_hi,
        bias55_threshold=bias55_threshold,
        h2_shift_hours=h2_shift_hours,
        ea_executable_diag=ea_executable_diag,
    )
    h2 = load_h2_context(extra_shift_hours=h2_shift_hours)
    if ea_executable_diag:
        threshold, picked = apply_layer3_ea_executable(final_acc, h2, top_pct=top_pct)
    else:
        threshold, picked = apply_layer3(final_acc, top_pct=top_pct)
    out = s12.summarize_variant(df, picked, stage1_r, stage2_trail_r, stage2_force_r)
    total_m = s12.metric(out["total_points"].values)
    train_m, test_m = s12.split_metrics(out)
    out["year"] = pd.to_datetime(out["date"]).dt.year
    return {
        "df": df,
        "h2": h2,
        "accepted": final_acc,
        "threshold": threshold,
        "picked": picked,
        "trades": out,
        "total": total_m,
        "train": train_m,
        "test": test_m,
        "ea_executable_diag": ea_executable_diag,
    }
