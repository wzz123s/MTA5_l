# -*- coding: utf-8 -*-
"""补抓 XAUUSDm H1/H6 更长历史（2015 起）"""
import MetaTrader5 as mt5
import datetime
import pandas as pd
import numpy as np
from pathlib import Path

GOLD = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\raw")
mt5.initialize()
start = datetime.datetime(2015, 1, 1)
end = datetime.datetime.now()
for tf, name in [(mt5.TIMEFRAME_H1, "H1"), (mt5.TIMEFRAME_H6, "H6")]:
    chunks = []
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + datetime.timedelta(days=365), end)
        c = mt5.copy_rates_range("XAUUSDm", tf, cursor, chunk_end)
        if c is None or len(c) == 0:
            break
        chunks.append(c)
        cursor = chunk_end
    if not chunks:
        print(name, "NO DATA")
        continue
    rates = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
    rates = np.unique(rates, axis=0)
    rates = rates[np.argsort(rates["time"])]
    df = pd.DataFrame(rates)
    df["date"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df[["date", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]]
    df.to_csv(GOLD / ("XAUUSDm_" + name + ".csv"), index=False)
    print(name, "rows:", len(df), "range:", df["date"].min().strftime('%Y-%m-%d'), "->", df["date"].max().strftime('%Y-%m-%d'))
mt5.shutdown()
