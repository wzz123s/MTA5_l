# -*- coding: utf-8 -*-
"""BiasReversal_Combo 监控复现（只读，纯函数，无顶层执行）。

逐 bar 复刻 auto_trade/BiasReversal_Combo_EA.mq5 已部署逻辑：
  做空: H4 门(close>SMA5 & close>SMA55 & bias55>=3.5%，取最新收盘 H4 bar)
        + Check2HShortSetup: S5/S13 交叉分段，当前段必须为 up 段、上一段为 down 段；
        rise=(当前段 SMA13 最高-上一段 SMA13 最低)/上一段最低；wsw/vwsw 在段内
        极值高点 bar 处取数（vol_ma=最近600根累计均值，与 EA 一致）
        -> 信号 bar 收盘后下一根 2H bar 开盘做空
        止损 = 信号 bar 收盘价 x 1.012（EA: stop = r[1].close*(1+InpStopPct/100)）
        止盈 = entry - (stop-entry)*3；退出: SL/TP 触及价 / 2H 金叉下根开盘平
        冷却: 连续 2 次 SL 后 120h（设计口径，与 v7 回测一致）
  做多: 6H 门(close>SMA5 & close>SMA55) + H1 SMMA5/13 金叉(已收盘 bar)
        -> 下一根 H1 bar 开盘做多；止损=信号 bar 收盘价 x 0.988
        退出: SL/TP 触及价 / H1 死叉下根开盘平
点数口径: 1点=0.01价，0.01手 1点=$1（XAUUSDm），即价差 x100。
"""
from __future__ import annotations

import bisect

import numpy as np
import pandas as pd

from replay_raw_signals_with_stops import add_indicators, standardize_mt5_csv


def pipeline(csv_path, tf):
    """标准化 + 指标（监控复现只需要价格/SMA/量）。"""
    frame = standardize_mt5_csv(csv_path, tf, closed_time=True)
    frame = add_indicators(frame)
    return frame.reset_index(drop=True)


def _smma(arr, period):
    out = np.full(len(arr), 0.0)
    if len(arr) < period:
        return out
    out[period - 1] = arr[:period].mean()
    for i in range(period, len(arr)):
        out[i] = (out[i - 1] * (period - 1) + arr[i]) / period
    return out


def _ea_short_setup(frame, i, s5, s13):
    """复刻 EA Check2HShortSetup（在已收盘 2H bar i 上评估）。

    返回 (rise, wsw, vwsw, ok) 或 None（段结构不成立）。
    """
    n = frame.shape[0]
    vol = frame["volume"].to_numpy(dtype=float)
    lows = frame["low"].to_numpy(dtype=float)
    highs = frame["high"].to_numpy(dtype=float)
    # EA 窗口: CopyRates(600)，vol_ma 为窗口内累计均值
    win0 = max(0, i - 599)
    vsum = 0.0
    cnt = 0
    vol_ma = np.full(n, np.nan)
    for j in range(win0, i + 1):
        vsum += vol[j]
        cnt += 1
        vol_ma[j] = vsum / cnt
    # 当前段起点（S5/S13 交叉）
    seg_start = win0
    seg_up = s5[win0] > s13[win0]
    for j in range(win0 + 1, i + 1):
        up = s5[j] > s13[j]
        if up != seg_up:
            seg_up = up
            seg_start = j
    if not seg_up:
        return None
    prev_end = seg_start - 1
    if prev_end < win0:
        return None
    prev_up = s5[prev_end] > s13[prev_end]
    prev_start = win0
    for j in range(prev_end - 1, win0 - 1, -1):
        up = s5[j] > s13[j]
        if up != prev_up:
            prev_start = j + 1
            break
    if prev_up:
        return None
    seg = s13[prev_start : prev_end + 1]
    if not (seg > 0).any():
        return None
    prev_min = float(seg.min())
    y = x = z = 0
    cur_max = 0.0
    ext_idx = -1
    ext_high = 0.0
    ext_wsw = 0.0
    ext_vwsw = 0.0
    for j in range(seg_start, i + 1):
        y += 1
        if lows[j] >= s13[j] and highs[j] >= highs[j - 1]:
            x += 1
        if vol[j] <= vol_ma[j]:
            z += 1
        if s13[j] > cur_max:
            cur_max = s13[j]
        if highs[j] > ext_high:
            ext_high = highs[j]
            ext_idx = j
        if ext_idx == j:
            ext_wsw = x / y if y > 0 else 0.0
            ext_vwsw = z / y if y > 0 else 0.0
    if y < 3:
        return None
    rise = (cur_max - prev_min) / prev_min * 100.0
    return rise, ext_wsw, ext_vwsw, (rise >= 3.0 and ext_wsw >= 0.5 and ext_vwsw >= 0.5)


