# -*- coding: utf-8 -*-
"""V反策略：通用多周期档位验证引擎（参考资料周期档逐个回测）

用法：
  python validate_periods.py --symbol XAUUSDm --signal M30 --gate H6 --mode s2b --side long [--thr 2.5] [--seg-min 8 --seg-max 30]
  python validate_periods.py --symbol XAUUSDm --signal H1 --gate H4 --mode s1 --side short --thr 3.0

模式：
  s2b 顺势回归V反（黄金主方向）：gate趋势门+回调 + signal同向穿越
  s1  超涨超跌V反：gate bias55 超阈值 + signal反向穿越
输出：控制台统计 + data/period_trades_<tag>.csv
"""
from __future__ import annotations
import argparse
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parents[1]
PROC = BASE / "data" / "processed"
OUT = BASE / "data"

DEFAULT_MAX_BARS = {"M15": 960, "M30": 240, "H1": 240, "H2": 120, "H4": 120, "H6": 120, "H8": 120, "D1": 120, "W1": 120}
TF_MIN = {"M15": 15, "M30": 30, "H1": 60, "H2": 120, "H4": 240, "H6": 360, "H8": 480, "D1": 1440, "W1": 10080}

def load(symbol, tf):
    df = pd.read_csv(PROC / f"{symbol}_{tf}_features.csv")
    df["dt"] = pd.to_datetime(df["dt"], utc=True)
    return df

def last_closed(gate, t, tf_gate, tf_sig):
    # 因果修复(2026-09-04): 门 bar 必须在信号 bar 收盘时已经收盘。
    # dt 是 bar 开盘时间, bias/seg_len 在该 bar 收盘(dt+TF)才确定。
    # 原只判 gate.dt <= t 会读到"决策时尚未收盘"的门 bar 终值(泄漏未来 1~5.5h)。
    cutoff = t + pd.Timedelta(minutes=TF_MIN[tf_sig])
    m = (gate["dt"] + pd.Timedelta(minutes=TF_MIN[tf_gate])) <= cutoff
    if not m.any():
        return None
    return gate.loc[m].iloc[-1]

def find_entry_idx(df, entry_dt):
    m = df["dt"] == entry_dt
    if not m.any():
        return None
    return df.index.get_loc(df.index[m][0])

def simulate_stage(df, row, max_bars):
    """三段式：0.5仓@2R + 1.0仓@4R + 1.5仓@反向叉；止损 -3R"""
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
    total = 0.0; seg1 = False; seg2 = False
    for j in range(start, end):
        bar = df.iloc[j]
        high, low, close = float(bar["high"]), float(bar["low"]), float(bar["close"])
        if direction == "short":
            if high >= stop:
                return {"R": -3.0, "reason": "stop", "signal_dt": row["signal_dt"]}
            if not seg1 and low <= entry - 2.0 * sd:
                total += 0.5 * 2.0; seg1 = True
            if seg1 and not seg2 and low <= entry - 4.0 * sd:
                total += 1.0 * 4.0; seg2 = True
            if bar["dir"] == "good":
                return {"R": total + 1.5 * (entry - close) / sd, "reason": "staged", "signal_dt": row["signal_dt"]}
        else:
            if low <= stop:
                return {"R": -3.0, "reason": "stop", "signal_dt": row["signal_dt"]}
            if not seg1 and high >= entry + 2.0 * sd:
                total += 0.5 * 2.0; seg1 = True
            if seg1 and not seg2 and high >= entry + 4.0 * sd:
                total += 1.0 * 4.0; seg2 = True
            if bar["dir"] == "bad":
                return {"R": total + 1.5 * (close - entry) / sd, "reason": "staged", "signal_dt": row["signal_dt"]}
    last = df.iloc[end - 1]
    close = float(last["close"])
    r = (entry - close) / sd if direction == "short" else (close - entry) / sd
    return {"R": total + 1.5 * r, "reason": "staged_timeout", "signal_dt": row["signal_dt"]}

