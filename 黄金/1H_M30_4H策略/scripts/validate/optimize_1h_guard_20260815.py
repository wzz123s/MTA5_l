# -*- coding: utf-8 -*-
"""Test 2024-type guards on the improved 1H candidate (drop pn56 + Stage1 1.5R).

Guards:
  G1: reject SELL when short ratio of last 60 signals > 0.75
  G2: reject SELL when short ratio of last 60 signals > 0.80
  G3: reject SELL when short ratio of trailing 180 days > 0.75
  G4: reject SELL when H4 SMMA5 > SMMA13 (uptrend)
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



import sys
from pathlib import Path

import pandas as pd


SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import experiment_1h_m30_4h_variants_20260813 as v  # noqa: E402
from experiment_1h_m30_4h_combined_20260813 import build_combined_trades  # noqa: E402
from replay_1h_bias55_h1_stop_optimization import load_frames  # noqa: E402
from replay_1h_way_momentum_filter_scan import add_h1_way_and_momentum  # noqa: E402
from replay_raw_signals_with_stops import attach_context  # noqa: E402


OUT_DIR = (
    Path(r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\data\validation\experiments_20260813")
    / "combined_20260813"
    / "validation_20260814"
    / "optimize_1h_20260815"
)
STAGE_UNITS = {1: 0.5, 2: 1.0, 3: 1.5}


def replay_improved(trades: pd.DataFrame, m30_state) -> pd.DataFrame:
    scoped = trades[~trades["mode"].isin({"post_n5", "post_n6"})].copy().reset_index(drop=True)
    v.STAGE1_R = 1.5
    try:
        return v.replay_three_stage(m30_state, scoped)
    finally:
        v.STAGE1_R = 2.0


def per_trade(st: pd.DataFrame) -> pd.DataFrame:
    st = st.copy()
    st["w"] = st["stage_pnl"].astype(float) * st["stage"].map(STAGE_UNITS)
    per = st.groupby(["signal_time", "dir"], sort=True).agg(
        ts=("signal_time", "first"),
        w=("w", "sum"),
        year=("signal_time", lambda x: pd.to_datetime(x.iloc[0]).year),
    ).reset_index()
    return per


def summarize(per: pd.DataFrame) -> dict:
    vals = per["w"]
    wins = vals[vals > 0]
    losses = vals[vals < 0]
    gw = wins.sum()
    gl = abs(losses.sum())
    pf = gw / gl if gl > 0 else (999.0 if gw > 0 else 0.0)
    ordered = per.sort_values("ts").reset_index(drop=True)
    cutoff_idx = min(max(int(len(ordered) * 0.70), 1), len(ordered) - 1)
    cutoff = ordered.loc[cutoff_idx, "ts"]
    test = ordered.loc[ordered["ts"] >= cutoff, "w"]
    tw = test[test > 0]
    tl = test[test < 0]
    test_pf = (tw.sum() / abs(tl.sum())) if abs(tl.sum()) > 0 else (999.0 if tw.sum() > 0 else 0.0)
    years = per.groupby("year")["w"].sum()
    return {
        "n": int(len(vals)),
        "wr": float((vals > 0).mean() * 100.0),
        "pf": float(pf),
        "ev": float(vals.mean()),
        "pnl_points": float(vals.sum()),
        "test_pf": float(test_pf),
        "pos_years": f"{int((years > 0).sum())}/{len(years)}",
    }


def apply_guards(trades: pd.DataFrame, guard: str) -> pd.DataFrame:
    t = trades.sort_values("signal_time").reset_index(drop=True).copy()
    if guard == "none":
        return t
    is_short = t["dir"].astype(str).str.upper().eq("S")
    if guard in ("G1", "G2"):
        thr = 0.75 if guard == "G1" else 0.80
        reject = pd.Series(False, index=t.index)
        for i in t.index:
            if not is_short.loc[i]:
                continue
            prev = t.iloc[max(0, i - 60):i]
            if len(prev) == 0:
                continue
            ratio = prev["dir"].astype(str).str.upper().eq("S").mean()
            if ratio > thr:
                reject.loc[i] = True
        return t.loc[~reject].copy().reset_index(drop=True)
    if guard == "G3":
        ts = pd.to_datetime(t["signal_time"])
        reject = pd.Series(False, index=t.index)
        for i in t.index:
            if not is_short.loc[i]:
                continue
            window = t.loc[(ts >= ts.iloc[i] - pd.Timedelta(days=180)) & (ts < ts.iloc[i])]
            if len(window) == 0:
                continue
            ratio = window["dir"].astype(str).str.upper().eq("S").mean()
            if ratio > 0.75:
                reject.loc[i] = True
        return t.loc[~reject].copy().reset_index(drop=True)
    if guard == "G4":
        h4_dir = pd.to_numeric(t["4h_dir"], errors="coerce")
        reject = is_short & h4_dir.gt(0)
        return t.loc[~reject].copy().reset_index(drop=True)
    raise KeyError(guard)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _, m30, h1, contexts = load_frames()
    h4 = contexts["4H"]
    h1_way = add_h1_way_and_momentum(h1)
    m30_state = v.add_m30_state(m30)
    trades = build_combined_trades(m30, h1_way, h4, 5.0, 35.0, 0.6)
    trades["entry_bar_idx"] = pd.to_numeric(trades["entry_bar_idx"], errors="coerce").astype(int)
    trades = attach_context(trades, h4, "4h")

    rows = []
    yearly_rows = []
    for guard in ["none", "G1", "G2", "G3", "G4"]:
        scoped = apply_guards(trades, guard)
        st = replay_improved(scoped, m30_state)
        per = per_trade(st)
        s = summarize(per)
        s["guard"] = guard
        rows.append(s)
        y = {int(k): round(float(g["w"].sum()), 1) for k, g in per.groupby("year", sort=True)}
        y["guard"] = guard
        yearly_rows.append(y)
        print(f"{guard}: n={s['n']} pf={s['pf']:.3f} ev={s['ev']:+.2f} test_pf={s['test_pf']:.3f} "
              f"years={s['pos_years']} 2024={y.get(2024)} 2025={y.get(2025)} 2026={y.get(2026)}")

    pd.DataFrame(rows).to_csv(OUT_DIR / "guard_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(yearly_rows).to_csv(OUT_DIR / "guard_yearly.csv", index=False, encoding="utf-8-sig")
    print(f"\nwrote: {OUT_DIR}")


if __name__ == "__main__":
    main()
