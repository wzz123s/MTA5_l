# -*- coding: utf-8 -*-
"""Scan the revised pre_cross definition.

Definition under test:
  - price/close crosses SMA13 on the current M30 bar;
  - SMA5 has not crossed SMA13 yet and remains on the original side;
  - abs(SMA5 - SMA13) / SMA13 is within a tested threshold range.

The validation keeps the current project baseline:
  - Layer 1: |H2 Bias_55| > 3.0% applied to all modes;
  - Layer 2: pre_cross + cross + post_n(2-6);
  - Layer 3: Bias_5 top 30%;
  - stop spec: [5, 35] pt.
"""
import os
import sys
import bisect

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from processing.prepare import prepare
from processing.smma import calc_smma
from _h2_context import load_h2_context


SPEC_LO = 5
SPEC_HI = 35
POST_N_MIN = 2
POST_N_MAX = 6
BIAS_55_THRESHOLD = 3.0
BIAS_5_TOP_PCT = 30
M15_FILTER_NAME = "m15_close_side"


def stats(tdf):
    if len(tdf) == 0:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "ev": 0.0, "pnl": 0.0, "ml": 0}
    n = len(tdf)
    won = int(tdf["won"].sum())
    gross_win = tdf.loc[tdf["won"], "pnl"].sum()
    gross_loss = abs(tdf.loc[~tdf["won"], "pnl"].sum())
    pf = gross_win / gross_loss if gross_loss > 0 else 0.0
    cl = 0
    ml = 0
    for won_flag in tdf["won"]:
        if won_flag:
            cl = 0
        else:
            cl += 1
            ml = max(ml, cl)
    pnl = gross_win - gross_loss
    return {
        "n": n,
        "wr": won / n * 100.0,
        "pf": pf,
        "ev": pnl / n,
        "pnl": pnl,
        "ml": ml,
    }


def fmt(s):
    return (
        f"{s['n']:>5}  WR {s['wr']:>5.1f}%  PF {s['pf']:>5.2f}  "
        f"EV {s['ev']:>+7.2f}pt  PnL ${s['pnl']:>7.0f}  MaxCL {s['ml']:>3}"
    )


def precompute_h2(h2_df, m30_times):
    h2_times = pd.to_datetime(h2_df["date"]).values.astype("datetime64[ns]")
    h2_close = h2_df["close"].values
    h2_sma5 = h2_df["SMA_5"].values
    h2_sma13 = h2_df["SMA_13"].values
    h2_sma55 = h2_df["SMA_55"].values

    bias55 = np.where(
        ~np.isnan(h2_sma55) & (h2_sma55 != 0),
        (h2_close - h2_sma55) / h2_sma55 * 100.0,
        np.nan,
    )
    bias5 = np.where(
        ~np.isnan(h2_sma5) & (h2_sma5 != 0),
        np.abs((h2_close - h2_sma5) / h2_sma5 * 100.0),
        np.nan,
    )
    bias13 = np.where(
        ~np.isnan(h2_sma13) & (h2_sma13 != 0),
        np.abs((h2_close - h2_sma13) / h2_sma13 * 100.0),
        np.nan,
    )

    pass_set = set()
    factor_map = {}
    m30_t = pd.to_datetime(m30_times).values.astype("datetime64[ns]")
    for i, t in enumerate(m30_t):
        idx = bisect.bisect_right(h2_times, t) - 1
        if idx < 0 or pd.isna(bias55[idx]):
            continue
        if abs(bias55[idx]) > BIAS_55_THRESHOLD:
            pass_set.add(i)
        factor_map[i] = {
            "Bias_5": bias5[idx],
            "Bias_13": bias13[idx],
            "Bias_55": abs(bias55[idx]),
        }
    return pass_set, factor_map


def add_factor(trade, factor_map):
    if trade["i"] in factor_map:
        trade.update(factor_map[trade["i"]])
    return trade


def prior_segment_stop(i, is_long, direction, sma13):
    k = i - 1
    while k >= 0 and direction[k] not in ("good", "bad"):
        k -= 1
    if k < 0:
        return np.nan
    seg = sma13[k:i]
    seg = seg[~np.isnan(seg)]
    if len(seg) == 0:
        return np.nan
    return np.nanmin(seg) if is_long else np.nanmax(seg)


