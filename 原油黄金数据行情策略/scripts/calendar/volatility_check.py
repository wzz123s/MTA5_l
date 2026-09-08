# -*- coding: utf-8 -*-
"""M2.3 波动率验证：高影响事件窗口内 |收益率| 倍数 vs 基线。
窗口：±30m / ±60m / 后2h / 后4h；分品种分事件类别。
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[2]

WINDOWS = [
    ("pm30", np.timedelta64(-30, "m"), np.timedelta64(30, "m")),
    ("pm60", np.timedelta64(-60, "m"), np.timedelta64(60, "m")),
    ("post2h", np.timedelta64(0, "m"), np.timedelta64(120, "m")),
    ("post4h", np.timedelta64(0, "m"), np.timedelta64(240, "m")),
]


def analyze(symbol: str, tf: str, events: pd.DataFrame, name: str) -> None:
    if symbol == "XAUUSDm":
        f = ROOT / "data" / "raw" / "mt5_history" / "gold_mt5_20190101" / f"{symbol}_{tf}.csv"
    else:
        f = ROOT / "data" / "raw" / "mt5_history" / "oil_mt5_20190101" / f"{symbol}_{tf}.csv"
    df = pd.read_csv(f, parse_dates=["time"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["ret"] = df["close"].pct_change().abs()
    base = float(df["ret"].mean())
    et = events["event_time_utc"].to_numpy().astype("datetime64[ns]")
    ts = df["time"].to_numpy().astype("datetime64[ns]")
    rows = []
    for wname, lo, hi in WINDOWS:
        in_mask = np.zeros(len(df), dtype=bool)
        for ev_t in et:
            in_mask |= (ts >= ev_t + lo) & (ts <= ev_t + hi)
        vals = df.loc[in_mask, "ret"]
        ratio = float(vals.mean() / base) if len(vals) and base > 0 else np.nan
        rows.append({"window": wname, "n_bars": int(in_mask.sum()),
                     "mean_ret": round(float(vals.mean()), 6), "ratio": round(ratio, 2)})
    res = pd.DataFrame(rows)
    print(f"== {name} ({tf}) baseline|ret|={base:.6f} ==")
    print(res.to_string(index=False))
    res.to_csv(ROOT / "data" / "validation" / f"volatility_{name}.csv", index=False, encoding="utf-8-sig")
    cats = events["category"].value_counts().head(12).index
    cat_rows = []
    for cat in cats:
        sub = events[events["category"] == cat]
        in_mask = np.zeros(len(df), dtype=bool)
        for ev_t in sub["event_time_utc"].to_numpy().astype("datetime64[ns]"):
            in_mask |= (ts >= ev_t - np.timedelta64(60, "m")) & (ts <= ev_t + np.timedelta64(60, "m"))
        vals = df.loc[in_mask, "ret"]
        if len(vals) and base > 0:
            cat_rows.append({"category": cat, "n_events": len(sub), "n_bars": int(in_mask.sum()),
                             "ratio": round(float(vals.mean() / base), 2)})
    cres = pd.DataFrame(cat_rows).sort_values("ratio", ascending=False)
    print(f"== {name} by category (pm60) ==")
    print(cres.to_string(index=False))
    cres.to_csv(ROOT / "data" / "validation" / f"volatility_{name}_bycat.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    ev = pd.read_csv(ROOT / "data" / "processed" / "calendar_events.csv", parse_dates=["event_time_utc"])
    ev = ev[ev["is_blackout_event"] == True].copy()  # noqa: E712
    ev["event_time_utc"] = pd.to_datetime(ev["event_time_utc"], utc=True)
    analyze("XAUUSDm", "M30", ev, "gold")
    analyze("USOILm", "M30", ev, "oil")
