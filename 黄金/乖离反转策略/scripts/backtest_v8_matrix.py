# -*- coding: utf-8 -*-
"""v8: 门增强(bias5/H4way) + 1H小周期 + post_n + SMA13止损（做空侧）+ 做多侧变体"""
import sys
sys.path.insert(0, r"F:\use_code\MTA5_l\scripts")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\scripts\signals")
import numpy as np
import pandas as pd
from pathlib import Path
from backtest_v5_dual_symbols import pipeline, seg_extremes, stats

RAW = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\raw")
OUT = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\validation")


def prep_gate(gate_tf):
    g = pipeline(RAW / ("XAUUSDm_" + gate_tf + ".csv"), LBLX.get(gate_tf, gate_tf))
    b55 = pd.to_numeric(g["SMA_55"], errors="coerce")
    bias55 = (g["close"] - b55) / b55 * 100.0
    s5 = pd.to_numeric(g["SMA_5"], errors="coerce")
    bias5 = (g["close"] - s5) / s5 * 100.0
    return g, bias55, bias5


LBLX = {"H1": "1H", "H2": "2H", "H4": "4H", "H6": "6H", "M30": "30M"}

def prep_sig(sig_tf):
    f = pipeline(RAW / ("XAUUSDm_" + sig_tf + ".csv"), LBLX.get(sig_tf, sig_tf))
    rise, ext_wsw, ext_vwsw = seg_extremes(f)
    return f, rise, ext_wsw, ext_vwsw


def run_short_v8(sig_tf, gate_b5_thr, gate_way, post_n, stop_mode, cd_hours=120,
                 stop_pct=1.2, tp_r=3.0, cost=0.05, rise_thr=3.0, w_thr=0.5):
    """做空：H4门(可选bias5/way增强) + sig_tf段结构(可选post_n) + 止损(固定/SMA13) + 冷却"""
    g, bias55, bias5 = prep_gate("H4")
    gate = (g["close"] > pd.to_numeric(g["SMA_5"], errors="coerce")) & (g["close"] > pd.to_numeric(g["SMA_55"], errors="coerce")) & (bias55 >= 3.5)
    if gate_b5_thr is not None:
        gate = gate & (bias5 >= gate_b5_thr)
    if gate_way:
        g2 = pipeline(RAW / "XAUUSDm_H4.csv", "4H")
        _, g_wsw, g_vwsw = seg_extremes(g2)
        gate = gate & (g_wsw >= 0.5) & (g_vwsw >= 0.5)
    g_times = g["bar_close_time"].to_numpy()
    gstate = gate.to_numpy(dtype=int)

    f, rise, ext_wsw, ext_vwsw = prep_sig(sig_tf)
    direction = f["方向_合并后"].values.astype(object)
    raw_dir = f["方向"].values.astype(object)
    sma13 = pd.to_numeric(f["SMA_13"], errors="coerce").to_numpy()
    opens = f["open"].to_numpy(dtype=float)
    highs = f["high"].to_numpy(dtype=float)
    lows = f["low"].to_numpy(dtype=float)
    times = f["bar_close_time"].to_numpy()
    n = len(f)
    # last bad (dead cross) index per bar
    last_bad = np.zeros(n, dtype=int)
    lb = -9999
    for i in range(n):
        if raw_dir[i] == "bad":
            lb = i
        last_bad[i] = lb

    import bisect
    trades = []; pos = None
    streak_loss = 0; cd_until = None
    for i in range(1, n):
        t = times[i]
        gi = bisect.bisect_right(g_times, t) - 1
        st = int(gstate[gi]) if gi >= 0 else 0
        if pos is None:
            if cd_until is not None and t < cd_until:
                continue
            in_up = (direction[i - 1] == "up" or raw_dir[i - 1] == "bad")
            cond = (st == 1 and in_up and np.isfinite(rise[i - 1]) and rise[i - 1] >= rise_thr and
                    ext_wsw[i - 1] >= w_thr and ext_vwsw[i - 1] >= w_thr)
            if post_n > 0:
                dist = (i - 1) - last_bad[i - 1]
                cond = cond and (2 <= dist <= post_n)
            if cond:
                entry = opens[i]
                if stop_mode == "sma13":
                    s13 = sma13[i - 1] if np.isfinite(sma13[i - 1]) else entry
                    stop = s13 if s13 > entry * 1.002 else entry * 1.002
                else:
                    stop = entry * (1.0 + stop_pct / 100.0)
                pos = {"dir": -1, "entry": entry, "stop": stop,
                       "tp": entry - (stop - entry) * tp_r, "entry_i": i}
        else:
            exit_px = None; reason = None
            if highs[i] >= pos["stop"]: exit_px, reason = pos["stop"], "SL hit"
            elif lows[i] <= pos["tp"]: exit_px, reason = pos["tp"], "TP hit"
            if exit_px is None and direction[i] == "good":
                exit_px, reason = opens[i], "reverse cross"
            if exit_px is not None:
                pnl = (pos["entry"] - exit_px) - pos["entry"] * cost / 100.0 * 2.0
                trades.append({"signal_time": times[pos["entry_i"] - 1], "dir": -1,
                               "entry": pos["entry"], "stop": pos["stop"],
                               "exit_time": t, "exit": exit_px, "exit_reason": reason,
                               "pnl_points": pnl, "holding_bars": i - pos["entry_i"]})
                pos = None
                streak_loss = streak_loss + 1 if pnl < 0 else 0
                if streak_loss >= 2:
                    cd_until = t + pd.Timedelta(hours=cd_hours)
    return pd.DataFrame(trades)


