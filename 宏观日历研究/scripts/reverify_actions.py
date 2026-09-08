# -*- coding: utf-8 -*-
"""三个建议行动项：从原始数据→信号重建→完整重放 复核。

行动1: USOIL4H 事件门 T=1/2/4/8h（信号级）
行动2: 1H_M30_4H post_n 降档 6→5→4（信号级，改 POST_N_MAX 后重建）
行动3: BiasReversal 做空侧（仅做多 / 仅做空 独立重放）
"""
from __future__ import annotations

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

ROOT = _Path(r"F:\use_code\MTA5_l")
RESEARCH = ROOT / "宏观日历研究"
EVENTS_CSV = RESEARCH / "data" / "calendar_export.csv"
OUT_CSV = RESEARCH / "报告" / "行动项复核_汇总.csv"


def load_high_events():
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


def stats(w: np.ndarray) -> dict:
    if len(w) == 0:
        return {"n": 0, "wr": np.nan, "total": 0.0, "avg": np.nan, "pf": np.nan, "maxdd": 0.0}
    eq = np.cumsum(w)
    dd = (np.maximum.accumulate(eq) - eq).max()
    wins, losses = w[w > 0].sum(), -w[w < 0].sum()
    return {"n": len(w), "wr": (w > 0).mean(), "total": w.sum(), "avg": w.mean(),
            "pf": wins / losses if losses > 0 else np.inf, "maxdd": dd}


def yearly(w: np.ndarray, ts: np.ndarray) -> dict:
    s = pd.Series(w, index=pd.to_datetime(ts))
    return {int(k): float(v) for k, v in s.groupby(s.index.year).sum().items()}


def fmt(s: dict, yearly_map=None):
    pf = "inf" if np.isinf(s["pf"]) else f"{s['pf']:.2f}"
    line = (f"n={s['n']:>4} WR={s['wr']:.1%} 合计={s['total']:>11,.0f} 平均={s['avg']:>9,.1f} "
            f"PF={pf} MaxDD={s['maxdd']:>10,.0f}")
    if yearly_map:
        line += "  年度:" + " ".join(f"{k}:{v:+,.0f}" for k, v in yearly_map.items())
    return line


def main():
    hi = load_high_events()
    rows = []
    print("=" * 110)

    # ============ 行动1: USOIL4H 事件门 ============
    from validate_usoil_gate_strategy import (  # noqa: E402
        STRATEGIES as GATE_STRATEGIES,
        build_triggers,
        gate_check,
        load_2h,
        load_gate,
    )
    print("行动1: USOIL4H 事件门（信号级，信号即交易）")
    strategy_dir = ROOT / "原油" / "原油4H门策略"
    cfg = GATE_STRATEGIES["原油4H门策略"]
    tf2 = load_2h(strategy_dir)
    gt = load_gate(strategy_dir, cfg)
    trig = build_triggers(tf2)
    check = gate_check(gt, cfg["n_min"], cfg["thr"], *cfg["amp"])
    keep = np.array([check(t, r["dir"] == "L") for t, r in zip(trig["signal_time"], trig.to_dict("records"))])
    trades = trig.loc[keep].copy().reset_index(drop=True)
    w0 = pd.to_numeric(trades["pnl_points"], errors="coerce").to_numpy(dtype=float) * 1000.0
    ts0 = pd.to_datetime(trades["signal_time"]).to_numpy(dtype="datetime64[ns]")
    s0 = stats(w0)
    rows.append({"action": "USOIL4H事件门", "variant": "baseline", **s0})
    print("  baseline:", fmt(s0, yearly(w0, ts0)))
    ev_next = next_event_hours(ts0, hi)
    for T in [1, 2, 4, 8]:
        m = ev_next > T
        s = stats(w0[m])
        rows.append({"action": "USOIL4H事件门", "variant": f"event_gate_T{T}h", **s})
        print(f"  event_gate_T{T}h: {fmt(s, yearly(w0[m], ts0[m]))}")

    # ============ 行动2: 1H_M30_4H post_n 降档 ============
    from replay_1h_bias55_h1_stop_optimization import load_frames as load_frames_1h  # noqa: E402
    from replay_1h_way_momentum_filter_scan import add_h1_way_and_momentum  # noqa: E402
    from experiment_1h_m30_4h_variants_20260813 import add_m30_state, replay_three_stage  # noqa: E402
    import experiment_1h_m30_4h_variants_20260813 as V_MOD  # noqa: E402
    from experiment_1h_m30_4h_combined_20260813 import build_combined_trades  # noqa: E402

    print()
    print("=" * 110)
    print("行动2: 1H_M30_4H post_n 降档（信号级重建）")
    _, m30, h1, contexts = load_frames_1h()
    h4 = contexts["4H"]
    h1_way = add_h1_way_and_momentum(h1)
    m30_state = add_m30_state(m30)
    for pmax in [6, 5, 4]:
        V_MOD.POST_N_MAX = pmax
        trades = build_combined_trades(m30, h1_way, h4, 5.0, 35.0, 0.6).copy()
        trades["entry_bar_idx"] = pd.to_numeric(trades["entry_bar_idx"], errors="coerce").astype(int)
        st = replay_three_stage(m30_state, trades)
        st["_w"] = st["stage_pnl"].astype(float) * st["stage"].map({1: 0.5, 2: 1.0, 3: 1.5})
        per = st.groupby(["signal_time", "dir"], sort=False)["_w"].sum().reset_index()
        w = per["_w"].to_numpy(dtype=float)
        ts = pd.to_datetime(per["signal_time"]).to_numpy(dtype="datetime64[ns]")
        s = stats(w)
        rows.append({"action": "1H_post_n降档", "variant": f"post_n2-{pmax}", **s})
        print(f"  post_n2-{pmax}: {fmt(s, yearly(w, ts))}")
    V_MOD.POST_N_MAX = 6  # restore

    # ============ 行动3: BiasReversal 做空侧 ============
    from bias_reversal_replay import pipeline, replay_long, replay_short  # noqa: E402

    print()
    print("=" * 110)
    print("行动3: BiasReversal 做空侧（独立重放）")
    bdir = ROOT / "黄金" / "乖离反转策略" / "data" / "raw" / "mt5_history" / "bias_reversal_live"
    h4 = pipeline(bdir / "XAUUSDm_H4.csv", "4H")
    h6 = pipeline(bdir / "XAUUSDm_H6.csv", "6H")
    h2 = pipeline(bdir / "XAUUSDm_H2.csv", "2H")
    h1 = pipeline(bdir / "XAUUSDm_H1.csv", "1H")
    variants = {
        "baseline(多+空)": pd.concat([replay_long(h6, h1), replay_short(h4, h2)], ignore_index=True),
        "仅做多": replay_long(h6, h1),
        "仅做空": replay_short(h4, h2),
    }
    for label, st in variants.items():
        st = st.copy()
        st["signal_time"] = pd.to_datetime(st["signal_time"])
        w = pd.to_numeric(st["stage_pnl"], errors="coerce").to_numpy(dtype=float) * 100.0
        ts = st["signal_time"].to_numpy(dtype="datetime64[ns]")
        s = stats(w)
        rows.append({"action": "BiasReversal做空侧", "variant": label, **s})
        print(f"  {label}: {fmt(s, yearly(w, ts))}")

    out = pd.DataFrame(rows)
    out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print()
    print("[已输出]", OUT_CSV)


if __name__ == "__main__":
    main()
