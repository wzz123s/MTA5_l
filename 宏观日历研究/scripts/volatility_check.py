# -*- coding: utf-8 -*-
"""阶段3：验证高影响事件是否引发波动率尖峰（K线实测）。

对每个高影响事件，计算事件前后窗口的 |收益率|，与全样本基线对比。
窗口: ±30m / ±60m / 事件后60m / 事件后4h
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
SYMBOLS = {
    "XAUUSDm": ("黄金/1H_M30_4H策略/data/raw/mt5_history/1h_m30_4h_live/XAUUSDm_M30.csv", "金"),
    "USOILm":  ("原油/原油2H策略/data/raw/mt5_history/usoil2h_live/USOILm_M30.csv", "油"),
}


def load_events(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep="|", dtype={"event_id": "int64", "time": "int64"})
    df["time_utc"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df["category"] = df["event_name"].map(classify)
    df["is_high"] = df["importance"] >= 3  # 实测本终端build: importance=0..3, 3=HIGH（impact_type 恒为0/1/2）
    return df


def load_bars(rel: str) -> pd.DataFrame:
    df = pd.read_csv(ROOT / rel, parse_dates=["time"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df.sort_values("time").reset_index(drop=True)


def ret_window(bars: pd.DataFrame, t: pd.Timestamp, before_h: float, after_h: float):
    """返回 [t-before_h, t+after_h] 窗口的收益率（收盘-开盘 或 首末close）。"""
    mask = (bars["time"] >= t - pd.Timedelta(hours=before_h)) & (bars["time"] <= t + pd.Timedelta(hours=after_h))
    sub = bars[mask]
    if len(sub) < 2:
        return np.nan
    return float(sub["close"].iloc[-1] / sub["open"].iloc[0] - 1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", default=str(RESEARCH / "data" / "calendar_export.csv"))
    args = ap.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    events = load_events(Path(args.events))
    high = events[events["is_high"]].reset_index(drop=True)
    print(f"高影响事件: {len(high)}")

    windows = [("±30m", 0.5, 0.5), ("±60m", 1.0, 1.0), ("后60m", 0.0, 1.0), ("后4h", 0.0, 4.0)]
    out_rows = []
    for sym, (bars_rel, label) in SYMBOLS.items():
        bars = load_bars(bars_rel)
        t0, t1 = bars["time"].min(), bars["time"].max()
        print(f"\n===== {sym} ({label}) K线 {t0} ~ {t1} n={len(bars)} =====")
        # 基线：全部可计算窗口的 |ret| 均值
        base = {}
        for wname, bh, ah in windows:
            mask = (bars["time"] >= t0 + pd.Timedelta(hours=bh)) & (bars["time"] <= t1 - pd.Timedelta(hours=ah))
            sub = bars[mask]
            if len(sub) < 2:
                continue
            r = sub["close"].values[1:] / sub["close"].values[:-1] - 1.0
            base[wname] = np.abs(r).mean()
        print("基线平均|收益|: " + ", ".join(f"{k}={v:.5f}" for k, v in base.items()))

        evs = high[(high["time_utc"] >= t0) & (high["time_utc"] <= t1)]
        rows = []
        for _, ev in evs.iterrows():
            t = ev["time_utc"]
            row = {"time": t, "category": ev["category"], "event": ev["event_name"]}
            for wname, bh, ah in windows:
                row[wname] = abs(ret_window(bars, t, bh, ah))
            rows.append(row)
        evdf = pd.DataFrame(rows)
        if evdf.empty:
            continue
        print(f"\n事件窗口平均|收益| vs 基线倍数:")
        ratio_rows = []
        for wname, _, _ in windows:
            if wname not in base:
                continue
            evmean = evdf[wname].mean()
            ratio = evmean / base[wname] if base[wname] > 0 else np.nan
            print(f"  {wname:>6}: 事件={evmean:.5f} 基线={base[wname]:.5f} 倍数={ratio:.2f}x")
            ratio_rows.append({"symbol": sym, "window": wname, "event_mean_abs_ret": evmean,
                               "baseline_mean_abs_ret": base[wname], "ratio": ratio})
        out_rows.extend(ratio_rows)

        # 按类别
        print("\n按类别(±60m窗口倍数):")
        for cat, g in evdf.groupby("category"):
            if len(g) < 5:
                continue
            m = g["±60m"].mean()
            r = m / base["±60m"] if base.get("±60m") else np.nan
            print(f"  {cat:>12}: n={len(g):>4} 倍数={r:.2f}x")
            out_rows.append({"symbol": sym, "window": "±60m_bycat", "category": cat, "event_mean_abs_ret": m,
                             "baseline_mean_abs_ret": base.get("±60m"), "ratio": r})

    out = pd.DataFrame(out_rows)
    out_path = REPORT_DIR / "波动率验证_汇总.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n[已输出] {out_path}")


if __name__ == "__main__":
    main()
