# -*- coding: utf-8 -*-
"""阶段3：模拟盘回放（v1.0 三段式规则逐笔结果）

对 sim_signals_*.csv 的信号按 v1.0 三段式退出回放：
  0.5仓@2R -> 1.0仓@4R -> 1.5仓@反向叉；止损 -3.0R（全仓）
输出：data/sim_results_<symbol>.csv
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
OUT = BASE / "data"

def load(symbol, tf):
    df = pd.read_csv(PROC / f"{symbol}_{tf}_features.csv")
    df["dt"] = pd.to_datetime(df["dt"], utc=True)
    return df

def replay(df, sig, max_bars):
    entry = float(sig["entry"]); stop = float(sig["stop"]); direction = sig["dir"]
    sd = abs(entry - stop)
    if sd <= 0: return None
    m = df["dt"] == sig["entry_dt"]
    if not m.any(): return None
    idx = df.index.get_loc(df.index[m][0])
    start = idx + 1
    end = min(start + max_bars, len(df))
    total = 0.0
    seg1 = False; seg2 = False
    for j in range(start, end):
        bar = df.iloc[j]
        high, low, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
        if direction == "short":
            if high >= stop:
                return {"R": -3.0, "exit": "stop", "exit_dt": bar["dt"]}
            if not seg1 and low <= entry - 2.0 * sd:
                total += 1.0; seg1 = True
            if seg1 and not seg2 and low <= entry - 4.0 * sd:
                total += 4.0; seg2 = True
            if bar["dir"] == "good":
                return {"R": total + 1.5 * (entry - close) / sd, "exit": "cross", "exit_dt": bar["dt"]}
        else:
            if low <= stop:
                return {"R": -3.0, "exit": "stop", "exit_dt": bar["dt"]}
            if not seg1 and high >= entry + 2.0 * sd:
                total += 1.0; seg1 = True
            if seg1 and not seg2 and high >= entry + 4.0 * sd:
                total += 4.0; seg2 = True
            if bar["dir"] == "bad":
                return {"R": total + 1.5 * (close - entry) / sd, "exit": "cross", "exit_dt": bar["dt"]}
    last = df.iloc[end - 1]
    close = float(last["close"])
    r = (entry - close) / sd if direction == "short" else (close - entry) / sd
    return {"R": total + 1.5 * r, "exit": "timeout", "exit_dt": last["dt"]}

def main():
    for symbol, sig_tf, max_bars in [("USOILm", "H2", 120), ("XAUUSDm", "M30", 240)]:
        sig_path = OUT / f"sim_signals_{symbol}.csv"
        if not sig_path.exists():
            continue
        sigs = pd.read_csv(sig_path)
        df = load(symbol, sig_tf)
        rows = []
        for _, s in sigs.iterrows():
            res = replay(df, s, max_bars)
            if res:
                sig_dt = s.get("dt") if "dt" in s.index else s.get("signal_dt")
                rows.append({"signal_dt": sig_dt, "dir": s["dir"], "entry": s["entry"], "stop": s["stop"], "exit": res["exit"], "exit_dt": res["exit_dt"], "R": round(res["R"], 2)})
        rt = pd.DataFrame(rows)
        rt.to_csv(OUT / f"sim_results_{symbol}.csv", index=False)
        print(f"[{symbol}] 回放完成 {len(rt)} 笔：")
        for _, r in rt.iterrows():
            print(f"  {r['signal_dt']} {r['dir']} entry={r['entry']:.3f} exit={r['exit']}@({r['exit_dt']}) R={r['R']:+.2f}")
        wins = rt[rt['R'] > 0]
        if len(rt):
            print(f"  胜率={len(wins)/len(rt):.0%} 总R={rt['R'].sum():+.2f} 平均R={rt['R'].mean():+.2f}")

if __name__ == "__main__":
    main()