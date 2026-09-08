# -*- coding: utf-8 -*-
"""V反策略 阶段3：模拟盘信号生成器 v1.1

v1.1 改进（复盘#1）：
  1. 最小止损距离：原油/黄金 stop_dist >= 0.3%（剔除微止损信号）
  2. 信号冷却：同品种同方向 48h 内只保留首个信号
  3. 事件窗口标记：高影响事件（CPI/FOMC/EIA/非农等）±2h 内信号打标（优先级高）
"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
OUT = BASE / "data"
CAL = Path(r"F:\use_code\MTA5_l\宏观日历研究\data\calendar_export.csv")
MIN_STOP = 0.003  # 0.3%
COOLDOWN_H = 48
EVENT_WIN_H = 2

def load(symbol, tf):
    df = pd.read_csv(PROC / f"{symbol}_{tf}_features.csv")
    df["dt"] = pd.to_datetime(df["dt"], utc=True)
    return df

TF_MIN = {"M15": 15, "M30": 30, "H1": 60, "H2": 120, "H4": 240, "H6": 360, "H8": 480, "D1": 1440, "W1": 10080}

def last_closed(df_hi, t, tf_gate, tf_sig):
    # 因果修复(2026-09-04): 门 bar 收盘 <= 信号 bar 收盘
    cutoff = t + pd.Timedelta(minutes=TF_MIN[tf_sig])
    m = (df_hi["dt"] + pd.Timedelta(minutes=TF_MIN[tf_gate])) <= cutoff
    if not m.any():
        return None
    return df_hi.loc[m].iloc[-1]

def load_events():
    kw = ["CPI", "FOMC", "EIA", "非农", "GDP", "PCE", "PPI", "失业率", "利率决议", "原油库存"]
    df = pd.read_csv(CAL, sep="|", usecols=["event_name", "importance", "time"])
    hi = df[df["importance"] >= 3]
    names = hi["event_name"].astype(str)
    mask = np.zeros(len(hi), dtype=bool)
    for k in kw:
        mask |= names.str.contains(k, na=False)
    return sorted(pd.to_datetime(hi.loc[mask, "time"], unit="s", utc=True).tolist())

def in_event(t, events):
    from bisect import bisect_left
    lo = t - pd.Timedelta(hours=EVENT_WIN_H)
    hi = t + pd.Timedelta(hours=EVENT_WIN_H)
    i = bisect_left(events, lo)
    return i < len(events) and events[i] <= hi

def cooldown_filter(rows, hours=COOLDOWN_H):
    """同方向冷却：按时间排序，48h 内同方向只保留首个"""
    rows = sorted(rows, key=lambda r: r['dt'])
    kept = []
    last_dt = {}
    for r in rows:
        d = r['dir']
        if d in last_dt and (r['dt'] - last_dt[d]) < pd.Timedelta(hours=hours):
            continue
        last_dt[d] = r['dt']
        kept.append(r)
    return kept

def oil_signals(days=120):
    df = load("USOILm", "H2")
    h4 = load("USOILm", "H4")
    cutoff = df['dt'].max() - pd.Timedelta(days=days)
    rows = []
    crosses = df[(df["dir"].isin(["bad", "good"])) & (df["dt"] >= cutoff)]
    for _, row in crosses.iterrows():
        t = row["dt"]
        g4 = last_closed(h4, t, "H4", "H2")
        if g4 is None or g4['seg_len'] < 8: continue
        if row["dir"] == "bad":
            if g4["bias55_pct"] < 2.5: continue
            direction, stop = "short", row["prev_seg_high_sma13"]
        else:
            if g4["bias55_pct"] > -2.5: continue
            direction, stop = "long", row["prev_seg_low_sma13"]
        if pd.isna(stop): continue
        idx = df.index.get_loc(row.name)
        if idx + 1 >= len(df): continue
        nb = df.iloc[idx + 1]
        entry = float(nb["open"])
        sd = abs(entry - float(stop))
        if sd <= 0 or sd / entry < MIN_STOP or sd / entry > 0.01: continue
        rows.append({"dt": t, "dir": direction, "entry_dt": nb["dt"], "entry": entry, "stop": float(stop), "sd_pct": round(sd / entry * 100, 2), "gate_seg_len": int(g4["seg_len"]), "gate_bias55": round(float(g4["bias55_pct"]), 2)})
    return pd.DataFrame(cooldown_filter(rows))

def gold_signals(days=120):
    df = load("XAUUSDm", "M30")
    h6 = load("XAUUSDm", "H6")
    cutoff = df['dt'].max() - pd.Timedelta(days=days)
    rows = []
    goods = df[(df["dir"] == "good") & (df["dt"] >= cutoff)]
    for _, row in goods.iterrows():
        t = row["dt"]
        g6 = last_closed(h6, t, "H6", "M30")
        if g6 is None: continue
        if not (g6["bias5_pct"] > 0 and g6["bias55_pct"] > 0): continue
        if abs(g6["bias13_pct"]) >= 2.0: continue
        stop = row["prev_seg_low_sma13"]
        if pd.isna(stop): continue
        idx = df.index.get_loc(row.name)
        if idx + 1 >= len(df): continue
        nb = df.iloc[idx + 1]
        entry = float(nb["open"])
        sd = abs(entry - float(stop))
        if sd <= 0 or sd / entry < MIN_STOP or sd / entry > 0.008: continue
        rows.append({"dt": t, "dir": "long", "entry_dt": nb["dt"], "entry": entry, "stop": float(stop), "sd_pct": round(sd / entry * 100, 2), "gate_bias5": round(float(g6["bias5_pct"]), 2), "gate_bias13": round(float(g6["bias13_pct"]), 2), "gate_bias55": round(float(g6["bias55_pct"]), 2)})
    return pd.DataFrame(cooldown_filter(rows))

def main():
    events = load_events()
    print(f"events: {len(events)}")
    for symbol, fn in [("USOILm", oil_signals), ("XAUUSDm", gold_signals)]:
        s = fn(days=180)
        if s.empty:
            print(f"[{symbol}] 180天无信号")
            continue
        s["event_win"] = [in_event(t, events) for t in s["dt"]]
        s.to_csv(OUT / f"sim_signals_{symbol}.csv", index=False)
        print(f"[{symbol}] v1.1 信号 {len(s)} 个：")
        for _, r in s.iterrows():
            ev = "事件窗" if r["event_win"] else "-"
            print(f"  {r['dt']} {r['dir']} entry={r['entry']:.3f} stop={r['stop']:.3f}({r['sd_pct']}%) {ev}")

if __name__ == "__main__":
    main()