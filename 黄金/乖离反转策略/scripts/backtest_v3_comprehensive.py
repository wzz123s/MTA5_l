# -*- coding: utf-8 -*-
"""乖离反转 v3：综合变体测试
维度：
  A. 趋势过滤：H4 bias55 进入区间 [thr_lo, thr_hi]（thr_hi=None 不设上限）
  B. H4 bias5 上限（超涨时 |H4 bias5| <= hi，防止过热）
  C. M30 bias5 上限（入场时 |M30 bias5| <= hi，金叉/死叉时偏离不过远）
  D. 退出模式：rev_cross（M30 反向交叉）/ h4_flip（H4 状态翻转，顺势持有）
  标的：XAUUSDm（趋势市） + USOILm（震荡市）
"""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\scripts")
RAW = ROOT / "data" / "raw"
OIL = Path(r"F:\use_code\MTA5_l\原油\原油4H门策略\data\raw\mt5_history\usoil_4h_gate_gen_20200101_20260815")


def smma(series, n):
    out = np.full(len(series), np.nan)
    if len(series) < n:
        return out
    out[n - 1] = series[:n].mean()
    for i in range(n, len(series)):
        out[i] = (out[i - 1] * (n - 1) + series[i]) / n
    return out


def load(symbol):
    if symbol == "XAUUSDm":
        m30 = pd.read_csv(RAW / "XAUUSDm_M30.csv", parse_dates=["date"])
        h4 = pd.read_csv(RAW / "XAUUSDm_H4.csv", parse_dates=["date"])
    else:
        m30 = pd.read_csv(OIL / "USOILm_M30.csv")
        h4 = pd.read_csv(OIL / "USOILm_H4.csv")
        m30 = m30.rename(columns={"time": "date"})
        h4 = h4.rename(columns={"time": "date"})
        m30["date"] = pd.to_datetime(m30["date"], utc=True).dt.tz_localize(None)
        h4["date"] = pd.to_datetime(h4["date"], utc=True).dt.tz_localize(None)
    for d in (m30, h4):
        d["date"] = d["date"].dt.tz_localize(None)
    return m30, h4


