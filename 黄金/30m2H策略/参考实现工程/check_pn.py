# -*- coding: utf-8 -*-
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "scripts"))
import pandas as pd
import _current_baseline as base

df, h2, m15 = base.load_market_context()
codes, roll_pn = base.rolling_merged_postn(df)
df["tstr"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d %H:%M")
df = df.reset_index(drop=True)
i = df.index[df["tstr"] == "2025-10-07 13:30"][0]
print(f"i={i}  roll_pn={roll_pn[i]}  code={codes[i]}")
print(f"close={df['close'].iloc[i]:.3f}  sma13={df['SMA_13'].iloc[i]:.3f}")
print(f"stop>=entry: {df['SMA_13'].iloc[i] >= df['close'].iloc[i]}")
print(f"sd={abs(df['close'].iloc[i]-df['SMA_13'].iloc[i]):.2f}")
# 前 2 根 bar 的 counter
for t in ["2025-10-07 13:00", "2025-10-07 13:30", "2025-10-07 14:00"]:
    j = df.index[df["tstr"] == t][0]
    print(f"{t}: roll_pn={roll_pn[j]} code={codes[j]}")
