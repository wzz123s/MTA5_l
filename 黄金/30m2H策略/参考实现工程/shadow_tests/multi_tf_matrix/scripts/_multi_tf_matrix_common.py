# -*- coding: utf-8 -*-
"""Shared helpers for multi-timeframe shadow research."""
import bisect
import os
import re
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from processing.smma import calc_smma
from scripts._current_baseline import summarize_strategy


SPLIT_DATE = pd.Timestamp("2023-01-01")
TIMEFRAME_MATRIX = [
    {"name": "H1_M30_H4", "frames": ["30M", "1H", "4H"]},
    {"name": "H2_H6_H8", "frames": ["2H", "6H", "8H"]},
    {"name": "H3_H10_H12", "frames": ["3H", "10H", "12H"]},
    {"name": "H4_H16", "frames": ["4H", "16H"]},
    {"name": "H5_H20", "frames": ["5H", "20H"]},
    {"name": "H6_H24", "frames": ["6H", "24H"]},
]


def metric(values):
    vals = np.asarray(values, dtype=float)
    if len(vals) == 0:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "ev": 0.0, "pnl": 0.0, "ml": 0}
    wins = vals > 0
    gross_win = vals[wins].sum()
    gross_loss = abs(vals[~wins].sum())
    pf = gross_win / gross_loss if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0)
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
        "n": int(len(vals)),
        "wr": float(wins.mean() * 100.0),
        "pf": float(pf),
        "ev": float(pnl / len(vals)),
        "pnl": float(pnl),
        "ml": int(ml),
    }


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def tf_label_to_hours(label):
    if label == "30M":
        return 0.5
    if label.endswith("H"):
        return int(label[:-1])
    raise ValueError(f"Unsupported timeframe label: {label}")


def tf_slug(label):
    return label.lower()


def load_m30_raw(path="base_data/XAUUSDm30.csv", add_hours=2):
    df = pd.read_csv(path, encoding="gbk")
    df.columns = [
        "date", "open", "high", "low", "close", "volume",
        "spread", "real_volume", "symbol", "time_diff",
    ]
    df["date"] = pd.to_datetime(df["date"]) + pd.Timedelta(hours=add_hours)
    return df.sort_values("date").reset_index(drop=True)


def build_tf(raw_m30, label):
    if label == "30M":
        tf = raw_m30.copy()
    else:
        hours = tf_label_to_hours(label)
        tf = (
            raw_m30.set_index("date")
            .resample(f"{int(hours)}h", label="right", closed="right")
            .agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
                "spread": "mean",
                "real_volume": "sum",
                "symbol": "last",
                "time_diff": "last",
            })
            .dropna(subset=["open", "high", "low", "close"])
            .reset_index()
        )
    tf["SMA_5"] = calc_smma(tf["close"], 5).values
    tf["SMA_13"] = calc_smma(tf["close"], 13).values
    tf["SMA_55"] = calc_smma(tf["close"], 55).values
    tf["dir"] = np.where(tf["SMA_5"] > tf["SMA_13"], 1, -1)
    tf.loc[tf["SMA_5"].isna() | tf["SMA_13"].isna(), "dir"] = 0
    tf["bias5"] = np.where(
        tf["SMA_5"].notna() & (tf["SMA_5"] != 0),
        (tf["close"] - tf["SMA_5"]).abs() / tf["SMA_5"] * 100,
        np.nan,
    )
    tf["bias55"] = np.where(
        tf["SMA_55"].notna() & (tf["SMA_55"] != 0),
        (tf["close"] - tf["SMA_55"]).abs() / tf["SMA_55"] * 100,
        np.nan,
    )
    tf["close_side"] = np.where(
        tf["SMA_13"].isna(),
        0,
        np.where(tf["close"] > tf["SMA_13"], 1, np.where(tf["close"] < tf["SMA_13"], -1, 0)),
    )
    return tf