def build_pre_cross(df, gap_thr, layer1_pass_set, factor_map):
    direction = df["方向"].values
    direction_merged = df["方向_合并后"].values
    sma5 = df["SMA_5"].values
    sma13 = df["SMA_13"].values
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    trades = []

    for i in range(1, len(df) - 1):
        if i not in layer1_pass_set:
            continue
        if any(pd.isna(x) for x in (sma5[i], sma13[i], sma13[i - 1], close[i], close[i - 1])):
            continue
        if direction[i] in ("good", "bad"):
            continue

        gap = abs(sma5[i] - sma13[i]) / sma13[i]
        if gap > gap_thr:
            continue

        long_setup = close[i - 1] <= sma13[i - 1] and close[i] > sma13[i] and sma5[i] < sma13[i]
        short_setup = close[i - 1] >= sma13[i - 1] and close[i] < sma13[i] and sma5[i] > sma13[i]
        if not (long_setup or short_setup):
            continue

        is_long = long_setup
        entry = close[i]
        sl = prior_segment_stop(i, is_long, direction, sma13)
        if pd.isna(sl):
            continue
        if is_long and sl >= entry:
            continue
        if (not is_long) and sl <= entry:
            continue
        sd = abs(entry - sl)
        if sd < SPEC_LO or sd > SPEC_HI:
            continue

        opp = "bad" if is_long else "good"
        j = i + 1
        while j < len(df) and direction_merged[j] != opp:
            j += 1
        if j >= len(df):
            continue
        path = low[i + 1 : j + 1] if is_long else high[i + 1 : j + 1]
        hit = (path <= sl).any() if is_long else (path >= sl).any()
        exit_px = df.iloc[j]["close"]
        if pd.isna(exit_px):
            continue
        pnl = (exit_px - entry) if is_long else (entry - exit_px)
        if hit:
            pnl = -sd
        trades.append(
            add_factor(
                {
                    "i": i,
                    "date": df.iloc[i]["date"],
                    "mode": "pre_cross",
                    "dir": "L" if is_long else "S",
                    "entry": entry,
                    "stop": sl,
                    "sd": sd,
                    "pnl": pnl,
                    "won": pnl > 0,
                },
                factor_map,
            )
        )
    return trades


def build_cross(df, layer1_pass_set, factor_map):
    direction = df["方向"].values
    sma13 = df["SMA_13"].values
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    trades = []
    for i in range(len(df)):
        if i not in layer1_pass_set:
            continue
        d = direction[i]
        if d not in ("good", "bad") or pd.isna(sma13[i]):
            continue
        is_long = d == "good"
        entry = (high[i] + low[i] + close[i]) / 3.0
        sl = prior_segment_stop(i, is_long, direction, sma13)
        if pd.isna(sl):
            continue
        if is_long and sl >= entry:
            continue
        if (not is_long) and sl <= entry:
            continue
        sd = abs(entry - sl)
        if sd < SPEC_LO or sd > SPEC_HI:
            continue
        opp = "bad" if is_long else "good"
        j = i + 1
        while j < len(df) and direction[j] != opp:
            j += 1
        if j >= len(df):
            continue
        path = low[i + 1 : j + 1] if is_long else high[i + 1 : j + 1]
        hit = (path <= sl).any() if is_long else (path >= sl).any()
        exit_px = df.iloc[j]["close"]
        if pd.isna(exit_px):
            continue
        pnl = (exit_px - entry) if is_long else (entry - exit_px)
        if hit:
            pnl = -sd
        trades.append(
            add_factor(
                {
                    "i": i,
                    "date": df.iloc[i]["date"],
                    "mode": "cross",
                    "dir": "L" if is_long else "S",
                    "entry": entry,
                    "stop": sl,
                    "sd": sd,
                    "pnl": pnl,
                    "won": pnl > 0,
                },
                factor_map,
            )
        )
    return trades


