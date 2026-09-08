# -*- coding: utf-8 -*-
"""P3: 组合版 = 超涨反转做空(R3: H4门+2H结构) + 顺势做多(6H bias5+55>0门 + M30金叉, 参考2H_M30_6H)"""
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
LBL = {"H1": "1H", "H2": "2H", "H4": "4H", "H6": "6H"}


def pipeline(csv_path, tf):
    frame = standardize_mt5_csv(csv_path, tf, closed_time=True)
    frame = add_indicators(frame)
    frame["vol_ma_120"] = pd.to_numeric(frame["volume"], errors="coerce").fillna(0).rolling(120, min_periods=1).mean()
    frame = mark_direction(frame)
    frame = filter_short_segments(frame, min_len=8)
    frame = add_way_grade(frame)
    return frame.reset_index(drop=True)


def short_side(gate_thr=3.5, thr_rise=3.0, thr_w=0.5, stop_pct=1.2, tp_r=3.0, cost=0.05):
    """超涨反转做空: H4 bias55>=gate 门 + 2H up段 SMA13涨幅 + way/vol_way 极值"""
    h4 = pipeline(RAW / "XAUUSDm_H4.csv", "4H")
    b55 = pd.to_numeric(h4["SMA_55"], errors="coerce")
    bias55 = (h4["close"] - b55) / b55 * 100.0
    s5 = pd.to_numeric(h4["SMA_5"], errors="coerce")
    # D 修复 (2026-09-06, EA 审查联动): 原 state 单调置 1 不回落 —— 一旦某根 H4 触发超涨门,
    # 之后所有 bar 做空资格恒真 (python 参考高估做空机会; EA RefreshGates 每 H4 bar 重算是正确的)。
    # 改为按每根 H4 bar 自身条件即时判门 (不锁存), 与 EA RefreshGates 逐 bar 一致。
    cond = ((h4["close"] > s5) & (h4["close"] > b55) & (bias55 >= gate_thr)).to_numpy()
    state = cond.astype(int)
    h4_times = h4["bar_close_time"].to_numpy()

    h2 = pipeline(RAW / "XAUUSDm_H2.csv", "2H")
    direction = h2["方向_合并后"].values.astype(object)
    sma13 = pd.to_numeric(h2["SMA_13"], errors="coerce").to_numpy()
    high = h2["high"].to_numpy(dtype=float)
    low = h2["low"].to_numpy(dtype=float)
    wsw = pd.to_numeric(h2["way_s_way"], errors="coerce").to_numpy()
    vwsw = pd.to_numeric(h2["vol_way_s_way"], errors="coerce").to_numpy()
    n2 = len(h2)
    crosses = [i for i in range(n2) if direction[i] in ("good", "bad")]
    rise = np.full(n2, np.nan); ext_wsw = np.full(n2, np.nan); ext_vwsw = np.full(n2, np.nan)
    cur_sign = 0; run_ext_idx = -1
    for i in range(n2):
        d = direction[i]
        sign = 1 if d in ("good", "up") else (-1 if d in ("bad", "down") else 0)
        if sign != cur_sign:
            cur_sign = sign; run_ext_idx = i
        elif cur_sign == 1 and high[i] > high[run_ext_idx]:
            run_ext_idx = i
        elif cur_sign == -1 and low[i] < low[run_ext_idx]:
            run_ext_idx = i
        if run_ext_idx >= 0:
            ext_wsw[i] = wsw[run_ext_idx]; ext_vwsw[i] = vwsw[run_ext_idx]
        ci = np.searchsorted(crosses, i) - 1
        if ci >= 1 and cur_sign == 1:
            c1 = crosses[ci]; c0 = crosses[ci - 1]
            cur_seg = sma13[c1:i + 1][np.isfinite(sma13[c1:i + 1])]
            prev_seg = sma13[c0:c1][np.isfinite(sma13[c0:c1])]
            if len(cur_seg) and len(prev_seg) and prev_seg.min():
                rise[i] = (cur_seg.max() - prev_seg.min()) / prev_seg.min() * 100.0
    opens = h2["open"].to_numpy(dtype=float); highs = h2["high"].to_numpy(dtype=float)
    lows = h2["low"].to_numpy(dtype=float); times = h2["bar_close_time"].to_numpy()
    import bisect
    trades = []; pos = None
    for i in range(1, n2):
        t = times[i]
        gi = bisect.bisect_right(h4_times, t) - 1
        st = int(state[gi]) if gi >= 0 else 0
        if pos is None:
            if st == 1 and direction[i - 1] == "up" and np.isfinite(rise[i - 1]) and rise[i - 1] >= thr_rise and ext_wsw[i - 1] >= thr_w and ext_vwsw[i - 1] >= thr_w:
                entry = opens[i]; stop = entry * (1.0 + stop_pct / 100.0)
                pos = {"dir": -1, "entry": entry, "stop": stop, "tp": entry - (stop - entry) * tp_r, "entry_i": i}
        else:
            exit_px = None; reason = None
            if highs[i] >= pos["stop"]: exit_px, reason = pos["stop"], "SL hit"
            elif lows[i] <= pos["tp"]: exit_px, reason = pos["tp"], "TP hit"
            if exit_px is None and direction[i] == "good":
                exit_px, reason = opens[i], "reverse cross"
            if exit_px is not None:
                pnl = (pos["entry"] - exit_px) - pos["entry"] * cost / 100.0 * 2.0
                trades.append({"signal_time": times[pos["entry_i"] - 1], "dir": -1, "entry": pos["entry"],
                               "stop": pos["stop"], "exit_time": t, "exit": exit_px, "exit_reason": reason,
                               "pnl_points": pnl, "holding_bars": i - pos["entry_i"]})
                pos = None
    return pd.DataFrame(trades)


