# -*- coding: utf-8 -*-
"""M3 预注册变体回测（V1-V5）+ bootstrap CI + 年度一致性。
V1 开仓过滤（事件前T小时不开仓）；V2 事件平仓；V3=V1+V2；V4 窗口内仓位减半；V5 事件感知止损放宽。
黄金单位：R；原油单位：pts（各自 vs 自身基线）。
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "validate"))
from backtest_baseline import gen_signals_gold, gen_signals_oil, COST  # noqa: E402

COST_PT = 0.05


def load_blackout_events(cat: str = "") -> np.ndarray:
    ev = pd.read_csv(ROOT / "data" / "processed" / "calendar_events.csv", parse_dates=["event_time_utc"])
    ev = ev[ev["is_blackout_event"] == True]  # noqa: E712
    if cat:
        ev = ev[ev["category"] == cat]
    return pd.to_datetime(ev["event_time_utc"], utc=True).to_numpy().astype("datetime64[ns]")


def next_event_gap_h(ts: np.datetime64, et: np.ndarray) -> float:
    """开仓时刻距下一高影响事件的小时数（正=事件在未来）"""
    idx = np.searchsorted(et, ts, side="right")
    if idx >= len(et):
        return np.inf
    return float((et[idx] - ts) / np.timedelta64(1, "h"))


def event_between(t0: np.datetime64, t1: np.datetime64, et: np.ndarray) -> bool:
    i0 = np.searchsorted(et, t0, side="right")
    i1 = np.searchsorted(et, t1, side="right")
    return i1 > i0


EA_REASON_MAP = {
    "sl": "SL hit", "tp1": "2.0R TP", "trail": "trail/SL hit",
    "force": "4.0R forced", "rev": "M30 merged cross", "evt": "event close",
    "eod": "end of data",
}


def simulate_with_variant(df, sig_col, et, variant: str, v1_hours: float = 0.0,
                          widen_mult: float = 2.5, half_win_h: float = 4.0,
                          widen_hours: float = 4.0,
                          trade_unit: str = "R",
                          stop_spec: tuple | None = None,
                          with_detail: bool = False,
                          max_open: int | None = None,
                          loss_cd_loss: int = 0, loss_cd_hours: float = 0.0,
                          same_dir_cd_bars: int = 0,
                          exit_semantics: str = "py") -> list[dict]:
    """stop_spec=(lo,hi)：止损距离（价格单位）过滤——黄金 405 笔口径 (5.0, 35.0) 美元。
    with_detail=True：trade 附带 signal_time/entry/stop/stop_dist/mode/stages
    （逐段 exit_time/exit_price/reason/pnl_price 价格单位），供 expected ledger 使用。
    EA 运行时过滤（M4 对齐 v1）：max_open=并发信号上限（EA InpMaxOpenVirtual=3）；
    loss_cd_loss=连续亏损信号组数触发冷却（EA InpLossCdLoss=2，组加权盈亏=0.5*s1+1.0*s2+1.5*s3）；
    same_dir_cd_bars=post_n 同向冷却根数（EA InpSameDirCdBars=3）。
    """
    trades = []
    open_trades: list[dict] = []      # 未平仓信号组（EA g_trades）
    loss_streak = 0
    loss_cd_until = None              # np.datetime64 冷却截止
    last_sig_dir = 0
    last_sig_bar = -999
    bar_seq = 0
    i = 0
    n = len(df)
    times = df["time"].to_numpy().astype("datetime64[ns]")
    while i < n:
        sig = df[sig_col].iloc[i]
        if not sig or i + 1 >= n:
            i += 1
            continue
        is_long = sig.startswith("long")
        entry_bar = i + 1
        entry = df["open"].iloc[entry_bar]
        stop = df["long_stop"].iloc[i] if is_long else df["short_stop"].iloc[i]
        if not np.isfinite(stop) or not np.isfinite(entry):
            i += 1
            continue
        r = abs(entry - stop)
        if r <= 0 or r > entry * 0.05:
            i += 1
            continue
        if stop_spec is not None and not (stop_spec[0] <= r <= stop_spec[1]):
            i += 1
            continue
        ts0 = times[entry_bar]
        # V1: 事件前 T 小时内不开仓
        if variant in ("v1", "v3", "v1v5") and v1_hours > 0:
            gap = next_event_gap_h(ts0, et)
            if gap < v1_hours:
                i += 1
                continue
        # EA 运行时过滤（M4 对齐 v1）
        bar_seq += 1
        if max_open is not None:
            # 清理已平仓信号组（exit_time <= 当前开仓时刻）
            open_trades = [t for t in open_trades if np.datetime64(t["exit_time"]) > ts0]
            if len(open_trades) >= max_open:
                i += 1
                continue
        if loss_cd_loss > 0 and loss_cd_until is not None and ts0 < np.datetime64(loss_cd_until):
            i += 1
            continue
        mode_sig = sig.split("_")[-1] if "_" in sig else sig
        if same_dir_cd_bars > 0 and mode_sig == "post_n":
            sd = 1 if sig.startswith("long") else -1
            if sd == last_sig_dir and (bar_seq - last_sig_bar) < same_dir_cd_bars:
                i += 1
                continue
        # V4: 事件窗口内仓位减半（开仓时刻距事件 < half_win_h）
        weight = 1.0
        if variant == "v4":
            gap = next_event_gap_h(ts0, et)
            gap_prev = float((ts0 - et[np.searchsorted(et, ts0, side="right") - 1]) / np.timedelta64(1, "h"))                 if np.searchsorted(et, ts0, side="right") > 0 else np.inf
            if min(gap, gap_prev) < half_win_h:
                weight = 0.5
        # V5: 持仓遇事件 → 事件后 4h 窗口内 SL 判定放宽（R 基准保持原始止损，超时恢复）
        r_eff = r
        exits = {"s1": None, "s2": None, "s3": None}
        exit_times = {"s1": None, "s2": None, "s3": None}
        # EA 语义：stage2 trail 初始=stop（EA stage2_trail_sl = stop）
        trail_s2 = stop if exit_semantics == "ea" else None
        j = entry_bar
        event_hit = False
        ev_time = None
        widen_win = np.timedelta64(int(widen_hours * 3600), "s")  # 事件后放宽窗口
        while j < n:
            row = df.iloc[j]
            hi, lo, cl = row["high"], row["low"], row["close"]
            s13 = row["SMA_13"]
            d = row["方向"]
            # V2: 持仓遇事件 → 该 bar 开盘平仓（事件时刻近似为 bar 内）
            if variant in ("v2", "v3") and not event_hit:
                if event_between(times[entry_bar], times[j], et):
                    event_hit = True
                    px = row["open"]
                    for k in ("s1", "s2", "s3"):
                        if exits[k] is None:
                            exits[k] = ("evt", px)
                            exit_times[k] = times[j]
                    break
            # V5: 事件发生（记录时刻）→ 事件后 widen_hours 内 SL 判定放宽，超时恢复
            stop_judge = stop
            if variant in ("v5", "v1v5"):
                if not event_hit:
                    i0 = np.searchsorted(et, times[entry_bar], side="right")
                    if i0 < len(et) and et[i0] <= times[j]:
                        event_hit = True
                        ev_time = et[i0]
                if event_hit and ev_time is not None and (times[j] - ev_time) <= widen_win:
                    stop_judge = entry + widen_mult * (stop - entry) if is_long else entry - widen_mult * (entry - stop)
            if exit_semantics == "ea":
                # ---- EA ProcessOpenTrades 语义（M4 对齐 v2）：逐段独立 + bound@close ----
                # bound: merged 反向（对多单 merged<0；对空单 merged>0）
                dm = row.get("方向_m", d)
                bound = (is_long and dm in ("bad", "down")) or (not is_long and dm in ("good", "up"))
                tp1 = entry + (2.0 * r_eff if is_long else -2.0 * r_eff)
                act2 = entry + (1.5 * r_eff if is_long else -1.5 * r_eff)
                force2 = entry + (4.0 * r_eff if is_long else -4.0 * r_eff)
                # stage1: 仅 TP(2.0R) / SL
                if exits["s1"] is None:
                    if (is_long and lo <= stop_judge) or (not is_long and hi >= stop_judge):
                        exits["s1"] = ("sl", min(stop_judge, entry) if is_long else max(stop_judge, entry))
                        exit_times["s1"] = times[j]
                    elif (is_long and hi >= tp1) or (not is_long and lo <= tp1):
                        exits["s1"] = ("tp1", tp1)
                        exit_times["s1"] = times[j]
                # stage2: force(4.0R) / trail(1.5R激活,SMA13) / bound@close
                if exits["s2"] is None:
                    if (is_long and hi >= force2) or (not is_long and lo <= force2):
                        exits["s2"] = ("force", force2)
                        exit_times["s2"] = times[j]
                    elif trail_s2 is not None and ((is_long and lo <= trail_s2) or (not is_long and hi >= trail_s2)):
                        exits["s2"] = ("trail", trail_s2)
                        exit_times["s2"] = times[j]
                    elif ((is_long and hi >= act2) or (not is_long and lo <= act2)) and                          ((is_long and s13 > trail_s2) or (not is_long and s13 < trail_s2)):
                        trail_s2 = s13
                    if exits["s2"] is None and bound:
                        exits["s2"] = ("rev", cl)
                        exit_times["s2"] = times[j]
                # stage3: SL / bound@close
                if exits["s3"] is None:
                    if (is_long and lo <= stop_judge) or (not is_long and hi >= stop_judge):
                        exits["s3"] = ("sl", min(stop_judge, entry) if is_long else max(stop_judge, entry))
                        exit_times["s3"] = times[j]
                    elif bound:
                        exits["s3"] = ("rev", cl)
                        exit_times["s3"] = times[j]
            elif is_long:
                if lo <= stop_judge:
                    px = min(stop_judge, entry)
                    for k in ("s1", "s2", "s3"):
                        if exits[k] is None:
                            exits[k] = ("sl", px)
                            exit_times[k] = times[j]
                    break
                tp1 = entry + 2.0 * r_eff
                if exits["s1"] is None and hi >= tp1:
                    exits["s1"] = ("tp1", tp1)
                    exit_times["s1"] = times[j]
                act2 = entry + 1.5 * r_eff
                force2 = entry + 4.0 * r_eff
                if exits["s2"] is None:
                    if trail_s2 is None and hi >= act2:
                        trail_s2 = s13
                    if trail_s2 is not None:
                        trail_s2 = max(trail_s2, s13)
                        if lo <= trail_s2:
                            exits["s2"] = ("trail", trail_s2)
                            exit_times["s2"] = times[j]
                    if hi >= force2:
                        exits["s2"] = ("force", force2)
                        exit_times["s2"] = times[j]
                if exits["s3"] is None and d in ("bad", "down") and j > entry_bar:
                    exits["s3"] = ("rev", row["open"])
                    exit_times["s3"] = times[j]
            else:
                if hi >= stop_judge:
                    px = max(stop_judge, entry)
                    for k in ("s1", "s2", "s3"):
                        if exits[k] is None:
                            exits[k] = ("sl", px)
                            exit_times[k] = times[j]
                    break
                tp1 = entry - 2.0 * r_eff
                if exits["s1"] is None and lo <= tp1:
                    exits["s1"] = ("tp1", tp1)
                    exit_times["s1"] = times[j]
                act2 = entry - 1.5 * r_eff
                force2 = entry - 4.0 * r_eff
                if exits["s2"] is None:
                    if trail_s2 is None and lo <= act2:
                        trail_s2 = s13
                    if trail_s2 is not None:
                        trail_s2 = min(trail_s2, s13)
                        if hi >= trail_s2:
                            exits["s2"] = ("trail", trail_s2)
                            exit_times["s2"] = times[j]
                    if lo <= force2:
                        exits["s2"] = ("force", force2)
                        exit_times["s2"] = times[j]
                if exits["s3"] is None and d in ("good", "up") and j > entry_bar:
                    exits["s3"] = ("rev", row["open"])
                    exit_times["s3"] = times[j]
            if exits["s1"] and exits["s2"] and exits["s3"]:
                break
            j += 1
        if j >= n:
            last_close = df["close"].iloc[-1]
            for k in ("s1", "s2", "s3"):
                if exits[k] is None:
                    exits[k] = ("eod", last_close)
                    exit_times[k] = times[-1]
        pnl = 0.0
        for k in ("s1", "s2", "s3"):
            _, px = exits[k]
            pnl += ((px - entry) if is_long else (entry - px)) / r_eff * 33.3333
        pnl -= COST * 100.0 * 3 if trade_unit == "R" else COST_PT * 3
        pnl *= weight
        trade = {"entry_time": df["time"].iloc[entry_bar], "dir": "L" if is_long else "S",
                 "pnl": pnl, "exit_time": df["time"].iloc[j] if j < n else df["time"].iloc[-1]}
        # EA 运行时记账（M4 对齐 v1）
        if max_open is not None or loss_cd_loss > 0 or same_dir_cd_bars > 0:
            open_trades.append(trade)
            if max_open is not None:
                open_trades = [t for t in open_trades if np.datetime64(t["exit_time"]) > np.datetime64(trade["entry_time"])]
            if loss_cd_loss > 0:
                gp = pnl  # 近似：R 单位加权（EA 用价格单位 0.5/1.0/1.5 加权）
                if gp < 0:
                    loss_streak += 1
                    if loss_streak >= loss_cd_loss:
                        loss_cd_until = np.datetime64(trade["exit_time"]) + np.timedelta64(int(loss_cd_hours * 3600), "s")
                else:
                    loss_streak = 0
            last_sig_dir = 1 if is_long else -1
            last_sig_bar = bar_seq
        if with_detail:
            mode = sig.replace("long_", "").replace("short_", "")
            trade.update({
                "signal_time": df["time"].iloc[i],
                "mode": mode,
                "entry": entry, "stop": stop, "stop_dist": r,
                "stages": [{"stage": int(k[1]), "exit_time": exit_times[k], "exit_price": exits[k][1],
                            "reason": exits[k][0], "ea_reason": EA_REASON_MAP.get(exits[k][0], exits[k][0]),
                            "pnl_price": round((exits[k][1] - entry) if is_long else (entry - exits[k][1]), 5)}
                           for k in ("s1", "s2", "s3")],
            })
        trades.append(trade)
        i = j + 1
    return trades


def summarize(trades: list[dict], label: str) -> dict:
    if not trades:
        return {"label": label, "n": 0}
    pnls = np.array([t["pnl"] for t in trades])
    wins = pnls[pnls > 0]; losses = pnls[pnls <= 0]
    gw = wins.sum(); gl = -losses.sum()
    return {"label": label, "n": len(trades), "wr": round(len(wins) / len(trades), 3),
            "avg": round(float(pnls.mean()), 3), "ev": round(float(pnls.sum()), 2),
            "pf": round(gw / gl, 3) if gl > 0 else 999,
            "maxcl": 0}


def maxcl(pnls: np.ndarray) -> int:
    m = c = 0
    for p in pnls:
        if p <= 0:
            c += 1; m = max(m, c)
        else:
            c = 0
    return m


def bootstrap_ci(pnls: np.ndarray, n_boot: int = 2000, seed: int = 42) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(pnls, size=len(pnls), replace=True).mean() for _ in range(n_boot)])
    return round(float(np.percentile(means, 2.5)), 3), round(float(np.percentile(means, 97.5)), 3)


def yearly_consistency(trades: list[dict]) -> str:
    if not trades:
        return "-"
    td = pd.DataFrame(trades)
    td["year"] = pd.to_datetime(td["entry_time"]).dt.year
    y = td.groupby("year")["pnl"].sum()
    return f"{int((y > 0).sum())}/{len(y)}"


def run_strategy(name: str, ctx_path: str, gen_fn, sig_col: str, unit: str,
                 stop_spec: tuple | None = None, tag: str = "") -> None:
    print(f"\n======== {name} ========")
    if stop_spec is not None:
        print(f"StopSpec 过滤: [{stop_spec[0]}, {stop_spec[1]}] 价格单位")
    ctx = pd.read_csv(ctx_path, parse_dates=["time"])
    ctx["time"] = pd.to_datetime(ctx["time"], utc=True)
    df = gen_fn(ctx)
    et = load_blackout_events()
    rows = []
    base = simulate_with_variant(df, sig_col, et, "base", trade_unit=unit, stop_spec=stop_spec)
    rows.append(summarize(base, "baseline"))
    # V1 各窗口
    for t in (1, 2, 4, 8):
        tr = simulate_with_variant(df, sig_col, et, "v1", v1_hours=t, trade_unit=unit, stop_spec=stop_spec)
        rows.append(summarize(tr, f"V1_T{t}h"))
    # V2 / V3(T2h) / V4(T4h) / V5(2.5x)
    rows.append(summarize(simulate_with_variant(df, sig_col, et, "v2", trade_unit=unit, stop_spec=stop_spec), "V2_event_close"))
    rows.append(summarize(simulate_with_variant(df, sig_col, et, "v3", v1_hours=2, trade_unit=unit, stop_spec=stop_spec), "V3_T2h"))
    rows.append(summarize(simulate_with_variant(df, sig_col, et, "v4", half_win_h=4, trade_unit=unit, stop_spec=stop_spec), "V4_halve_T4h"))
    rows.append(summarize(simulate_with_variant(df, sig_col, et, "v5", widen_mult=2.5, widen_hours=4.0, trade_unit=unit, stop_spec=stop_spec), "V5_widen2.5x_4h"))
    rows.append(summarize(simulate_with_variant(df, sig_col, et, "v5", widen_mult=3.0, widen_hours=4.0, trade_unit=unit, stop_spec=stop_spec), "V5_widen3.0x_4h"))
    rows.append(summarize(simulate_with_variant(df, sig_col, et, "v5", widen_mult=2.0, widen_hours=8.0, trade_unit=unit, stop_spec=stop_spec), "V5_widen2.0x_8h"))
    # 组合：V1+V5
    rows.append(summarize(simulate_with_variant(df, sig_col, et, "v1v5", v1_hours=2, widen_mult=3.0, widen_hours=4.0, trade_unit=unit, stop_spec=stop_spec), "V1T2h_V5w3x"))
    rows.append(summarize(simulate_with_variant(df, sig_col, et, "v1v5", v1_hours=1, widen_mult=3.0, widen_hours=4.0, trade_unit=unit, stop_spec=stop_spec), "V1T1h_V5w3x"))
    res = pd.DataFrame(rows)
    # bootstrap 与年度一致性
    all_trades = {}
    all_trades["baseline"] = simulate_with_variant(df, sig_col, et, "base", trade_unit=unit, stop_spec=stop_spec)
    for t in (1, 2, 4, 8):
        all_trades[f"V1_T{t}h"] = simulate_with_variant(df, sig_col, et, "v1", v1_hours=t, trade_unit=unit, stop_spec=stop_spec)
    all_trades["V2_event_close"] = simulate_with_variant(df, sig_col, et, "v2", trade_unit=unit, stop_spec=stop_spec)
    all_trades["V3_T2h"] = simulate_with_variant(df, sig_col, et, "v3", v1_hours=2, trade_unit=unit, stop_spec=stop_spec)
    all_trades["V4_halve_T4h"] = simulate_with_variant(df, sig_col, et, "v4", half_win_h=4, trade_unit=unit, stop_spec=stop_spec)
    all_trades["V5_widen2.5x_4h"] = simulate_with_variant(df, sig_col, et, "v5", widen_mult=2.5, widen_hours=4.0, trade_unit=unit, stop_spec=stop_spec)
    all_trades["V5_widen3.0x_4h"] = simulate_with_variant(df, sig_col, et, "v5", widen_mult=3.0, widen_hours=4.0, trade_unit=unit, stop_spec=stop_spec)
    all_trades["V5_widen2.0x_8h"] = simulate_with_variant(df, sig_col, et, "v5", widen_mult=2.0, widen_hours=8.0, trade_unit=unit, stop_spec=stop_spec)
    all_trades["V1T2h_V5w3x"] = simulate_with_variant(df, sig_col, et, "v1v5", v1_hours=2, widen_mult=3.0, widen_hours=4.0, trade_unit=unit, stop_spec=stop_spec)
    all_trades["V1T1h_V5w3x"] = simulate_with_variant(df, sig_col, et, "v1v5", v1_hours=1, widen_mult=3.0, widen_hours=4.0, trade_unit=unit, stop_spec=stop_spec)
    for v, tr in all_trades.items():
        if not tr:
            continue
        pnls = np.array([t["pnl"] for t in tr])
        lo, hi = bootstrap_ci(pnls)
        res.loc[res["label"] == v, "boot_ci"] = f"[{lo}, {hi}]"
        res.loc[res["label"] == v, "pos_years"] = yearly_consistency(tr)
        res.loc[res["label"] == v, "maxcl"] = maxcl(pnls)
    print(res.to_string(index=False))
    out = ROOT / "data" / "validation" / f"variants_{name}{tag}.csv"
    res.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"saved: {out}")


if __name__ == "__main__":
    # 黄金：405 笔口径 = StopSpec 5-35 美元过滤（与 EA InpStopLoPt/HiPt 一致）
    run_strategy("gold", ROOT / "data" / "processed" / "gold_context.csv",
                 gen_signals_gold, "sig", "R", stop_spec=(5.0, 35.0), tag="_405")
    run_strategy("oil", ROOT / "data" / "processed" / "oil_context_h2.csv",
                 gen_signals_oil, "sig", "pts")