def cooldown(rows, hours=48):
    rows = sorted(rows, key=lambda r: r.get("dt", r.get("signal_dt")))
    kept = []; last_dt = {}
    for r in rows:
        d = r["dir"]
        rt = r.get("dt", r.get("signal_dt"))
        if d in last_dt and (rt - last_dt[d]) < pd.Timedelta(hours=hours):
            continue
        last_dt[d] = rt
        kept.append(r)
    return kept

def s2b_signals(sig, gate, side="long", tf_gate="H4", tf_sig="H1", seg_min=0, seg_max=999, min_stop=0.003, max_stop=0.008, cooldown_h=48):
    """顺势回归V反：gate 趋势门(bias5/bias55同向) + 回调(|bias13|<2%) + signal 同向穿越"""
    rows = []
    cross = "good" if side == "long" else "bad"
    sig_rows = sig[sig["dir"] == cross]
    for _, row in sig_rows.iterrows():
        t = row["dt"]
        g = last_closed(gate, t, tf_gate, tf_sig)
        if g is None:
            continue
        if side == "long":
            if not (g["bias5_pct"] > 0 and g["bias55_pct"] > 0):
                continue
        else:
            if not (g["bias5_pct"] < 0 and g["bias55_pct"] < 0):
                continue
        if abs(g["bias13_pct"]) >= 2.0:
            continue
        if g["seg_len"] < seg_min or g["seg_len"] > seg_max:
            continue
        stop_col = "prev_seg_low_sma13" if side == "long" else "prev_seg_high_sma13"
        stop = row[stop_col]
        if pd.isna(stop):
            continue
        idx = sig.index.get_loc(row.name)
        if idx + 1 >= len(sig):
            continue
        nb = sig.iloc[idx + 1]
        entry = float(nb["open"])
        sd = abs(entry - float(stop))
        if sd <= 0 or sd / entry < min_stop or sd / entry > max_stop:
            continue
        rows.append({"dir": side, "entry_dt": nb["dt"], "entry": entry, "stop": float(stop),
                     "signal_dt": t, "sd_pct": round(sd / entry * 100, 2),
                     "gate_seg_len": int(g["seg_len"]), "gate_bias13": round(float(g["bias13_pct"]), 2)})
    return pd.DataFrame(cooldown(rows, hours=cooldown_h))

def s1_signals(sig, gate, side="short", tf_gate="H4", tf_sig="H1", thr=2.5, seg_min=0, seg_max=999, min_stop=0.003, max_stop=0.008, cooldown_h=48):
    """超涨超跌V反：gate bias55 超阈值 + signal 反向穿越"""
    rows = []
    cross = "bad" if side == "short" else "good"
    sig_rows = sig[sig["dir"] == cross]
    for _, row in sig_rows.iterrows():
        t = row["dt"]
        g = last_closed(gate, t, tf_gate, tf_sig)
        if g is None:
            continue
        if side == "short":
            if g["bias55_pct"] < thr:
                continue
        else:
            if g["bias55_pct"] > -thr:
                continue
        if g["seg_len"] < seg_min or g["seg_len"] > seg_max:
            continue
        stop_col = "prev_seg_high_sma13" if side == "short" else "prev_seg_low_sma13"
        stop = row[stop_col]
        if pd.isna(stop):
            continue
        idx = sig.index.get_loc(row.name)
        if idx + 1 >= len(sig):
            continue
        nb = sig.iloc[idx + 1]
        entry = float(nb["open"])
        sd = abs(entry - float(stop))
        if sd <= 0 or sd / entry < min_stop or sd / entry > max_stop:
            continue
        rows.append({"dir": side, "entry_dt": nb["dt"], "entry": entry, "stop": float(stop),
                     "signal_dt": t, "sd_pct": round(sd / entry * 100, 2),
                     "gate_seg_len": int(g["seg_len"]), "gate_bias55": round(float(g["bias55_pct"]), 2)})
    return pd.DataFrame(cooldown(rows, hours=cooldown_h))

