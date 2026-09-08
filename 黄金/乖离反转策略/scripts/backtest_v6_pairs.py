# -*- coding: utf-8 -*-
"""v6: 周期配对扩展 + 多空组合
P1: H4 门 + 1H 段结构反转
P2: 6H 门 + 2H 段结构反转
P3: 组合 = 超涨反转做空(R3) + 顺势做多(6H bias5+55>0 门 + M30 金叉, 参考 2H_M30_6H)
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
OUT = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\validation")


def pipeline(csv_path, tf):
    frame = standardize_mt5_csv(csv_path, tf, closed_time=True)
    frame = add_indicators(frame)
    frame["vol_ma_120"] = pd.to_numeric(frame["volume"], errors="coerce").fillna(0).rolling(120, min_periods=1).mean()
    frame = mark_direction(frame)
    frame = filter_short_segments(frame, min_len=8)
    frame = add_way_grade(frame)
    return frame.reset_index(drop=True)


LBL = {"H1": "1H", "H2": "2H", "H4": "4H", "H6": "6H"}


def gate_state(gate_tf, thr):
    g = pipeline(RAW / ("XAUUSDm_" + gate_tf + ".csv"), LBL.get(gate_tf, gate_tf))
    b55 = pd.to_numeric(g["SMA_55"], errors="coerce")
    bias55 = (g["close"] - b55) / b55 * 100.0
    s5 = pd.to_numeric(g["SMA_5"], errors="coerce")
    state = np.zeros(len(g), dtype=int)
    over = (g["close"] > s5) & (g["close"] > b55) & (bias55 >= thr)
    under = (g["close"] < s5) & (g["close"] < b55) & (bias55 <= -thr)
    state[over.to_numpy()] = 1
    state[under.to_numpy()] = -1
    return state, g["bar_close_time"].to_numpy()


def seg_extremes(tf):
    f = pipeline(RAW / ("XAUUSDm_" + tf + ".csv"), LBL.get(tf, tf))
    direction = f["方向_合并后"].values.astype(object)
    sma13 = pd.to_numeric(f["SMA_13"], errors="coerce").to_numpy()
    high = f["high"].to_numpy(dtype=float)
    low = f["low"].to_numpy(dtype=float)
    wsw = pd.to_numeric(f["way_s_way"], errors="coerce").to_numpy()
    vwsw = pd.to_numeric(f["vol_way_s_way"], errors="coerce").to_numpy()
    n = len(f)
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
            cur_seg = sma13[c1:i + 1]; prev_seg = sma13[c0:c1]
            cur_seg = cur_seg[np.isfinite(cur_seg)]; prev_seg = prev_seg[np.isfinite(prev_seg)]
            if len(cur_seg) and len(prev_seg):
                if cur_sign == 1:
                    prev_ext = prev_seg.min()
                    rise[i] = (cur_seg.max() - prev_ext) / prev_ext * 100.0 if prev_ext else np.nan
                else:
                    prev_ext = prev_seg.max()
                    rise[i] = (prev_ext - cur_seg.min()) / prev_ext * 100.0 if prev_ext else np.nan
    return f, rise, ext_wsw, ext_vwsw


def run_pair(gate_tf, sig_tf, thr, thr_rise, thr_w, stop_pct, tp_r=3.0, cost=0.05):
    state, g_times = gate_state(gate_tf, thr)
    sig, rise, ext_wsw, ext_vwsw = seg_extremes(sig_tf)
    direction = sig["方向_合并后"].values.astype(object)
    opens = sig["open"].to_numpy(dtype=float)
    highs = sig["high"].to_numpy(dtype=float)
    lows = sig["low"].to_numpy(dtype=float)
    times = sig["bar_close_time"].to_numpy()
    n = len(sig)
    import bisect
    trades = []
    pos = None
    for i in range(1, n):
        t = times[i]
        gi = bisect.bisect_right(g_times, t) - 1
        st = int(state[gi]) if gi >= 0 else 0
        if pos is None:
            sig2 = 0
            if st == 1 and direction[i - 1] == "up" and np.isfinite(rise[i - 1]) and rise[i - 1] >= thr_rise and ext_wsw[i - 1] >= thr_w and ext_vwsw[i - 1] >= thr_w:
                sig2 = -1
            elif st == -1 and direction[i - 1] == "down" and np.isfinite(rise[i - 1]) and rise[i - 1] >= thr_rise and ext_wsw[i - 1] >= thr_w and ext_vwsw[i - 1] >= thr_w:
                sig2 = 1
            if sig2 == -1:
                entry = opens[i]; stop = entry * (1.0 + stop_pct / 100.0)
                pos = {"dir": -1, "entry": entry, "stop": stop, "tp": entry - (stop - entry) * tp_r, "entry_i": i}
            elif sig2 == 1:
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


print("=== P1: H4 门 + 1H 结构反转 (stop 0.8%) ===")
for gt in [2.5, 3.0, 3.5]:
    for tr_ in [1.5, 2.0, 3.0]:
        for tw in [0.4, 0.5]:
            m = stats(run_pair("H4", "H1", gt, tr_, tw, 0.8))
            if m and m["n"] >= 20:
                print("gate=%4.1f rise=%4.1f w=%.1f  n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
                    gt, tr_, tw, m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))

print()
print("=== P2: 6H 门 + 2H 结构反转 (stop 1.2%) ===")
for gt in [2.5, 3.0, 3.5]:
    for tr_ in [1.5, 2.0, 3.0]:
        for tw in [0.4, 0.5]:
            m = stats(run_pair("H6", "H2", gt, tr_, tw, 1.2))
            if m and m["n"] >= 20:
                print("gate=%4.1f rise=%4.1f w=%.1f  n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
                    gt, tr_, tw, m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))
