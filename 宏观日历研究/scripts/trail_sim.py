# -*- coding: utf-8 -*-
"""移动止损模拟：BiasReversal 多/空逐bar重放 + 4种trail规则 vs 基线。

规则:
  0 = 基线（固定SL + TP3R + 交叉离场）
  1 = 保本: 浮盈达1R时 SL移到入场价
  2 = 保本+锁盈: 1R保本, 2R时SL锁+1R
  3 = 50%峰值追踪: SL = entry - 0.5*(entry - min_low)（空）/ entry + 0.5*(max_high - entry)（多）
  4 = 2R后锁1R: 浮盈达2R时 SL移到+1R
"""
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*")]:
    if str(_p) not in _sys.path:
        _sys.path.insert(0, str(_p))

import numpy as np
import pandas as pd
import bias_reversal_replay as BR
from bias_reversal_replay import pipeline

ROOT = _Path(r"F:\use_code\MTA5_l")
OUT = ROOT / "宏观日历研究" / "报告" / "BiasReversal移动止损模拟.md"
bdir = ROOT / "黄金" / "乖离反转策略" / "data" / "raw" / "mt5_history" / "bias_reversal_live"


def sim_long(h6, h1, stop_pct=1.2, tp_r=3.0, trail=0):
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
    s5 = BR._smma(closes, 5)
    s13 = BR._smma(closes, 13)
    trades = []
    pos = None
    for i in range(1, n - 1):
        t = times[i]
        if pos is None:
            gold = s5[i] > s13[i] and s5[i - 1] <= s13[i - 1]
            if gold and BR._gate_state(h6, t):
                entry = opens[i + 1]
                stop = closes[i] * (1.0 - stop_pct / 100.0)
                pos = {"dir": 1, "entry": entry, "stop": stop, "tp": entry + (entry - stop) * tp_r,
                       "signal_time": times[i], "entry_i": i + 1, "peak": entry}
        else:
            # trail update first (using completed bars)
            if trail == 1 and (highs[i] - pos["entry"]) >= (pos["entry"] - pos["stop"]):
                pos["stop"] = pos["entry"]
            elif trail == 2:
                r1 = pos["entry"] - pos["stop"]
                if (highs[i] - pos["entry"]) >= 2 * r1:
                    pos["stop"] = pos["entry"] + r1
                elif (highs[i] - pos["entry"]) >= r1:
                    pos["stop"] = pos["entry"]
            elif trail == 3:
                pos["peak"] = max(pos["peak"], highs[i])
                pos["stop"] = max(pos["stop"], pos["entry"] + 0.5 * (pos["peak"] - pos["entry"]))
            elif trail == 4:
                r1 = pos["entry"] - pos["stop"]
                if (highs[i] - pos["entry"]) >= 2 * r1:
                    pos["stop"] = pos["entry"] + r1
            elif trail in (5, 6, 7):
                # 现价追踪（固定百分比距离）：5=1.2% 6=2.0% 7=3.0%
                tr_pct = {5: stop_pct, 6: 2.0, 7: 3.0}[trail]
                pos["stop"] = max(pos["stop"], closes[i] * (1.0 - tr_pct / 100.0))
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
                trades.append({"signal_time": pos["signal_time"], "dir": "L", "pnl": pnl * 100.0,
                               "reason": reason, "t": times[i]})
                pos = None
    if pos is not None:
        trades.append({"signal_time": pos["signal_time"], "dir": "L",
                       "pnl": (closes[n - 2] - pos["entry"]) * 100.0, "reason": "open", "t": times[n - 2]})
    return trades


