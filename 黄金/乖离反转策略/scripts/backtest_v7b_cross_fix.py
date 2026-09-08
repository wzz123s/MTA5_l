# -*- coding: utf-8 -*-
"""v7b: 修正死叉确认条件（bad bar 属于 up 段尾部）+ 确认冷却结论"""
import sys
sys.path.insert(0, r"F:\use_code\MTA5_l\scripts")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\scripts\signals")
import numpy as np
import pandas as pd
from pathlib import Path
from backtest_v7_cooldown import run_short_v7, stats

# 修正版：need_cross 时允许 direction==up 或 raw_dir==bad（死叉在 up 段末尾）
# 直接改函数参数意义：在 v7 脚本里 need_cross 用的是 raw_dir[i-1]=="bad" 且 direction[i-1]=="up"
# 重新实现交叉确认版本
import importlib, backtest_v7_cooldown as v7
importlib.reload(v7)

def run_cross(stop_pct, cd_rule, cd_hours, cost=0.05, tp_r=3.0):
    """做空：H4超涨门 + 2H段结构(up 或 bad bar) + 段涨幅/way 达标；bad bar 视为确认"""
    from backtest_v5_dual_symbols import pipeline, h4_states, seg_extremes
    RAW = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\raw")
    h4 = pipeline(RAW / "XAUUSDm_H4.csv", "4H")
    b55 = pd.to_numeric(h4["SMA_55"], errors="coerce")
    bias55 = (h4["close"] - b55) / b55 * 100.0
    s5 = pd.to_numeric(h4["SMA_5"], errors="coerce")
    state = np.zeros(len(h4), dtype=int)
    state[((h4["close"] > s5) & (h4["close"] > b55) & (bias55 >= 3.5)).to_numpy()] = 1
    h4_times = h4["bar_close_time"].to_numpy()
    h2 = pipeline(RAW / "XAUUSDm_H2.csv", "2H")
    direction = h2["方向_合并后"].values.astype(object)
    raw_dir = h2["方向"].values.astype(object)
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
    streak_loss = 0; cd_until = None
    for i in range(1, n2):
        t = times[i]
        gi = bisect.bisect_right(h4_times, t) - 1
        st = int(state[gi]) if gi >= 0 else 0
        if pos is None:
            if cd_until is not None and t < cd_until:
                continue
            in_up = (direction[i - 1] == "up" or raw_dir[i - 1] == "bad")
            cond = (st == 1 and in_up and np.isfinite(rise[i - 1]) and rise[i - 1] >= 3.0 and
                    ext_wsw[i - 1] >= 0.5 and ext_vwsw[i - 1] >= 0.5)
            if cond:
                entry = opens[i]; stop = entry * (1.0 + stop_pct / 100.0)
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
                if cd_rule == "loss_streak" and streak_loss >= 2:
                    cd_until = t + pd.Timedelta(hours=cd_hours)
    return pd.DataFrame(trades)

print("=== B2. 死叉确认（修正：bad bar 计入 up 段）===")
for sp in [1.0, 1.2]:
    for cd, h in [(None, 0), ("loss_streak", 120)]:
        tr = run_cross(sp, cd, h)
        m = stats(tr)
        if m:
            print("stop=%.1f%% cd=%s  n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
                sp, cd or "none", m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))
