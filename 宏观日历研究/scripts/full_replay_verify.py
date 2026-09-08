# -*- coding: utf-8 -*-
"""信号级完整重放复核：冷却过滤 vs 消息面过滤（ABC 三策略）。

与 monitor_all_strategies 完全一致地重建信号与三段出场，区别仅在信号接受处
插入状态机（按 M30 bar 序）：
  - cd_post : post_n 同向冷却（已接受信号方向 + N bar 内跳过，被跳过不更新状态）
  - loss_cd : 平仓事件按 bar 序驱动连续亏损组计数；2 连亏 -> 从平仓 bar 起冷却 120h
  - news    : 距下一个高影响事件 < T 小时不开仓
被跳过的信号不产生交易（盈亏不计入），与 EA 语义一致。
"""
from __future__ import annotations

import heapq
import sys as _sys
from pathlib import Path as _Path

_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程",
           *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"),
           *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"),
           *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)

import numpy as np
import pandas as pd

from replay_1h_bias55_h1_stop_optimization import load_frames as load_frames_1h  # noqa: E402
from replay_1h_way_momentum_filter_scan import add_h1_way_and_momentum  # noqa: E402
from experiment_1h_m30_4h_variants_20260813 import add_m30_state, replay_three_stage  # noqa: E402
from experiment_1h_m30_4h_combined_20260813 import build_combined_trades as build_combined_trades_1h  # noqa: E402
from combined_abc_30m2h_2h_20260814 import (  # noqa: E402
    STRATS as ABC_STRATS,
    attach_context,
    build_combo,
    build_three_opportunities,
    load_strategy,
    replay_signals,
)

STAGE_UNITS = {1: 0.5, 2: 1.0, 3: 1.5}
ROOT = _Path(r"F:\use_code\MTA5_l")
EVENTS_CSV = ROOT / "宏观日历研究" / "data" / "calendar_export.csv"
OUT_CSV = ROOT / "宏观日历研究" / "报告" / "完整重放_冷却vs消息面.csv"

CD_POST_BARS = {"1H_M30_4H": 6, "30m2H": 3, "2H_M30_6H": 3}
NEWS_TS = [1, 2, 4, 8]


def build_signals(strat: str):
    """重建信号（与 monitor 相同管线），返回 (m30_state, trades)。"""
    if strat == "1H_M30_4H":
        _, m30, h1, contexts = load_frames_1h()
        h4 = contexts["4H"]
        h1_way = add_h1_way_and_momentum(h1)
        m30_state = add_m30_state(m30)
        trades = build_combined_trades_1h(m30, h1_way, h4, 5.0, 35.0, 0.6)
    else:
        cfg = ABC_STRATS[strat]
        m30, gate_tf = load_strategy(cfg)
        m30_state = add_m30_state(m30)
        sig = build_three_opportunities(m30, spec_lo=5.0, spec_hi=35.0)
        replayed = replay_signals(sig, m30)
        prefix = str(cfg["c_tf"]).lower()
        enriched = attach_context(replayed, gate_tf, prefix)
        bias5_thr = 0.2 if strat == "30m2H" else 0.0
        trades = build_combo(enriched, cfg, bias5_thr)
    trades = trades.copy()
    trades["entry_bar_idx"] = pd.to_numeric(trades["entry_bar_idx"], errors="coerce").astype(int)
    trades["signal_time"] = pd.to_datetime(trades["signal_time"])
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])
    trades["dir"] = trades["dir"].astype(str).str.upper()
    trades["mode"] = trades["mode"].astype(str)
    return m30_state, trades


