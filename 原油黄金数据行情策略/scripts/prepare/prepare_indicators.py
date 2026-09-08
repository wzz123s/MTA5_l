# -*- coding: utf-8 -*-
"""标准化指标：SMMA(5/13/55/144/233) + 段状态机(good/up/bad/down) + 段内极值追踪 + 穿越点开仓止损 + signed bias。

口径对照：交易规则/SMA均线参数配置_v3.1.md（MTA5 库）
- SMMA M=1 递推：SMA(i)=(1*CLOSE(i)+(N-1)*SMA(i-1))/N，前 N-1 行空值
- 段状态机：good=5SMA上穿13SMA；up=持续在上；bad=下穿；down=持续在下（首行按位置纠正）
- 极值追踪：up段内最高价+SMA13最高值；down段内最低价+SMA13最低值（独立追踪）
- 穿越点：good行→long_entry=(H+L+C)/3、long_stop=prev_seg_low_sma13；bad行→short_entry/short_stop
- signed bias：trade_sign*(close-SMA)/SMA*100（不abs）

用法: python prepare_indicators.py --symbol XAUUSDm --timeframes M30,H2,H6 --out gold_context.csv
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = ROOT / "data" / "raw" / "mt5_history"


def calc_sma(series: pd.Series, n: int, m: int = 1) -> pd.Series:
    """SMMA(X,N,M)，前 n-1 行返回 NA（与 v3.1 文档一致）"""
    sma = pd.Series(index=series.index, dtype=float)
    sma.iloc[: n - 1] = np.nan
    if len(series) >= n:
        sma.iloc[n - 1] = series.iloc[:n].mean()
        for i in range(n, len(series)):
            sma.iloc[i] = (m * series.iloc[i] + (n - m) * sma.iloc[i - 1]) / n
    return sma


def mark_direction(df: pd.DataFrame) -> pd.DataFrame:
    """5SMA vs 13SMA 缠绕状态机，返回 good/up/bad/down（首行纠正）"""
    _df = df.dropna(subset=["SMA_13"]).copy()
    sma5_gt = _df["SMA_5"] > _df["SMA_13"]
    sma5_gt_prev = sma5_gt.shift(1).fillna(False)
    conds = [
        sma5_gt & ~sma5_gt_prev,
        ~sma5_gt & sma5_gt_prev,
        sma5_gt & sma5_gt_prev,
        ~sma5_gt & ~sma5_gt_prev,
    ]
    _df["方向"] = np.select(conds, ["good", "bad", "up", "down"], default="down")
    _df.loc[_df.index[0], "方向"] = "up" if sma5_gt.iloc[0] else "down"
    return _df


def track_extremes(df: pd.DataFrame) -> pd.DataFrame:
    """段内极值追踪 + 穿越点标记（v3.1 口径）"""
    df = df.copy()
    cols = ["up_high_price", "up_high_sma13", "down_low_price", "down_low_sma13",
            "prev_seg_low_price", "prev_seg_low_sma13", "prev_seg_high_price", "prev_seg_high_sma13",
            "long_entry", "long_stop", "short_entry", "short_stop"]
    for c in cols:
        df[c] = np.nan
    c_up_hp = c_up_hs = c_dn_lp = c_dn_ls = np.nan
    pseg_low_p = pseg_low_s = pseg_high_p = pseg_high_s = np.nan
    prev_dir = None
    for i in range(len(df)):
        d = df["方向"].iloc[i]
        high = df["high"].iloc[i]
        low = df["low"].iloc[i]
        s13 = df["SMA_13"].iloc[i]
        if d == "up":
            if np.isnan(c_up_hp) or high > c_up_hp:
                c_up_hp = high
            if np.isnan(c_up_hs) or s13 > c_up_hs:
                c_up_hs = s13
            df.iloc[i, df.columns.get_loc("up_high_price")] = c_up_hp
            df.iloc[i, df.columns.get_loc("up_high_sma13")] = c_up_hs
        elif d == "down":
            if np.isnan(c_dn_lp) or low < c_dn_lp:
                c_dn_lp = low
            if np.isnan(c_dn_ls) or s13 < c_dn_ls:
                c_dn_ls = s13
            df.iloc[i, df.columns.get_loc("down_low_price")] = c_dn_lp
            df.iloc[i, df.columns.get_loc("down_low_sma13")] = c_dn_ls
        elif d == "good":  # 上穿：紧邻前 down 段的极值（先归档后使用）
            pseg_low_p, pseg_low_s = c_dn_lp, c_dn_ls
            df.iloc[i, df.columns.get_loc("prev_seg_low_price")] = pseg_low_p
            df.iloc[i, df.columns.get_loc("prev_seg_low_sma13")] = pseg_low_s
            df.iloc[i, df.columns.get_loc("long_entry")] = (high + low + df["close"].iloc[i]) / 3
            df.iloc[i, df.columns.get_loc("long_stop")] = pseg_low_s
            c_up_hp = c_up_hs = np.nan  # 新 up 段开始
        elif d == "bad":  # 下穿：紧邻前 up 段的极值（先归档后使用）
            pseg_high_p, pseg_high_s = c_up_hp, c_up_hs
            df.iloc[i, df.columns.get_loc("prev_seg_high_price")] = pseg_high_p
            df.iloc[i, df.columns.get_loc("prev_seg_high_sma13")] = pseg_high_s
            df.iloc[i, df.columns.get_loc("short_entry")] = (high + low + df["close"].iloc[i]) / 3
            df.iloc[i, df.columns.get_loc("short_stop")] = pseg_high_s
            c_dn_lp = c_dn_ls = np.nan  # 新 down 段开始
        prev_dir = d
    return df


def add_bias(df: pd.DataFrame) -> pd.DataFrame:
    """带方向偏离 signed bias（%）：biasN = sign_trade*(close-SMA)/SMA*100"""
    for n in ("5", "13", "55", "144", "233"):
        col = f"SMA_{n}"
        if col in df.columns:
            df[f"bias{n}_signed_pct"] = (df["close"] - df[col]) / df[col] * 100.0
    return df


def way_grade(df: pd.DataFrame) -> pd.DataFrame:
    """段内强度评估（v4 链式口径，对齐 MTA5_l way_grade.py）：
    way=|段持续根数|(带方向)、way_s_way=结构延续比例、vol_way_s_way=缩量延续比例"""
    df = df.copy()
    df["vol_ma_120"] = df["tick_volume"].rolling(120, min_periods=1).mean()
    direction = df["方向"].values
    sma13 = df["SMA_13"].values
    low = df["low"].values
    high = df["high"].values
    vol = df["tick_volume"].values.astype(float)
    vol_ma = df["vol_ma_120"].values
    n = len(df)
    way = np.zeros(n); way_s = np.zeros(n); wsw = np.zeros(n)
    vol_way = np.zeros(n); vwsw = np.zeros(n)
    y = x = z = 0
    prev_d = None
    for i in range(n):
        d = direction[i]
        if d in ("good", "bad"):
            y = x = z = 0
            s_way = 0.0; v_way = 0.0
        elif d == "up":
            if prev_d == "good":
                y, x = 1, 1
                z = 1 if vol[i] <= vol_ma[i] else 0
            elif prev_d == "up":
                y += 1
                if low[i] >= sma13[i] and high[i] >= high[i - 1]:
                    x += 1
                if vol[i] <= vol_ma[i]:
                    z += 1
            else:
                y, x = 1, 1
                z = 1 if vol[i] <= vol_ma[i] else 0
            s_way = round(x / y, 2) if y else 0.0
            v_way = round(z / y, 2) if y else 0.0
        elif d == "down":
            if prev_d == "bad":
                y, x = -1, -1
                z = -1 if vol[i] <= vol_ma[i] else 0
            elif prev_d == "down":
                y -= 1
                if high[i] <= sma13[i] and low[i] <= low[i - 1]:
                    x -= 1
                if vol[i] <= vol_ma[i]:
                    z -= 1
            else:
                y, x = -1, -1
                z = -1 if vol[i] <= vol_ma[i] else 0
            s_way = round(x / y, 2) if y else 0.0
            v_way = round(z / y, 2) if y else 0.0
        else:
            s_way = 0.0; v_way = 0.0
        way[i] = y; way_s[i] = x; wsw[i] = s_way; vol_way[i] = z; vwsw[i] = v_way
        prev_d = d
    df["way"] = way; df["way_s"] = way_s; df["way_s_way"] = wsw
    df["vol_way"] = vol_way; df["vol_way_s_way"] = vwsw
    return df


def build_context(symbol: str, timeframes: list[str], out_path: Path) -> None:
    """主表：以最低周期为轴，挂载高周期门值（已收盘 bar，无未来函数）"""
    frames: dict[str, pd.DataFrame] = {}
    base_tf = timeframes[0]
    for tf in timeframes:
        f = RAW_ROOT / f"{symbol}_{tf}.csv"
        for bundle in (RAW_ROOT / f"{symbol.lower()}_mt5_20190101", RAW_ROOT / f"gold_mt5_20190101", RAW_ROOT / f"oil_mt5_20190101"):
            cand = bundle / f"{symbol}_{tf}.csv"
            if cand.exists():
                f = cand
                break
        df = pd.read_csv(f, parse_dates=["time"])
        df["time"] = pd.to_datetime(df["time"], utc=True)
        for n in ("5", "13", "55", "144", "233"):
            df[f"SMA_{n}"] = calc_sma(df["close"], int(n))
        df = mark_direction(df)
        df = track_extremes(df)
        df = add_bias(df)
        df = way_grade(df)
        frames[tf] = df
    base = frames[base_tf].copy()
    base["date_utc"] = pd.to_datetime(base["time"], utc=True)
    for tf in timeframes[1:]:
        hi = frames[tf].copy()
        hi["date_utc"] = pd.to_datetime(hi["time"], utc=True)
        hi = hi[["date_utc", f"bias5_signed_pct", f"bias13_signed_pct", f"bias55_signed_pct", "SMA_55"]]
        hi.columns = [f"{tf}_" + c if c != "date_utc" else "date_utc" for c in hi.columns]
        base = pd.merge_asof(base.sort_values("date_utc"), hi.sort_values("date_utc"),
                             on="date_utc", direction="backward")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    base.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"context saved: {out_path} rows={len(base)} cols={base.shape[1]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--timeframes", required=True, help="逗号分隔，第一个为基准周期")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    build_context(args.symbol, [t.strip() for t in args.timeframes.split(",")], ROOT / "data" / "processed" / args.out)
