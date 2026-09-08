# -*- coding: utf-8 -*-
"""
stage1_common.py —— MCT 大周期拐点策略 · 阶段1 公共工具

数据源：阶段1 多周期验证数据包（mct_mt5_multiperiod_20260901_115708）
  - 所有文件已截断至真密度（valid_from 见 manifest）
  - H16/D2 为派生周期（H4x4 / D1x2 连续合成）
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent
                       / "阶段0_规则与数据准备" / "scripts"))
import segment_analysis as sa

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw" / "mt5_history"
SRC = sorted(RAW.glob("mct_mt5_multiperiod_*"))[-1]   # 最新 source_id
PROC = BASE / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

PERIOD_PAIRS = ["1H/4H", "2H/6H/8H", "3H/12H", "4H/16H", "6H/1D", "12H/2D", "1D/1W"]
ALL_TFS = ["H1", "H2", "H3", "H4", "H6", "H8", "H12", "H16", "D1", "D2", "W1"]
TF_BARS = {"H1": 1, "H2": 2, "H3": 3, "H4": 4, "H6": 6, "H8": 8,
           "H12": 12, "H16": 16, "D1": 24, "D2": 48, "W1": 168}
# 档位对：(入场TF, 本级别TF)
TIERS = [("H1", "H4"), ("H2", "H6"), ("H2", "H8"), ("H3", "H12"),
         ("H4", "H16"), ("H6", "D1"), ("H12", "D2"), ("D1", "W1")]

GLUE_THRESH = 0.003   # 13x55 粘合阈值 0.3%


def load_tf(symbol: str, tf: str) -> pd.DataFrame:
    """读取多周期数据包中的周期 CSV（time 转 UTC datetime）。"""
    f = SRC / f"{symbol}_{tf}.csv"
    if not f.exists():
        raise FileNotFoundError(f)
    df = pd.read_csv(f, parse_dates=["time"])
    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
    return df


def analyze_tf(symbol: str, tf: str, min_len: int = 8) -> pd.DataFrame:
    """段分析流水线（SMA + 方向 + v4合并 + way + 极值 + 穿越标记）。"""
    df = load_tf(symbol, tf)
    return sa.analyze(df, min_len=min_len, calc_55=True)


def find_cross13_55(df: pd.DataFrame) -> pd.DataFrame:
    """日线/任意周期 SMA13 x55 穿越点清单。

    返回列: time, dir(+1=上穿做多 / -1=下穿做空), price(穿越行 close),
            sma13, sma55, glue(是否粘合临界), idx
    """
    s13 = df["SMA_13"].values
    s55 = df["SMA_55"].values
    t = df["time"].values
    n = len(df)
    rows = []
    for i in range(1, n):
        if np.isnan(s13[i]) or np.isnan(s55[i]) or np.isnan(s13[i-1]) or np.isnan(s55[i-1]):
            continue
        prev_gt = s13[i-1] > s55[i-1]
        cur_gt = s13[i] > s55[i]
        d = 0
        if (not prev_gt) and cur_gt:
            d = 1          # 上穿 → 做多
        elif prev_gt and (not cur_gt):
            d = -1         # 下穿 → 做空
        if d == 0:
            continue
        glue = abs(s13[i] - s55[i]) / s55[i] < GLUE_THRESH
        rows.append({"time": t[i], "dir": d, "price": df["close"].iloc[i],
                     "sma13": s13[i], "sma55": s55[i], "glue": glue, "idx": i})
    out = pd.DataFrame(rows)
    if len(out):
        out["time"] = pd.to_datetime(out["time"]).dt.tz_localize(None)
    return out


def forward_stats(df: pd.DataFrame, crossings: pd.DataFrame,
                  horizons=(20, 60, 120)) -> pd.DataFrame:
    """穿越后各 horizon 的收益分布 + 新高/新低比例（方向胜率）。

    LONG 胜 = 正向收益（r_h>0）或 60 根内创新高
    SHORT 胜 = 负向收益（r_h<0）或 60 根内创新低
    """
    n = len(df)
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    idxs = crossings["idx"].values
    dirs = crossings["dir"].values
    rows = []
    max_h = max(horizons)
    for k, (i, d) in enumerate(zip(idxs, dirs)):
        if i + max_h >= n:
            break
        rec = {"idx": i, "dir": d}
        for h in horizons:
            r = close[i + h] / close[i] - 1.0
            rec[f"r{h}"] = r
            rec[f"win{h}"] = (r > 0) if d == 1 else (r < 0)
        new_high = high[i + 1:i + 61].max() > high[i] if i + 61 <= n else np.nan
        new_low = low[i + 1:i + 61].min() < low[i] if i + 61 <= n else np.nan
        rec["new_high60"] = bool(new_high)
        rec["new_low60"] = bool(new_low)
        rec["win60_struct"] = bool(new_high) if d == 1 else bool(new_low)
        rows.append(rec)
    return pd.DataFrame(rows)


def summarize_winrate(fs: pd.DataFrame, label: str) -> dict:
    """汇总方向胜率表。"""
    out = {"label": label, "n": len(fs)}
    if len(fs) == 0:
        return out
    for h in (20, 60, 120):
        out[f"winrate_r{h}"] = round(float(fs[f"win{h}"].mean()) * 100, 1)
        out[f"median_r{h}_pct"] = round(float(fs[f"r{h}"].median()) * 100, 2)
        out[f"mean_r{h}_pct"] = round(float(fs[f"r{h}"].mean()) * 100, 2)
    out["winrate_60struct"] = round(float(fs["win60_struct"].mean()) * 100, 1)
    long = fs[fs["dir"] == 1]
    short = fs[fs["dir"] == -1]
    out["n_long"] = len(long)
    out["n_short"] = len(short)
    if len(long):
        out["long_win60"] = round(float(long["win60"].mean()) * 100, 1)
    if len(short):
        out["short_win60"] = round(float(short["win60"].mean()) * 100, 1)
    return out
