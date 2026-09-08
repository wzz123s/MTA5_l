# -*- coding: utf-8 -*-
"""v5: R3 段结构反转 双标的全测（黄金 2015-2026 / 原油 2019-2026）
- 全网格（gate x rise x w）
- 做多/做空分开统计
- 年度分解
"""
import sys
sys.path.insert(0, r"F:\use_code\MTA5_l\scripts")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\scripts\signals")
import numpy as np
import pandas as pd
from pathlib import Path

from replay_raw_signals_with_stops import add_indicators, standardize_mt5_csv
from replay_1h_way_momentum_filter_scan import add_way_grade, filter_short_segments_causal as filter_short_segments, mark_direction  # P1-1 因果化

RAW = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\raw")
RAWO = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\raw_oil")
OUT = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\validation")


def pipeline(csv_path, tf):
    frame = standardize_mt5_csv(csv_path, tf, closed_time=True)
    frame = add_indicators(frame)
    frame["vol_ma_120"] = pd.to_numeric(frame["volume"], errors="coerce").fillna(0).rolling(120, min_periods=1).mean()
    frame = mark_direction(frame)
    frame = filter_short_segments(frame, min_len=8)
    frame = add_way_grade(frame)
    return frame.reset_index(drop=True)


def h4_states(h4, thr):
    b55 = pd.to_numeric(h4["SMA_55"], errors="coerce")
    bias55 = (h4["close"] - b55) / b55 * 100.0
    s5 = pd.to_numeric(h4["SMA_5"], errors="coerce")
    state = np.zeros(len(h4), dtype=int)
    over = (h4["close"] > s5) & (h4["close"] > b55) & (bias55 >= thr)
    under = (h4["close"] < s5) & (h4["close"] < b55) & (bias55 <= -thr)
    state[over.to_numpy()] = 1
    state[under.to_numpy()] = -1
    return state, h4["bar_close_time"].to_numpy()


def seg_extremes(h2):
    direction = h2["方向_合并后"].values.astype(object)
    sma13 = pd.to_numeric(h2["SMA_13"], errors="coerce").to_numpy()
    high = h2["high"].to_numpy(dtype=float)
    low = h2["low"].to_numpy(dtype=float)
    wsw = pd.to_numeric(h2["way_s_way"], errors="coerce").to_numpy()
    vwsw = pd.to_numeric(h2["vol_way_s_way"], errors="coerce").to_numpy()
    n = len(h2)
    crosses = [i for i in range(n) if direction[i] in ("good", "bad")]
    rise = np.full(n, np.nan)
    ext_wsw = np.full(n, np.nan)
    ext_vwsw = np.full(n, np.nan)
    cur_sign = 0
    run_ext_idx = -1
    for i in range(n):
        d = direction[i]
        sign = 1 if d in ("good", "up") else (-1 if d in ("bad", "down") else 0)
        if sign != cur_sign:
            cur_sign = sign
            run_ext_idx = i
        elif cur_sign == 1 and high[i] > high[run_ext_idx]:
            run_ext_idx = i
        elif cur_sign == -1 and low[i] < low[run_ext_idx]:
            run_ext_idx = i
        if run_ext_idx >= 0:
            ext_wsw[i] = wsw[run_ext_idx]
            ext_vwsw[i] = vwsw[run_ext_idx]
        ci = np.searchsorted(crosses, i) - 1
        if ci >= 1 and cur_sign != 0:
            c1 = crosses[ci]; c0 = crosses[ci - 1]
            cur_seg = sma13[c1:i + 1]
            prev_seg = sma13[c0:c1]
            cur_seg = cur_seg[np.isfinite(cur_seg)]
            prev_seg = prev_seg[np.isfinite(prev_seg)]
            if len(cur_seg) and len(prev_seg):
                if cur_sign == 1:
                    prev_ext = prev_seg.min()
                    rise[i] = (cur_seg.max() - prev_ext) / prev_ext * 100.0 if prev_ext else np.nan
                else:
                    prev_ext = prev_seg.max()
                    rise[i] = (prev_ext - cur_seg.min()) / prev_ext * 100.0 if prev_ext else np.nan
    return rise, ext_wsw, ext_vwsw


