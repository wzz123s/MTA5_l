# -*- coding: utf-8 -*-

"""验证 +30min 配对: Python 滚动 counter vs EA"""
import os
import sys

os.chdir(r"F:\use_code_MTA5_l\黄金/30m2H策略\参考实现工程")
sys.path.insert(0, r"F:\use_code_MTA5_l\黄金/30m2H策略\参考实现工程")
sys.path.insert(0, r"F:\use_code_MTA5_l\黄金/30m2H策略\参考实现工程\scripts")

import pandas as pd

import _current_baseline as base

pairs = [
    ("2025-10-07 13:30", "2025-10-07 14:00"),
    ("2025-10-09 00:00", "2025-10-09 00:30"),
    ("2025-10-14 17:30", "2025-10-14 18:00"),
    ("2025-10-20 11:30", "2025-10-20 12:00"),
    ("2022-11-14 15:30", "2022-11-14 16:00"),
    ("2024-04-03 15:30", "2024-04-03 16:00"),
]

df, h2, m15 = base.load_market_context()
codes, roll_pn = base.rolling_merged_postn(df)
df["tstr"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d %H:%M")
df = df.reset_index(drop=True)

act = pd.read_csv(
    r"F:\use_code_MTA5_l\黄金/30m2H策略\data\validation\final_ea_alignment_20260811\30m2H_strategy_trade_ledger_v335.csv",
    encoding="utf-8-sig",
)
act["tstr"] = pd.to_datetime(act["signal_anchor_time"]).dt.strftime("%Y-%m-%d %H:%M")
ea_src = {}
for _, r in act.iterrows():
    ea_src.setdefault(r["tstr"], r["signal_src"])

for ea_t, py_t in pairs:
    i1 = df.index[df["tstr"] == ea_t]
    i2 = df.index[df["tstr"] == py_t]
    if len(i1) == 0 or len(i2) == 0:
        print(f"{ea_t}/{py_t}: 无数据")
        continue
    i1, i2 = i1[0], i2[0]
    print(
        f"EA {ea_t} (src={ea_src.get(ea_t, '?')}): roll_pn={roll_pn[i1]}  |  "
        f"Python {py_t}: roll_pn={roll_pn[i2]}"
    )
