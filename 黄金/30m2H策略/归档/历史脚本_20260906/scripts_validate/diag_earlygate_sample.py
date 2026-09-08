# -*- coding: utf-8 -*-

import bisect
import os
import sys

os.chdir(r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\30m2H策略\参考实现工程\scripts")

import pandas as pd

import _current_baseline as base

df, h2, m15 = base.load_market_context()
h2_times = pd.to_datetime(h2["date"]).values.astype("datetime64[ns]")
h2_sma55 = h2["SMA_55"].values
close_m30 = df["close"].values
df["tstr"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d %H:%M")
i = df.index[df["tstr"] == "2020-08-04 16:30"][0]
t = pd.to_datetime(df["date"].iloc[i])
prev_idx = bisect.bisect_right(h2_times, t.to_datetime64()) - 1
print(f"bar={t}  prev_idx={prev_idx}  prev_h2_time={pd.Timestamp(h2_times[prev_idx])}")
print(f"prev_sma55 = {h2_sma55[prev_idx]:.5f}")
partial_close = close_m30[i]
print(f"partial_close (bar close) = {partial_close:.3f}")
est_sma55 = h2_sma55[prev_idx] + (partial_close - h2_sma55[prev_idx]) / 55
est_bias55 = abs((partial_close - est_sma55) / est_sma55) * 100.0
print(f"est_sma55 = {est_sma55:.5f}  est_bias55 = {est_bias55:.5f}  (EA: 3.11490 EARLY_PASS)")
