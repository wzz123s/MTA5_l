# -*- coding: utf-8 -*-
"""M3.3 稳健性验证：年度拆分、walk-forward(70/30)、成本敏感性（黄金 R 口径 / 原油 pts 口径）。
输入: baseline_{gold,oil}_trades.csv（已含逐笔 pnl）
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[2]


def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "validation" / f"baseline_{name}_trades.csv", parse_dates=["entry_time"])
    col = "pnl_r_units" if name == "gold" else "pnl_pts"
    df["pnl"] = df[col]
    return df


def pf(pnls: np.ndarray) -> float:
    w = pnls[pnls > 0].sum()
    l = -pnls[pnls <= 0].sum()
    return round(w / l, 3) if l > 0 else 999.0


def robustness(name: str) -> None:
    df = load(name)
    df["year"] = df["entry_time"].dt.year
    print(f"\n======== {name} ========")
    # 年度
    y = df.groupby("year")["pnl"].agg(n="size", ev="sum")
    y["pf"] = df.groupby("year")["pnl"].apply(lambda s: pf(s.to_numpy()))
    y["pos"] = df.groupby("year")["pnl"].apply(lambda s: (s > 0).mean()).round(3)
    print("== 年度拆分 ==")
    print(y.to_string())
    # walk-forward 70/30（时间顺序）
    srt = df.sort_values("entry_time").reset_index(drop=True)
    cut = max(int(len(srt) * 0.70), 1)
    tr, te = srt.iloc[:cut], srt.iloc[cut:]
    print("== walk-forward ==")
    print(f"train n={len(tr)} ev={tr['pnl'].sum():.1f} pf={pf(tr['pnl'].to_numpy())} | "
          f"test n={len(te)} ev={te['pnl'].sum():.1f} pf={pf(te['pnl'].to_numpy())}")
    # 成本敏感性：黄金 R 单位成本近似（0.05% 对应 R 需按 stop_dist 折算——简化：直接扣固定 R/笔）
    print("== 成本敏感性 ==")
    if name == "gold":
        for cost_r in (0.05, 0.15, 0.30, 0.50):
            pn = df["pnl"].to_numpy() - cost_r
            print(f"cost={cost_r}R/笔: pf={pf(pn)} ev={pn.sum():.0f}")
    else:
        for cost_pt in (0.02, 0.05, 0.10):
            pn = df["pnl"].to_numpy() - cost_pt
            print(f"cost={cost_pt}pt/笔: pf={pf(pn)} ev={pn.sum():.1f}")
    df.to_csv(ROOT / "data" / "validation" / f"robustness_{name}_trades.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    robustness("gold")
    robustness("oil")
