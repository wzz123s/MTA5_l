# -*- coding: utf-8 -*-
"""Compare research H6 features with EA H6 values for unmatched trades."""
from __future__ import annotations

import pandas as pd
import numpy as np


def calc_smma(series: pd.Series, n: int, m: int = 1) -> pd.Series:
    sma = pd.Series(index=series.index, dtype=float)
    sma.iloc[: n - 1] = pd.NA
    if len(series) >= n:
        sma.iloc[n - 1] = series.iloc[:n].mean()
        for i in range(n, len(series)):
            sma.iloc[i] = (m * series.iloc[i] + (n - m) * sma.iloc[i - 1]) / n
    return sma


def main() -> None:
    raw = pd.read_csv(
        r"黄金/2H_M30_6H策略\data\raw\mt5_history\2h_m30_6h_mt5_gen_20240101_20260725\XAUUSDm_M30.csv"
    )
    raw["date"] = pd.to_datetime(raw["time"], utc=True).dt.tz_convert(None)
    raw = raw.sort_values("date").reset_index(drop=True)
    tf = (
        raw.set_index("date")
        .resample("6h", label="right", closed="right")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna(subset=["open", "high", "low", "close"])
        .reset_index()
    )
    tf["SMA_5"] = calc_smma(tf["close"], 5).values
    tf["SMA_13"] = calc_smma(tf["close"], 13).values
    tf["SMA_55"] = calc_smma(tf["close"], 55).values

    def h6_ctx(t: str) -> pd.Series:
        idx = np.searchsorted(tf["date"].values, np.datetime64(t), side="right") - 1
        if idx < 0:
            return pd.Series(dtype=float)
        return tf.iloc[idx]

    cases = [
        ("extra 2024-01-02 01:30", "2024-01-02 01:30:00"),
        ("expected 2024-05-20 17:30", "2024-05-20 17:30:00"),
        ("expected 2024-01-23 12:00", "2024-01-23 12:00:00"),
        ("EA-delta 2024-01-23 19:30", "2024-01-23 19:30:00"),
        ("EA-delta 2024-01-25 17:30", "2024-01-25 17:30:00"),
    ]
    for label, t in cases:
        r = h6_ctx(t)
        print(label)
        if r.empty:
            print("  no h6 row")
            continue
        print(
            "  date=%s close=%.3f sma5=%.4f sma13=%.4f sma55=%.4f"
            % (r["date"], r["close"], r["SMA_5"], r["SMA_13"], r["SMA_55"])
        )
        print(
            "  bias5pct(BUY)=%.6f bias13pct(BUY)=%.6f bias55pct(BUY)=%.6f"
            % (
                (r["close"] - r["SMA_5"]) / r["SMA_5"] * 100,
                (r["close"] - r["SMA_13"]) / r["SMA_13"] * 100,
                (r["close"] - r["SMA_55"]) / r["SMA_55"] * 100,
            )
        )

    print("--- first 8 H6 rows after research start ---")
    sub = tf[(tf["date"] >= "2024-01-01") & (tf["date"] <= "2024-01-08")]
    print(sub[["date", "open", "high", "low", "close", "SMA_5", "SMA_13"]].to_string())


if __name__ == "__main__":
    main()
