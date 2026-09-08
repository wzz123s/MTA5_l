# -*- coding: utf-8 -*-
"""M2.2 事件邻近度分析：每笔交易计算与最近高影响黑名单事件的间距，按窗口分组对比。
输出: data/validation/event_proximity_{gold,oil}.csv + 汇总
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[2]

WINDOWS = [1, 2, 4, 8, 12, 24]


def load_events() -> pd.DataFrame:
    ev = pd.read_csv(ROOT / "data" / "processed" / "calendar_events.csv", parse_dates=["event_time_utc"])
    # 黑名单事件：高影响 + 白名单币种
    ev = ev[ev["is_blackout_event"] == True].copy()  # noqa: E712
    ev["event_time_utc"] = pd.to_datetime(ev["event_time_utc"], utc=True)
    return ev.sort_values("event_time_utc").reset_index(drop=True)


def analyze(trades: pd.DataFrame, events: pd.DataFrame, name: str) -> None:
    t = trades.copy()
    t["entry_time"] = pd.to_datetime(t["entry_time"], utc=True)
    t = t.sort_values("entry_time").reset_index(drop=True)
    et = events["event_time_utc"].to_numpy().astype("datetime64[ns]")
    # 每笔交易：开仓前最近事件间隔（小时，负=事件在开仓前）——et 升序，用 searchsorted 找最后一个 <= ts 的事件
    gaps_before = []
    for ts in t["entry_time"].to_numpy().astype("datetime64[ns]"):
        idx = np.searchsorted(et, ts, side="right") - 1
        gaps_before.append(float((ts - et[idx]) / np.timedelta64(1, "h")) if idx >= 0 else np.nan)
    t["gap_before_h"] = gaps_before
    # 持仓期间是否有事件（entry_time ~ exit_time）
    t["exit_time"] = pd.to_datetime(t["exit_time"], utc=True)
    t["event_within_trade"] = False
    for i, row in t.iterrows():
        mask = (et >= row["entry_time"].to_datetime64()) & (et <= row["exit_time"].to_datetime64())
        t.loc[i, "event_within_trade"] = bool(mask.any())
    # 窗口分组统计（gap_before 绝对值 <= 窗口 → 窗口内开仓）
    rows = []
    for w in WINDOWS:
        inw = t[abs(t["gap_before_h"]) <= w]
        outw = t[abs(t["gap_before_h"]) > w]
        for label, g in (("in", inw), ("out", outw)):
            if len(g) == 0:
                continue
            pnls = g["pnl_pts" if "pnl_pts" in g.columns else "pnl_r_units"].to_numpy()
            wins = pnls[pnls > 0]; losses = pnls[pnls <= 0]
            gw = wins.sum(); gl = -losses.sum()
            rows.append({
                "window_h": w, "group": label, "n": len(g),
                "wr": round(len(wins) / len(g), 3),
                "avg": round(float(pnls.mean()), 3),
                "ev": round(float(pnls.sum()), 2),
                "pf": round(gw / gl, 3) if gl > 0 else 999,
            })
    # 持仓遇事件 vs 未遇
    for label, g in (("event_in_trade", t[t["event_within_trade"] == True]), ("no_event", t[t["event_within_trade"] == False])):
        if len(g) == 0:
            continue
        pnls = g["pnl_pts" if "pnl_pts" in g.columns else "pnl_r_units"].to_numpy()
        wins = pnls[pnls > 0]; losses = pnls[pnls <= 0]
        rows.append({
            "window_h": -1, "group": label, "n": len(g),
            "wr": round(len(wins) / len(g), 3),
            "avg": round(float(pnls.mean()), 3),
            "ev": round(float(pnls.sum()), 2),
            "pf": round(wins.sum() / abs(losses.sum()), 3) if abs(losses.sum()) > 0 else 999,
        })
    res = pd.DataFrame(rows)
    out = ROOT / "data" / "validation" / f"event_proximity_{name}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    res.to_csv(out, index=False, encoding="utf-8-sig")
    t.to_csv(ROOT / "data" / "validation" / f"trades_with_events_{name}.csv", index=False, encoding="utf-8-sig")
    print(f"== {name} ==")
    print(res.to_string(index=False))


if __name__ == "__main__":
    events = load_events()
    gold = pd.read_csv(ROOT / "data" / "validation" / "baseline_gold_trades.csv")
    analyze(gold, events, "gold")
    oil = pd.read_csv(ROOT / "data" / "validation" / "baseline_oil_trades.csv")
    analyze(oil, events, "oil")