def _gate_state(gate_frame, t):
    gt = gate_frame["bar_close_time"].to_numpy()
    gs = gate_frame["_gate"].to_numpy(dtype=int)
    gi = bisect.bisect_right(gt, t) - 1
    return bool(gs[gi]) if gi >= 0 else False


def replay_short(h4, h2, gate_thr=3.5, rise_thr=3.0, w_thr=0.5,
                 cd_loss=2, cd_hours=120.0, stop_pct=1.2, tp_r=3.0):
    """做空复现（EA 逐 bar 语义）。返回长表行。"""
    b55 = pd.to_numeric(h4["SMA_55"], errors="coerce").to_numpy(dtype=float)
    close4 = h4["close"].to_numpy(dtype=float)
    s54 = pd.to_numeric(h4["SMA_5"], errors="coerce").to_numpy(dtype=float)
    bias55 = (close4 - b55) / b55 * 100.0
    h4 = h4.copy()
    h4["_gate"] = (close4 > s54) & (close4 > b55) & (bias55 >= gate_thr)

    closes = h2["close"].to_numpy(dtype=float)
    opens = h2["open"].to_numpy(dtype=float)
    highs = h2["high"].to_numpy(dtype=float)
    lows = h2["low"].to_numpy(dtype=float)
    times = h2["bar_close_time"].to_numpy()
    n = len(h2)
    s5 = _smma(closes, 5)
    s13 = _smma(closes, 13)

    trades = []
    pos = None
    streak_loss = 0
    cd_until = None
    for i in range(1, n - 1):  # 只评估已收盘 bar（最后1根视为未完成）
        t = times[i]
        if pos is None:
            if cd_until is not None and pd.Timestamp(t) < cd_until:
                continue
            if _gate_state(h4, t):
                r = _ea_short_setup(h2, i, s5, s13)
                if r is not None and r[3]:
                    entry = opens[i + 1]
                    stop = closes[i] * (1.0 + stop_pct / 100.0)
                    pos = {
                        "dir": "S", "entry": entry, "stop": stop,
                        "tp": entry - (stop - entry) * tp_r,
                        "signal_time": times[i], "entry_i": i + 1,
                    }
        else:
            exit_px = None
            reason = None
            if highs[i] >= pos["stop"]:
                exit_px, reason = pos["stop"], "SL hit"
            elif lows[i] <= pos["tp"]:
                exit_px, reason = pos["tp"], "TP hit"
            elif s5[i] > s13[i] and s5[i - 1] <= s13[i - 1]:
                exit_px, reason = opens[i + 1], "gold cross"
            if exit_px is not None:
                pnl = pos["entry"] - exit_px
                trades.append({
                    "signal_time": pos["signal_time"],
                    "dir": "S",
                    "entry": pos["entry"],
                    "stop": pos["stop"],
                    "stage_pnl": pnl,
                    "stop_distance": abs(pos["entry"] - pos["stop"]),
                    "mode": "H4超涨+2H段反转",
                    "stage": 1,
                    "stage_exit_time": times[i] if reason in ("SL hit", "TP hit") else times[i + 1],
                    "stage_exit_price": exit_px,
                    "stage_reason": reason,
                })
                pos = None
                if pnl < 0:
                    streak_loss += 1
                    if streak_loss >= cd_loss:
                        cd_until = pd.Timestamp(t) + pd.Timedelta(hours=cd_hours)
                else:
                    streak_loss = 0
    if pos is not None:
        trades.append({
            "signal_time": pos["signal_time"],
            "dir": "S",
            "entry": pos["entry"],
            "stop": pos["stop"],
            "stage_pnl": pos["entry"] - closes[n - 2],
            "stop_distance": abs(pos["entry"] - pos["stop"]),
            "mode": "H4超涨+2H段反转",
            "stage": 1,
            "stage_exit_time": times[n - 2],
            "stage_exit_price": closes[n - 2],
            "stage_reason": "open",
        })
    return pd.DataFrame(trades)


