# -*- coding: utf-8 -*-
"""宏观日历 × 策略交易 影响分析（阶段2-4）。

输入：
  - 事件: 宏观日历研究/data/calendar_export.csv (MQL5导出)
  - 交易: observation_dashboard/<策略>/trades_snapshot.csv
  - K线:  各策略 data/raw/mt5_history/<bundle>/<SYMBOL>m_M30.csv (波动率验证)
输出：
  - 宏观日历研究/报告/ 下的事件邻近分析、波动率验证、过滤变体报告
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
RESEARCH = ROOT / "宏观日历研究"
sys.path.insert(0, str(RESEARCH / "scripts"))
from classify_events import classify  # noqa: E402

EVENTS_CSV = RESEARCH / "data" / "calendar_export.csv"
REPORT_DIR = RESEARCH / "报告"
SCALE = 1e6  # MT5日历数值按100万倍存储

STRATEGIES = {
    "1H_M30_4H": dict(dir="黄金/1H_M30_4H策略", symbol="XAUUSDm", bars="data/raw/mt5_history/1h_m30_4h_live/XAUUSDm_M30.csv", usd_per_pt=10.0),
    "30m2H":     dict(dir="黄金/30m2H策略",     symbol="XAUUSDm", bars="data/raw/mt5_history/30m2h_live/XAUUSDm_M30.csv", usd_per_pt=10.0),
    "2H_M30_6H": dict(dir="黄金/2H_M30_6H策略", symbol="XAUUSDm", bars="data/raw/mt5_history/2h_m30_6h_live/XAUUSDm_M30.csv", usd_per_pt=10.0),
    "BiasReversal": dict(dir="黄金/乖离反转策略", symbol="XAUUSDm", bars="data/raw/mt5_history/bias_reversal_live/XAUUSDm_M30.csv", usd_per_pt=10.0),
    "USOIL2H":   dict(dir="原油/原油2H策略",    symbol="USOILm",  bars="data/raw/mt5_history/usoil2h_live/USOILm_M30.csv", usd_per_pt=1.0),
    "USOIL4H":   dict(dir="原油/原油4H门策略",  symbol="USOILm",  bars="data/raw/mt5_history/usoil_4h_gate_live/USOILm_M30.csv", usd_per_pt=1.0),
}


def load_events(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="|", dtype={"event_id": "int64", "time": "int64", "value_id": "int64"})
    for col in ["actual", "forecast", "prev", "revised_prev"]:
        df[col] = pd.to_numeric(df[col], errors="coerce") / SCALE
    df["time_utc"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df["category"] = df["event_name"].map(classify)
    df["is_high"] = df["importance"] >= 3  # 实测本终端build: importance=0..3, 3=HIGH（impact_type 恒为0/1/2）
    df["importance_hi"] = df["importance"] >= 70
    return df


def load_trades(strat: str) -> pd.DataFrame:
    cfg = STRATEGIES[strat]
    path = ROOT / "observation_dashboard" / strat / "trades_snapshot.csv"
    df = pd.read_csv(path, parse_dates=["signal_time", "stage3_exit_time"])
    df["signal_time"] = pd.to_datetime(df["signal_time"], utc=True)
    df["stage3_exit_time"] = pd.to_datetime(df["stage3_exit_time"], utc=True)
    df["strat"] = strat
    df["pnl_usd_per_lot"] = df["weighted_pts"] * cfg["usd_per_pt"]
    return df


def nearest_event_features(trades: pd.DataFrame, events: pd.DataFrame, high: pd.DataFrame):
    """对每笔交易计算事件邻近特征。"""
    t = trades["signal_time"].to_numpy(dtype="datetime64[ns]")
    eh = high["time_utc"].to_numpy(dtype="datetime64[ns]")
    idx = np.searchsorted(eh, t)
    gaps_before = np.full(len(t), np.nan)   # 开仓前最近高影响事件的小时数（负值表示在过去）
    gaps_after = np.full(len(t), np.nan)    # 开仓后最近高影响事件的小时数
    for i in range(len(t)):
        j = idx[i]
        if j < len(eh):
            gaps_after[i] = (eh[j] - t[i]).astype("timedelta64[h]").astype(float)
        if j > 0:
            gaps_before[i] = (eh[j - 1] - t[i]).astype("timedelta64[h]").astype(float)
    out = pd.DataFrame({
        "gap_before_h": gaps_before,
        "gap_after_h": gaps_after,
        "min_abs_gap_h": np.minimum(np.abs(gaps_before), np.abs(gaps_after)),
    })
    # 持仓期间是否有高影响事件
    out["event_in_trade"] = False
    evs = high[["time_utc"]].to_numpy(dtype="datetime64[ns]")[:, 0]
    for i, row in trades.iterrows():
        m = (evs > row["signal_time"].to_datetime64()) & (evs < row["stage3_exit_time"].to_datetime64())
        out.loc[i, "event_in_trade"] = bool(m.any())
    return out


def bootstrap_diff(a: np.ndarray, b: np.ndarray, n_iter: int = 5000, seed: int = 42) -> tuple[float, float, float]:
    """均值差异的bootstrap置信区间与p值（置换检验）。返回 (diff, ci_lo, ci_hi, p)。"""
    rng = np.random.default_rng(seed)
    if len(a) < 5 or len(b) < 5:
        return (np.nan, np.nan, np.nan, np.nan)
    pooled = np.concatenate([a, b])
    na, nb = len(a), len(b)
    perm_diffs = np.empty(n_iter)
    for k in range(n_iter):
        perm = rng.permutation(pooled)
        perm_diffs[k] = perm[:na].mean() - perm[na:].mean()
    diff = a.mean() - b.mean()
    p = (np.abs(perm_diffs) >= np.abs(diff)).mean()
    boot = np.empty(n_iter)
    for k in range(n_iter):
        sa = rng.choice(a, na, replace=True)
        sb = rng.choice(b, nb, replace=True)
        boot[k] = sa.mean() - sb.mean()
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return diff, lo, hi, p


def fmt(x, nd=2):
    return "nan" if pd.isna(x) else f"{x:.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default=str(EVENTS_CSV))
    ap.add_argument("--no-vol", action="store_true", help="跳过波动率验证")
    args = ap.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events(Path(args.events))
    high = events[events["is_high"]].copy()
    print(f"事件总数: {len(events)}, 高影响: {len(high)}, 时间范围: {events['time_utc'].min()} ~ {events['time_utc'].max()}")
    print("事件类别分布(高影响):")
    print(high["category"].value_counts().head(20).to_string())

    # 事件时间对齐校验：检查非农/CPI是否落在常见发布时刻
    if len(high) > 0:
        for cat in ["非农就业", "CPI通胀"]:
            sub = high[high["category"] == cat]
            if len(sub):
                hh = sub["time_utc"].dt.hour.value_counts().sort_index()
                print(f"--- {cat} 发布小时分布(UTC): {dict(hh.head(6))}")

    rows = []
    vol_rows = []
    for strat, cfg in STRATEGIES.items():
        trades = load_trades(strat)
        feats = nearest_event_features(trades, events, high)
        merged = pd.concat([trades.reset_index(drop=True), feats.reset_index(drop=True)], axis=1)
        base = merged
        n = len(base)
        win_pts = base["weighted_pts"]
        summary = {
            "strategy": strat,
            "n": n,
            "win_rate": (win_pts > 0).mean(),
            "avg_pts": win_pts.mean(),
            "expectancy_per_trade_pts": win_pts.mean(),
            "profit_factor": win_pts[win_pts > 0].sum() / -win_pts[win_pts < 0].sum() if (win_pts < 0).any() else np.inf,
        }
        rows.append(summary)
        print(f"\n===== {strat}: n={n} 胜率={summary['win_rate']:.1%} 平均={summary['avg_pts']:.1f}pts =====")

        # 邻近窗口分组
        for w in [1, 2, 4, 8, 12, 24]:
            mask = merged["min_abs_gap_h"] <= w
            a, b = merged[mask]["weighted_pts"].to_numpy(float), merged[~mask]["weighted_pts"].to_numpy(float)
            diff, lo, hi, p = bootstrap_diff(a, b)
            sign = "显著" if (p < 0.05 and not np.isnan(p)) else ""
            print(f"  ±{w:>2}h窗口内开仓: n={len(a):>4} 平均={a.mean():8.2f} vs 窗口外 n={len(b):>4} 平均={b.mean():8.2f} | diff={fmt(diff)} [{fmt(lo)},{fmt(hi)}] p={fmt(p,3)} {sign}")
            rows.append({"strategy": strat, "bucket": f"±{w}h内", "n": len(a), "win_rate": (a > 0).mean() if len(a) else np.nan,
                         "avg_pts": a.mean() if len(a) else np.nan, "p": p})
            rows.append({"strategy": strat, "bucket": f"±{w}h外", "n": len(b), "win_rate": (b > 0).mean() if len(b) else np.nan,
                         "avg_pts": b.mean() if len(b) else np.nan, "p": np.nan})

        # 持仓期间事件
        m = merged["event_in_trade"]
        if m.sum() > 0:
            a, b = merged[m]["weighted_pts"].to_numpy(float), merged[~m]["weighted_pts"].to_numpy(float)
            diff, lo, hi, p = bootstrap_diff(a, b)
            print(f"  持仓期间有高影响事件: n={len(a)} 平均={a.mean():.2f} vs 无事件 n={len(b)} 平均={b.mean():.2f} | diff={fmt(diff)} p={fmt(p,3)}")
            rows.append({"strategy": strat, "bucket": "持仓期事件", "n": len(a), "win_rate": (a > 0).mean(), "avg_pts": a.mean(), "p": p})

        # 事件类别分组（开仓前24h内）
        ev_before = high[high["time_utc"] < merged["signal_time"].max()]
        for cat in ["FOMC利率决议", "CPI通胀", "非农就业", "EIA原油库存", "失业率/初请", "美债拍卖/收益率"]:
            evs = high[high["category"] == cat]
            if len(evs) == 0:
                continue
            et = evs["time_utc"].to_numpy(dtype="datetime64[ns]")
            st = merged["signal_time"].to_numpy(dtype="datetime64[ns]")
            # 开仓前24h内发生过该类事件
            idx = np.searchsorted(et, st)
            within = np.zeros(len(st), dtype=bool)
            for i in range(len(st)):
                j = idx[i]
                if j > 0 and (st[i] - et[j - 1]) <= np.timedelta64(24, "h"):
                    within[i] = True
            if within.sum() == 0:
                continue
            a = merged[within]["weighted_pts"].to_numpy(float)
            b = merged[~within]["weighted_pts"].to_numpy(float)
            diff, lo, hi, p = bootstrap_diff(a, b)
            print(f"  前24h内[{cat}]: n={len(a)} 平均={a.mean():8.2f} vs n={len(b)} 平均={b.mean():8.2f} | diff={fmt(diff)} p={fmt(p,3)}")

    # 汇总表
    summ = pd.DataFrame(rows)
    summ.to_csv(REPORT_DIR / "事件邻近_汇总.csv", index=False, encoding="utf-8-sig")
    print("\n[已输出] 事件邻近_汇总.csv")


if __name__ == "__main__":
    main()
