# -*- coding: utf-8 -*-
"""原油基线（精确对齐 MTA5_l 原油4H门策略）：
4H 门（C1 持续根数|way|>=8 + C2 极值bar way_s_way/vol_way_s_way>=0.5 + C3 SMMA13极值幅度 0.5-5%）
→ 2H cross/pre_cross 触发（不含 post_n）→ 2H 结构止损 0.1-1.0% → 单段退出（2H 反向穿越，止损优先）。
"""
from __future__ import annotations
import sys
from pathlib import Path
import bisect
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[2]

N_MIN = 8
THR = 0.5
AMP_LO, AMP_HI = 0.5, 5.0
STOP_LO, STOP_HI = 0.001, 0.01  # 0.1%-1.0%
COST_PT = 0.05  # 每笔往返成本（USOILm 真实口径，参考 validation_report）


def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["time"])
    df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def gate_arrays(tf: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Per-bar: dir_sign, seg_len(|way|), ext wsw/vwsw, amplitude"""
    direction = tf["方向"].values
    way = pd.to_numeric(tf["way"], errors="coerce").to_numpy()
    wsw = pd.to_numeric(tf["way_s_way"], errors="coerce").to_numpy()
    vwsw = pd.to_numeric(tf["vol_way_s_way"], errors="coerce").to_numpy()
    low = tf["low"].to_numpy(); high = tf["high"].to_numpy()
    sma13 = tf["SMA_13"].to_numpy(); close = tf["close"].to_numpy()
    n = len(tf)
    cross_idx = [i for i in range(n) if direction[i] in ("good", "bad")]
    dir_sign = np.zeros(n, dtype=int)
    seg_len = np.zeros(n, dtype=int)
    ext_wsw = np.full(n, np.nan); ext_vwsw = np.full(n, np.nan)
    amp = np.full(n, np.nan)
    run_ext_idx = -1; cur_sign = 0
    for i in range(n):
        d = direction[i]
        sign = 1 if d in ("good", "up") else (-1 if d in ("bad", "down") else 0)
        if sign != cur_sign:
            cur_sign = sign; run_ext_idx = i
        else:
            if cur_sign == 1 and high[i] > high[run_ext_idx]:
                run_ext_idx = i
            elif cur_sign == -1 and low[i] < low[run_ext_idx]:
                run_ext_idx = i
        dir_sign[i] = cur_sign
        seg_len[i] = int(abs(way[i])) if np.isfinite(way[i]) else 0
        if run_ext_idx >= 0:
            ext_wsw[i] = wsw[run_ext_idx]
            ext_vwsw[i] = vwsw[run_ext_idx]
        ci = bisect.bisect_right(cross_idx, i) - 1
        if ci >= 1 and cur_sign != 0:
            c1 = cross_idx[ci]; c0 = cross_idx[ci - 1]
            cur_seg = sma13[c1:i + 1]; prev_seg = sma13[c0:c1]
            cur_seg = cur_seg[np.isfinite(cur_seg)]; prev_seg = prev_seg[np.isfinite(prev_seg)]
            if len(cur_seg) and len(prev_seg) and np.isfinite(close[i]) and close[i] != 0:
                if cur_sign == -1:
                    cur_ext = cur_seg.min(); prev_ext = prev_seg.max()
                else:
                    cur_ext = cur_seg.max(); prev_ext = prev_seg.min()
                amp[i] = abs(cur_ext - prev_ext) / close[i] * 100.0
    return dir_sign, seg_len, ext_wsw, ext_vwsw, amp


VARIANT = "base"
V1_HOURS = 4.0
WIDEN = 2.5
WIDEN_HOURS = 4.0
CAT_FILTER = ""
ET = np.array([])


def load_blackout_events() -> np.ndarray:
    ev = pd.read_csv(ROOT / "data" / "processed" / "calendar_events.csv", parse_dates=["event_time_utc"])
    ev = ev[ev["is_blackout_event"] == True]  # noqa: E712
    if CAT_FILTER:
        ev = ev[ev["category"] == CAT_FILTER]
    return pd.to_datetime(ev["event_time_utc"], utc=True).to_numpy().astype("datetime64[ns]")


def main() -> None:
    global VARIANT, V1_HOURS, WIDEN, ET
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="base", choices=["base", "v1", "v5"])
    ap.add_argument("--hours", type=float, default=4.0)
    ap.add_argument("--widen", type=float, default=2.5)
    ap.add_argument("--widen-hours", type=float, default=4.0)
    ap.add_argument("--cat", default="")
    args = ap.parse_args()
    VARIANT, V1_HOURS, WIDEN, WIDEN_HOURS, CAT_FILTER = args.variant, args.hours, args.widen, args.widen_hours, args.cat
    ET = load_blackout_events() if VARIANT in ("v1", "v5") else np.array([])
    h2 = load(ROOT / "data" / "processed" / "oil_context_h2.csv")
    h4 = load(ROOT / "data" / "raw" / "mt5_history" / "oil_mt5_20190101" / "USOILm_H4.csv")
    for n in ("5", "13", "55"):
        h4[f"SMA_{n}"] = None  # placeholder, will compute below
    # 计算 H4 的完整指标（SMMA + 方向 + way + 极值）
    sys.path.insert(0, str(ROOT / "scripts" / "prepare"))
    from prepare_indicators import calc_sma, mark_direction, track_extremes, add_bias, way_grade
    for n in ("5", "13", "55", "144", "233"):
        h4[f"SMA_{n}"] = calc_sma(h4["close"], int(n))
    h4 = mark_direction(h4)
    h4 = track_extremes(h4)
    h4 = add_bias(h4)
    h4 = way_grade(h4)
    # H4 门数组（每个 H2 bar 用 merge_asof 取最近 H4 门值）
    d4, sl4, w4, v4, amp4 = gate_arrays(h4)
    h4["dir_sign"] = d4; h4["seg_len"] = sl4; h4["ext_wsw"] = w4
    h4["ext_vwsw"] = v4; h4["amp"] = amp4
    gate_cols = ["time", "dir_sign", "seg_len", "ext_wsw", "ext_vwsw", "amp"]
    h4g = h4[gate_cols].rename(columns={c: f"H4_{c}" for c in gate_cols if c != "time"})
    h2m = pd.merge_asof(h2.sort_values("time"), h4g.sort_values("time"), on="time", direction="backward")
    # pre_cross：close 穿越 SMA13 而 5SMA 尚未穿越（gap<=0.300%），与 MTA5_l 2H 触发口径一致
    gap_pct = (h2m["SMA_5"] - h2m["SMA_13"]).abs() / h2m["SMA_13"] * 100
    prev_close = h2m["close"].shift(1)
    h2m["pre_cross_l"] = (prev_close <= h2m["SMA_13"].shift(1)) & (h2m["close"] > h2m["SMA_13"]) & (h2m["SMA_5"] < h2m["SMA_13"]) & (gap_pct <= 0.300)
    h2m["pre_cross_s"] = (prev_close >= h2m["SMA_13"].shift(1)) & (h2m["close"] < h2m["SMA_13"]) & (h2m["SMA_5"] > h2m["SMA_13"]) & (gap_pct <= 0.300)
    # pre_cross 行向前填充最近 good/bad 的 prev_seg 极值作为止损
    h2m["long_stop_f"] = h2m["long_stop"].ffill()
    h2m["short_stop_f"] = h2m["short_stop"].ffill()
    # 触发信号：2H good/bad（cross）或 pre_cross（pre_cross 不重复 good/bad 行），门成立才开
    trades = []
    i = 0
    n = len(h2m)
    while i < n:
        row = h2m.iloc[i]
        d = row["方向"]
        is_cross_l = d == "good"
        is_cross_s = d == "bad"
        is_pre_l = bool(row["pre_cross_l"]) and not is_cross_l
        is_pre_s = bool(row["pre_cross_s"]) and not is_cross_s
        is_long = is_cross_l or is_pre_l
        is_short = is_cross_s or is_pre_s
        if not (is_long or is_short):
            i += 1
            continue
        # 门检查（对齐 MTA5_l apply_gate：做多要求 dir_sign==-1 即 4H 处于下跌段）
        if is_long:
            ok = (row["H4_dir_sign"] == -1) and (row["H4_seg_len"] >= N_MIN) and                  (row["H4_ext_wsw"] >= THR) and (row["H4_ext_vwsw"] >= THR)  # BUG修复: way_s_way无符号
            stop = row["long_stop"] if is_cross_l else row["long_stop_f"]
        else:
            ok = (row["H4_dir_sign"] == 1) and (row["H4_seg_len"] >= N_MIN) and                  (row["H4_ext_wsw"] >= THR) and (row["H4_ext_vwsw"] >= THR)
            stop = row["short_stop"] if is_cross_s else row["short_stop_f"]
        if not ok or not np.isfinite(row["H4_amp"]) or not (AMP_LO <= row["H4_amp"] <= AMP_HI):
            i += 1
            continue
        if i + 1 >= n:
            break
        entry_bar = i + 1
        entry = h2m["open"].iloc[entry_bar]
        if not np.isfinite(stop) or not np.isfinite(entry):
            i += 1
            continue
        # V1：事件前 T 小时内不开仓
        if VARIANT == "v1":
            ts0 = h2m["time"].iloc[entry_bar].to_datetime64()
            idx = np.searchsorted(ET, ts0, side="right")
            if idx < len(ET):
                gap = float((ET[idx] - ts0) / np.timedelta64(1, "h"))
                if gap < V1_HOURS:
                    i += 1
                    continue
        stop_dist = abs(entry - stop)
        if not (STOP_LO * entry <= stop_dist <= STOP_HI * entry):
            i += 1
            continue
        r = stop_dist
        # 单段退出：止损优先 / 2H 反向穿越（下一根开盘）；V5：事件后 WIDEN_HOURS 窗口内 SL 判定放宽
        exit_price = None; exit_reason = None; j = entry_bar
        ev_hit = False; ev_t = None
        win = np.timedelta64(int(WIDEN_HOURS * 3600), "s")
        while j < n:
            rr = h2m.iloc[j]
            stop_judge = stop
            if VARIANT == "v5":
                if not ev_hit:
                    i0 = np.searchsorted(ET, h2m["time"].iloc[entry_bar].to_datetime64(), side="right")
                    if i0 < len(ET) and ET[i0] <= rr["time"].to_datetime64():
                        ev_hit = True; ev_t = ET[i0]
                if ev_hit and (rr["time"].to_datetime64() - ev_t) <= win:
                    stop_judge = entry - WIDEN * (entry - stop) if is_long else entry + WIDEN * (stop - entry)
            if is_long and rr["low"] <= stop_judge:
                exit_price, exit_reason = stop_judge, "sl"
                break
            if is_short and rr["high"] >= stop_judge:
                exit_price, exit_reason = stop_judge, "sl"
                break
            if rr["方向"] in ("bad", "down") if is_long else rr["方向"] in ("good", "up"):
                if j > entry_bar:
                    exit_price, exit_reason = rr["open"], "rev"
                    break
            j += 1
        if exit_price is None:
            exit_price = h2m["close"].iloc[-1]; exit_reason = "eod"
        pnl_pts = ((exit_price - entry) if is_long else (entry - exit_price)) / h2m["close"].iloc[entry_bar] * 100.0
        pnl_pts -= COST_PT
        trades.append({
            "signal_time": h2m["time"].iloc[i], "entry_time": h2m["time"].iloc[entry_bar],
            "dir": "L" if is_long else "S",
            "entry": round(entry, 3), "stop": round(stop, 3),
            "stop_pct": round(stop_dist / entry * 100, 3),
            "exit_reason": exit_reason, "exit_price": round(exit_price, 3),
            "pnl_pts": round(pnl_pts, 3),
            "exit_time": h2m["time"].iloc[j] if j < n else h2m["time"].iloc[-1],
            "h4_amp": round(row["H4_amp"], 3), "h4_seg_len": int(row["H4_seg_len"]),
        })
        i = j + 1
    tdf = pd.DataFrame(trades)
    tag = VARIANT if VARIANT == "base" else f"{VARIANT}_{V1_HOURS}h"
    out = ROOT / "data" / "validation" / f"baseline_oil_trades_{tag}.csv" if VARIANT != "base" else ROOT / "data" / "validation" / "baseline_oil_trades.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    tdf.to_csv(out, index=False, encoding="utf-8-sig")
    if not len(tdf):
        print("[oil] n=0")
        return
    pnls = tdf["pnl_pts"].to_numpy()
    wins = pnls[pnls > 0]; losses = pnls[pnls <= 0]
    gw = wins.sum(); gl = -losses.sum()
    print(f"[oil] n={len(tdf)} wr={(len(wins)/len(tdf)):.3f} avg={pnls.mean():.3f}pts ev={pnls.sum():.3f} pf={(gw/gl if gl>0 else 999):.3f}")
    tdf["year"] = pd.to_datetime(tdf["entry_time"]).dt.year
    print(tdf.groupby("year").agg(n=("pnl_pts","size"), sum=("pnl_pts","sum")).to_string())
    # 退出原因分布
    print(tdf["exit_reason"].value_counts().to_string())


if __name__ == "__main__":
    main()
