# -*- coding: utf-8 -*-
"""Compare Stage 3 exit rules on the current 30m x 2H candidate signals.

Entry set:
  - Layer 1: |H2 Bias_55| > 3.0%
  - Layer 2: pre_cross(gap<=0.300%) + cross + post_n(2-6)
  - Layer 3: Bias_5 top 30%
  - Layer 4: M15 close-side filter
  - stop spec: [5, 35] pt

Stage 1/2 stay fixed:
  - Stage 1: 1.2R target, original SL.
  - Stage 2: after 2R trail by M30 SMA13, 3R force close, original/trailing SL.

Only Stage 3 changes:
  - m30_raw_cross: lower-timeframe raw SMA5/13 opposite cross.
  - m30_merged_cross: lower-timeframe merged/confirmed opposite cross.
  - h2_raw_cross: H2 raw SMA5/13 opposite cross.
  - h2_merged_flip: H2 merged direction reversal.
"""
import os
import sys
import bisect

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from processing.prepare import prepare
import _pre_cross_range_test as pct
from _h2_context import load_h2_context


PRE_GAP = 0.003
STAGE1_R = 1.2
STAGE2_TRAIL_R = 2.0
STAGE2_FORCE_R = 3.0
LOTS_PER_STAGE = 0.02
PT_VALUE_PER_LOT = 10.0


def metric(values):
    vals = np.asarray(values, dtype=float)
    if len(vals) == 0:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "ev": 0.0, "pnl": 0.0, "ml": 0}
    wins = vals > 0
    gross_win = vals[wins].sum()
    gross_loss = abs(vals[~wins].sum())
    pf = gross_win / gross_loss if gross_loss > 0 else 0.0
    cl = 0
    ml = 0
    for w in wins:
        if w:
            cl = 0
        else:
            cl += 1
            ml = max(ml, cl)
    pnl = gross_win - gross_loss
    return {
        "n": len(vals),
        "wr": wins.mean() * 100.0,
        "pf": pf,
        "ev": pnl / len(vals),
        "pnl": pnl,
        "ml": ml,
    }


def fmt(m):
    return (
        f"{m['n']:>4}  WR {m['wr']:>5.1f}%  PF {m['pf']:>5.2f}  "
        f"EV {m['ev']:>+7.2f}pt  PnL {m['pnl']:>+8.0f}pt  MaxCL {m['ml']:>2}"
    )


def first_opposite_idx(direction, start_i, is_long):
    target = "bad" if is_long else "good"
    for i in range(start_i + 1, len(direction)):
        if direction[i] == target:
            return i
    return len(direction) - 1


def first_h2_opposite_idx(h2_dir, h2_times, entry_time, is_long):
    target = "bad" if is_long else "good"
    start = bisect.bisect_right(h2_times, np.datetime64(entry_time))
    for i in range(start, len(h2_dir)):
        if h2_dir[i] == target:
            return i
    return len(h2_dir) - 1


def sl_hit_before(df, start_i, end_i, is_long, stop):
    if end_i <= start_i:
        return None
    seg = df.iloc[start_i + 1 : end_i + 1]
    if len(seg) == 0:
        return None
    hits = seg["low"] <= stop if is_long else seg["high"] >= stop
    if hits.any():
        hit_pos = hits.to_numpy().argmax()
        row = seg.iloc[hit_pos]
        return {"price": stop, "time": row["date"], "idx": int(seg.index[hit_pos])}
    return None


def sl_hit_until_time(df, start_i, exit_time, is_long, stop):
    seg = df[(df.index > start_i) & (df["date"] <= exit_time)]
    if len(seg) == 0:
        return None
    hits = seg["low"] <= stop if is_long else seg["high"] >= stop
    if hits.any():
        hit_pos = hits.to_numpy().argmax()
        row = seg.iloc[hit_pos]
        return {"price": stop, "time": row["date"], "idx": int(seg.index[hit_pos])}
    return None