def add_context(trades, tf, prefix):
    out = trades.copy()
    times = pd.to_datetime(tf["date"]).values.astype("datetime64[ns]")
    trade_times = pd.to_datetime(out["date"]).values.astype("datetime64[ns]")

    cols = {
        f"{prefix}_idx": [],
        f"{prefix}_date": [],
        f"{prefix}_dir": [],
        f"{prefix}_close_side": [],
        f"{prefix}_bias5": [],
        f"{prefix}_bias55": [],
        f"{prefix}_dir_prev1": [],
        f"{prefix}_dir_prev2": [],
        f"{prefix}_high": [],
        f"{prefix}_low": [],
        f"{prefix}_sma13": [],
    }
    for t in trade_times:
        idx = bisect.bisect_right(times, t) - 1
        cols[f"{prefix}_idx"].append(idx)
        if idx < 0:
            cols[f"{prefix}_date"].append(pd.NaT)
            cols[f"{prefix}_dir"].append(0)
            cols[f"{prefix}_close_side"].append(0)
            cols[f"{prefix}_bias5"].append(np.nan)
            cols[f"{prefix}_bias55"].append(np.nan)
            cols[f"{prefix}_dir_prev1"].append(0)
            cols[f"{prefix}_dir_prev2"].append(0)
            cols[f"{prefix}_high"].append(np.nan)
            cols[f"{prefix}_low"].append(np.nan)
            cols[f"{prefix}_sma13"].append(np.nan)
            continue
        row = tf.iloc[idx]
        cols[f"{prefix}_date"].append(row["date"])
        cols[f"{prefix}_dir"].append(int(row["dir"]))
        cols[f"{prefix}_close_side"].append(int(row["close_side"]))
        cols[f"{prefix}_bias5"].append(float(row["bias5"]) if not pd.isna(row["bias5"]) else np.nan)
        cols[f"{prefix}_bias55"].append(float(row["bias55"]) if not pd.isna(row["bias55"]) else np.nan)
        cols[f"{prefix}_dir_prev1"].append(int(tf.iloc[idx - 1]["dir"]) if idx - 1 >= 0 else 0)
        cols[f"{prefix}_dir_prev2"].append(int(tf.iloc[idx - 2]["dir"]) if idx - 2 >= 0 else 0)
        cols[f"{prefix}_high"].append(float(row["high"]) if not pd.isna(row["high"]) else np.nan)
        cols[f"{prefix}_low"].append(float(row["low"]) if not pd.isna(row["low"]) else np.nan)
        cols[f"{prefix}_sma13"].append(float(row["SMA_13"]) if not pd.isna(row["SMA_13"]) else np.nan)
    for key, val in cols.items():
        out[key] = val
    return out


def attach_all_context(trades, frames):
    raw_m30 = load_m30_raw()
    out = trades.copy()
    for label in frames:
        out = add_context(out, build_tf(raw_m30, label), tf_slug(label))
    return out


def load_mainline_bundle():
    strategy = summarize_strategy()
    return _bundle_from_strategy(strategy)


def load_mainline_bundle_for_spec(spec_lo=5, spec_hi=35, top_pct=34, bias55_threshold=3.0):
    strategy = summarize_strategy(
        spec_lo=spec_lo,
        spec_hi=spec_hi,
        top_pct=top_pct,
        bias55_threshold=bias55_threshold,
    )
    return _bundle_from_strategy(strategy)


def _bundle_from_strategy(strategy):
    signals = strategy["picked"].copy().sort_values("date").reset_index(drop=True)
    trades = strategy["trades"].copy().sort_values("date").reset_index(drop=True)
    merged = signals.merge(
        trades[["date", "mode", "dir", "total_points", "stage1_pnl", "stage2_pnl", "stage3_pnl"]],
        on=["date", "mode", "dir"],
        how="left",
    )
    merged["pnl"] = merged["total_points"].astype(float)
    merged["year"] = pd.to_datetime(merged["date"]).dt.year
    return {
        "df": strategy["df"],
        "signals": merged,
        "trades": trades,
        "strategy": strategy,
    }


def load_mainline_trades():
    return load_mainline_bundle()["signals"]


def trade_sign(tdf):
    return np.where(tdf["dir"] == "L", 1, -1)


def extract_focus_label(variant_name, combo_name):
    prefix = f"{combo_name}__"
    key = variant_name[len(prefix):] if variant_name.startswith(prefix) else variant_name
    if key == "baseline":
        parts = combo_name.split("_")
        if len(parts) >= 2 and parts[1].upper() == "M30":
            return "30m"
        return parts[0].lower()
    m = re.match(r"([a-z0-9]+)_(.+)", key)
    if m:
        return m.group(1)
    parts = combo_name.split("_")
    if len(parts) >= 2 and parts[1].upper() == "M30":
        return "30m"
    return parts[0].lower()


def recompute_focus_sd(frame, focus_label):
    out = frame.copy()
    prefix = focus_label.lower()
    high_col = f"{prefix}_high"
    low_col = f"{prefix}_low"
    sma13_col = f"{prefix}_sma13"
    idx_col = f"{prefix}_idx"

    stops = []
    sds = []
    for _, row in out.iterrows():
        entry = float(row["entry"])
        if idx_col not in out.columns or int(row[idx_col]) < 0:
            stops.append(np.nan)
            sds.append(np.nan)
            continue
        if row["dir"] == "L":
            candidates = [row.get(low_col, np.nan), row.get(sma13_col, np.nan)]
            candidates = [float(x) for x in candidates if not pd.isna(x) and float(x) < entry]
            stop = min(candidates) if candidates else np.nan
        else:
            candidates = [row.get(high_col, np.nan), row.get(sma13_col, np.nan)]
            candidates = [float(x) for x in candidates if not pd.isna(x) and float(x) > entry]
            stop = max(candidates) if candidates else np.nan
        sd = abs(entry - stop) if not pd.isna(stop) else np.nan
        stops.append(stop)
        sds.append(sd)
    out["focus_stop"] = stops
    out["focus_sd"] = sds
    return out


