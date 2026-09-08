# -*- coding: utf-8 -*-
"""v5b: 做多侧（超跌反转）单独放宽测试 - 黄金 + 原油
做多条件放宽：gate 1.5/2.0/2.5、rise 1.0/1.5/2.0、w 0.3/0.4/0.5
"""
import sys
sys.path.insert(0, r"F:\use_code\MTA5_l\scripts")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\scripts\signals")
import numpy as np
import pandas as pd
from pathlib import Path
from backtest_v5_dual_symbols import pipeline, h4_states, seg_extremes, stats

RAW = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\raw")
RAWO = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\raw_oil")


def run_long_only(symbol, thr, thr_rise, thr_w, stop_pct=1.2, tp_r=3.0, cost=0.05):
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
            if st == -1 and direction[i - 1] == "down" and np.isfinite(rise[i - 1]) and rise[i - 1] >= thr_rise and ext_wsw[i - 1] >= thr_w and ext_vwsw[i - 1] >= thr_w:
                sig = 1
            if sig == 1:
                entry = opens[i]; stop = entry * (1.0 - stop_pct / 100.0)
                pos = {"dir": 1, "entry": entry, "stop": stop, "tp": entry + (entry - stop) * tp_r, "entry_i": i}
        else:
            d = 1; exit_px = None; reason = None
            if lows[i] <= pos["stop"]: exit_px, reason = pos["stop"], "SL hit"
            elif highs[i] >= pos["tp"]: exit_px, reason = pos["tp"], "TP hit"
            if exit_px is None:
                if direction[i] == "bad": exit_px, reason = opens[i], "reverse cross"
            if exit_px is not None:
                pnl = (exit_px - pos["entry"]) - pos["entry"] * cost / 100.0 * 2.0
                trades.append({"signal_time": times[pos["entry_i"] - 1], "dir": 1,
                               "entry": pos["entry"], "stop": pos["stop"],
                               "exit_time": t, "exit": exit_px, "exit_reason": reason,
                               "pnl_points": pnl, "holding_bars": i - pos["entry_i"]})
                pos = None
    return pd.DataFrame(trades)


for symbol in ["XAUUSDm", "USOILm"]:
    print("=" * 26, symbol, "做多侧放宽", "=" * 26)
    rows = []
    for gt in [1.5, 2.0, 2.5]:
        for tr_ in [1.0, 1.5, 2.0]:
            for tw in [0.3, 0.4, 0.5]:
                tr = run_long_only(symbol, gt, tr_, tw)
                m = stats(tr)
                if m and m["n"] >= 10:
                    rows.append((gt, tr_, tw, m, tr))
    rows.sort(key=lambda x: -x[3]["pf"])
    for gt, tr_, tw, m, tr in rows[:8]:
        print("  gate=%4.1f rise=%4.1f w=%.1f  n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
            gt, tr_, tw, m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))
    if rows:
        gt, tr_, tw, m, tr = rows[0]
        df = tr.copy(); df["year"] = pd.to_datetime(df["signal_time"]).dt.year
        print("  推荐: gate=%s rise=%s w=%s" % (gt, tr_, tw))
        print(df.groupby("year").agg(n=("pnl_points", "size"), pnl=("pnl_points", "sum")).round(2).to_string())
    else:
        print("  （无 n>=10 组合）")
    print()
