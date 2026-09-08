# -*- coding: utf-8 -*-
"""V反策略 H3-H8 验证轮（v0.2）"""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
SIG = BASE / "data" / "signals"
REP = BASE / "报告"
CAL = Path(r"F:\use_code\MTA5_l\宏观日历研究\data\calendar_export.csv")

KEYWORDS = ["CPI", "FOMC", "EIA", "非农", "GDP", "PCE", "PPI", "失业率", "利率决议", "原油库存"]

def load_events():
    df = pd.read_csv(CAL, sep="|", usecols=["event_name", "importance", "time"])
    hi = df[df["importance"] >= 3]
    names = hi["event_name"].astype(str)
    mask = np.zeros(len(hi), dtype=bool)
    for kw in KEYWORDS:
        mask |= names.str.contains(kw, na=False)
    times = pd.to_datetime(hi.loc[mask, "time"], unit="s", utc=True)
    return sorted(times.tolist())

def in_event_window(t, events, hours):
    from bisect import bisect_left
    lo = t - pd.Timedelta(hours=hours)
    hi = t + pd.Timedelta(hours=hours)
    i = bisect_left(events, lo)
    return i < len(events) and events[i] <= hi

def find_entry_idx(df, entry_dt):
    m = df["dt"] == entry_dt
    if not m.any():
        return None
    return df.index.get_loc(df.index[m][0])

def simulate_struct(df, row, max_bars):
    """结构止损模拟（空：high>=stop；多：low<=stop；目标：回归SMA55；反向叉平仓）"""
    entry = float(row["entry"]); stop = float(row["stop"]); direction = row["dir"]
    sd = abs(entry - stop)
    if sd <= 0:
        return None
    idx = find_entry_idx(df, row["entry_dt"])
    if idx is None:
        return None
    start = idx + 1
    end = min(start + max_bars, len(df))
    if start >= len(df):
        return None
    for j in range(start, end):
        bar = df.iloc[j]
        high, low, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
        sma55 = bar["sma55"]
        if direction == "short":
            if high >= stop:
                return {"R": -1.0, "reason": "stop", "target1": False}
            if not pd.isna(sma55) and close <= sma55:
                return {"R": (entry - close) / sd, "reason": "target1", "target1": True}
            if bar["dir"] == "good":
                return {"R": (entry - close) / sd, "reason": "cross", "target1": False}
        else:
            if low <= stop:
                return {"R": -1.0, "reason": "stop", "target1": False}
            if not pd.isna(sma55) and close >= sma55:
                return {"R": (close - entry) / sd, "reason": "target1", "target1": True}
            if bar["dir"] == "bad":
                return {"R": (close - entry) / sd, "reason": "cross", "target1": False}
    last = df.iloc[end - 1]
    close = float(last["close"])
    r = (entry - close) / sd if direction == "short" else (close - entry) / sd
    return {"R": r, "reason": "timeout", "target1": False}

def simulate_fixed(df, row, max_bars, fixed_pct):
    entry = float(row["entry"]); direction = row["dir"]
    sd = entry * fixed_pct
    if sd <= 0:
        return None
    stop = entry + sd if direction == "short" else entry - sd
    idx = find_entry_idx(df, row["entry_dt"])
    if idx is None:
        return None
    start = idx + 1
    end = min(start + max_bars, len(df))
    for j in range(start, end):
        bar = df.iloc[j]
        high, low, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
        sma55 = bar["sma55"]
        if direction == "short":
            if high >= stop:
                return {"R": -1.0, "reason": "stop", "target1": False}
            if not pd.isna(sma55) and close <= sma55:
                return {"R": (entry - close) / sd, "reason": "target1", "target1": True}
            if bar["dir"] == "good":
                return {"R": (entry - close) / sd, "reason": "cross", "target1": False}
        else:
            if low <= stop:
                return {"R": -1.0, "reason": "stop", "target1": False}
            if not pd.isna(sma55) and close >= sma55:
                return {"R": (close - entry) / sd, "reason": "target1", "target1": True}
            if bar["dir"] == "bad":
                return {"R": (close - entry) / sd, "reason": "cross", "target1": False}
    last = df.iloc[end - 1]
    close = float(last["close"])
    r = (entry - close) / sd if direction == "short" else (close - entry) / sd
    return {"R": r, "reason": "timeout", "target1": False}

