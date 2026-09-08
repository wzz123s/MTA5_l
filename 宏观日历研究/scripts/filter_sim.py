# -*- coding: utf-8 -*-
"""阶段4：事件过滤/避险变体模拟（因果重放）。

V1 开仓过滤: 距下一个高影响事件 < T 小时 不开仓
V2 事件平仓: 持仓期间遇高影响事件 -> 事件后第一根M30 bar开盘价平仓(因果) + 滑点
V3 = V1(T=2) + V2
V4 动态减半: 事件窗口内开仓的仓位点数减半（风险近似）
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
RESEARCH = ROOT / "宏观日历研究"
sys.path.insert(0, str(RESEARCH / "scripts"))
from classify_events import classify  # noqa: E402

REPORT_DIR = RESEARCH / "报告"
# pts_per_price: 各策略交易清单中"点数"与价格的换算（黄金三套x1, 乖离反转x100, 原油x1000）
STRATEGIES = {
    "1H_M30_4H": dict(dir="黄金/1H_M30_4H策略", bars="data/raw/mt5_history/1h_m30_4h_live/XAUUSDm_M30.csv", slp_pts=0.3, ppp=1.0),
    "30m2H":     dict(dir="黄金/30m2H策略",     bars="data/raw/mt5_history/30m2h_live/XAUUSDm_M30.csv", slp_pts=0.3, ppp=1.0),
    "2H_M30_6H": dict(dir="黄金/2H_M30_6H策略", bars="data/raw/mt5_history/2h_m30_6h_live/XAUUSDm_M30.csv", slp_pts=0.3, ppp=1.0),
    "BiasReversal": dict(dir="黄金/乖离反转策略", bars="data/raw/mt5_history/bias_reversal_live/XAUUSDm_M30.csv", slp_pts=30.0, ppp=100.0),
    "USOIL2H":   dict(dir="原油/原油2H策略",    bars="data/raw/mt5_history/usoil2h_live/USOILm_M30.csv", slp_pts=30.0, ppp=1000.0),
    "USOIL4H":   dict(dir="原油/原油4H门策略",  bars="data/raw/mt5_history/usoil_4h_gate_live/USOILm_M30.csv", slp_pts=30.0, ppp=1000.0),
}


def load_events(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="|", dtype={"event_id": "int64", "time": "int64"})
    df["time_utc"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df["category"] = df["event_name"].map(classify)
    df["is_high"] = df["importance"] >= 3  # 实测本终端build: importance=0..3, 3=HIGH（impact_type 恒为0/1/2）
    return df


def load_trades(strat: str) -> pd.DataFrame:
    path = ROOT / "observation_dashboard" / strat / "trades_snapshot.csv"
    df = pd.read_csv(path, parse_dates=["signal_time", "stage3_exit_time"])
    df["signal_time"] = pd.to_datetime(df["signal_time"], utc=True)
    df["stage3_exit_time"] = pd.to_datetime(df["stage3_exit_time"], utc=True)
    df["strat"] = strat
    return df


def load_bars(cfg) -> pd.DataFrame:
    path = ROOT / cfg["dir"] / cfg["bars"]
    df = pd.read_csv(path, parse_dates=["time"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.sort_values("time").reset_index(drop=True)


def next_bar_open_after(bars: pd.DataFrame, t: pd.Timestamp):
    ts = bars["time"].to_numpy(dtype="datetime64[ns]")
    i = np.searchsorted(ts, t.to_datetime64(), side="right")
    if i < len(bars):
        return float(bars["open"].iloc[i])
    return None


def stats(pts) -> dict:
    p = np.asarray(pts, dtype=float)
    if len(p) == 0:
        return {"n": 0, "win_rate": np.nan, "avg_pts": np.nan, "total_pts": 0.0, "profit_factor": np.nan, "max_dd_pts": 0.0}
    eq = np.cumsum(p)
    dd = (np.maximum.accumulate(eq) - eq).max()
    wins = p[p > 0].sum()
    losses = -p[p < 0].sum()
    return {
        "n": len(p), "win_rate": (p > 0).mean(), "avg_pts": p.mean(), "total_pts": p.sum(),
        "profit_factor": wins / losses if losses > 0 else np.inf, "max_dd_pts": dd,
    }


def fmt_stats(s: dict) -> str:
    pf = "inf" if np.isinf(s["profit_factor"]) else f"{s['profit_factor']:.2f}"
    return (f"n={s['n']:>4} 胜率={s['win_rate']:.1%} 平均={s['avg_pts']:8.2f} "
            f"合计={s['total_pts']:10.1f} PF={pf} MaxDD={s['max_dd_pts']:.1f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default=str(RESEARCH / "data" / "calendar_export.csv"))
    ap.add_argument("--ts", nargs="+", type=float, default=[1, 2, 4, 8])
    args = ap.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events(Path(args.events))
    high = events[events["is_high"]].sort_values("time_utc").reset_index(drop=True)
    print(f"高影响事件总数: {len(high)}  [{high['time_utc'].min()} ~ {high['time_utc'].max()}]")

    all_rows = []
    for strat, cfg in STRATEGIES.items():
        trades = load_trades(strat)
        if trades.empty:
            print(f"\n===== {strat}: 无交易 =====")
            continue
        bars = load_bars(cfg)
        eh = high["time_utc"].to_numpy(dtype="datetime64[ns]")
        st = trades["signal_time"].to_numpy(dtype="datetime64[ns]")
        ex = trades["stage3_exit_time"].to_numpy(dtype="datetime64[ns]")
        idx = np.searchsorted(eh, st)
        gap_after = np.array([float((eh[j] - st[i]) / np.timedelta64(1, "h")) if j < len(eh) else np.nan
                              for i, j in enumerate(idx)])

        ev_in_trade = np.zeros(len(trades), dtype=bool)
        ev_time = np.full(len(trades), np.datetime64("NaT", "ns"))
        for i in range(len(trades)):
            j = idx[i]
            while j < len(eh) and eh[j] < ex[i]:
                ev_in_trade[i] = True
                ev_time[i] = eh[j]
                break

        base = stats(trades["weighted_pts"])
        print(f"\n========== {strat} 基线: {fmt_stats(base)} ==========")
        all_rows.append({"strategy": strat, "variant": "baseline", **base})

        for T in args.ts:
            keep = gap_after >= T
            kept = stats(trades.loc[keep, "weighted_pts"])
            dropped = stats(trades.loc[~keep, "weighted_pts"])
            print(f"  V1[T={T:g}h] 保留 {fmt_stats(kept)} | 过滤 {fmt_stats(dropped)}")
            all_rows.append({"strategy": strat, "variant": f"V1_T{T:g}h", **kept, "dropped_n": int(dropped["n"])})

        if ev_in_trade.any():
            pts2 = trades["weighted_pts"].astype(float).copy()
            forced = 0
            for i in range(len(trades)):
                if not ev_in_trade[i]:
                    continue
                p = next_bar_open_after(bars, pd.Timestamp(ev_time[i]))
                if p is None:
                    continue
                entry = float(trades["entry"].iloc[i])
                d = 1.0 if trades["dir"].iloc[i] == "L" else -1.0
                pts2.iloc[i] = d * (p - entry) * cfg["ppp"] - cfg["slp_pts"]
                forced += 1
            v2 = stats(pts2)
            print(f"  V2[事件平仓] 平仓{forced}笔: {fmt_stats(v2)}")
            all_rows.append({"strategy": strat, "variant": "V2_event_close", **v2, "forced": forced})

            for T in [2]:
                keep = gap_after >= T
                pts3 = pts2[np.asarray(keep)]
                v3 = stats(pts3)
                print(f"  V3[T=2h+平仓] 保留 {fmt_stats(v3)}")
                all_rows.append({"strategy": strat, "variant": f"V3_T{T:g}h", **v3, "dropped_n": int((~keep).sum()), "forced": forced})
        else:
            print("  V2 跳过（无持仓期事件样本）")

        for T in [2, 4]:
            mask = gap_after <= T
            pts4 = trades["weighted_pts"].astype(float).copy()
            pts4[mask] = pts4[mask] * 0.5
            v4 = stats(pts4)
            print(f"  V4[T={T:g}h减半] 影响{int(mask.sum())}笔: {fmt_stats(v4)}")
            all_rows.append({"strategy": strat, "variant": f"V4_T{T:g}h", **v4, "halved": int(mask.sum())})

    out = pd.DataFrame(all_rows)
    out_path = REPORT_DIR / "过滤变体_汇总.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n[已输出] {out_path}")


if __name__ == "__main__":
    main()