def per_signal_records(m30_state: pd.DataFrame, trades: pd.DataFrame) -> list[dict]:
    """为每个信号计算：出场 bar 索引（三段中最大）、组加权盈亏（0.5/1.0/1.5）。"""
    st = replay_three_stage(m30_state, trades)
    m30_times = pd.to_datetime(m30_state["date"]).to_numpy(dtype="datetime64[ns]")
    st["_sig"] = st["signal_time"].astype(str) + "|" + st["dir"].astype(str).str.upper()
    rec = {}
    for key, g in st.groupby("_sig", sort=False):
        exit_t = g["stage_exit_time"].max()
        idx = int(np.searchsorted(m30_times, exit_t.to_datetime64(), side="right") - 1)
        idx = max(0, idx)
        gpnl = float((g["stage_pnl"].astype(float) * g["stage"].map(STAGE_UNITS)).sum())
        first = g.iloc[0]
        rec[key] = {"exit_bar": idx, "gpnl": gpnl,
                    "signal_time": pd.Timestamp(first["signal_time"]),
                    "dir": str(first["dir"]).upper(), "mode": str(first["mode"])}
    out = []
    for _, tr in trades.iterrows():
        key = str(tr["signal_time"]) + "|" + str(tr["dir"]).upper()
        if key not in rec:
            continue
        r = rec[key]
        r["signal_bar_idx"] = int(tr["signal_bar_idx"])
        r["signal_time"] = pd.Timestamp(tr["signal_time"])
        out.append(r)
    out.sort(key=lambda r: (r["signal_bar_idx"], r["dir"]))
    return out


def run_replay(sigs: list[dict], events_next_h: np.ndarray,
               cd_post_bars: int = 0, loss_thr: int = 0, loss_hours: int = 0, news_T: float = 0.0):
    """信号级状态机重放。返回 (接受的gpnl数组, 跳过数, 冷却触发次数)。"""
    close_heap = []     # (exit_bar, gpnl)
    loss_streak = 0
    cd_until = -1
    last_cd: dict[str, int] = {}
    accepted = []
    skipped = 0
    cd_blocks = 0
    for i, s in enumerate(sigs):
        # 1) 先处理该信号 bar 之前的平仓事件
        while close_heap and close_heap[0][0] <= s["signal_bar_idx"]:
            _, gpnl = heapq.heappop(close_heap)
            if gpnl < 0:
                loss_streak += 1
                if loss_thr and loss_streak >= loss_thr:
                    cd_until = s["signal_bar_idx"] + loss_hours * 2   # M30 bar = 0.5h
                    cd_blocks += 1
            else:
                loss_streak = 0
        # 2) 损失冷却
        if loss_thr and s["signal_bar_idx"] < cd_until:
            skipped += 1
            continue
        # 3) 同向冷却 (post_n only)
        if cd_post_bars and s["mode"].startswith("post_n"):
            prev = last_cd.get(s["dir"])
            if prev is not None and s["signal_bar_idx"] - prev < cd_post_bars:
                skipped += 1
                continue
        # 4) 消息面过滤
        if news_T and events_next_h[i] <= news_T:
            skipped += 1
            continue
        # 接受
        accepted.append(s["gpnl"])
        last_cd[s["dir"]] = s["signal_bar_idx"]
        heapq.heappush(close_heap, (s["exit_bar"], s["gpnl"]))
    return np.asarray(accepted, dtype=float), skipped, cd_blocks


def stats(pts: np.ndarray) -> dict:
    if len(pts) == 0:
        return {"n": 0, "win_rate": np.nan, "avg_pts": np.nan, "total_pts": 0.0, "pf": np.nan, "max_dd_pts": 0.0, "sl_total": 0.0}
    eq = np.cumsum(pts)
    dd = (np.maximum.accumulate(eq) - eq).max()
    wins = pts[pts > 0].sum()
    losses = -pts[pts < 0].sum()
    return {"n": len(pts), "win_rate": (pts > 0).mean(), "avg_pts": pts.mean(), "total_pts": pts.sum(),
            "pf": wins / losses if losses > 0 else np.inf, "max_dd_pts": dd, "sl_total": losses}


def load_events():
    df = pd.read_csv(EVENTS_CSV, sep="|", dtype={"event_id": "int64", "time": "int64"})
    t = pd.to_datetime(df["time"], unit="s", utc=True)
    hi = t[df["importance"] >= 3].to_numpy(dtype="datetime64[ns]")
    return np.sort(hi)


