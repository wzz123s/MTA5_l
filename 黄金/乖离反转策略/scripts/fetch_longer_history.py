# -*- coding: utf-8 -*-
"""抓取更长历史：XAUUSDm + USOILm 的 M30/H2/H4（2015-01-01 起，视终端深度）"""
import MetaTrader5 as mt5
import datetime
import pandas as pd
import numpy as np
from pathlib import Path

GOLD = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\raw")
OIL = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\raw_oil")
OIL.mkdir(parents=True, exist_ok=True)
mt5.initialize()

def fetch(symbol, outdir, start_year=2015):
    start = datetime.datetime(start_year, 1, 1)
    end = datetime.datetime.now()
    for tf, name in [(mt5.TIMEFRAME_M30, "M30"), (mt5.TIMEFRAME_H2, "H2"), (mt5.TIMEFRAME_H4, "H4")]:
        chunks = []
        cursor = start
        while cursor < end:
            chunk_end = min(cursor + datetime.timedelta(days=365), end)
            c = mt5.copy_rates_range(symbol, tf, cursor, chunk_end)
            if c is None or len(c) == 0:
                break
            chunks.append(c)
            cursor = chunk_end
        if not chunks:
            print(symbol, name, "NO DATA from", start_year)
            continue
        rates = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
        rates = np.unique(rates, axis=0)
        rates = rates[np.argsort(rates["time"])]
        df = pd.DataFrame(rates)
        df["date"] = pd.to_datetime(df["time"], unit="s", utc=True)
        df = df[["date", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]]
        df.to_csv(outdir / ("%s_%s.csv" % (symbol, name)), index=False)
        print(symbol, name, "rows:", len(df), "range:", df["date"].min().strftime('%Y-%m-%d'), "->", df["date"].max().strftime('%Y-%m-%d'))

fetch("XAUUSDm", GOLD, 2015)
fetch("USOILm", OIL, 2015)
mt5.shutdown()