def long_side(stop_pct=1.2, tp_r=3.0, cost=0.05):
    """顺势做多: 6H bias5>0 & bias55>0 门 + M30 金叉（参考 2H_M30_6H）"""
    h6 = pipeline(RAW / "XAUUSDm_H6.csv", "6H")
    b5 = (h6["close"] - pd.to_numeric(h6["SMA_5"], errors="coerce")) / pd.to_numeric(h6["SMA_5"], errors="coerce") * 100.0
    b55 = (h6["close"] - pd.to_numeric(h6["SMA_55"], errors="coerce")) / pd.to_numeric(h6["SMA_55"], errors="coerce") * 100.0
    gate = (b5 > 0) & (b55 > 0)
    h6_times = h6["bar_close_time"].to_numpy()

    m30 = pipeline(RAW / "XAUUSDm_M30.csv", "30M")
    prev5 = m30["SMA_5"].shift(1); prev13 = m30["SMA_13"].shift(1)
    gold = ((m30["SMA_5"] > m30["SMA_13"]) & (prev5 <= prev13)).to_numpy()
    dead = ((m30["SMA_5"] < m30["SMA_13"]) & (prev5 >= prev13)).to_numpy()
    opens = m30["open"].to_numpy(dtype=float); highs = m30["high"].to_numpy(dtype=float)
    lows = m30["low"].to_numpy(dtype=float); times = m30["bar_close_time"].to_numpy()
    n = len(m30)
    import bisect
    trades = []; pos = None
    for i in range(1, n):
        t = times[i]
        gi = bisect.bisect_right(h6_times, t) - 1
        gopen = bool(gate.iloc[gi]) if gi >= 0 else False
        if pos is None:
            if gold[i - 1] and gopen:
                entry = opens[i]; stop = entry * (1.0 - stop_pct / 100.0)
                pos = {"dir": 1, "entry": entry, "stop": stop, "tp": entry + (entry - stop) * tp_r, "entry_i": i}
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


sh = short_side()
lo = long_side()
all_t = pd.concat([sh, lo], ignore_index=True).sort_values("signal_time").reset_index(drop=True)
print("=== 做空侧（超涨反转 R3）===")
ms = stats(sh)
print("n=%d pf=%.3f pnl=%.1f test_pf=%.3f wr=%.1f%%" % (ms["n"], ms["pf"], ms["pnl"], ms["test_pf"], ms["wr"]))
print("=== 做多侧（6H门+M30金叉 顺势）===")
ml = stats(lo)
print("n=%d pf=%.3f pnl=%.1f test_pf=%.3f wr=%.1f%%" % (ml["n"], ml["pf"], ml["pnl"], ml["test_pf"], ml["wr"]))
print("=== 组合（多空合并）===")
mc = stats(all_t)
print("n=%d pf=%.3f pnl=%.1f test_pf=%.3f wr=%.1f%%" % (mc["n"], mc["pf"], mc["pnl"], mc["test_pf"], mc["wr"]))
df = all_t.copy(); df["year"] = pd.to_datetime(df["signal_time"]).dt.year
g = df.groupby(["year", "dir"]).agg(n=("pnl_points", "size"), pnl=("pnl_points", "sum")).round(1)
print(g.to_string())
all_t.to_csv(OUT / "bias_reversal_v6_combined_trades.csv", index=False, encoding="utf-8-sig")
