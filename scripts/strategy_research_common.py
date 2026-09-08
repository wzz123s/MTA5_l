# -*- coding: utf-8 -*-
"""Shared research helpers for strategy-owned MT5 data."""
from __future__ import annotations

import bisect
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
REF_ROOT = ROOT / "黄金" / "30m2H策略" / "参考实现工程"
if str(REF_ROOT) not in sys.path:
    sys.path.insert(0, str(REF_ROOT))

from processing.smma import calc_smma  # type: ignore  # noqa: E402


def tf_label_to_hours(label: str) -> float:
    if label == "30M":
        return 0.5
    if label.endswith("H"):
        return float(int(label[:-1]))
    raise ValueError(f"Unsupported timeframe label: {label}")


def tf_slug(label: str) -> str:
    return label.lower()


def _safe_pct(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return np.where(
        denominator.notna() & denominator.ne(0),
        numerator / denominator * 100.0,
        np.nan,
    )


def build_tf(raw_m30: pd.DataFrame, label: str) -> pd.DataFrame:
    """Build timeframe bars with non-trade-specific moving-average deviations."""
    if label == "30M":
        tf = raw_m30.copy()
    else:
        hours = tf_label_to_hours(label)
        tf = (
            raw_m30.set_index("date")
            .resample(f"{int(hours)}h", label="right", closed="right")
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                    "spread": "mean",
                    "real_volume": "sum",
                    "symbol": "last",
                    "time_diff": "last",
                }
            )
            .dropna(subset=["open", "high", "low", "close"])
            .reset_index()
        )

    tf["SMA_5"] = calc_smma(tf["close"], 5).values
    tf["SMA_13"] = calc_smma(tf["close"], 13).values
    tf["SMA_55"] = calc_smma(tf["close"], 55).values
    tf["sma5"] = tf["SMA_5"]
    tf["sma13"] = tf["SMA_13"]
    tf["sma55"] = tf["SMA_55"]
    tf["dir"] = np.where(tf["SMA_5"] > tf["SMA_13"], 1, -1)
    tf.loc[tf["SMA_5"].isna() | tf["SMA_13"].isna(), "dir"] = 0
    tf["close_side"] = np.where(
        tf["SMA_13"].isna(),
        0,
        np.where(tf["close"] > tf["SMA_13"], 1, np.where(tf["close"] < tf["SMA_13"], -1, 0)),
    )

    for period, sma_col in [(5, "SMA_5"), (13, "SMA_13"), (55, "SMA_55")]:
        raw_col = f"bias{period}_raw"
        pct_col = f"bias{period}_raw_pct"
        abs_col = f"bias{period}_abs_pct"
        tf[raw_col] = tf["close"] - tf[sma_col]
        tf[pct_col] = _safe_pct(tf[raw_col], tf[sma_col])
        tf[abs_col] = pd.Series(tf[pct_col]).abs()
        # Compatibility alias. Trade-specific context rewrites prefix_biasN
        # to signed pct, so formal signal gates never consume this bar-level
        # non-trade-specific alias directly.
        tf[f"bias{period}"] = tf[pct_col]
    return tf


def _trade_sign(value: object) -> int:
    text = str(value).strip().upper()
    if text in {"L", "LONG", "BUY", "1"}:
        return 1
    if text in {"S", "SHORT", "SELL", "-1"}:
        return -1
    return 0


def _append_missing_context(cols: dict[str, list], prefix: str) -> None:
    cols[f"{prefix}_idx"].append(-1)
    cols[f"{prefix}_date"].append(pd.NaT)
    cols[f"{prefix}_dir"].append(0)
    cols[f"{prefix}_close_side"].append(0)
    cols[f"{prefix}_dir_prev1"].append(0)
    cols[f"{prefix}_dir_prev2"].append(0)
    for name in ["open", "high", "low", "close", "sma5", "sma13", "sma55"]:
        cols[f"{prefix}_{name}"].append(np.nan)
    for period in (5, 13, 55):
        for suffix in ["", "_signed", "_signed_pct", "_raw", "_raw_pct", "_abs_pct"]:
            cols[f"{prefix}_bias{period}{suffix}"].append(np.nan)