def build_post_n(df, layer1_pass_set, factor_map):
    direction_merged = df["方向_合并后"].values
    post_n = df["merged_post_cross_n"].values
    sma13 = df["SMA_13"].values
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    trades = []
    for i in range(len(df)):
        if i not in layer1_pass_set:
            continue
        pn = post_n[i]
        if abs(pn) < POST_N_MIN or abs(pn) > POST_N_MAX:
            continue
        is_long = pn > 0
        entry = close[i]
        sl = sma13[i]
        if pd.isna(entry) or pd.isna(sl):
            continue
        if is_long and sl >= entry:
            continue
        if (not is_long) and sl <= entry:
            continue
        sd = abs(entry - sl)
        if sd < SPEC_LO or sd > SPEC_HI:
            continue
        opp = "bad" if is_long else "good"
        j = i + 1
        while j < len(df) and direction_merged[j] != opp:
            j += 1
        if j >= len(df):
            continue
        path = low[i + 1 : j + 1] if is_long else high[i + 1 : j + 1]
        hit = (path <= sl).any() if is_long else (path >= sl).any()
        exit_px = df.iloc[j]["close"]
        if pd.isna(exit_px):
            continue
        pnl = (exit_px - entry) if is_long else (entry - exit_px)
        if hit:
            pnl = -sd
        trades.append(
            add_factor(
                {
                    "i": i,
                    "date": df.iloc[i]["date"],
                    "mode": f"post_n{abs(pn)}",
                    "dir": "L" if is_long else "S",
                    "entry": entry,
                    "stop": sl,
                    "sd": sd,
                    "pnl": pnl,
                    "won": pnl > 0,
                },
                factor_map,
            )
        )
    return trades


def dedupe(trades):
    if not trades:
        return pd.DataFrame()
    tdf = pd.DataFrame(trades)
    priority = {"pre_cross": 0, "cross": 1}
    for n in range(POST_N_MIN, POST_N_MAX + 1):
        priority[f"post_n{n}"] = 2
    tdf["_pri"] = tdf["mode"].map(priority).fillna(99)
    tdf = tdf.sort_values(["date", "dir", "_pri"])
    tdf = tdf.drop_duplicates(subset=["date", "dir"], keep="first")
    return tdf.drop(columns=["_pri"]).reset_index(drop=True)


def layer3_top(tdf):
    if len(tdf) <= 30 or "Bias_5" not in tdf:
        return tdf.iloc[0:0].copy()
    threshold = tdf["Bias_5"].quantile(1 - BIAS_5_TOP_PCT / 100.0)
    return tdf[tdf["Bias_5"] >= threshold].reset_index(drop=True)


def load_m15_filter_context(path="base_data/XAUUSDm15.csv", add_hours=2):
    """Load M15 bars used by the main close-side filter."""
    m15 = pd.read_csv(path, encoding="gbk")
    m15.columns = [
        "date", "open", "high", "low", "close", "volume",
        "spread", "real_volume", "symbol", "time_diff",
    ]
    m15["date"] = pd.to_datetime(m15["date"]) + pd.Timedelta(hours=add_hours)
    m15 = m15.sort_values("date").reset_index(drop=True)
    m15["SMA_13"] = calc_smma(m15["close"], 13).values
    return m15


def apply_m15_close_side(tdf, m15=None):
    """Keep trades whose latest M15 close is on the trade side of M15 SMMA13."""
    if len(tdf) == 0:
        return tdf.copy()
    if m15 is None:
        m15 = load_m15_filter_context()

    out = tdf.copy().sort_values("date").reset_index(drop=True)
    m15_times = pd.to_datetime(m15["date"]).values.astype("datetime64[ns]")
    trade_times = pd.to_datetime(out["date"]).values.astype("datetime64[ns]")

    idxs = []
    closes = []
    sma13s = []
    dates = []
    for t in trade_times:
        idx = bisect.bisect_right(m15_times, t) - 1
        idxs.append(idx)
        if idx < 0:
            dates.append(pd.NaT)
            closes.append(np.nan)
            sma13s.append(np.nan)
            continue
        row = m15.iloc[idx]
        dates.append(row["date"])
        closes.append(row["close"])
        sma13s.append(row["SMA_13"])

    out["m15_idx"] = idxs
    out["m15_date"] = dates
    out["m15_close"] = closes
    out["m15_sma13"] = sma13s
    sign = np.where(out["dir"] == "L", 1, -1)
    available = out["m15_idx"] >= 0
    same_side = available & (
        ((sign == 1) & (out["m15_close"] > out["m15_sma13"])) |
        ((sign == -1) & (out["m15_close"] < out["m15_sma13"]))
    )
    return out[same_side].reset_index(drop=True)