def run(symbol, cfg):
    m30, h4 = load(symbol)
    c4 = h4["close"].to_numpy(dtype=float)
    h4["s5"] = smma(c4, 5); h4["s55"] = smma(c4, 55)
    h4 = h4.dropna(subset=["s55"]).reset_index(drop=True)
    h4["bias55"] = (h4["close"] - h4["s55"]) / h4["s55"] * 100.0
    h4["bias5"] = (h4["close"] - h4["s5"]) / h4["s5"] * 100.0
    thr_lo, thr_hi = cfg["thr_lo"], cfg["thr_hi"]
    h4b5_hi = cfg["h4b5_hi"]
    state = np.zeros(len(h4), dtype=int)
    m1 = (h4["close"] > h4["s5"]) & (h4["close"] > h4["s55"]) & (h4["bias55"] >= thr_lo) & h4["bias55"].le(thr_hi if thr_hi else 1e9) & h4["bias5"].abs().le(h4b5_hi if h4b5_hi else 1e9)
    m2 = (h4["close"] < h4["s5"]) & (h4["close"] < h4["s55"]) & (h4["bias55"] <= -thr_lo) & h4["bias55"].ge(-(thr_hi if thr_hi else 1e9)) & h4["bias5"].abs().le(h4b5_hi if h4b5_hi else 1e9)
    state[m1.to_numpy()] = 1
    state[m2.to_numpy()] = -1
    h4["state"] = state
    h4_times = h4["date"].to_numpy()

    c30 = m30["close"].to_numpy(dtype=float)
    m30["s5"] = smma(c30, 5); m30["s13"] = smma(c30, 13); m30["s55"] = smma(c30, 55)
    m30 = m30.dropna(subset=["s55"]).reset_index(drop=True)
    m30["bias5"] = (m30["close"] - m30["s5"]) / m30["s5"] * 100.0
    p5, p13 = m30["s5"].shift(1), m30["s13"].shift(1)
    m30["cross"] = np.where((m30["s5"] > m30["s13"]) & (p5 <= p13), 1,
                     np.where((m30["s5"] < m30["s13"]) & (p5 >= p13), -1, 0))
    m30b5_hi = cfg["m30b5_hi"]
    m30["ok_b5"] = m30["bias5"].abs() <= (m30b5_hi if m30b5_hi else 1e9)

    n = len(m30)
    opens = m30["open"].to_numpy(dtype=float)
    highs = m30["high"].to_numpy(dtype=float)
    lows = m30["low"].to_numpy(dtype=float)
    times = m30["date"].to_numpy()
    crosses = m30["cross"].to_numpy()
    ok_b5 = m30["ok_b5"].to_numpy()
    stop_pct, tp_r, cost = cfg["stop_pct"], cfg["tp_r"], cfg["cost"]
    exit_mode = cfg["exit_mode"]

    import bisect
    trades = []
    pos = None
    for i in range(1, n):
        t = times[i]
        h4i = bisect.bisect_right(h4_times, t) - 1
        state_now = int(h4["state"].iloc[h4i]) if h4i >= 0 else 0
        if pos is None:
            sig = crosses[i - 1]
            if sig == 1 and state_now == -1 and ok_b5[i - 1]:
                entry = opens[i]; stop = entry * (1.0 - stop_pct / 100.0)
                pos = {"dir": 1, "entry": entry, "stop": stop, "tp": entry + (entry - stop) * tp_r, "entry_i": i}
            elif sig == -1 and state_now == 1 and ok_b5[i - 1]:
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
            if exit_px is None and exit_mode == "rev_cross":
                rc = crosses[i]
                if rc == 1 and d == -1: exit_px, reason = opens[i], "reverse cross"
                elif rc == -1 and d == 1: exit_px, reason = opens[i], "reverse cross"
            if exit_px is None and exit_mode == "h4_flip":
                # H4 state flipped against position
                if d == 1 and state_now != -1 and (h4i >= 0 and int(h4["state"].iloc[h4i]) != -1 and int(h4["state"].iloc[max(0, h4i - 1)]) == -1):
                    exit_px, reason = opens[i], "h4 flip"
                elif d == -1 and state_now != 1 and (h4i >= 0 and int(h4["state"].iloc[h4i]) != 1 and int(h4["state"].iloc[max(0, h4i - 1)]) == 1):
                    exit_px, reason = opens[i], "h4 flip"
            if exit_px is not None:
                pnl = (exit_px - pos["entry"]) * d - pos["entry"] * cost / 100.0 * 2.0
                trades.append({"signal_time": times[pos["entry_i"] - 1], "dir": d,
                               "entry": pos["entry"], "stop": pos["stop"],
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
    return {"n": len(tr), "wr": float((pnl > 0).mean() * 100), "pf": float(gw / gl if gl > 0 else 999),
            "ev": float(pnl.mean()), "pnl": float(pnl.sum()), "test_pf": float(tw / tl if tl > 0 else 999)}


BASE = {"stop_pct": 1.2, "tp_r": 3.0, "cost": 0.05}

print("========== XAUUSDm（趋势市）==========")
print("--- A. 趋势过滤: thr_lo x thr_hi（exit=rev_cross）---")
for tl in [1.5, 2.0, 2.5]:
    for th in [None, 4.0, 6.0]:
        cfg = {**BASE, "thr_lo": tl, "thr_hi": th, "h4b5_hi": None, "m30b5_hi": None, "exit_mode": "rev_cross"}
        m = summ(run("XAUUSDm", cfg))
        if m:
            print("thr=[%4.1f,%5s] n=%3d pf=%.3f ev=%7.2f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
                tl, str(th), m["n"], m["pf"], m["ev"], m["pnl"], m["test_pf"], m["wr"]))
print("--- D. h4_flip 退出（顺势持有）---")
for tl in [1.5, 2.0, 2.5]:
    cfg = {**BASE, "thr_lo": tl, "thr_hi": None, "h4b5_hi": None, "m30b5_hi": None, "exit_mode": "h4_flip"}
    m = summ(run("XAUUSDm", cfg))
    if m:
        print("thr=%4.1f n=%3d pf=%.3f ev=%7.2f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (tl, m["n"], m["pf"], m["ev"], m["pnl"], m["test_pf"], m["wr"]))
print("--- B+C. H4 bias5 / M30 bias5 上限（thr_lo=2.0, exit=rev_cross）---")
for h5 in [None, 2.0, 3.0]:
    for m5 in [None, 0.5, 1.0]:
        cfg = {**BASE, "thr_lo": 2.0, "thr_hi": None, "h4b5_hi": h5, "m30b5_hi": m5, "exit_mode": "rev_cross"}
        mm = summ(run("XAUUSDm", cfg))
        if mm:
            print("h4b5=%5s m30b5=%5s n=%3d pf=%.3f ev=%7.2f pnl=%8.1f test_pf=%.3f" % (
                str(h5), str(m5), mm["n"], mm["pf"], mm["ev"], mm["pnl"], mm["test_pf"]))

print()
print("========== USOILm（震荡市）==========")
for tl in [1.5, 2.0, 2.5]:
    for th in [None, 4.0]:
        cfg = {**BASE, "thr_lo": tl, "thr_hi": th, "h4b5_hi": None, "m30b5_hi": None, "exit_mode": "rev_cross"}
        m = summ(run("USOILm", cfg))
        if m:
            print("thr=[%4.1f,%5s] n=%3d pf=%.3f ev=%7.2f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
                tl, str(th), m["n"], m["pf"], m["ev"], m["pnl"], m["test_pf"], m["wr"]))
for h5 in [None, 2.0]:
    cfg = {**BASE, "thr_lo": 2.0, "thr_hi": None, "h4b5_hi": h5, "m30b5_hi": 0.5, "exit_mode": "rev_cross"}
    m = summ(run("USOILm", cfg))
    if m:
        print("h4b5=%5s m30b5=0.5 n=%3d pf=%.3f ev=%7.2f pnl=%8.1f test_pf=%.3f" % (
            str(h5), m["n"], m["pf"], m["ev"], m["pnl"], m["test_pf"]))
cfg = {**BASE, "thr_lo": 2.0, "thr_hi": None, "h4b5_hi": None, "m30b5_hi": None, "exit_mode": "h4_flip"}
m = summ(run("USOILm", cfg))
if m:
    print("h4_flip thr=2.0 n=%3d pf=%.3f ev=%7.2f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (m["n"], m["pf"], m["ev"], m["pnl"], m["test_pf"], m["wr"]))