def add_context(trades: pd.DataFrame, tf: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Attach timeframe context and trade-direction signed bias fields."""
    out = trades.copy()
    times = pd.to_datetime(tf["date"]).values.astype("datetime64[ns]")
    trade_times = pd.to_datetime(out["date"]).values.astype("datetime64[ns]")
    trade_dirs = out["dir"].tolist()

    cols: dict[str, list] = {
        f"{prefix}_idx": [],
        f"{prefix}_date": [],
        f"{prefix}_dir": [],
        f"{prefix}_close_side": [],
        f"{prefix}_dir_prev1": [],
        f"{prefix}_dir_prev2": [],
    }
    for name in ["open", "high", "low", "close", "sma5", "sma13", "sma55"]:
        cols[f"{prefix}_{name}"] = []
    for period in (5, 13, 55):
        for suffix in ["", "_signed", "_signed_pct", "_raw", "_raw_pct", "_abs_pct"]:
            cols[f"{prefix}_bias{period}{suffix}"] = []

    for pos, t in enumerate(trade_times):
        idx = bisect.bisect_right(times, t) - 1
        if idx < 0:
            _append_missing_context(cols, prefix)
            continue

        row = tf.iloc[idx]
        sign = _trade_sign(trade_dirs[pos])
        cols[f"{prefix}_idx"].append(idx)
        cols[f"{prefix}_date"].append(row["date"])
        cols[f"{prefix}_dir"].append(int(row["dir"]))
        cols[f"{prefix}_close_side"].append(int(row["close_side"]))
        cols[f"{prefix}_dir_prev1"].append(int(tf.iloc[idx - 1]["dir"]) if idx - 1 >= 0 else 0)
        cols[f"{prefix}_dir_prev2"].append(int(tf.iloc[idx - 2]["dir"]) if idx - 2 >= 0 else 0)
        for name, source in [
            ("open", "open"),
            ("high", "high"),
            ("low", "low"),
            ("close", "close"),
            ("sma5", "SMA_5"),
            ("sma13", "SMA_13"),
            ("sma55", "SMA_55"),
        ]:
            cols[f"{prefix}_{name}"].append(float(row[source]) if not pd.isna(row[source]) else np.nan)

        for period in (5, 13, 55):
            raw = float(row[f"bias{period}_raw"]) if not pd.isna(row[f"bias{period}_raw"]) else np.nan
            raw_pct = float(row[f"bias{period}_raw_pct"]) if not pd.isna(row[f"bias{period}_raw_pct"]) else np.nan
            signed = raw * sign if sign else np.nan
            signed_pct = raw_pct * sign if sign else np.nan
            cols[f"{prefix}_bias{period}"].append(signed_pct)
            cols[f"{prefix}_bias{period}_signed"].append(signed)
            cols[f"{prefix}_bias{period}_signed_pct"].append(signed_pct)
            cols[f"{prefix}_bias{period}_raw"].append(raw)
            cols[f"{prefix}_bias{period}_raw_pct"].append(raw_pct)
            cols[f"{prefix}_bias{period}_abs_pct"].append(abs(raw_pct) if not pd.isna(raw_pct) else np.nan)

    for key, values in cols.items():
        out[key] = values
    return out


def recompute_stop_distance(frame: pd.DataFrame, focus_label: str | None = None) -> pd.DataFrame:
    """Compatibility helper: preserve formal StopSpec on stop_distance."""
    out = frame.copy()
    if "structural_stop_price" not in out.columns:
        if "structural_stop" in out.columns:
            out["structural_stop_price"] = out["structural_stop"]
        elif "stop" in out.columns:
            out["structural_stop_price"] = out["stop"]
        else:
            out["structural_stop_price"] = np.nan
    if "stop_distance" not in out.columns:
        out["stop_distance"] = (
            pd.to_numeric(out["entry"], errors="coerce")
            - pd.to_numeric(out["structural_stop_price"], errors="coerce")
        ).abs()
    out["stop_distance"] = pd.to_numeric(out["stop_distance"], errors="coerce")
    out["sd"] = out["stop_distance"]
    out["stop"] = out["structural_stop_price"]
    # Legacy aliases for older reports; not a formal StopSpec source.
    out["focus_stop"] = out["structural_stop_price"]
    out["focus_sd"] = out["stop_distance"]
    return out


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index)
    return pd.to_numeric(frame[column], errors="coerce")


def _top30_mask(frame: pd.DataFrame, available: pd.Series, column: str) -> pd.Series:
    values = _numeric(frame, column)
    valid = available & values.notna()
    if not valid.any():
        return pd.Series(False, index=frame.index)
    threshold = values.loc[valid].quantile(0.70)
    return valid & values.ge(threshold)


def build_combo_variant_frames(combo: dict, ctx: pd.DataFrame) -> list[dict]:
    sign = np.where(ctx["dir"].astype(str).str.upper() == "L", 1, -1)
    variants = [
        {
            "combo": combo["name"],
            "variant": f"{combo['name']}__baseline",
            "desc": f"{'/'.join(combo['frames'])} 覆盖期基线",
            "frame": ctx.copy(),
        }
    ]
    masks_for_stack: list[dict[str, object]] = []

    for label in combo["frames"]:
        prefix = tf_slug(label)
        idx = _numeric(ctx, f"{prefix}_idx")
        available = idx.ge(0)
        tf_dir = _numeric(ctx, f"{prefix}_dir").fillna(0).astype(int)
        close_side = _numeric(ctx, f"{prefix}_close_side").fillna(0).astype(int)
        dir_prev1 = _numeric(ctx, f"{prefix}_dir_prev1").fillna(0).astype(int)

        dir_align = available & (tf_dir.values == sign)
        dir_against = available & (tf_dir.values == -sign)
        recent2_any = available & ((tf_dir.values == sign) | (dir_prev1.values == sign))
        close_side_align = available & (close_side.values == sign)

        variants.extend(
            [
                {"combo": combo["name"], "variant": f"{combo['name']}__{prefix}_dir_align", "desc": f"{label} 方向同向", "frame": ctx[dir_align].copy()},
                {"combo": combo["name"], "variant": f"{combo['name']}__{prefix}_dir_against", "desc": f"{label} 方向反向", "frame": ctx[dir_against].copy()},
                {"combo": combo["name"], "variant": f"{combo['name']}__{prefix}_close_side", "desc": f"{label} close位于SMA13交易方向一侧", "frame": ctx[close_side_align].copy()},
                {"combo": combo["name"], "variant": f"{combo['name']}__{prefix}_recent2_any", "desc": f"{label} 最近2根至少1根同向_对照", "frame": ctx[recent2_any].copy()},
            ]
        )

        bias_masks: dict[str, pd.Series] = {}
        for period in (5, 13, 55):
            col = f"{prefix}_bias{period}_signed_pct"
            values = _numeric(ctx, col)
            pos_mask = available & values.gt(0)
            top30_mask = _top30_mask(ctx, available, col)
            bias_masks[f"bias{period}_pos"] = pos_mask
            bias_masks[f"bias{period}_top30"] = top30_mask
            variants.extend(
                [
                    {"combo": combo["name"], "variant": f"{combo['name']}__{prefix}_bias{period}_signed_pos", "desc": f"{label} Bias_{period} signed > 0", "frame": ctx[pos_mask].copy()},
                    {"combo": combo["name"], "variant": f"{combo['name']}__{prefix}_bias{period}_signed_top30", "desc": f"{label} Bias_{period} signed top30%", "frame": ctx[top30_mask].copy()},
                ]
            )

        bias5_13_pos = bias_masks["bias5_pos"] & bias_masks["bias13_pos"]
        bias_all_pos = bias5_13_pos & bias_masks["bias55_pos"]
        variants.extend(
            [
                {"combo": combo["name"], "variant": f"{combo['name']}__{prefix}_bias5_13_signed_pos", "desc": f"{label} Bias_5+13 signed > 0", "frame": ctx[bias5_13_pos].copy()},
                {"combo": combo["name"], "variant": f"{combo['name']}__{prefix}_bias5_13_55_signed_pos", "desc": f"{label} Bias_5+13+55 signed > 0", "frame": ctx[bias_all_pos].copy()},
            ]
        )
        masks_for_stack.append(
            {
                "label": label,
                "dir_align": dir_align,
                "close_side": close_side_align,
                "bias13_pos": bias_masks["bias13_pos"],
                "bias55_top30": bias_masks["bias55_top30"],
            }
        )

    if masks_for_stack:
        all_dir = np.logical_and.reduce([item["dir_align"] for item in masks_for_stack])
        variants.append({"combo": combo["name"], "variant": f"{combo['name']}__all_dir_align", "desc": "全组合方向同向", "frame": ctx[all_dir].copy()})

    if len(masks_for_stack) >= 2:
        first = masks_for_stack[0]
        last = masks_for_stack[-1]
        core_mask = first["close_side"] & last["bias55_top30"]
        core_desc = f"{first['label']} close同侧 + {last['label']} Bias_55 signed top30%"
        if len(masks_for_stack) >= 3:
            mid = masks_for_stack[1]
            core_mask = core_mask & mid["bias13_pos"]
            core_desc = f"{first['label']} close同侧 + {mid['label']} Bias_13 signed > 0 + {last['label']} Bias_55 signed top30%"
        variants.append({"combo": combo["name"], "variant": f"{combo['name']}__stack_core", "desc": core_desc, "frame": ctx[core_mask].copy()})
    return variants
