# -*- coding: utf-8 -*-
"""V反策略 P3：信号验证 v0.2（止损方向修正版）

退出规则：
- 止损：空单 high>=stop / 多单 low<=stop（止损单固定 -1.0R）
- 第一目标：信号周期价格回归 SMA55
- 反向穿越：空单 good / 多单 bad → 平仓
- 时间上限：黄金 M30=240根；原油 H2=120根
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

PROC = Path(__file__).resolve().parents[1] / "data" / "processed"
SIG = Path(__file__).resolve().parents[1] / "data" / "signals"

def simulate(df: pd.DataFrame, row, max_bars: int):
    direction = row["dir"]
    entry = float(row["entry"])
    stop = float(row["stop"])
    m = df["dt"] == row["entry_dt"]
    if not m.any():
        return None
    idx = df.index.get_loc(df.index[m][0])
    start = idx + 1
    end = min(start + max_bars, len(df))
    if start >= len(df):
        return None
    stop_dist = abs(entry - stop)
    if stop_dist <= 0:
        return None
    for j in range(start, end):
        bar = df.iloc[j]
        high, low, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
        sma55 = bar["sma55"]
        if direction == "short":
            if high >= stop:
                return {"R": -1.0, "exit_reason": "stop", "exit_dt": bar["dt"], "target1_hit": False}
            if not pd.isna(sma55) and close <= sma55:
                return {"R": (entry - close) / stop_dist, "exit_reason": "target1", "exit_dt": bar["dt"], "target1_hit": True}
            if bar["dir"] == "good":
                return {"R": (entry - close) / stop_dist, "exit_reason": "reverse_cross", "exit_dt": bar["dt"], "target1_hit": False}
        else:
            if low <= stop:
                return {"R": -1.0, "exit_reason": "stop", "exit_dt": bar["dt"], "target1_hit": False}
            if not pd.isna(sma55) and close >= sma55:
                return {"R": (close - entry) / stop_dist, "exit_reason": "target1", "exit_dt": bar["dt"], "target1_hit": True}
            if bar["dir"] == "bad":
                return {"R": (close - entry) / stop_dist, "exit_reason": "reverse_cross", "exit_dt": bar["dt"], "target1_hit": False}
    last = df.iloc[end - 1]
    close = float(last["close"])
    r = (entry - close) / stop_dist if direction == "short" else (close - entry) / stop_dist
    return {"R": r, "exit_reason": "timeout", "exit_dt": last["dt"], "target1_hit": False}

def summarize(trades: pd.DataFrame, label: str) -> None:
    if trades.empty:
        print(f"[{label}] 无交易")
        return
    wins = trades[trades["R"] > 0]
    losses = trades[trades["R"] <= 0]
    gw = float(wins["R"].sum()) if not wins.empty else 0.0
    gl = -float(losses["R"].sum()) if not losses.empty else 0.0
    pf = gw / gl if gl > 0 else float("inf")
    ev = float(trades["R"].mean())
    wr = len(wins) / len(trades)
    t2 = trades.copy()
    t2["year"] = pd.to_datetime(t2["signal_dt"], utc=True).dt.year
    yearly = t2.groupby("year").agg(n=("R", "size"), ev=("R", "mean"))
    t2 = t2.sort_values("signal_dt").reset_index(drop=True)
    split = int(len(t2) * 0.7)
    tr = t2.iloc[:split]
    te = t2.iloc[split:]
    pf_tr = float(tr[tr["R"] > 0]["R"].sum()) / max(-float(tr[tr["R"] <= 0]["R"].sum()), 1e-9) if len(tr) else float("nan")
    pf_te = float(te[te["R"] > 0]["R"].sum()) / max(-float(te[te["R"] <= 0]["R"].sum()), 1e-9) if len(te) else float("nan")
    max_dd = 0
    cur = 0
    for r in t2["R"]:
        cur = cur + 1 if r <= 0 else 0
        max_dd = max(max_dd, cur)
    print(f"[{label}] n={len(trades)} 胜率={wr:.1%} EV={ev:.3f}R PF={pf:.2f} 训练PF={pf_tr:.2f} 测试PF={pf_te:.2f} 最大连亏={max_dd}")
    print(f"    退出: {trades['exit_reason'].value_counts().to_dict()} | 目标1达标率: {trades['target1_hit'].mean():.1%}")
    print(f"    年度: {yearly.to_string().replace(chr(10), ' | ')}")

def run(symbol: str, sig_tf: str, cand_file: str, out_file: str, max_bars: int) -> None:
    cand = pd.read_csv(SIG / cand_file)
    df = pd.read_csv(PROC / f"{symbol}_{sig_tf}_features.csv")
    df["dt"] = pd.to_datetime(df["dt"], utc=True)
    trades = []
    for _, row in cand.iterrows():
        res = simulate(df, row, max_bars)
        if res:
            for k in ["signal", "dir", "signal_dt", "entry", "stop", "threshold", "gate_bias55_pct"]:
                res[k] = row[k]
            trades.append(res)
    t = pd.DataFrame(trades)
    t.to_csv(SIG / out_file, index=False)
    summarize(t, f"{symbol} 全部")
    if not t.empty:
        summarize(t[t["dir"] == "short"], f"{symbol} S1做空")
        if (t["dir"] == "long").any():
            summarize(t[t["dir"] == "long"], f"{symbol} S2做多")

if __name__ == "__main__":
    run("XAUUSDm", "M30", "candidates_XAUUSDm.csv", "trades_XAUUSDm.csv", 240)
    print()
    run("USOILm", "H2", "candidates_USOILm.csv", "trades_USOILm.csv", 120)
