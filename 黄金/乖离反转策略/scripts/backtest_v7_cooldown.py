# -*- coding: utf-8 -*-
"""v7: R3 黄金做空侧 - 冷却规则 + 止损幅度 + 2H死叉确认 测试"""
import sys
sys.path.insert(0, r"F:\use_code\MTA5_l\scripts")
sys.path.insert(0, r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\scripts\signals")
import numpy as np
import pandas as pd
from pathlib import Path
from backtest_v5_dual_symbols import pipeline, h4_states, seg_extremes, stats

RAW = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\raw")
OUT = Path(r"F:\use_code\MTA5_l\黄金\乖离反转策略\data\validation")


def run_short_v7(stop_pct, need_cross, cd_rule, cd_hours, big_win_pts=100.0, win_streak=2, loss_streak=2, cost=0.05, tp_r=3.0):
    """黄金做空侧（H4超涨门 + 2H段结构，可选2H死叉；冷却规则）"""
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
    last_close_time = None
    streak_win = 0; streak_loss = 0
    cd_until = None  # datetime of cooldown expiry
    for i in range(1, n2):
        t = times[i]
        gi = bisect.bisect_right(h4_times, t) - 1
        st = int(state[gi]) if gi >= 0 else 0
        if pos is None:
            # cooldown check
            if cd_until is not None and t < cd_until:
                continue
            cond_seg = (st == 1 and direction[i - 1] == "up" and np.isfinite(rise[i - 1]) and
                        rise[i - 1] >= 3.0 and ext_wsw[i - 1] >= 0.5 and ext_vwsw[i - 1] >= 0.5)
            cond_cross = (raw_dir[i - 1] == "bad") if need_cross else True
            if cond_seg and cond_cross:
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
                last_close_time = t
                # update streaks & cooldown
                if pnl > 0:
                    streak_win += 1; streak_loss = 0
                else:
                    streak_loss += 1; streak_win = 0
                if cd_rule == "big_win" and pnl >= big_win_pts:
                    cd_until = t + pd.Timedelta(hours=cd_hours)
                elif cd_rule == "win_streak" and streak_win >= win_streak:
                    cd_until = t + pd.Timedelta(hours=cd_hours)
                elif cd_rule == "loss_streak" and streak_loss >= loss_streak:
                    cd_until = t + pd.Timedelta(hours=cd_hours)
    return pd.DataFrame(trades)


print("=== A. 止损幅度敏感性（无冷却, 无cross）===")
for sp in [0.6, 0.8, 1.0, 1.2]:
    tr = run_short_v7(sp, False, None, 0)
    m = stats(tr)
    if m:
        risk01 = sp / 100.0 * 4600  # 0.01手止损金额(约)
        print("stop=%.1f%% (0.01手≈$%.0f)  n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
            sp, risk01, m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))

print()
print("=== B. 2H 死叉确认（need_cross）===")
for sp in [0.8, 1.2]:
    tr = run_short_v7(sp, True, None, 0)
    m = stats(tr)
    if m:
        print("stop=%.1f%% cross=on  n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
            sp, m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))

print()
print("=== C. 冷却规则（stop=1.0%, 无cross）===")
for rule, h in [("big_win", 72), ("win_streak", 72), ("loss_streak", 48), ("loss_streak", 72), ("loss_streak", 120)]:
    tr = run_short_v7(1.0, False, rule, h)
    m = stats(tr)
    if m:
        print("rule=%-12s %3dh  n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
            rule, h, m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))

print()
print("=== D. 组合：冷却 + 止损 0.8/1.0 ===")
for sp in [0.8, 1.0]:
    for rule, h in [("loss_streak", 72), ("big_win", 72)]:
        tr = run_short_v7(sp, False, rule, h)
        m = stats(tr)
        if m:
            print("stop=%.1f%% rule=%-12s %3dh  n=%3d pf=%.3f pnl=%8.1f test_pf=%.3f wr=%5.1f%%" % (
                sp, rule, h, m["n"], m["pf"], m["pnl"], m["test_pf"], m["wr"]))
