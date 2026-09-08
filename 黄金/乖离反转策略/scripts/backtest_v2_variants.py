# -*- coding: utf-8 -*-
"""乖离反转 v2: 变体对比（M30交叉 / H1交叉 / H1收盘确认）+ 年度分解"""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\scripts")
RAW = ROOT / "data" / "raw"

def smma(series, n):
    out = np.full(len(series), np.nan)
    if len(series) < n:
        return out
    out[n - 1] = series[:n].mean()
    for i in range(n, len(series)):
        out[i] = (out[i - 1] * (n - 1) + series[i]) / n
    return out

def load():
    m30 = pd.read_csv(RAW / "XAUUSDm_M30.csv", parse_dates=["date"])
    h4 = pd.read_csv(RAW / "XAUUSDm_H4.csv", parse_dates=["date"])
    h1 = pd.read_csv(RAW / "XAUUSDm_H1.csv", parse_dates=["date"])
    for d in (m30, h4, h1):
        d["date"] = d["date"].dt.tz_localize(None)
    return m30, h4, h1

def run_v2(threshold, stop_pct, tp_r, mode, cost_pct=0.05):
    m30, h4, h1 = load()
    c4 = h4["close"].to_numpy(dtype=float)
    h4["s5"] = smma(c4, 5); h4["s55"] = smma(c4, 55)
    h4 = h4.dropna(subset=["s55"]).reset_index(drop=True)
    h4["bias55"] = (h4["close"] - h4["s55"]) / h4["s55"] * 100.0
    h4["state"] = 0
    h4.loc[(h4["close"] > h4["s5"]) & (h4["close"] > h4["s55"]) & (h4["bias55"] >= threshold), "state"] = 1
    h4.loc[(h4["close"] < h4["s5"]) & (h4["close"] < h4["s55"]) & (h4["bias55"] <= -threshold), "state"] = -1
    h4_times = h4["date"].to_numpy()

    c30 = m30["close"].to_numpy(dtype=float)
    m30["s5"] = smma(c30, 5); m30["s13"] = smma(c30, 13)
    m30 = m30.dropna(subset=["s13"]).reset_index(drop=True)
    p5, p13 = m30["s5"].shift(1), m30["s13"].shift(1)
    m30["cross"] = np.where((m30["s5"] > m30["s13"]) & (p5 <= p13), 1,
                     np.where((m30["s5"] < m30["s13"]) & (p5 >= p13), -1, 0))

    c1 = h1["close"].to_numpy(dtype=float)
    h1["s5"] = smma(c1, 5); h1["s13"] = smma(c1, 13)
    h1 = h1.dropna(subset=["s13"]).reset_index(drop=True)
    q5, q13 = h1["s5"].shift(1), h1["s13"].shift(1)
    h1["cross"] = np.where((h1["s5"] > h1["s13"]) & (q5 <= q13), 1,
                    np.where((h1["s5"] < h1["s13"]) & (q5 >= q13), -1, 0))
    h1_times = h1["date"].to_numpy()

    n = len(m30)
    closes = m30["close"].to_numpy(dtype=float)
    highs = m30["high"].to_numpy(dtype=float)
    lows = m30["low"].to_numpy(dtype=float)
    opens = m30["open"].to_numpy(dtype=float)
    times = m30["date"].to_numpy()
    crosses = m30["cross"].to_numpy()

    import bisect
    trades = []
    pos = None
    for i in range(1, n):
        t = times[i]
        h4i = bisect.bisect_right(h4_times, t) - 1
        state = int(h4["state"].iloc[h4i]) if h4i >= 0 else 0
        if pos is None:
            sig = crosses[i - 1]
            # extra confirmation from H1 (bar i-1 closed): check latest closed H1
            h1i = bisect.bisect_right(h1_times, t) - 1
            extra = 0
            if h1i >= 0:
                if mode == "h1cross":
                    extra = int(h1["cross"].iloc[h1i])
                elif mode == "h1close":
                    extra = 1 if h1["close"].iloc[h1i] > h1["s5"].iloc[h1i] else -1
                else:
                    extra = 1  # m30cross: no extra confirmation
            if sig == 1 and state == -1 and extra == 1:
                entry = opens[i]; stop = entry * (1.0 - stop_pct / 100.0)
                pos = {"dir": 1, "entry": entry, "stop": stop, "tp": entry + (entry - stop) * tp_r, "entry_i": i}
            elif sig == -1 and state == 1 and extra == -1:
                entry = opens[i]; stop = entry * (1.0 + stop_pct / 100.0)
                pos = {"dir": -1, "entry": entry, "stop": stop, "tp": entry - (stop - entry) * tp_r, "entry_i": i}
        else:
            d = pos["dir"]; exit_px = None; reason = None
            if d == 1:
                if lows[i] <= pos["stop"]: exit_px, reason = pos["stop"], "SL hit"
                elif highs[i] >= pos["tp"]: exit_px, reason = pos["tp"], "TP hit"
            else:
                if highs[i] >= pos["stop"]: exit_px, reason = pos["stop"], "SL hit"
                elif lows[i] <= pos["tp"]: exit_px, reason = pos["tp"], "TP hit"
            if exit_px is None:
                rc = crosses[i]
                if rc == 1 and d == -1: exit_px, reason = opens[i], "reverse cross"
                elif rc == -1 and d == 1: exit_px, reason = opens[i], "reverse cross"
            if exit_px is not None:
                pnl = (exit_px - pos["entry"]) * d - pos["entry"] * cost_pct / 100.0 * 2.0
                trades.append({"signal_time": times[pos["entry_i"] - 1], "entry_time": times[pos["entry_i"]],
                               "dir": d, "entry": pos["entry"], "stop": pos["stop"],
                               "exit_time": t, "exit": exit_px, "exit_reason": reason,
                               "pnl_points": pnl, "holding_bars": i - pos["entry_i"]})
                pos = None
    return pd.DataFrame(trades)

