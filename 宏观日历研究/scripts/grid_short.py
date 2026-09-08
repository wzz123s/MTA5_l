# -*- coding: utf-8 -*-
"""做空侧最优配置网格搜索：H4门门槛 × 2H涨幅门槛 × 结构强度 + 半仓选项。

评估：做空侧单独 + 多空组合（多侧固定），年度分解防过拟合。
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
OUT = ROOT / "宏观日历研究" / "报告" / "BiasReversal做空侧网格搜索.md"
bdir = ROOT / "黄金" / "乖离反转策略" / "data" / "raw" / "mt5_history" / "bias_reversal_live"


def sim_short(h4, h2, gate_thr=3.5, rise_thr=0.0, w_thr=0.0, stop_pct=1.2, tp_r=3.0, half=False):
    """带冷却的做空重放，rise/wsw 门槛接线（r[0]>=rise_thr, r[1]>=w_thr）。"""
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
                if rr is not None and rr[3] and rr[0] >= rise_thr and rr[1] >= w_thr:
                    entry = opens[i + 1]
                    stop = closes[i] * (1.0 + stop_pct / 100.0)
                    pos = {"dir": "S", "entry": entry, "stop": stop,
                           "tp": entry - (stop - entry) * tp_r,
                           "signal_time": times[i], "entry_i": i + 1}
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
                pnl = (pos["entry"] - exit_px) * 100.0
                if half:
                    pnl *= 0.5
                trades.append({"signal_time": pos["signal_time"], "dir": "S", "pnl": pnl,
                               "reason": reason, "year": pd.Timestamp(times[i]).year})
                if reason == "SL hit":
                    streak_loss += 1
                    if streak_loss >= 2:
                        cd_until = pd.Timestamp(times[i]) + pd.Timedelta(hours=120)
                else:
                    streak_loss = 0
                pos = None
    if pos is not None:
        pnl = (pos["entry"] - closes[n - 2]) * 100.0
        if half:
            pnl *= 0.5
        trades.append({"signal_time": pos["signal_time"], "dir": "S", "pnl": pnl,
                       "reason": "open", "year": pd.Timestamp(times[n - 2]).year})
    return trades


def stats(trades):
    w = np.array([t["pnl"] for t in trades], dtype=float)
    if not len(w):
        return None
    eq = np.cumsum(w)
    dd = (np.maximum.accumulate(eq) - eq).max()
    wins, losses = w[w > 0].sum(), -w[w < 0].sum()
    return {"n": len(w), "wr": (w > 0).mean(), "total": w.sum(), "pf": wins / losses if losses > 0 else np.inf, "maxdd": dd}


def main():
    h4 = pipeline(bdir / "XAUUSDm_H4.csv", "4H")
    h6 = pipeline(bdir / "XAUUSDm_H6.csv", "6H")
    h2 = pipeline(bdir / "XAUUSDm_H2.csv", "2H")
    h1 = pipeline(bdir / "XAUUSDm_H1.csv", "1H")
    # 做多侧（固定，与部署一致：无冷却）
    longs = BR.replay_long(h6, h1)
    long_w = pd.to_numeric(longs["stage_pnl"], errors="coerce").to_numpy(dtype=float) * 100.0
    long_years = pd.to_datetime(longs["signal_time"]).dt.year.to_numpy()

    lines = ["# BiasReversal 做空侧配置网格搜索（2026-08-28）", ""]
    lines.append("> 做多侧固定（265 笔 +213,456 / PF 2.37 / MaxDD 18,987）。做空侧扫描 H4门门槛×2H涨幅×结构强度+半仓。")
    lines.append("> 注意：replay_short 原实现未接线 rise_thr/w_thr（只用 ok 标志），本测试补上接线评估加严效果。\n")

    def comb(short_trades):
        w = np.array([t["pnl"] for t in short_trades], dtype=float)
        all_w = np.concatenate([long_w, w])
        return stats(short_trades), stats([{"pnl": v} for v in all_w])

    # 单维扫描
    lines.append("## 做空侧单独（H4门门槛扫描）")
    lines.append("| 配置 | n | WR | 合计 | PF | MaxDD | 年度 |")
    lines.append("|---|---|---|---|---|---|---|")
    for gt in [3.5, 4.0, 4.5, 5.0, 5.5]:
        st = sim_short(h4, h2, gate_thr=gt)
        s = stats(st)
        ys = {}
        for t in st:
            ys[t["year"]] = ys.get(t["year"], 0.0) + t["pnl"]
        pf = "inf" if np.isinf(s["pf"]) else f"{s['pf']:.2f}"
        ystr = " ".join(f"{k}:{v:+,.0f}" for k, v in sorted(ys.items()))
        lines.append(f"| gate={gt}% | {s['n']} | {s['wr']:.0%} | {s['total']:+,.0f} | {pf} | {s['maxdd']:,.0f} | {ystr} |")

    lines.append("")
    lines.append("## 多+空组合（各配置下总收益/PF/MaxDD，含半仓与仅做多对照）")
    lines.append("| 配置 | 空n | 组合合计 | 组合PF | 组合MaxDD | vs仅做多 |")
    lines.append("|---|---|---|---|---|---|")
    configs = [
        ("现状 gate3.5 (全开)", dict(gate_thr=3.5)),
        ("仅做多(全停,已部署)", None),
        ("gate=4.0", dict(gate_thr=4.0)),
        ("gate=4.5", dict(gate_thr=4.5)),
        ("gate=5.0", dict(gate_thr=5.0)),
        ("gate=5.5", dict(gate_thr=5.5)),
        ("gate=4.0 + rise>=4", dict(gate_thr=4.0, rise_thr=4.0)),
        ("gate=4.0 + rise>=5", dict(gate_thr=4.0, rise_thr=5.0)),
        ("gate=4.5 + rise>=5", dict(gate_thr=4.5, rise_thr=5.0)),
        ("gate=4.0 + w>=0.8", dict(gate_thr=4.0, w_thr=0.8)),
        ("gate=5.0 + rise>=4", dict(gate_thr=5.0, rise_thr=4.0)),
        ("gate=4.5 半仓", dict(gate_thr=4.5, half=True)),
        ("gate=5.0 半仓", dict(gate_thr=5.0, half=True)),
        ("gate=4.0+rise>=4 半仓", dict(gate_thr=4.0, rise_thr=4.0, half=True)),
    ]
    base = stats([{"pnl": v} for v in long_w])
    for label, kw in configs:
        if kw is None:
            s = base
            pf = "inf" if np.isinf(s["pf"]) else f"{s['pf']:.2f}"
            lines.append(f"| {label} | 0 | {s['total']:+,.0f} | {pf} | {s['maxdd']:,.0f} | — |")
            continue
        st = sim_short(h4, h2, **kw)
        ss, cs = comb(st)
        if ss is None:
            pf = "inf" if np.isinf(cs["pf"]) else f"{cs['pf']:.2f}"
            chg = (cs["total"] / base["total"] - 1) * 100
            lines.append(f"| {label} | 0 | {cs['total']:+,.0f} | {pf} | {cs['maxdd']:,.0f} | {chg:+.1f}% |")
            continue
        pf = "inf" if np.isinf(cs["pf"]) else f"{cs['pf']:.2f}"
        chg = (cs["total"] / base["total"] - 1) * 100
        lines.append(f"| {label} | {ss['n']} | {cs['total']:+,.0f} | {pf} | {cs['maxdd']:,.0f} | {chg:+.1f}% |")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