def simulate_stage(df, row, max_bars):
    """三段式：0.5仓@2R + 1.0仓@4R + 1.5仓@反向叉"""
    entry = float(row["entry"]); stop = float(row["stop"]); direction = row["dir"]
    sd = abs(entry - stop)
    if sd <= 0:
        return None
    idx = find_entry_idx(df, row["entry_dt"])
    if idx is None:
        return None
    start = idx + 1
    end = min(start + max_bars, len(df))
    total = 0.0
    seg1 = False
    seg2 = False
    for j in range(start, end):
        bar = df.iloc[j]
        high, low, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
        if direction == "short":
            if high >= stop:
                return {"R": -3.0, "reason": "stop", "target1": False}
            if not seg1 and low <= entry - 2.0 * sd:
                total += 0.5 * 2.0; seg1 = True
            if seg1 and not seg2 and low <= entry - 4.0 * sd:
                total += 1.0 * 4.0; seg2 = True
            if bar["dir"] == "good":
                return {"R": total + 1.5 * (entry - close) / sd, "reason": "staged", "target1": False}
        else:
            if low <= stop:
                return {"R": -3.0, "reason": "stop", "target1": False}
            if not seg1 and high >= entry + 2.0 * sd:
                total += 0.5 * 2.0; seg1 = True
            if seg1 and not seg2 and high >= entry + 4.0 * sd:
                total += 1.0 * 4.0; seg2 = True
            if bar["dir"] == "bad":
                return {"R": total + 1.5 * (close - entry) / sd, "reason": "staged", "target1": False}
    last = df.iloc[end - 1]
    close = float(last["close"])
    r = (entry - close) / sd if direction == "short" else (close - entry) / sd
    return {"R": total + 1.5 * r, "reason": "staged_timeout", "target1": False}

def pf_ev(trades):
    if trades is None or len(trades) == 0:
        return None
    wins = trades[trades["R"] > 0]
    losses = trades[trades["R"] <= 0]
    gw = float(wins["R"].sum()) if not wins.empty else 0.0
    gl = -float(losses["R"].sum()) if not losses.empty else 0.0
    pf = gw / gl if gl > 0 else float("inf")
    return {"n": len(trades), "wr": len(wins) / len(trades), "ev": float(trades["R"].mean()), "pf": pf}

def fmt(r):
    if r is None:
        return "n=0"
    return f"n={r['n']} wr={r['wr']:.1%} ev={r['ev']:.2f}R pf={r['pf']:.2f}"

def build_struct_trades(df, cand, max_bars):
    trades = []
    for _, row in cand.iterrows():
        res = simulate_struct(df, row, max_bars)
        if res:
            res["signal_dt"] = row["signal_dt"]
            res["entry"] = float(row["entry"])
            res["dir"] = row["dir"]
            trades.append(res)
    return pd.DataFrame(trades)