def replay_long(h6, h1, stop_pct=1.2, tp_r=3.0):
    """做多复现（EA 语义）：6H 门 + H1 金叉 -> 下根 H1 开盘。"""
    close6 = h6["close"].to_numpy(dtype=float)
    s56 = pd.to_numeric(h6["SMA_5"], errors="coerce").to_numpy(dtype=float)
    s556 = pd.to_numeric(h6["SMA_55"], errors="coerce").to_numpy(dtype=float)
    h6 = h6.copy()
    h6["_gate"] = (close6 > s56) & (close6 > s556)

    closes = h1["close"].to_numpy(dtype=float)
    opens = h1["open"].to_numpy(dtype=float)
    highs = h1["high"].to_numpy(dtype=float)
    lows = h1["low"].to_numpy(dtype=float)
    times = h1["bar_close_time"].to_numpy()
    n = len(h1)
    s5 = _smma(closes, 5)
    s13 = _smma(closes, 13)

    trades = []
    pos = None
    for i in range(1, n - 1):
        t = times[i]
        if pos is None:
            gold_cross = s5[i] > s13[i] and s5[i - 1] <= s13[i - 1]
            if gold_cross and _gate_state(h6, t):
                entry = opens[i + 1]
                stop = closes[i] * (1.0 - stop_pct / 100.0)
                pos = {
                    "dir": "L", "entry": entry, "stop": stop,
                    "tp": entry + (entry - stop) * tp_r,
                    "signal_time": times[i], "entry_i": i + 1,
                }
        else:
            exit_px = None
            reason = None
            if lows[i] <= pos["stop"]:
                exit_px, reason = pos["stop"], "SL hit"
            elif highs[i] >= pos["tp"]:
                exit_px, reason = pos["tp"], "TP hit"
            elif s5[i] < s13[i] and s5[i - 1] >= s13[i - 1]:
                exit_px, reason = opens[i + 1], "dead cross"
            if exit_px is not None:
                pnl = exit_px - pos["entry"]
                trades.append({
                    "signal_time": pos["signal_time"],
                    "dir": "L",
                    "entry": pos["entry"],
                    "stop": pos["stop"],
                    "stage_pnl": pnl,
                    "stop_distance": abs(pos["entry"] - pos["stop"]),
                    "mode": "6H门+H1金叉",
                    "stage": 1,
                    "stage_exit_time": times[i] if reason in ("SL hit", "TP hit") else times[i + 1],
                    "stage_exit_price": exit_px,
                    "stage_reason": reason,
                })
                pos = None
    if pos is not None:
        trades.append({
            "signal_time": pos["signal_time"],
            "dir": "L",
            "entry": pos["entry"],
            "stop": pos["stop"],
            "stage_pnl": closes[n - 2] - pos["entry"],
            "stop_distance": abs(pos["entry"] - pos["stop"]),
            "mode": "6H门+H1金叉",
            "stage": 1,
            "stage_exit_time": times[n - 2],
            "stage_exit_price": closes[n - 2],
            "stage_reason": "open",
        })
    return pd.DataFrame(trades)


def replay_combo(h4_csv, h6_csv, h2_csv, h1_csv):
    """入口：返回 (长表 st, H1 帧)。st 列满足监控 per_trade_summary 契约。"""
    h4 = pipeline(h4_csv, "4H")
    h6 = pipeline(h6_csv, "6H")
    h2 = pipeline(h2_csv, "2H")
    h1 = pipeline(h1_csv, "1H")
    st = pd.concat(
        [replay_long(h6, h1), replay_short(h4, h2)],
        ignore_index=True,
    )
    for col in ("stage_pnl", "stop_distance"):
        st[col] = pd.to_numeric(st[col], errors="coerce") * 100.0
    st["signal_time"] = pd.to_datetime(st["signal_time"])
    st["stage_exit_time"] = pd.to_datetime(st["stage_exit_time"])
    return st, h1