def run_trades(sig_df, cand, max_bars, cost_points=0.0, point=0.001):
    out = []
    for _, row in cand.iterrows():
        res = simulate_stage(sig_df, row, max_bars)
        if res:
            res["entry"] = float(row["entry"])
            res["dir"] = row["dir"]
            sd = abs(float(row["entry"]) - float(row["stop"]))
            if cost_points > 0 and sd > 0:
                # 往返成本（点）折成 R：成本/止损距离
                res["R"] = res["R"] - (cost_points * point) / sd
            out.append(res)
    return pd.DataFrame(out)

def stats(t):
    if t is None or len(t) == 0:
        return None
    w = t[t["R"] > 0]; l = t[t["R"] <= 0]
    gw = float(w["R"].sum()) if not w.empty else 0.0
    gl = -float(l["R"].sum()) if not l.empty else 0.0
    pf = gw / gl if gl > 0 else float("inf")
    return {"n": len(t), "wr": len(w) / len(t), "ev": float(t["R"].mean()), "pf": pf, "sumR": float(t["R"].sum())}

def fmt(r):
    if r is None:
        return "n=0"
    return f"n={r['n']} wr={r['wr']:.1%} ev={r['ev']:.2f}R pf={r['pf']:.2f} sumR={r['sumR']:+.1f}"

def split_stats(t):
    if t is None or len(t) == 0:
        return {"all": None, "e20_24": None, "l25_26": None}
    t2 = t.copy()
    t2["dt"] = pd.to_datetime(t2["signal_dt"], utc=True)
    return {
        "all": stats(t2),
        "e20_24": stats(t2[t2["dt"] < "2025-01-01"]),
        "l25_26": stats(t2[t2["dt"] >= "2025-01-01"]),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--signal", required=True)
    ap.add_argument("--gate", required=True)
    ap.add_argument("--mode", choices=["s2b", "s1"], required=True)
    ap.add_argument("--side", choices=["long", "short"], required=True)
    ap.add_argument("--thr", type=float, default=2.5)
    ap.add_argument("--seg-min", type=int, default=8)
    ap.add_argument("--seg-max", type=int, default=30)
    ap.add_argument("--min-stop", type=float, default=0.003)
    ap.add_argument("--max-stop", type=float, default=0.008)
    ap.add_argument("--cooldown", type=float, default=48)
    ap.add_argument("--max-bars", type=int, default=None)
    ap.add_argument("--cost-points", type=float, default=0.0, help="往返点差成本（点数），0=不计")
    ap.add_argument("--point", type=float, default=0.001)
    args = ap.parse_args()

    sig = load(args.symbol, args.signal)
    gate = load(args.symbol, args.gate)
    mb = args.max_bars or DEFAULT_MAX_BARS.get(args.signal, 240)

    if args.mode == "s2b":
        cand = s2b_signals(sig, gate, side=args.side, tf_gate=args.gate, tf_sig=args.signal,
                           seg_min=args.seg_min, seg_max=args.seg_max,
                           min_stop=args.min_stop, max_stop=args.max_stop, cooldown_h=args.cooldown)
    else:
        cand = s1_signals(sig, gate, side=args.side, tf_gate=args.gate, tf_sig=args.signal, thr=args.thr,
                          seg_min=args.seg_min, seg_max=args.seg_max,
                          min_stop=args.min_stop, max_stop=args.max_stop, cooldown_h=args.cooldown)

    tag = f"{args.symbol}_{args.signal}x{args.gate}_{args.mode}_{args.side}_{args.thr:g}"
    if len(cand):
        cand.to_csv(OUT / f"period_cand_{tag}.csv", index=False)
    trades = run_trades(sig, cand, mb, cost_points=args.cost_points, point=args.point)
    if len(trades):
        trades.to_csv(OUT / f"period_trades_{tag}.csv", index=False)
    s = split_stats(trades)
    print(f"== {tag} ==  (seg {args.seg_min}-{args.seg_max}, stop {args.min_stop}-{args.max_stop}, mb={mb}, cost={args.cost_points:g}pts)")
    print(f"  全样本   : {fmt(s['all'])}")
    print(f"  2020-2024: {fmt(s['e20_24'])}")
    print(f"  2025-2026: {fmt(s['l25_26'])}")

if __name__ == "__main__":
    main()