def summ(tr, split=0.7):
    if tr is None or len(tr) == 0:
        return None
    pnl = tr["pnl_points"].to_numpy(dtype=float)
    wins, losses = pnl[pnl > 0], pnl[pnl < 0]
    gw, gl = wins.sum(), abs(losses.sum())
    ts = pd.to_datetime(tr["signal_time"])
    cutoff = ts.min() + (ts.max() - ts.min()) * split
    test = tr[ts >= cutoff]["pnl_points"].to_numpy(dtype=float)
    tw, tl = test[test > 0].sum(), abs(test[test < 0].sum())
    eq = np.cumsum(pnl); dd = (np.maximum.accumulate(eq) - eq).max()
    return {"n": len(tr), "wr": float((pnl > 0).mean() * 100), "pf": float(gw / gl if gl > 0 else 999),
            "ev": float(pnl.mean()), "pnl": float(pnl.sum()), "test_pf": float(tw / tl if tl > 0 else 999),
            "max_dd": float(dd), "sl": int((tr["exit_reason"] == "SL hit").sum()),
            "tp": int((tr["exit_reason"] == "TP hit").sum()), "rev": int((tr["exit_reason"] == "reverse cross").sum())}

print("=== 变体对比 (thr=2.0, stop=1.2%, tpR=3, cost=0.05%) ===")
for mode in ["m30cross", "h1cross", "h1close"]:
    tr = run_v2(2.0, 1.2, 3.0, mode)
    m = summ(tr)
    print("%-9s n=%3d pf=%.3f ev=%7.2f pnl=%8.1f test_pf=%.3f wr=%5.1f%% dd=%7.1f SL=%d TP=%d REV=%d" % (
        mode, m["n"], m["pf"], m["ev"], m["pnl"], m["test_pf"], m["wr"], m["max_dd"], m["sl"], m["tp"], m["rev"]))

print()
print("=== 分年度 (h1close 变体) ===")
tr = run_v2(2.0, 1.2, 3.0, "h1close")
df = tr.copy(); df["year"] = pd.to_datetime(df["signal_time"]).dt.year
print(df.groupby("year").agg(n=("pnl_points", "size"), pnl=("pnl_points", "sum"),
                              wr=("pnl_points", lambda x: (x > 0).mean() * 100)).round(2).to_string())
print()
print("=== 分年度 (m30cross 基础版) ===")
tr = run_v2(2.0, 1.2, 3.0, "m30cross")
df = tr.copy(); df["year"] = pd.to_datetime(df["signal_time"]).dt.year
print(df.groupby("year").agg(n=("pnl_points", "size"), pnl=("pnl_points", "sum"),
                              wr=("pnl_points", lambda x: (x > 0).mean() * 100)).round(2).to_string())