def sim_short(h4, h2, trail=0, gate_thr=3.5, rise_thr=3.0, w_thr=0.5, stop_pct=1.2, tp_r=3.0):
    # 复用 replay_short 的信号判定与逐bar管理（注入 trail）
    h4 = h4.copy()
    close4 = pd.to_numeric(h4["close"], errors="coerce").to_numpy(dtype=float)
    s54 = pd.to_numeric(h4["SMA_5"], errors="coerce").to_numpy(dtype=float)
    s554 = pd.to_numeric(h4["SMA_55"], errors="coerce").to_numpy(dtype=float)
    h4["_bias55"] = np.where(s554 != 0, (close4 - s554) / s554 * 100.0, 0.0)
    h4["_bias5"] = np.where(s54 != 0, (close4 - s54) / s54 * 100.0, 0.0)
    h4["_gate"] = (close4 > s54) & (close4 > s554) & (h4["_bias55"] >= gate_thr)
    closes = h2["close"].to_numpy(dtype=float)
    opens = h2["open"].to_numpy(dtype=float)
    highs = h2["high"].to_numpy(dtype=float)
    lows = h2["low"].to_numpy(dtype=float)
    times = h2["bar_close_time"].to_numpy()
    n = len(h2)
    s5 = BR._smma(closes, 5)
    s13 = BR._smma(closes, 13)
    trades = []
    pos = None
    streak_loss = 0
    cd_until = None
    for i in range(1, n - 1):
        t = times[i]
        if pos is None:
            if cd_until is not None and pd.Timestamp(t) < cd_until:
                continue
            if BR._gate_state(h4, t):
                rr = BR._ea_short_setup(h2, i, s5, s13)
                if rr is not None and rr[3]:
                    entry = opens[i + 1]
                    stop = closes[i] * (1.0 + stop_pct / 100.0)
                    pos = {"dir": -1, "entry": entry, "stop": stop, "tp": entry - (stop - entry) * tp_r,
                           "signal_time": times[i], "entry_i": i + 1, "peak": entry}
        else:
            if trail == 1 and (pos["entry"] - lows[i]) >= (pos["stop"] - pos["entry"]):
                pos["stop"] = pos["entry"]
            elif trail == 2:
                r1 = pos["stop"] - pos["entry"]
                if (pos["entry"] - lows[i]) >= 2 * r1:
                    pos["stop"] = pos["entry"] - r1
                elif (pos["entry"] - lows[i]) >= r1:
                    pos["stop"] = pos["entry"]
            elif trail == 3:
                pos["peak"] = min(pos["peak"], lows[i])
                pos["stop"] = min(pos["stop"], pos["entry"] - 0.5 * (pos["entry"] - pos["peak"]))
            elif trail == 4:
                r1 = pos["stop"] - pos["entry"]
                if (pos["entry"] - lows[i]) >= 2 * r1:
                    pos["stop"] = pos["entry"] - r1
            elif trail in (5, 6, 7):
                # 现价追踪（固定百分比距离）：5=1.2% 6=2.0% 7=3.0%
                tr_pct = {5: stop_pct, 6: 2.0, 7: 3.0}[trail]
                pos["stop"] = min(pos["stop"], closes[i] * (1.0 + tr_pct / 100.0))
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
                trades.append({"signal_time": pos["signal_time"], "dir": "S", "pnl": pnl * 100.0,
                               "reason": reason, "t": times[i]})
                if reason == "SL hit":
                    streak_loss += 1
                    if streak_loss >= 2:
                        cd_until = pd.Timestamp(times[i]) + pd.Timedelta(hours=120)
                else:
                    streak_loss = 0
                pos = None
    if pos is not None:
        trades.append({"signal_time": pos["signal_time"], "dir": "S",
                       "pnl": (pos["entry"] - closes[n - 2]) * 100.0, "reason": "open", "t": times[n - 2]})
    return trades


def stats(trades):
    w = np.array([t["pnl"] for t in trades], dtype=float)
    if not len(w):
        return None
    eq = np.cumsum(w)
    dd = (np.maximum.accumulate(eq) - eq).max()
    wins, losses = w[w > 0].sum(), -w[w < 0].sum()
    return {"n": len(w), "wr": (w > 0).mean(), "total": w.sum(), "avg": w.mean(),
            "pf": wins / losses if losses > 0 else np.inf, "maxdd": dd}


def main():
    h4 = pipeline(bdir / "XAUUSDm_H4.csv", "4H")
    h6 = pipeline(bdir / "XAUUSDm_H6.csv", "6H")
    h2 = pipeline(bdir / "XAUUSDm_H2.csv", "2H")
    h1 = pipeline(bdir / "XAUUSDm_H1.csv", "1H")

    lines = ["# BiasReversal 移动止损模拟（逐bar重放，2018-2026）", ""]
    lines.append("| 规则 | 多空 | n | WR | 合计(pts) | PF | MaxDD | SL占比 | TP占比 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    rows_all = []
    for label, trail in [("基线(固定SL)", 0), ("保本@1R", 1), ("保本@1R+锁1R@2R", 2), ("50%峰值追踪", 3), ("2R后锁1R", 4), ("1.2%现价追踪", 5), ("2.0%现价追踪", 6), ("3.0%现价追踪", 7)]:
        lt = sim_long(h6, h1, trail=trail)
        st = sim_short(h4, h2, trail=trail)
        all_t = lt + st
        for tag, trs in [("多", lt), ("空", st), ("多+空", all_t)]:
            s = stats(trs)
            if s is None:
                continue
            rs = pd.Series([t["reason"] for t in trs]).value_counts()
            sl_r = rs.get("SL hit", 0) / len(trs)
            tp_r = rs.get("TP hit", 0) / len(trs)
            pf = "inf" if np.isinf(s["pf"]) else f"{s['pf']:.2f}"
            lines.append(f"| {label} | {tag} | {s['n']} | {s['wr']:.0%} | {s['total']:+,.0f} | {pf} | {s['maxdd']:,.0f} | {sl_r:.0%} | {tp_r:.0%} |")
            if tag == "多+空":
                rows_all.append((label, s))
    lines.append("")
    lines.append("## 多+空 汇总对比（相对基线）")
    base = rows_all[0][1]
    for label, s in rows_all:
        chg = (s["total"] / base["total"] - 1) * 100 if base["total"] else 0
        lines.append(f"- {label}: 合计 {s['total']:+,.0f}（{chg:+.0f}%） PF {s['pf']:.2f} MaxDD {s['maxdd']:,.0f}")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