def main():
    print("=" * 110)
    print("pre_cross range test: price crossed SMA13, SMA5 close to SMA13")
    print("=" * 110)
    print(
        f"Layer1 |Bias_55|>{BIAS_55_THRESHOLD}%, post_n {POST_N_MIN}-{POST_N_MAX}, "
        f"spec [{SPEC_LO}, {SPEC_HI}], Layer3 Bias_5 top {BIAS_5_TOP_PCT}%"
    )

    df, _ = prepare("base_data/XAUUSDm30.csv", min_len=8)
    h2_df = load_h2_context()
    m15 = load_m15_filter_context()
    layer1_pass_set, factor_map = precompute_h2(h2_df, df["date"].values)
    print(f"M30 bars: {len(df)}, Layer1 pass bars: {len(layer1_pass_set)}")
    print()

    cross = build_cross(df, layer1_pass_set, factor_map)
    post = build_post_n(df, layer1_pass_set, factor_map)
    base = dedupe(cross + post)
    base_top = layer3_top(base)
    print("Baseline without pre_cross:")
    print(f"  L1+2 cross+post_n        {fmt(stats(base))}")
    print(f"  L1+2+3 Bias_5 top30      {fmt(stats(base_top))}")
    print()

    thresholds = [0.0002, 0.0005, 0.0010, 0.0015, 0.0020, 0.0030, 0.0050, 0.0080, 0.0100]
    print("Threshold scan:")
    print(
        f"{'gap_thr':>9}  {'pre only':<54}  {'three modes':<54}  {'three + top30':<54}"
    )
    print("-" * 180)
    rows = []
    for thr in thresholds:
        pre = build_pre_cross(df, thr, layer1_pass_set, factor_map)
        all_modes = dedupe(pre + cross + post)
        top = layer3_top(all_modes)
        pre_df = pd.DataFrame(pre)
        s_pre = stats(pre_df)
        s_all = stats(all_modes)
        s_top = stats(top)
        rows.append((thr, s_pre, s_all, s_top, all_modes, top))
        print(f"{thr*100:8.3f}%  {fmt(s_pre):<54}  {fmt(s_all):<54}  {fmt(s_top):<54}")

    print()
    best_pf = max(rows, key=lambda r: (r[3]["pf"], r[3]["ev"], r[3]["n"]))
    best_ev = max(rows, key=lambda r: (r[3]["ev"], r[3]["pf"], r[3]["n"]))
    print("Best by Layer3 PF:")
    print(f"  gap <= {best_pf[0]*100:.3f}%  {fmt(best_pf[3])}")
    print("Best by Layer3 EV:")
    print(f"  gap <= {best_ev[0]*100:.3f}%  {fmt(best_ev[3])}")

    best_thr, _, _, _, best_all, best_top = best_pf
    if len(best_top) > 0:
        print()
        print(f"Mode split for best PF threshold ({best_thr*100:.3f}%, after Layer3):")
        for mode, group in best_top.groupby("mode"):
            print(f"  {mode:<12} {fmt(stats(group))}")

    current_pre = build_pre_cross(df, 0.003, layer1_pass_set, factor_map)
    current_all = dedupe(current_pre + cross + post)
    current_top = layer3_top(current_all)
    current_m15 = apply_m15_close_side(current_top, m15)
    print()
    print("Current main candidate with M15 close-side filter:")
    print(f"  before M15 filter             {fmt(stats(current_top))}")
    print(f"  after M15 close-side filter   {fmt(stats(current_m15))}")
    print("  filter: LONG requires latest M15 close > M15 SMA13; SHORT requires close < SMA13")


if __name__ == "__main__":
    main()