def run(symbol, thr, thr_rise, thr_w, stop_pct=1.2, tp_r=3.0, cost=0.05):
    base = RAW if symbol == "XAUUSDm" else RAWO
    h2 = pipeline(base / ("%s_H2.csv" % symbol), "2H")
    h4 = pipeline(base / ("%s_H4.csv" % symbol), "4H")
    state, h4_times = h4_states(h4, thr)
    rise, ext_wsw, ext_vwsw = seg_extremes(h2)
    direction = h2["方向_合并后"].values.astype(object)
    opens = h2["open"].to_numpy(dtype=float)
    highs = h2["high"].to_numpy(dtype=float)
    lows = h2["low"].to_numpy(dtype=float)
    times = h2["bar_close_time"].to_numpy()
    n = len(h2)
    import bisect
    trades = []
    pos = None
    for i in range(1, n):
        t = times[i]
        h4i = bisect.bisect_right(h4_times, t) - 1
        st = int(state[h4i]) if h4i >= 0 else 0
        if pos is None:
            sig = 0
            if st == 1 and direction[i - 1] == "up" and np.isfinite(rise[i - 1]) and rise[i - 1] >= thr_rise and ext_wsw[i - 1] >= thr_w and ext_vwsw[i - 1] >= thr_w:
                sig = -1
            elif st == -1 and direction[i - 1] == "down" and np.isfinite(rise[i - 1]) and rise[i - 1] >= thr_rise and ext_wsw[i - 1] >= thr_w and ext_vwsw[i - 1] >= thr_w:
                sig = 1
            if sig == -1:
                entry = opens[i]; stop = entry * (1.0 + stop_pct / 100.0)
                pos = {"dir": -1, "entry": entry, "stop": stop, "tp": entry - (stop - entry) * tp_r, "entry_i": i}
            elif sig == 1:
                entry = opens[i]; stop = entry * (1.0 - stop_pct / 100.0)
                pos = {"dir": 1, "entry": entry, "stop": stop, "tp": entry + (entry - stop) * tp_r, "entry_i": i}
        else:
            d = pos["dir"]; exit_px = None; reason = None
            if d == 1:
                if lows[i] <= pos["stop"]: exit_px, reason = pos["stop"], "SL hit"
                elif highs[i] >= pos["tp"]: exit_px, reason = pos["tp"], "TP hit"
            else:
                if highs[i] >= pos["stop"]: exit_px, reason = pos["stop"], "SL hit"
                elif lows[i] <= pos["tp"]: exit_px, reason = pos["tp"], "TP hit"
            if exit_px is None:
                d2 = direction[i]
                if d2 == "good" and d == -1: exit_px, reason = opens[i], "reverse cross"
                elif d2 == "bad" and d == 1: exit_px, reason = opens[i], "reverse cross"
            if exit_px is not None:
                pnl = (exit_px - pos["entry"]) * d - pos["entry"] * cost / 100.0 * 2.0
                trades.append({"signal_time": times[pos["entry_i"] - 1], "dir": d,
                               "entry": pos["entry"], "stop": pos["stop"],
                               "exit_time": t, "exit": exit_px, "exit_reason": reason,
                               "pnl_points": pnl, "holding_bars": i - pos["entry_i"]})
                pos = None
    return pd.DataFrame(trades)


def stats(tr):
    if tr is None or len(tr) == 0:
        return None
    pnl = tr["pnl_points"].to_numpy(dtype=float)
    wins, losses = pnl[pnl > 0], pnl[pnl < 0]
    gw, gl = wins.sum(), abs(losses.sum())
    ts = pd.to_datetime(tr["signal_time"])
    cutoff = ts.min() + (ts.max() - ts.min()) * 0.7
    test = tr[ts >= cutoff]["pnl_points"].to_numpy(dtype=float)
    tw, tl = test[test > 0].sum(), abs(test[test < 0].sum())
    return {"n": len(tr), "wr": float((pnl > 0).mean() * 100), "pf": float(gw / gl if gl > 0 else 999),
            "ev": float(pnl.mean()), "pnl": float(pnl.sum()), "test_pf": float(tw / tl if tl > 0 else 999)}


for symbol in ["XAUUSDm", "USOILm"]:
    print("=" * 30, symbol, "=" * 30)
    rows = []
    for gt in [2.5, 3.0, 3.5]:
        for tr_ in [1.5, 2.0, 2.5, 3.0]:
            for tw in [0.5, 0.6]:
                tr = run(symbol, gt, tr_, tw)
                m = stats(tr)
                if m and m["n"] >= 10:
                    rows.append((gt, tr_, tw, m, tr))
    rows.sort(key=lambda x: -x[3]["pf"])
    print("Top8 (n>=10):")
    for gt, tr_, tw, m, tr in rows[:8]:
        ln = int((tr["dir"] == 1).sum()); sn = int((tr["dir"] == -1).sum())
        print("  gate=%4.1f rise=%4.1f w=%.1f  n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%% L=%d S=%d" % (
            gt, tr_, tw, m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"], ln, sn))
    # recommended: pick best n>=20 for yearly breakdown
    cand = [x for x in rows if x[3]["n"] >= 20]
    if not cand:
        cand = rows
    gt, tr_, tw, m, tr = cand[0]
    print()
    print("推荐（n>=20 中 PF 最高）: gate=%s rise=%s w=%s  n=%d pf=%.3f pnl=%.1f test_pf=%.3f" % (gt, tr_, tw, m["n"], m["pf"], m["pnl"], m["test_pf"]))
    df = tr.copy(); df["year"] = pd.to_datetime(df["signal_time"]).dt.year
    y = df.groupby("year").agg(n=("pnl_points", "size"), pnl=("pnl_points", "sum"),
                                wr=("pnl_points", lambda x: (x > 0).mean() * 100)).round(2)
    print(y.to_string())
    print("exit:", tr["exit_reason"].value_counts().to_dict(), "dir:", tr["dir"].value_counts().to_dict(), "avg_hold:", round(tr["holding_bars"].mean(), 1))
    tr.to_csv(OUT / ("bias_reversal_v5_%s.csv" % symbol), index=False, encoding="utf-8-sig")
    print()
