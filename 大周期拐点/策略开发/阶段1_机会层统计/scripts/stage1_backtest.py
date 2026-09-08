# -*- coding: utf-8 -*-
"""
stage1_backtest.py —— 阶段1 共享回测引擎（G1/G3/档位验证）

逻辑（对齐策略计划 7.4/7.5/7.6 简化版）：
  机会：本级别 SMA13x55 穿越（crossings）
  入场：穿越后 lookback_days 内，次级别出现同向 5x13 穿越（good/bad）
        + bias55_signed 同向 → fixed_delay_1（下一根次级别 open）
  止损：本级别 prev_seg SMA13 极值（结构止损）
  StopSpec：比例档（原油 0.8%~2.5%）或点数档（黄金 30~80pt）
  退出（exit_mode）：
    "1.5R_3R"：1/3 在 +1.5R 出（保本），2/3 在 +3R 或止损出；time_exit_bars 超时出
    "fixedH"：持有 H 根次级别 bar 后平仓（无止损，纯边际）
  成本：roundtrip 点差（价格单位）+ 每 bar 隔夜费（价格单位）
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def backtest(crossings: pd.DataFrame, home_df: pd.DataFrame, sub_df: pd.DataFrame,
             symbol: str, home_tf: str, sub_tf: str,
             lookback_days: float = 40.0,
             stop_mode: str = "home_struct",      # home_struct=D1结构止损 / sub_struct=次级别结构止损
             stop_spec=None,                       # None=不过滤 / ("pct", lo, hi) / ("pt", lo, hi)
             exit_mode: str = "1.5R_3R",
             time_exit_bars: int = 120,
             spread_price: float = 0.0,
             swap_per_bar: float = 0.0,
             bias_floor: float = 0.0,
             require_bias: bool = True,
             direct_entry: bool = False,           # True=穿越点下一根 home bar 直接入场(不等到次级别穿越)
             label: str = "") -> pd.DataFrame:
    """返回逐笔交易 DataFrame：time/entry/exit/dir/R/hold_bars/pnl_price(未扣费)/pnl_net/status"""
    trades = []
    n_sub = len(sub_df)
    sub_time = sub_df["time"].values
    sub_open = sub_df["open"].values
    sub_high = sub_df["high"].values
    sub_low = sub_df["low"].values
    sub_close = sub_df["close"].values
    sub_state = sub_df["方向_合并后"].values
    sub_bias = np.where(
        np.isnan(sub_df["SMA_55"].values) | (sub_df["SMA_55"].values == 0),
        np.nan,
        (sub_close - sub_df["SMA_55"].values) / sub_df["SMA_55"].values * 100.0)

    home_state = home_df["方向_合并后"].values
    good_pos = np.where(home_state == "good")[0]
    bad_pos = np.where(home_state == "bad")[0]
    home_stop_long = home_df["prev_seg_low_sma13"].values
    home_stop_short = home_df["prev_seg_high_sma13"].values

    sub_stop_long = sub_df["prev_seg_low_sma13"].values
    sub_stop_short = sub_df["prev_seg_high_sma13"].values

    def _struct_stop(i, d):
        """本级别结构止损：向前回溯最近一个 5x13 段边界(good/bad)的 prev_seg SMA13 极值。"""
        if d == 1:
            j = good_pos[good_pos <= i]
        else:
            j = bad_pos[bad_pos <= i]
        if len(j) == 0:
            return np.nan
        last = j[-1]
        return home_stop_long[last] if d == 1 else home_stop_short[last]

    for _, row in crossings.iterrows():
        d = int(row["dir"])
        i = int(row["idx"])
        t = row["time"]
        stop = _struct_stop(i, d)
        if np.isnan(stop):
            continue

        # 次级别窗口（穿越后 lookback_days 内）
        t_end = t + pd.Timedelta(days=lookback_days)
        mask = (pd.to_datetime(sub_time) > t) & (pd.to_datetime(sub_time) <= t_end)
        pos = np.where(mask)[0]

        if direct_entry:
            # 直接入场：穿越点下一根 home bar open（fixed_delay_1）
            home_after = np.where(pd.to_datetime(home_df["time"].values) > t)[0]
            if len(home_after) == 0:
                continue
            h0 = home_after[0]
            entry = home_df["open"].iloc[h0]
            e = None
        else:
            if len(pos) == 0:
                continue
            e = None
            for p in pos:
                st = sub_state[p]
                if d == 1 and st == "good":
                    if (not require_bias) or (not np.isnan(sub_bias[p]) and sub_bias[p] > bias_floor):
                        e = p
                        break
                elif d == -1 and st == "bad":
                    if (not require_bias) or (not np.isnan(sub_bias[p]) and sub_bias[p] < -bias_floor):
                        e = p
                        break
            if e is None:
                continue
            if e + 1 >= n_sub:
                continue
            entry = sub_open[e + 1]            # fixed_delay_1
        if np.isnan(entry):
            continue

        # 止损口径
        if stop_mode == "sub_struct" and e is not None:
            if d == 1:
                stop = sub_stop_long[e]
            else:
                stop = sub_stop_short[e]
            if np.isnan(stop):
                continue
        R = abs(entry - stop)
        # StopSpec
        if stop_spec is not None:
            if stop_spec[0] == "pct":
                lo, hi = stop_spec[1], stop_spec[2]
                if not (lo <= R / entry <= hi):
                    continue
            elif stop_spec[0] == "pt":
                lo, hi = stop_spec[1], stop_spec[2]     # 1pt = 0.1 价格
                if not (lo * 0.1 <= R <= hi * 0.1):
                    continue

        # ---- 模拟（从入场 bar sim_start 起）----
        if direct_entry:
            sim_start = h0          # 直接入场：穿越点下一根 home bar
        else:
            sim_start = e + 1       # 次级别入场：signal bar 下一根 open
        if exit_mode == "fixedH":
            # 持有 time_exit_bars 根后按 close 平仓
            hold = min(time_exit_bars, n_sub - sim_start)
            if hold <= 0:
                continue
            exit_price = sub_close[sim_start + hold - 1]
            pnl_price = (exit_price - entry) * d
            status = "fixedH"
            hold_bars = hold
        else:  # "1.5R_3R"
            tp1 = entry + 1.5 * R * d
            tp2 = entry + 3.0 * R * d
            frac1 = 1 / 3.0
            stop_cur = stop
            exit_price = None
            status = "time"
            hold_bars = 0
            pnl_1 = pnl_2 = 0.0
            for k in range(sim_start, min(sim_start + time_exit_bars, n_sub)):
                hold_bars += 1
                hi = sub_high[k]
                lo = sub_low[k]
                # 保守：同 bar 内先止损后止盈
                if d == 1 and lo <= stop_cur:
                    exit_price = min(stop_cur, sub_open[k])
                    pnl_1 = (exit_price - entry) * d * frac1
                    pnl_2 = 0.0
                    status = "stop"
                    break
                if d == -1 and hi >= stop_cur:
                    exit_price = max(stop_cur, sub_open[k])
                    pnl_1 = (exit_price - entry) * d * frac1
                    pnl_2 = 0.0
                    status = "stop"
                    break
                # 第一批 +1.5R（1/3 落袋，止损移至保本）
                if d == 1 and hi >= tp1:
                    pnl_1 = (tp1 - entry) * d * frac1
                    stop_cur = entry
                    # 第二批 +3R
                    if hi >= tp2:
                        pnl_2 = (tp2 - entry) * d * (1 - frac1)
                        exit_price = tp2
                        status = "tp2"
                        break
                elif d == -1 and lo <= tp1:
                    pnl_1 = (tp1 - entry) * d * frac1
                    stop_cur = entry
                    if lo <= tp2:
                        pnl_2 = (tp2 - entry) * d * (1 - frac1)
                        exit_price = tp2
                        status = "tp2"
                        break
            else:
                # 超时平仓
                exit_price = sub_close[min(e + 1 + time_exit_bars, n_sub) - 1]
                if exit_price is None:
                    continue
                # 按当前仓位结算（若第一批已出）
                frac_left = (1 - frac1) if pnl_1 != 0.0 or stop_cur == entry else 1.0
                pnl_2 = (exit_price - entry) * d * frac_left
                status = "time"
            pnl_price = pnl_1 + pnl_2

        cost = spread_price + swap_per_bar * hold_bars
        pnl_net = pnl_price - cost
        trades.append({
            "symbol": symbol, "home_tf": home_tf, "sub_tf": sub_tf,
            "time": t, "dir": d, "entry": entry, "stop": stop,
            "R": R, "exit_price": exit_price if exit_price is not None else np.nan,
            "hold_bars": hold_bars, "status": status,
            "pnl_price": pnl_price, "cost": cost, "pnl_net": pnl_net,
        })
    return pd.DataFrame(trades)


def summarize(trades: pd.DataFrame, label: str = "") -> dict:
    if len(trades) == 0:
        return {"label": label, "n": 0, "n_long": 0, "n_short": 0,
                "EV_price": 0.0, "EV_R": 0.0, "PF": 0.0, "PF_R": 0.0,
                "winrate": 0.0, "avg_hold_bars": 0.0,
                "total_pnl_price": 0.0, "status": {}}
    pos = trades[trades["pnl_net"] > 0]["pnl_net"]
    neg = trades[trades["pnl_net"] < 0]["pnl_net"]
    pf = float(pos.sum() / abs(neg.sum())) if len(neg) else float("inf")
    r_mult = trades["pnl_net"] / trades["R"].replace(0, np.nan)
    r_pos = r_mult[r_mult > 0]
    r_neg = r_mult[r_mult < 0]
    pf_r = float(r_pos.sum() / abs(r_neg.sum())) if len(r_neg) else float("inf")
    s = {
        "label": label, "n": len(trades),
        "n_long": int((trades["dir"] == 1).sum()),
        "n_short": int((trades["dir"] == -1).sum()),
        "EV_price": round(float(trades["pnl_net"].mean()), 4),
        "EV_R": round(float(r_mult.mean()), 3),
        "PF": round(pf, 2),
        "PF_R": round(pf_r, 2),
        "winrate": round(float((trades["pnl_net"] > 0).mean()) * 100, 1),
        "avg_hold_bars": round(float(trades["hold_bars"].mean()), 1),
        "total_pnl_price": round(float(trades["pnl_net"].sum()), 4),
        "status": dict(trades["status"].value_counts()),
    }
    return s