def run_long_v8(sig_tf, post_n, stop_mode, stop_pct=1.2, tp_r=3.0, cost=0.05):
    """做多：6H门 + sig_tf金叉(可选post_n) + 止损(固定/SMA13)"""
    h6, b5_6, b55_6 = prep_gate("H6")
    gate = (h6["close"] > pd.to_numeric(h6["SMA_5"], errors="coerce")) & (h6["close"] > pd.to_numeric(h6["SMA_55"], errors="coerce"))
    g_times = h6["bar_close_time"].to_numpy()
    gstate = gate.to_numpy(dtype=int)

    f = pipeline(RAW / ("XAUUSDm_" + sig_tf + ".csv"), LBLX.get(sig_tf, sig_tf))
    p5 = f["SMA_5"].shift(1); p13 = f["SMA_13"].shift(1)
    gold = ((f["SMA_5"] > f["SMA_13"]) & (p5 <= p13)).to_numpy()
    dead = ((f["SMA_5"] < f["SMA_13"]) & (p5 >= p13)).to_numpy()
    sma13 = pd.to_numeric(f["SMA_13"], errors="coerce").to_numpy()
    opens = f["open"].to_numpy(dtype=float); highs = f["high"].to_numpy(dtype=float)
    lows = f["low"].to_numpy(dtype=float); times = f["bar_close_time"].to_numpy()
    n = len(f)
    last_good = np.zeros(n, dtype=int)
    lg = -9999
    for i in range(n):
        if gold[i]:
            lg = i
        last_good[i] = lg
    import bisect
    trades = []; pos = None
    for i in range(1, n):
        t = times[i]
        gi = bisect.bisect_right(g_times, t) - 1
        st = bool(gstate[gi]) if gi >= 0 else False
        if pos is None:
            cond = gold[i - 1] and st
            if post_n > 0:
                dist = (i - 1) - last_good[i - 1]
                cond = cond or (st and 2 <= dist <= post_n)
            if cond:
                entry = opens[i]
                if stop_mode == "sma13":
                    s13 = sma13[i - 1] if np.isfinite(sma13[i - 1]) else entry
                    stop = s13 if s13 < entry * 0.998 else entry * 0.998
                else:
                    stop = entry * (1.0 - stop_pct / 100.0)
                pos = {"dir": 1, "entry": entry, "stop": stop,
                       "tp": entry + (entry - stop) * tp_r, "entry_i": i}
        else:
            exit_px = None; reason = None
            if lows[i] <= pos["stop"]: exit_px, reason = pos["stop"], "SL hit"
            elif highs[i] >= pos["tp"]: exit_px, reason = pos["tp"], "TP hit"
            if exit_px is None and dead[i]:
                exit_px, reason = opens[i], "dead cross"
            if exit_px is not None:
                pnl = (exit_px - pos["entry"]) - pos["entry"] * cost / 100.0 * 2.0
                trades.append({"signal_time": times[pos["entry_i"] - 1], "dir": 1,
                               "entry": pos["entry"], "stop": pos["stop"],
                               "exit_time": t, "exit": exit_px, "exit_reason": reason,
                               "pnl_points": pnl, "holding_bars": i - pos["entry_i"]})
                pos = None
    return pd.DataFrame(trades)


print("========== 做空侧（黄金，冷却120h 默认开启）==========")
print("--- V1: H4 bias5 超涨增强 + H4 way/vol_way 过滤（2H 信号, 固定1.2%止损）---")
for b5 in [None, 1.0, 1.5, 2.0]:
    for gw in [False, True]:
        tr = run_short_v8("H2", b5, gw, 0, "fixed")
        m = stats(tr)
        if m and m["n"] >= 10:
            print("b5=%-4s h4way=%-5s n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
                str(b5), str(gw), m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))

print()
print("--- V2: 1H 小周期信号（段结构在 1H）---")
for b5 in [None, 1.5]:
    tr = run_short_v8("H1", b5, False, 0, "fixed")
    m = stats(tr)
    if m and m["n"] >= 10:
        print("sig=1H b5=%-4s n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
            str(b5), m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))

print()
print("--- V3: post_n（死叉后第 2..N 根，2H 信号）---")
for pn in [0, 3, 5, 8]:
    tr = run_short_v8("H2", None, False, pn, "fixed")
    m = stats(tr)
    if m and m["n"] >= 10:
        print("post_n=%s  n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
            str(pn), m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))

print()
print("--- V4: SMA13 结构止损（vs 固定1.2%）---")
for sm in ["fixed", "sma13"]:
    for pn in [0, 5]:
        tr = run_short_v8("H2", None, False, pn, sm)
        m = stats(tr)
        if m and m["n"] >= 10:
            print("stop=%-6s post_n=%s  n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
                sm, str(pn), m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))

print()
print("========== 做多侧（黄金）==========")
for sig in ["M30", "H1"]:
    for pn in [0, 3]:
        tr = run_long_v8(sig, pn, "fixed")
        m = stats(tr)
        if m and m["n"] >= 10:
            print("sig=%-3s post_n=%s  n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
                sig, str(pn), m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))
tr = run_long_v8("H1", 0, "sma13")
m = stats(tr)
if m and m["n"] >= 10:
    print("sig=H1 sma13止损  n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))