def stage1(df, trade):
    i = int(trade["i"])
    is_long = trade["dir"] == "L"
    entry = float(trade["entry"])
    stop = float(trade["stop"])
    r = abs(entry - stop)
    target = entry + STAGE1_R * r if is_long else entry - STAGE1_R * r

    for j in range(i + 1, len(df)):
        row = df.iloc[j]
        if is_long and row["low"] <= stop:
            return -r, "SL hit", row["date"]
        if (not is_long) and row["high"] >= stop:
            return -r, "SL hit", row["date"]
        if is_long and row["high"] >= target:
            return STAGE1_R * r, "1.2R TP", row["date"]
        if (not is_long) and row["low"] <= target:
            return STAGE1_R * r, "1.2R TP", row["date"]
    return 0.0, "data end", df.iloc[-1]["date"]


def stage2(df, trade):
    i = int(trade["i"])
    is_long = trade["dir"] == "L"
    entry = float(trade["entry"])
    stop = float(trade["stop"])
    r = abs(entry - stop)
    trail_start = entry + STAGE2_TRAIL_R * r if is_long else entry - STAGE2_TRAIL_R * r
    force = entry + STAGE2_FORCE_R * r if is_long else entry - STAGE2_FORCE_R * r
    trail_sl = stop
    m30_end = first_opposite_idx(df["方向_合并后"].values, i, is_long)

    for j in range(i + 1, m30_end + 1):
        row = df.iloc[j]
        if is_long and row["high"] >= force:
            return STAGE2_FORCE_R * r, "3R forced", row["date"]
        if (not is_long) and row["low"] <= force:
            return STAGE2_FORCE_R * r, "3R forced", row["date"]
        if is_long and row["low"] <= trail_sl:
            return (trail_sl - entry), "SL hit", row["date"]
        if (not is_long) and row["high"] >= trail_sl:
            return (entry - trail_sl), "SL hit", row["date"]
        if is_long and row["high"] >= trail_start and row["SMA_13"] > trail_sl:
            trail_sl = row["SMA_13"]
        if (not is_long) and row["low"] <= trail_start and (row["SMA_13"] < trail_sl or trail_sl == stop):
            trail_sl = row["SMA_13"]

    exit_price = df.iloc[m30_end]["close"]
    pnl = exit_price - entry if is_long else entry - exit_price
    return pnl, "M30 merged cross", df.iloc[m30_end]["date"]


def stage3(df, h2, trade, variant):
    i = int(trade["i"])
    is_long = trade["dir"] == "L"
    entry = float(trade["entry"])
    stop = float(trade["stop"])

    if variant == "m30_raw_cross":
        end_i = first_opposite_idx(df["方向"].values, i, is_long)
        sl = sl_hit_before(df, i, end_i, is_long, stop)
        if sl is not None:
            return -abs(entry - stop), "SL hit", sl["time"]
        exit_price = df.iloc[end_i]["close"]
        return (exit_price - entry if is_long else entry - exit_price), "M30 raw cross", df.iloc[end_i]["date"]

    if variant == "m30_merged_cross":
        end_i = first_opposite_idx(df["方向_合并后"].values, i, is_long)
        sl = sl_hit_before(df, i, end_i, is_long, stop)
        if sl is not None:
            return -abs(entry - stop), "SL hit", sl["time"]
        exit_price = df.iloc[end_i]["close"]
        return (exit_price - entry if is_long else entry - exit_price), "M30 merged cross", df.iloc[end_i]["date"]

    entry_time = trade["date"]
    h2_times = h2["date"].values.astype("datetime64[ns]")
    if variant == "h2_raw_cross":
        h2_i = first_h2_opposite_idx(h2["direction"].values, h2_times, entry_time, is_long)
        label = "H2 raw cross"
    elif variant == "h2_merged_flip":
        h2_i = first_h2_opposite_idx(h2["direction_merged"].values, h2_times, entry_time, is_long)
        label = "H2 merged flip"
    else:
        raise ValueError(variant)

    exit_time = h2.iloc[h2_i]["date"]
    sl = sl_hit_until_time(df, i, exit_time, is_long, stop)
    if sl is not None:
        return -abs(entry - stop), "SL hit", sl["time"]
    exit_price = h2.iloc[h2_i]["close"]
    return (exit_price - entry if is_long else entry - exit_price), label, exit_time