def main():
    events = load_events()
    print(f"high-impact events: {len(events)}")
    out = []
    out.append("# H3-H8 验证结果（v0.2）")
    out.append("")
    out.append(f"> 高影响事件数：{len(events)}")
    out.append("")
    for symbol, sig_tf, cand_file, max_bars, intv in [
        ("XAUUSDm", "M30", "candidates_XAUUSDm.csv", 240, 100.0),
        ("USOILm", "H2", "candidates_USOILm.csv", 120, 1.0),
    ]:
        cand = pd.read_csv(SIG / cand_file)
        cand["signal_dt"] = pd.to_datetime(cand["signal_dt"], utc=True)
        df = pd.read_csv(PROC / f"{symbol}_{sig_tf}_features.csv")
        df["dt"] = pd.to_datetime(df["dt"], utc=True)
        st = build_struct_trades(df, cand, max_bars)
        out.append(f"## {symbol}")
        out.append("")
        out.append("### H3 事件窗口")
        out.append("")
        out.append("| 分组 | 结果 |")
        out.append("|---|---|")
        for h in [2, 4]:
            win = st[[in_event_window(t, events, h) for t in st["signal_dt"]]]
            outw = st[[not in_event_window(t, events, h) for t in st["signal_dt"]]]
            out.append(f"| ±{h}h 内 | {fmt(pf_ev(win))} |")
            out.append(f"| ±{h}h 外 | {fmt(pf_ev(outw))} |")
        out.append("")
        out.append("### H4 固定止损 vs 结构止损")
        out.append("")
        fixed = []
        for _, row in cand.iterrows():
            res = simulate_fixed(df, row, max_bars, 0.012)
            if res:
                res["signal_dt"] = row["signal_dt"]
                fixed.append(res)
        ft = pd.DataFrame(fixed)
        out.append(f"| 固定1.2% | {fmt(pf_ev(ft))} |")
        out.append(f"| 结构止损 | {fmt(pf_ev(st))} |")
        out.append("")
        out.append("### H5 整数位附近")
        out.append("")
        def near_int(e):
            r = abs(float(e) % intv)
            return r < intv * 0.005 or r > intv * 0.995
        near = st[[near_int(e) for e in st["entry"]]]
        far = st[[not near_int(e) for e in st["entry"]]]
        out.append(f"| 整数位附近 | {fmt(pf_ev(near))} |")
        out.append(f"| 远离整数位 | {fmt(pf_ev(far))} |")
        out.append("")
        out.append("### H6 三段式 vs 单仓")
        out.append("")
        staged = []
        for _, row in cand.iterrows():
            res = simulate_stage(df, row, max_bars)
            if res:
                res["signal_dt"] = row["signal_dt"]
                staged.append(res)
        sgt = pd.DataFrame(staged)
        out.append(f"| 三段式 | {fmt(pf_ev(sgt))} |")
        out.append(f"| 单仓结构止损 | {fmt(pf_ev(st))} |")
        out.append("")
        out.append("### 参数扰动（threshold 分组）")
        out.append("")
        out.append("| 阈值 | 结果 |")
        out.append("|---|---|")
        for thr, g in cand.groupby("threshold"):
            sub = st[st["signal_dt"].isin(g["signal_dt"])]
            out.append(f"| {thr}% | {fmt(pf_ev(sub))} |")
        out.append("")
    # H7 黄金 S2B 顺势回归
    out.append("## H7 黄金 S2B（顺势回归V反）")
    out.append("")
    h1 = pd.read_csv(PROC / "XAUUSDm_M30_features.csv"); h1["dt"] = pd.to_datetime(h1["dt"], utc=True)
    h6 = pd.read_csv(PROC / "XAUUSDm_H6_features.csv"); h6["dt"] = pd.to_datetime(h6["dt"], utc=True)
    s2b_rows = []
    goods = h1[h1["dir"] == "good"]
    for _, row in goods.iterrows():
        t = row["dt"]
        hi6 = h6[h6["dt"] <= t]
        if hi6.empty:
            continue
        g6 = hi6.iloc[-1]
        if not (g6["bias5_pct"] > 0 and g6["bias55_pct"] > 0):
            continue
        if abs(g6["bias13_pct"]) >= 2.0:
            continue
        idx = h1.index.get_loc(row.name)
        if idx + 1 >= len(h1):
            continue
        nb = h1.iloc[idx + 1]
        stop = row["prev_seg_low_sma13"]
        if pd.isna(stop):
            continue
        s2b_rows.append({"dir": "long", "entry_dt": nb["dt"], "entry": nb["open"], "stop": stop, "signal_dt": t})
    s2b = pd.DataFrame(s2b_rows)
    s2bt = build_struct_trades(h1, s2b, 240)
    out.append(f"| S2B 顺势回归 | {fmt(pf_ev(s2bt))} |")
    out.append("")
    out.append("## H8 品种差异")
    out.append("")
    out.append("| 品种 | S1做空 PF | 样本 |")
    out.append("|---|---|---|")
    out.append("| XAUUSDm | 0.81 | 96 |")
    out.append("| USOILm | 1.41 | 27 |")
    out.append("")
    REP.mkdir(parents=True, exist_ok=True)
    (REP / "H3-H8验证结果_v0.2.md").write_text("\n".join(out), encoding="utf-8")
    print("saved ->", REP / "H3-H8验证结果_v0.2.md")
    print("\n".join(out))

if __name__ == "__main__":
    main()