def split_metrics(points, dates):
    ts = pd.to_datetime(dates)
    train = metric(points[ts < SPLIT_DATE])
    test = metric(points[ts >= SPLIT_DATE])
    return train, test


def build_combo_variant_frames(combo, ctx):
    sign = trade_sign(ctx)
    variants = []
    masks_for_stack = []

    variants.append({
        "combo": combo["name"],
        "variant": f"{combo['name']}__baseline",
        "desc": f"{'/'.join(combo['frames'])} 覆盖期基线",
        "frame": ctx.copy(),
    })

    for label in combo["frames"]:
        prefix = tf_slug(label)
        available = ctx[f"{prefix}_idx"] >= 0
        dir_align = available & (ctx[f"{prefix}_dir"].values == sign)
        recent2_any = available & (
            (ctx[f"{prefix}_dir"].values == sign)
            | (ctx[f"{prefix}_dir_prev1"].values == sign)
        )
        close_side = available & (ctx[f"{prefix}_close_side"].values == sign)
        bias_thr = ctx.loc[available, f"{prefix}_bias5"].quantile(0.70) if available.any() else np.nan
        bias5_top30 = available & (ctx[f"{prefix}_bias5"] >= bias_thr) if available.any() else available

        variants.extend([
            {"combo": combo["name"], "variant": f"{combo['name']}__{prefix}_dir_align", "desc": f"{label} 方向同向", "frame": ctx[dir_align].copy()},
            {"combo": combo["name"], "variant": f"{combo['name']}__{prefix}_recent2_any", "desc": f"{label} 最近2根至少1根同向", "frame": ctx[recent2_any].copy()},
            {"combo": combo["name"], "variant": f"{combo['name']}__{prefix}_close_side", "desc": f"{label} close位于SMA13交易方向一侧", "frame": ctx[close_side].copy()},
            {"combo": combo["name"], "variant": f"{combo['name']}__{prefix}_bias5_top30", "desc": f"{label} Bias_5 top30%", "frame": ctx[bias5_top30].copy()},
        ])
        masks_for_stack.append((label, dir_align, recent2_any, close_side, bias5_top30))

    all_dir = np.logical_and.reduce([mask[1] for mask in masks_for_stack])
    all_recent = np.logical_and.reduce([mask[2] for mask in masks_for_stack])
    variants.append({"combo": combo["name"], "variant": f"{combo['name']}__all_dir_align", "desc": "全组合方向同向", "frame": ctx[all_dir].copy()})
    variants.append({"combo": combo["name"], "variant": f"{combo['name']}__all_recent2_any", "desc": "全组合最近2根至少1根同向", "frame": ctx[all_recent].copy()})

    if len(masks_for_stack) >= 2:
        first = masks_for_stack[0]
        last = masks_for_stack[-1]
        core_mask = first[3] & last[4]
        core_desc = f"{first[0]} close同侧 + {last[0]} Bias_5 top30%"
        if len(masks_for_stack) >= 3:
            mid = masks_for_stack[1]
            core_mask = core_mask & mid[1]
            core_desc = f"{first[0]} close同侧 + {mid[0]} 方向同向 + {last[0]} Bias_5 top30%"
        variants.append({"combo": combo["name"], "variant": f"{combo['name']}__stack_core", "desc": core_desc, "frame": ctx[core_mask].copy()})
    return variants


def summarize_variant_item(item):
    frame = item["frame"].copy().sort_values("date").reset_index(drop=True)
    m = metric(frame["pnl"].astype(float).values)
    train_m, test_m = split_metrics(frame["pnl"].astype(float).values, pd.to_datetime(frame["date"]))
    return {
        "combo": item["combo"],
        "variant": item["variant"],
        "desc": item["desc"],
        "n": m["n"],
        "wr": m["wr"],
        "pf": m["pf"],
        "ev": m["ev"],
        "pnl": m["pnl"],
        "max_loss_streak": m["ml"],
        "train_n": train_m["n"],
        "test_n": test_m["n"],
        "test_pf": test_m["pf"],
        "test_ev": test_m["ev"],
    }


def choose_primary_candidates(summary_df):
    winners = []
    for combo, frame in summary_df.groupby("combo"):
        scoped = frame.copy()
        scoped["is_stack"] = scoped["variant"].str.endswith("__stack_core")
        scoped["sample_ok"] = scoped["n"] >= 50
        if scoped["sample_ok"].any():
            scoped = scoped[scoped["sample_ok"]].copy()
        scoped["score"] = (
            scoped["pf"] * 10
            + scoped["test_pf"].clip(upper=50) * 2
            + scoped["ev"] * 0.02
            - scoped["is_stack"].astype(int) * 100
        )
        winners.append(
            scoped.sort_values(["score", "test_ev", "n"], ascending=[False, False, False]).head(1)
        )
    return pd.concat(winners, ignore_index=True).reset_index(drop=True)
