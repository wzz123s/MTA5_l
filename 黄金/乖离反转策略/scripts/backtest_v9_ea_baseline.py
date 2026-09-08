# -*- coding: utf-8 -*-
"""v9: EA 等价基线（2026-09-06, E 口径补齐）
EA BiasReversal_Combo_EA 默认(LongMode=0): 6H bias5&bias55>0 门 + H1 SMMA5 金叉做多;
退出 SL InpStopPct% / TP 3R / H1 死叉(下一 H1 开盘)。此处用因果 merged(方向_合并后) pipeline。
对照 v6b long_side(M30 金叉) 量化口径差异。
"""
import sys
sys.path.insert(0, r"F:\use_code\MTA5_l\scripts")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\scripts\signals")
import numpy as np
import pandas as pd
from pathlib import Path
from replay_raw_signals_with_stops import add_indicators, standardize_mt5_csv
from replay_1h_way_momentum_filter_scan import add_way_grade, filter_short_segments_causal as filter_short_segments, mark_direction

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


def long_ea_baseline(stop_pct=1.2, tp_r=3.0, cost=0.05):
    """EA 默认: 6H 门 + H1 SMMA5/13 金叉; SL/TP; H1 死叉平仓"""
    h6 = pipeline(RAW / "XAUUSDm_H6.csv", "6H")
    b5 = (h6["close"] - pd.to_numeric(h6["SMA_5"], errors="coerce")) / pd.to_numeric(h6["SMA_5"], errors="coerce") * 100.0
    b55 = (h6["close"] - pd.to_numeric(h6["SMA_55"], errors="coerce")) / pd.to_numeric(h6["SMA_55"], errors="coerce") * 100.0
    gate = ((b5 > 0) & (b55 > 0)).to_numpy()
    h6_times = h6["bar_close_time"].to_numpy()

    h1 = pipeline(RAW / "XAUUSDm_H1.csv", "1H")
    prev5 = pd.to_numeric(h1["SMA_5"], errors="coerce").shift(1)
    prev13 = pd.to_numeric(h1["SMA_13"], errors="coerce").shift(1)
    s5 = pd.to_numeric(h1["SMA_5"], errors="coerce").to_numpy()
    s13 = pd.to_numeric(h1["SMA_13"], errors="coerce").to_numpy()
    gold = ((s5 > s13) & (prev5 <= prev13)).to_numpy()
    dead = ((s5 < s13) & (prev5 >= prev13)).to_numpy()
    opens = h1["open"].to_numpy(dtype=float); highs = h1["high"].to_numpy(dtype=float)
    lows = h1["low"].to_numpy(dtype=float); times = h1["bar_close_time"].to_numpy()
    n = len(h1)
    import bisect
    trades = []; pos = None
    for i in range(1, n):
        t = times[i]
        gi = bisect.bisect_right(h6_times, t) - 1
        gopen = bool(gate[gi]) if gi >= 0 else False
        if pos is None:
            if gold[i - 1] and gopen:
                entry = opens[i]; stop = entry * (1.0 - stop_pct / 100.0)
                pos = {"entry": entry, "stop": stop, "tp": entry + (entry - stop) * tp_r, "entry_i": i}
        else:
            exit_px = None; reason = None
            if lows[i] <= pos["stop"]: exit_px, reason = pos["stop"], "SL hit"
            elif highs[i] >= pos["tp"]: exit_px, reason = pos["tp"], "TP hit"
            if exit_px is None and dead[i]:
                exit_px, reason = opens[i], "dead cross"
            if exit_px is not None:
                pnl = (exit_px - pos["entry"]) - pos["entry"] * cost / 100.0 * 2.0
                trades.append({"signal_time": times[pos["entry_i"] - 1], "dir": 1, "entry": pos["entry"],
                               "stop": pos["stop"], "exit_time": t, "exit": exit_px, "exit_reason": reason,
                               "pnl_points": pnl, "holding_bars": i - pos["entry_i"]})
                pos = None
    return pd.DataFrame(trades)


tr = long_ea_baseline()
m = stats(tr)
print("=== v9 EA 等价基线(6H门 + H1金叉/死叉) 做多侧 ===")
if m:
    print("n=%d pf=%.3f pnl=%.1f test_pf=%.3f wr=%.1f%%" % (m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))
    df = tr.copy(); df["year"] = pd.to_datetime(df["signal_time"]).dt.year
    print(df.groupby("year").agg(n=("pnl_points", "size"), pnl=("pnl_points", "sum")).round(1).to_string())
    print("exit reasons:", tr["exit_reason"].value_counts().to_dict())
tr.to_csv(OUT / "bias_reversal_v9_ea_baseline_long.csv", index=False, encoding="utf-8-sig")
