# -*- coding: utf-8 -*-
"""
stage2_backtest.py —— 阶段2 全链路回测引擎

链路（对齐策略计划 7.2~7.6 + 阶段1 结论）：
  J2 机会池：本级别 SMA13x55 穿越（可过滤粘合 glue）
  E3 方向：gold_long_only 时只做上穿；否则双向
  E5 入场：穿越后 lookback_days 内次级别首个同向 5x13 穿越 + bias55 同向 → fixed_delay_1
  S  止损：sub_struct（次级别 prev_seg SMA13 极值，StopSpec 过滤）或 home_struct
  X  退出：'tp'（1.5R/3R 三批）/ 'break'（反向穿越全出）/ 'trail'（高取低移动止损）/ 'hybrid'
  约束：同方向最多 1 个持仓（重叠信号跳过）；成本 = 点差 + 隔夜 x bar
输出：逐笔 + 年度统计（R 倍数口径）
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _trailing_stop_long(sub_df, start, stop_cur, entry, r):
    """高取低简化：4H 创新高后，移动止损至最近 down 段 SMA13 低点（不劣于保本）。"""
    return stop_cur


def fullchain_backtest(home_df: pd.DataFrame, sub_df: pd.DataFrame,
                       crossings: pd.DataFrame,
                       symbol: str, home_tf: str, sub_tf: str,
                       glue_thresh: float = 0.003,
                       bias_floor: float = 0.0,
                       stop_mode: str = "sub_struct",
                       stop_spec=None,
                       exit_mode: str = "tp",
                       time_exit_bars: int = 120,
                       lookback_days: float = 40.0,
                       long_only: bool = False,
                       spread_price: float = 0.0,
                       swap_per_bar: float = 0.0,
                       start: str = None, end: str = None) -> pd.DataFrame:
    """返回逐笔 trades DataFrame（含 pnl_R）。start/end 为窗口过滤（时间字符串）。"""
    n = len(sub_df)
    sub_time = pd.to_datetime(sub_df["time"].values)
    sub_open = sub_df["open"].values
    sub_high = sub_df["high"].values
    sub_low = sub_df["low"].values
    sub_close = sub_df["close"].values
    sub_state = sub_df["方向_合并后"].values
    sma55 = sub_df["SMA_55"].values
    sub_bias = np.where(np.isnan(sma55) | (sma55 == 0), np.nan,
                        (sub_close - sma55) / sma55 * 100.0)
    sub_stop_long = sub_df["prev_seg_low_sma13"].values
    sub_stop_short = sub_df["prev_seg_high_sma13"].values

    home_time = pd.to_datetime(home_df["time"].values)
    home_state = home_df["方向_合并后"].values
    good_pos = np.where(home_state == "good")[0]
    bad_pos = np.where(home_state == "bad")[0]
    home_stop_long = home_df["prev_seg_low_sma13"].values
    home_stop_short = home_df["prev_seg_high_sma13"].values

    def _struct_stop(i, d):
        if d == 1:
            j = good_pos[good_pos <= i]
            return home_stop_long[j[-1]] if len(j) else np.nan
        j = bad_pos[bad_pos <= i]
        return home_stop_short[j[-1]] if len(j) else np.nan

    open_pos = {}          # dir -> dict(entry, stop, R, sim_start, ...)
    trades = []

    # 按时间排序的穿越点
    cr = crossings.sort_values("time").reset_index(drop=True)

    for _, row in cr.iterrows():
        d = int(row["dir"])
        if long_only and d != 1:
            continue
        i = int(row["idx"])
        t = pd.to_datetime(row["time"])
        if start and t < pd.Timestamp(start):
            continue
        if end and t > pd.Timestamp(end):
            continue

        # 重叠约束：同方向已有持仓则跳过
        if d in open_pos:
            continue

        # 粘合过滤
        if glue_thresh is not None:
            if row["glue"] is not True:
                if abs(row["sma13"] - row["sma55"]) / row["sma55"] > glue_thresh:
                    continue

        # 结构止损（home 口径）
        stop = _struct_stop(i, d)
        if np.isnan(stop):
            continue

        # 入场：次级别同向穿越
        t_end = t + pd.Timedelta(days=lookback_days)
        mask = (sub_time > t) & (sub_time <= t_end)
        pos_idx = np.where(mask)[0]
        e = None
        for p in pos_idx:
            st = sub_state[p]
            if d == 1 and st == "good" and (np.isnan(sub_bias[p]) or sub_bias[p] > bias_floor):
                e = p
                break
            if d == -1 and st == "bad" and (np.isnan(sub_bias[p]) or sub_bias[p] < -bias_floor):
                e = p
                break
        if e is None or e + 1 >= n:
            continue
        entry = sub_open[e + 1]
        if np.isnan(entry):
            continue

        # 止损口径
        if stop_mode == "sub_struct":
            stop = sub_stop_long[e] if d == 1 else sub_stop_short[e]
            if np.isnan(stop):
                continue
        R = abs(entry - stop)
        if R <= 0:
            continue
        if stop_spec is not None:
            if stop_spec[0] == "pct":
                if not (stop_spec[1] <= R / entry <= stop_spec[2]):
                    continue
            elif stop_spec[0] == "pt":
                if not (stop_spec[1] * 0.1 <= R <= stop_spec[2] * 0.1):
                    continue

        open_pos[d] = {"dir": d, "entry": entry, "stop": stop, "R": R,
                       "sim_start": e + 1, "cross_time": t, "cross_dir": d}

        # ---- 逐 bar 模拟 ----
        pos = open_pos[d]
        if exit_mode == "tp":
            tp1 = entry + 1.5 * R * d
            tp2 = entry + 3.0 * R * d
            stop_cur = stop
            frac1 = 1 / 3.0
            realized = 0.0
            frac_open = 1.0
            exit_price = None
            status = "time"
            hold = 0
            exit_k = None
            for k in range(pos["sim_start"], min(pos["sim_start"] + time_exit_bars, n)):
                hold += 1
                hi, lo = sub_high[k], sub_low[k]
                # 止损（同 bar 保守：止损优先）
                if d == 1 and lo <= stop_cur:
                    xp = min(stop_cur, sub_open[k])
                    realized += (xp - entry) * d * frac_open
                    status = "stop"; exit_price = xp; exit_k = k; break
                if d == -1 and hi >= stop_cur:
                    xp = max(stop_cur, sub_open[k])
                    realized += (xp - entry) * d * frac_open
                    status = "stop"; exit_price = xp; exit_k = k; break
                # 第一批 +1.5R（1/3 落袋，止损移至保本）
                if d == 1 and hi >= tp1:
                    realized += (tp1 - entry) * d * frac1
                    frac_open -= frac1
                    stop_cur = entry
                    if hi >= tp2:
                        realized += (tp2 - entry) * d * frac_open
                        frac_open = 0.0
                        status = "tp2"; exit_price = tp2; exit_k = k; break
                elif d == -1 and lo <= tp1:
                    realized += (tp1 - entry) * d * frac1
                    frac_open -= frac1
                    stop_cur = entry
                    if lo <= tp2:
                        realized += (tp2 - entry) * d * frac_open
                        frac_open = 0.0
                        status = "tp2"; exit_price = tp2; exit_k = k; break
            else:
                kk = min(pos["sim_start"] + time_exit_bars, n) - 1
                exit_price = sub_close[kk]
                realized += (exit_price - entry) * d * frac_open
                status = "time"
                exit_k = kk
            pnl_price = realized
        elif exit_mode == "break":
            # X1 反向穿越全出（good/bad 反向即出）
            exit_price = None
            status = "time"
            hold = 0
            exit_k = None
            for k in range(pos["sim_start"], min(pos["sim_start"] + time_exit_bars, n)):
                hold += 1
                st = sub_state[k]
                hi, lo = sub_high[k], sub_low[k]
                if d == 1 and lo <= stop:
                    exit_price = min(stop, sub_open[k]); status = "stop"; exit_k = k; break
                if d == -1 and hi >= stop:
                    exit_price = max(stop, sub_open[k]); status = "stop"; exit_k = k; break
                if d == 1 and st in ("bad", "down") and sub_close[k] < entry:
                    exit_price = sub_close[k]; status = "break"; exit_k = k; break
                if d == -1 and st in ("good", "up") and sub_close[k] > entry:
                    exit_price = sub_close[k]; status = "break"; exit_k = k; break
            else:
                exit_price = sub_close[min(pos["sim_start"] + time_exit_bars, n) - 1]
                exit_k = min(pos["sim_start"] + time_exit_bars, n) - 1
            pnl_price = (exit_price - entry) * d
        elif exit_mode in ("trail", "hybrid"):
            # S3 高取低：4H 创新高（长）后，移动止损至最近 down 段 SMA13 低点
            stop_cur = stop
            frac1 = 1 / 3.0 if exit_mode == "hybrid" else 0.0
            tp1 = entry + 1.5 * R * d if exit_mode == "hybrid" else None
            pnl1 = 0.0
            tp1_hit = False
            exit_price = None
            status = "time"
            hold = 0
            exit_k = None
            for k in range(pos["sim_start"], min(pos["sim_start"] + time_exit_bars, n)):
                hold += 1
                hi, lo = sub_high[k], sub_low[k]
                if d == 1 and lo <= stop_cur:
                    exit_price = min(stop_cur, sub_open[k]); status = "stop"; exit_k = k; break
                if d == -1 and hi >= stop_cur:
                    exit_price = max(stop_cur, sub_open[k]); status = "stop"; exit_k = k; break
                # 高取低：新 down 段 SMA13 低点抬高止损（仅当盈利）
                if d == 1:
                    if not np.isnan(sub_stop_long[k]) and sub_stop_long[k] > stop_cur:
                        if sub_close[k] > entry:
                            stop_cur = max(entry, sub_stop_long[k])
                    if tp1 is not None and hi >= tp1:
                        pnl1 = (tp1 - entry) * d * frac1
                        stop_cur = max(stop_cur, entry)
                        tp1 = None
                        tp1_hit = True
                else:
                    if not np.isnan(sub_stop_short[k]) and sub_stop_short[k] < stop_cur:
                        if sub_close[k] < entry:
                            stop_cur = min(entry, sub_stop_short[k])
                    if tp1 is not None and lo <= tp1:
                        pnl1 = (tp1 - entry) * d * frac1
                        stop_cur = min(stop_cur, entry)
                        tp1 = None
                        tp1_hit = True
            else:
                exit_price = sub_close[min(pos["sim_start"] + time_exit_bars, n) - 1]
                exit_k = min(pos["sim_start"] + time_exit_bars, n) - 1
            pnl_price = pnl1 + (exit_price - entry) * d * (1 - frac1)
        else:
            raise ValueError(f"未知 exit_mode: {exit_mode}")

        cost = spread_price + swap_per_bar * hold
        pnl_net = pnl_price - cost
        trades.append({
            "symbol": symbol, "home_tf": home_tf, "sub_tf": sub_tf,
            "time": t, "dir": d, "entry": entry, "stop": stop, "R": R,
            "entry_time": sub_time[sim_start],
            "exit_time": sub_time[exit_k] if exit_k is not None else None,
            "exit_price": exit_price, "hold_bars": hold, "status": status,
            "tp1_hit": tp1_hit if exit_mode in ("trail", "hybrid") else False,
            "pnl_price": pnl_price, "cost": cost, "pnl_net": pnl_net,
            "pnl_R": pnl_net / R,
        })
        del open_pos[d]

    out = pd.DataFrame(trades)
    return out


def yearly_summary(trades: pd.DataFrame) -> pd.DataFrame:
    """年度统计（R 倍数口径）。"""
    if len(trades) == 0:
        return pd.DataFrame()
    df = trades.copy()
    df["year"] = pd.to_datetime(df["time"]).dt.year
    rows = []
    for y, g in df.groupby("year"):
        pos = g[g["pnl_R"] > 0]["pnl_R"]
        neg = g[g["pnl_R"] < 0]["pnl_R"]
        pf = float(pos.sum() / abs(neg.sum())) if len(neg) else float("inf")
        rows.append({
            "year": int(y), "n": len(g),
            "sum_R": round(float(g["pnl_R"].sum()), 3),
            "PF_R": round(pf, 2),
            "winrate": round(float((g["pnl_R"] > 0).mean()) * 100, 1),
        })
    return pd.DataFrame(rows)


def summary(trades: pd.DataFrame, label: str = "") -> dict:
    if len(trades) == 0:
        return {"label": label, "n": 0, "EV_R": 0.0, "PF_R": 0.0,
                "winrate": 0.0, "ann_pos": 0.0, "total_R": 0.0}
    ys = yearly_summary(trades)
    pos = trades[trades["pnl_R"] > 0]["pnl_R"]
    neg = trades[trades["pnl_R"] < 0]["pnl_R"]
    pf = float(pos.sum() / abs(neg.sum())) if len(neg) else float("inf")
    return {
        "label": label, "n": len(trades),
        "n_long": int((trades["dir"] == 1).sum()),
        "n_short": int((trades["dir"] == -1).sum()),
        "EV_R": round(float(trades["pnl_R"].mean()), 3),
        "PF_R": round(pf, 2),
        "winrate": round(float((trades["pnl_R"] > 0).mean()) * 100, 1),
        "total_R": round(float(trades["pnl_R"].sum()), 3),
        "ann_pos": round(float((ys["sum_R"] > 0).mean()) * 100, 1) if len(ys) else 0.0,
        "years": len(ys),
    }
