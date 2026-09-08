# -*- coding: utf-8 -*-
"""Signal validator - historical signal export for EA validation."""
import sys, os, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import MetaTrader5 as mt5
import pandas as pd
import numpy as np

CONFIG = {
    "mt5_path": r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe",
    "account": 277752085,
    "password": "Wazz20501166!",
    "server": "Exness-MT5Trial5",
    "symbol": "XAUUSDm",
    "max_bars": 500,     # keep small for speed
    "sma_fast": 5,
    "sma_slow": 13,
    "h2_threshold": 0.5,
}

def smma(series, n):
    r = np.full(len(series), np.nan)
    r[n-1] = series[:n].mean()
    for i in range(n, len(series)):
        r[i] = (series[i] + (n-1) * r[i-1]) / n
    return r

def run():
    t0 = time.time()
    if not mt5.initialize(path=CONFIG["mt5_path"]):
        print(f"Init failed: {mt5.last_error()}"); return
    mt5.login(login=CONFIG["account"], password=CONFIG["password"], server=CONFIG["server"])
    print(f"Connected in {time.time()-t0:.1f}s")

    # Load M30 and H2 data
    m30 = mt5.copy_rates_from_pos(CONFIG["symbol"], mt5.TIMEFRAME_M30, 0, CONFIG["max_bars"])
    h2  = mt5.copy_rates_from_pos(CONFIG["symbol"], mt5.TIMEFRAME_H2,  0, CONFIG["max_bars"])
    print(f"Load time: {time.time()-t0:.1f}s | M30={len(m30)} H2={len(h2)}")
    mt5.shutdown()

    df_m30 = pd.DataFrame(m30)
    df_h2  = pd.DataFrame(h2)
    df_m30["time"] = pd.to_datetime(df_m30["time"], unit="s")
    df_h2["time"]  = pd.to_datetime(df_h2["time"], unit="s")

    m30_close = df_m30["close"].values
    h2_close  = df_h2["close"].values

    m30_sf = smma(m30_close, CONFIG["sma_fast"])
    m30_ss = smma(m30_close, CONFIG["sma_slow"])
    h2_sf  = smma(h2_close,  CONFIG["sma_fast"])
    h2_ss  = smma(h2_close,  CONFIG["sma_slow"])

    warmup = CONFIG["sma_slow"]

    # Build H2 lookup: for each M30 bar, find last H2 bar time <= M30 bar time
    h2_times = df_h2["time"].values

    records = []
    for i in range(warmup, len(df_m30) - 1):
        m30_time = df_m30["time"].iloc[i]
        c  = m30_close[i]
        mf = m30_sf[i]; ms = m30_ss[i]

        # M30 cross
        cross = 0
        if not (np.isnan(mf) or np.isnan(ms) or np.isnan(m30_sf[i+1]) or np.isnan(m30_ss[i+1])):
            curr_above = mf > ms; prev_above = m30_sf[i+1] > m30_ss[i+1]
            cross = 1 if (not prev_above and curr_above) else (-1 if (prev_above and not curr_above) else 0)

        # H2 direction: use last valid H2 SMA
        h2_dir = 0; h2_dist = 0.0
        for j in range(len(h2_times)-1, -1, -1):
            if h2_times[j] <= m30_time and not (np.isnan(h2_sf[j]) or np.isnan(h2_ss[j])) and h2_sf[j] != 0:
                hf = h2_sf[j]; hs = h2_ss[j]
                h2_dist = (hs - hf) / hf * 100
                h2_dir  = 1 if h2_dist > CONFIG["h2_threshold"] else (-1 if h2_dist < -CONFIG["h2_threshold"] else 0)
                break

        m30_dist = (ms - mf) / mf * 100 if mf != 0 else 0
        sig = "NO_SIGNAL"
        if cross == 1 and h2_dir == 1:  sig = "BUY"
        elif cross == -1 and h2_dir == -1: sig = "SELL"
        elif cross == 1:  sig = "M30_GOLDEN_no_H2"
        elif cross == -1: sig = "M30_DEAD_no_H2"

        records.append({
            "bar_time":   str(m30_time),
            "close":      c,
            "m30_sma5":   round(mf,3) if not np.isnan(mf) else None,
            "m30_sma13":  round(ms,3) if not np.isnan(ms) else None,
            "m30_dist%":  round(m30_dist,4),
            "m30_cross":  {1:"GOLDEN",-1:"DEAD",0:"NONE"}[cross],
            "h2_dist%":   round(h2_dist,4),
            "h2_dir":     {1:"BULL",-1:"BEAR",0:"NEUTRAL"}[h2_dir],
            "signal":      sig,
        })

    df_out = pd.DataFrame(records)
    df_out.to_csv("auto_trade/signals_export.csv", index=False, encoding="utf-8")

    buys  = (df_out["signal"] == "BUY").sum()
    sells = (df_out["signal"] == "SELL").sum()
    print(f"\nTotal completed bars: {len(df_out)}")
    print(f"  BUY signals:  {buys}")
    print(f"  SELL signals: {sells}")
    print(f"Output: auto_trade/signals_export.csv")
    print(f"\nLast 10 rows:")
    print(df_out[["bar_time","close","m30_dist%","h2_dist%","m30_cross","h2_dir","signal"]].tail(10).to_string(index=False))

if __name__ == "__main__":
    run()