def build_signals(apply_m15=True):
    df, _ = prepare("base_data/XAUUSDm30.csv", min_len=8)
    h2 = load_h2_context()

    layer1_pass_set, factor_map = pct.precompute_h2(h2, df["date"].values)
    pre = pct.build_pre_cross(df, PRE_GAP, layer1_pass_set, factor_map)
    cross = pct.build_cross(df, layer1_pass_set, factor_map)
    post = pct.build_post_n(df, layer1_pass_set, factor_map)
    all_modes = pct.dedupe(pre + cross + post)
    top = pct.layer3_top(all_modes).sort_values("date").reset_index(drop=True)
    if apply_m15:
        top = pct.apply_m15_close_side(top)
    return df, h2, top


def summarize_variant(df, h2, signals, variant):
    rows = []
    for _, tr in signals.iterrows():
        s1_pnl, s1_exit, _ = stage1(df, tr)
        s2_pnl, s2_exit, _ = stage2(df, tr)
        s3_pnl, s3_exit, s3_time = stage3(df, h2, tr, variant)
        total_points = s1_pnl + s2_pnl + s3_pnl
        rows.append({
            "date": tr["date"],
            "mode": tr["mode"],
            "dir": tr["dir"],
            "stage1_pnl": s1_pnl,
            "stage2_pnl": s2_pnl,
            "stage3_pnl": s3_pnl,
            "total_points": total_points,
            "total_$": total_points * LOTS_PER_STAGE * PT_VALUE_PER_LOT,
            "stage1_exit": s1_exit,
            "stage2_exit": s2_exit,
            "stage3_exit": s3_exit,
            "stage3_time": s3_time,
        })
    return pd.DataFrame(rows)


def main():
    print("=" * 110)
    print("Stage 3 exit comparison on current main candidate with M15 close-side")
    print("=" * 110)
    df, h2, signals = build_signals()
    print(f"Signals: {len(signals)}  (pre_gap <= {PRE_GAP*100:.3f}%, Layer3 Bias_5 top30, M15 close-side)")
    print()

    variants = [
        "m30_raw_cross",
        "m30_merged_cross",
        "h2_raw_cross",
        "h2_merged_flip",
    ]

    print("Overall 3-stage result (equal 0.02 lots/stage; metrics in summed stage points):")
    print(f"{'variant':<18} {'total':<58} {'stage3 only':<58} {'$ pnl':>8}")
    print("-" * 150)
    results = {}
    for variant in variants:
        out = summarize_variant(df, h2, signals, variant)
        results[variant] = out
        total_m = metric(out["total_points"].values)
        s3_m = metric(out["stage3_pnl"].values)
        print(f"{variant:<18} {fmt(total_m):<58} {fmt(s3_m):<58} {out['total_$'].sum():>+8.0f}")

    print()
    print("Stage 3 exit reason counts:")
    for variant, out in results.items():
        counts = out["stage3_exit"].value_counts().to_dict()
        print(f"  {variant:<18} {counts}")

    print()
    print("Stage 3 mode split for best total-PF variant:")
    best = max(results.items(), key=lambda kv: (metric(kv[1]["total_points"].values)["pf"], metric(kv[1]["total_points"].values)["ev"]))
    best_name, best_df = best
    print(f"  best = {best_name}")
    for mode, group in best_df.groupby("mode"):
        print(f"  {mode:<12} total {fmt(metric(group['total_points'].values))} | s3 {fmt(metric(group['stage3_pnl'].values))}")


if __name__ == "__main__":
    main()
