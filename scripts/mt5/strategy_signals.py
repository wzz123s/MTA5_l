# -*- coding: utf-8 -*-
"""Build baseline research signals from strategy-owned MT5 M30 bars."""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_basic_cross_signals(
    m30_tf: pd.DataFrame,
    *,
    stop_lo: float | None = None,
    stop_hi: float | None = None,
) -> pd.DataFrame:
    """Create a conservative SMA5/SMA13 cross candidate set on the current raw data.

    The output is a research candidate set, not the final optimized strategy.
    It gives downstream multi-timeframe gates a current-data baseline without
    reusing the old strategy's accepted signal bundle. StopSpec is not applied
    here by default; downstream validation must filter on ``stop_distance``.
    """
    if m30_tf.empty:
        return _empty_signal_frame()

    frame = m30_tf.copy().sort_values("date").reset_index(drop=True)
    direction = frame["dir"].astype(int).to_numpy()
    cross_rows: list[tuple[int, str]] = []
    for idx in range(1, len(frame)):
        prev_dir = int(direction[idx - 1])
        cur_dir = int(direction[idx])
        if cur_dir > 0 and prev_dir <= 0:
            cross_rows.append((idx, "L"))
        elif cur_dir < 0 and prev_dir >= 0:
            cross_rows.append((idx, "S"))

    rows: list[dict] = []
    for pos, (idx, side) in enumerate(cross_rows):
        if pos == 0:
            continue
        prev_cross_idx = cross_rows[pos - 1][0]
        next_cross_idx = None
        for later_idx, later_side in cross_rows[pos + 1 :]:
            if later_side != side:
                next_cross_idx = later_idx
                break
        if next_cross_idx is None:
            continue

        row = frame.iloc[idx]
        segment = frame["SMA_13"].iloc[max(0, prev_cross_idx) : idx].dropna().astype(float)
        if segment.empty:
            continue

        entry = float((row["high"] + row["low"] + row["close"]) / 3.0)
        if side == "L":
            stop = float(segment.min())
            stop_pts = entry - stop
            exit_price = float(frame.iloc[next_cross_idx]["close"])
            pnl = exit_price - entry
            mode = "good"
        else:
            stop = float(segment.max())
            stop_pts = stop - entry
            exit_price = float(frame.iloc[next_cross_idx]["close"])
            pnl = entry - exit_price
            mode = "bad"

        if not np.isfinite(stop_pts) or stop_pts <= 0:
            continue
        if stop_lo is not None and stop_pts < stop_lo:
            continue
        if stop_hi is not None and stop_pts > stop_hi:
            continue

        date = pd.Timestamp(row["date"])
        exit_time = pd.Timestamp(frame.iloc[next_cross_idx]["date"])
        rows.append(
            {
                "date": date,
                "mode": mode,
                "dir": side,
                "entry_time": date,
                "entry": round(entry, 3),
                "structural_stop_price": round(stop, 3),
                "structural_stop_source": "m30_prev_cross_sma13_extreme",
                "stop_distance": round(float(stop_pts), 3),
                "stop": round(stop, 3),
                "sd": round(float(stop_pts), 3),
                "exit_time": exit_time,
                "exit": round(exit_price, 3),
                "pnl": round(float(pnl), 3),
                "total_points": round(float(pnl), 3),
                "stage1_pnl": round(float(pnl), 3),
                "stage2_pnl": 0.0,
                "stage3_pnl": 0.0,
                "signal_source": "mt5_basic_cross_v1",
                "stop_spec_lo": "" if stop_lo is None else float(stop_lo),
                "stop_spec_hi": "" if stop_hi is None else float(stop_hi),
            }
        )

    if not rows:
        return _empty_signal_frame()
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def _empty_signal_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "mode",
            "dir",
            "entry_time",
            "entry",
            "structural_stop_price",
            "structural_stop_source",
            "stop_distance",
            "stop",
            "sd",
            "exit_time",
            "exit",
            "pnl",
            "total_points",
            "stage1_pnl",
            "stage2_pnl",
            "stage3_pnl",
            "signal_source",
            "stop_spec_lo",
            "stop_spec_hi",
        ]
    )
