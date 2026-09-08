# -*- coding: utf-8 -*-
"""
stage4_causal.py —— MCT 因果化 expected ledger 生成器（对齐契约 v3 · 单一真源）

与 MCT_EA 完全同源（轮次3 收敛方案）：
  1. D1：SMMA13/55 穿越（closed bar），glue<=0.3%
  2. 武装窗口（因果）：穿越 D1 bar 时间 T → 武装 [T+24h, T+40d]
     （D1 bar 收盘次日 00:00 才可知，与 EA CheckD1AndArm 一致）
  3. H4：SMMA5/13 状态机 + 增量 v4 链式吸收（min_len=8，末穿越点=待定）
  4. 入场：bar p 的待定穿越点 = 增量链 cands[-1]（bar_time==t4[p-1]，与 EA 一致）
     → 入场价 = open4[p]；bias55 在穿越点判定；StopSpec 0.8%~2.5%
  5. 止损/移动：增量链 cands[-1] 的前段 merged run SMMA13 极值（与 EA 同算法）
  6. hybrid 退出：+1.5R 出 1/3（保本）→ 待定穿越点高取低移动 → 止损/120bar 超时
  7. 重叠：同方向 1 持仓；成本=0（对齐运行）
输出：data/validation/expected_ledger_mct_oil.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "阶段1_机会层统计" / "scripts"))
import stage1_common as C

PROC = Path(__file__).resolve().parent.parent / "data" / "validation"
PROC.mkdir(parents=True, exist_ok=True)

MIN_LEN = 8
GLUE = 0.003
ARM_DAYS = 40
ARM_KNOW_DELAY_H = 24          # D1 bar 收盘延迟
TIME_EXIT = 120
FRAC1 = 1 / 3.0
TP1_R = 1.5
SPEC = (0.008, 0.025)
SYMBOL = "USOILm"
EFF = "2021-07-01"
BALANCE0 = 500.0
LOT = 0.01
CONTRACT = 1000


def fmt(t):
    return pd.Timestamp(t).strftime("%Y-%m-%d %H:%M:%S")


def main():
    d1 = C.analyze_tf(SYMBOL, "D1")
    h4 = C.analyze_tf(SYMBOL, "H4").reset_index(drop=True)
    n = len(h4)

    cr = C.find_cross13_55(d1)
    cr = cr[pd.to_datetime(cr["time"]) >= EFF].reset_index(drop=True)
    cr = cr[np.abs(cr["sma13"] - cr["sma55"]) / cr["sma55"] <= GLUE].reset_index(drop=True)
    print(f"D1 穿越(glue<=0.3%): {len(cr)} 次")

    t4 = pd.to_datetime(h4["time"].values)
    sma5 = h4["SMA_5"].values
    sma13 = h4["SMA_13"].values
    sma55 = h4["SMA_55"].values
    close4 = h4["close"].values
    open4 = h4["open"].values
    high4 = h4["high"].values
    low4 = h4["low"].values

    # ---- 因果武装窗口 [T+24h, T+40d]（与 EA CheckD1AndArm 一致）----
    armed = {1: np.zeros(n, dtype=bool), -1: np.zeros(n, dtype=bool)}
    signal_t = {1: np.empty(n, dtype=object), -1: np.empty(n, dtype=object)}
    for tc, d in zip(pd.to_datetime(cr["time"].values), cr["dir"].values):
        t_know = tc + pd.Timedelta(hours=ARM_KNOW_DELAY_H)
        t_end = t_know + pd.Timedelta(days=ARM_DAYS)
        w = (t4 >= t_know) & (t4 <= t_end)
        armed[d][w] = True
        signal_t[d][w] = tc

    # ---- 单遍增量循环（链与模拟同步推进，与 EA 完全一致）----
    cands_idx = np.zeros(n, dtype=int)
    cands_type = np.zeros(n, dtype=int)
    cands_time = np.empty(n, dtype=object)
    cands_stop = np.zeros(n)
    cands_n = 0
    raw_code = np.zeros(n, dtype=int)
    prev_above = None

    open_pos = {}
    trades = []
    bal = BALANCE0

    def close_trade(pos, reason, exit_price, exit_time):
        nonlocal bal
        pnl_price = pos["realized"]
        pnl_usd = pnl_price * CONTRACT * LOT
        bal += pnl_usd
        trades.append({
            "signal_time": fmt(pos["signal_time"]),
            "entry_time": fmt(pos["entry_time"]),
            "dir": "BUY" if pos["dir"] == 1 else "SELL",
            "entry": round(pos["entry"], 5),
            "stop": round(pos["init_stop"], 5),
            "exit_time": fmt(exit_time),
            "exit_price": round(exit_price, 5),
            "reason": reason,
            "pnl_points": round(pnl_price, 5),
            "pnl_usd": round(pnl_usd, 5),
            "virtual_balance": round(bal, 5),
        })

    for p in range(n):
        e = p - 1
        # 1) 处理已收盘 bar e 的 raw 状态码 + 链吸收（与 EA UpdateH4State 处理 closed bar 一致）
        if e >= 0:
            if np.isnan(sma5[e]) or np.isnan(sma13[e]):
                raw_code[e] = 0
            else:
                above = sma5[e] > sma13[e]
                if prev_above is None:
                    raw_code[e] = 1 if above else -1
                elif above and not prev_above:
                    raw_code[e] = 2
                elif not above and prev_above:
                    raw_code[e] = -2
                else:
                    raw_code[e] = 1 if above else -1
                prev_above = above
                if abs(raw_code[e]) == 2:
                    cands_idx[cands_n] = e
                    cands_type[cands_n] = raw_code[e]
                    cands_time[cands_n] = t4[e]
                    cands_n += 1
                    while cands_n >= 2:
                        a = cands_idx[cands_n - 2]
                        b = cands_idx[cands_n - 1]
                        region = raw_code[a + 1:b]
                        rc = int(np.sum(region == (1 if cands_type[cands_n - 2] == 2 else -1)))
                        if rc < MIN_LEN:
                            cands_n -= 2
                        else:
                            break
                    s0 = (cands_idx[cands_n - 2] + 1) if cands_n >= 2 else 0
                    if cands_type[cands_n - 1] == 2:
                        v = np.min(sma13[s0:e])
                    else:
                        v = np.max(sma13[s0:e])
                    cands_stop[cands_n - 1] = v

        # 2) 开新仓：待定穿越点 = 链末（在上一收盘 bar e），与 EA TryOpen 一致
        pending_at_last = (cands_n > 0 and e >= 0 and cands_time[cands_n - 1] == t4[e])
        if pending_at_last:
            last_type = cands_type[cands_n - 1]
            d = 1 if last_type == 2 else -1
            if d not in open_pos and armed[d][p]:
                stop = cands_stop[cands_n - 1]
                if stop > 0.0 and not np.isnan(sma55[e]):
                    ok_bias = (d == 1 and close4[e] > sma55[e]) or (d == -1 and close4[e] < sma55[e])
                    if ok_bias:
                        entry = open4[p]
                        R = abs(entry - stop)
                        if R > 0 and SPEC[0] <= R / entry <= SPEC[1]:
                            open_pos[d] = {"dir": d, "entry": entry, "stop": stop,
                                           "init_stop": stop, "R": R,
                                           "entry_time": t4[p], "signal_time": signal_t[d][p],
                                           "tp1": None, "fo": 1.0, "realized": 0.0, "hold": 0}

        # 3) 持仓结算（bar p 的 OHLC，与 EA 逐 bar 结算一致）
        for d in list(open_pos.keys()):
            pos = open_pos[d]
            pos["hold"] += 1
            if pos["hold"] >= TIME_EXIT:
                xp = close4[p]
                pos["realized"] += (xp - pos["entry"]) * d * pos["fo"]
                close_trade(pos, "time exit", xp, t4[p])
                del open_pos[d]
                continue
            hi, lo = high4[p], low4[p]
            sc = pos["stop"]
            # 高取低：待定穿越点（与 EA ManagePositions 一致）
            if pending_at_last:
                tv = cands_stop[cands_n - 1]
                if d == 1 and cands_type[cands_n - 1] == 2 and tv > sc and close4[p] > pos["entry"]:
                    pos["stop"] = max(pos["entry"], tv)
                if d == -1 and cands_type[cands_n - 1] == -2 and tv < sc and close4[p] < pos["entry"]:
                    pos["stop"] = min(pos["entry"], tv)
                sc = pos["stop"]
            if d == 1 and lo <= sc:
                xp = min(sc, open4[p])
                pos["realized"] += (xp - pos["entry"]) * d * pos["fo"]
                close_trade(pos, "TP1+SL" if pos["tp1"] is not None else "SL hit", xp, t4[p])
                del open_pos[d]
                continue
            if d == -1 and hi >= sc:
                xp = max(sc, open4[p])
                pos["realized"] += (xp - pos["entry"]) * d * pos["fo"]
                close_trade(pos, "TP1+SL" if pos["tp1"] is not None else "SL hit", xp, t4[p])
                del open_pos[d]
                continue
            if pos["tp1"] is None:
                tp1 = pos["entry"] + TP1_R * pos["R"] * d
                if (d == 1 and hi >= tp1) or (d == -1 and lo <= tp1):
                    pos["realized"] += (tp1 - pos["entry"]) * d * FRAC1
                    pos["fo"] -= FRAC1
                    pos["stop"] = pos["entry"]
                    pos["tp1"] = tp1

    for d in list(open_pos.keys()):
        pos = open_pos[d]
        xp = close4[n - 1]
        pos["realized"] += (xp - pos["entry"]) * d * pos["fo"]
        close_trade(pos, "end of data", xp, t4[n - 1])

    tdf = pd.DataFrame(trades)
    if len(tdf):
        tdf.to_csv(PROC / "expected_ledger_mct_oil.csv", index=False, encoding="utf-8-sig")
    print(f"总交易: {len(tdf)} (L={int((tdf['dir']=='BUY').sum()) if len(tdf) else 0}/"
          f"S={int((tdf['dir']=='SELL').sum()) if len(tdf) else 0})")
    if len(tdf):
        print(f"总 pnl_points: {tdf['pnl_points'].sum():.3f}  终值余额: {bal:.2f}")
        print(tdf[["entry_time", "dir", "entry", "stop", "exit_time", "exit_price", "reason", "pnl_points"]].to_string(index=False))


if __name__ == "__main__":
    main()