def next_event_hours(sig_times: np.ndarray, hi: np.ndarray) -> np.ndarray:
    idx = np.searchsorted(hi, sig_times, side="right")
    out = np.full(len(sig_times), np.nan)
    for i, j in enumerate(idx):
        if j < len(hi):
            out[i] = (hi[j] - sig_times[i]) / np.timedelta64(1, "h")
    return out


def main():
    hi = load_events()
    rows = []
    for strat in ["1H_M30_4H", "30m2H", "2H_M30_6H"]:
        print("=" * 100)
        print(f"策略: {strat}")
        m30_state, trades = build_signals(strat)
        sigs = per_signal_records(m30_state, trades)
        sig_times = np.array([s["signal_time"].to_datetime64() for s in sigs], dtype="datetime64[ns]")
        ev_next = next_event_hours(sig_times, hi)
        print(f"  信号数(基线): {len(sigs)}  时间 {sigs[0]['signal_time']} ~ {sigs[-1]['signal_time']}")

        base_pts, _, _ = run_replay(sigs, ev_next)
        base = stats(base_pts)
        rows.append({"strategy": strat, "family": "基线", "variant": "baseline", **base})
        print(f"  baseline      : n={base['n']:>4} WR={base['win_rate']:.1%} 平均={base['avg_pts']:8.2f} "
              f"合计={base['total_pts']:10.1f} PF={base['pf']:.2f} MaxDD={base['max_dd_pts']:.1f}")

        # 冷却
        cd_bars = CD_POST_BARS[strat]
        for label, kw in [
            (f"cd_post={cd_bars}bar", dict(cd_post_bars=cd_bars)),
            ("loss_cd 2连亏120h", dict(loss_thr=2, loss_hours=120)),
            (f"cd_post{cd_bars}bar+loss_cd", dict(cd_post_bars=cd_bars, loss_thr=2, loss_hours=120)),
        ]:
            pts, skipped, cdb = run_replay(sigs, ev_next, **kw)
            s = stats(pts)
            rows.append({"strategy": strat, "family": "冷却", "variant": label, **s})
            print(f"  {label:<18}: n={s['n']:>4} WR={s['win_rate']:.1%} 平均={s['avg_pts']:8.2f} "
                  f"合计={s['total_pts']:10.1f} PF={s['pf']:.2f} MaxDD={s['max_dd_pts']:.1f} (跳过{skipped} 冷却{cdb}次)")

        # 消息面
        news_best = None
        for T in NEWS_TS:
            pts, skipped, _ = run_replay(sigs, ev_next, news_T=T)
            s = stats(pts)
            rows.append({"strategy": strat, "family": "消息面", "variant": f"news_V1_T{T}h", **s})
            if news_best is None or s["total_pts"] > news_best[1]["total_pts"]:
                news_best = (T, s)
        Tb, nb = news_best
        print(f"  news_V1_T{Tb}h(最优): n={nb['n']:>4} WR={nb['win_rate']:.1%} 平均={nb['avg_pts']:8.2f} "
              f"合计={nb['total_pts']:10.1f} PF={nb['pf']:.2f} MaxDD={nb['max_dd_pts']:.1f}")

        # 消息面最优 + 冷却
        pts, skipped, cdb = run_replay(sigs, ev_next, cd_post_bars=cd_bars, loss_thr=2, loss_hours=120, news_T=Tb)
        s = stats(pts)
        rows.append({"strategy": strat, "family": "组合", "variant": f"news_T{Tb}h+cd+loss_cd", **s})
        print(f"  news_T{Tb}h+cd+loss_cd: n={s['n']:>4} WR={s['win_rate']:.1%} 平均={s['avg_pts']:8.2f} "
              f"合计={s['total_pts']:10.1f} PF={s['pf']:.2f} MaxDD={s['max_dd_pts']:.1f}")

    out = pd.DataFrame(rows)
    out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print()
    print("[已输出]", OUT_CSV)


if __name__ == "__main__":
    main()
