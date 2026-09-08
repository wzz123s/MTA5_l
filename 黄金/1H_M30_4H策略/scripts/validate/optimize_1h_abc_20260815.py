# -*- coding: utf-8 -*-

"""Offline optimization tests for the 1H_M30_4H recommended combo.

Baseline: 5-35pt, H4 bias5>=0.6%, three opportunities, segment SMA13 stops,
three-stage exit 2.0R / 1.5R trail + 4.0R / M30 merged cross.

Variants target known weak points:
  A. drop post_n5
  B. drop post_n5 + post_n6
  C. Stage1 1.5R (was 2.0R)
  D. B + C combined
  E. B + C + H4 bias5>=0.8%
Metrics: n / PF / EV / OOS(last-30%) PF / positive years / yearly detail
and cost check at 1.0pt per stage.
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


OUT_DIR = (
    Path(r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\data\validation\experiments_20260813")
    / "combined_20260813"
    / "validation_20260814"
    / "optimize_1h_20260815"
)
STAGE_UNITS = {1: 0.5, 2: 1.0, 3: 1.5}


def weighted(st: pd.DataFrame) -> pd.Series:
    return st["stage_pnl"].astype(float) * st["stage"].map(STAGE_UNITS)


def per_trade(st: pd.DataFrame) -> pd.DataFrame:
    st = st.copy()
    st["w"] = weighted(st)
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
    def cal_pf(mask):
        vals = per.loc[mask, "w"]
        tw = vals[vals > 0]
        tl = vals[vals < 0]
        return float((tw.sum() / abs(tl.sum())) if abs(tl.sum()) > 0 else (999.0 if tw.sum() > 0 else 0.0))
    return {
        "n": int(len(vals)),
        "wr": float((vals > 0).mean() * 100.0),
        "pf": float(pf),
        "ev": float(vals.mean()),
        "pnl_points": float(vals.sum()),
        "test_pf": float(test_pf),
        "cal_test_2024_2026_pf": cal_pf(per["year"] >= 2024),
        "cal_test_2023_2026_pf": cal_pf(per["year"] >= 2023),
        "pos_years": f"{int((years > 0).sum())}/{len(years)}",
    }


def yearly(per: pd.DataFrame) -> dict:
    return {int(y): round(float(g["w"].sum()), 1) for y, g in per.groupby("year", sort=True)}


def run_variant(trades: pd.DataFrame, m30_state, *, drop_modes: set[str], stage1_r: float) -> pd.DataFrame:
    scoped = trades[~trades["mode"].isin(drop_modes)].copy().reset_index(drop=True)
    v.STAGE1_R = stage1_r
    try:
        st = v.replay_three_stage(m30_state, scoped)
    finally:
        v.STAGE1_R = 2.0
    return st


def cost_test_pf(st: pd.DataFrame, cost: float = 1.0) -> float:
    st = st.copy()
    st["w"] = (st["stage_pnl"].astype(float) - cost) * st["stage"].map(STAGE_UNITS)
    per = st.groupby(["signal_time", "dir"], sort=True)["w"].sum().reset_index()
    per = per.sort_values("signal_time").reset_index(drop=True)
    cutoff_idx = min(max(int(len(per) * 0.70), 1), len(per) - 1)
    cutoff = per.loc[cutoff_idx, "signal_time"]
    test = per.loc[per["signal_time"] >= cutoff, "w"]
    tw = test[test > 0]
    tl = test[test < 0]
    return float((tw.sum() / abs(tl.sum())) if abs(tl.sum()) > 0 else (999.0 if tw.sum() > 0 else 0.0))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _, m30, h1, contexts = load_frames()
    h4 = contexts["4H"]
    h1_way = add_h1_way_and_momentum(h1)
    m30_state = v.add_m30_state(m30)
    trades = build_combined_trades(m30, h1_way, h4, 5.0, 35.0, 0.6)
    trades["entry_bar_idx"] = pd.to_numeric(trades["entry_bar_idx"], errors="coerce").astype(int)

    variants = [
        ("baseline", set(), 2.0),
        ("drop_post_n5", {"post_n5"}, 2.0),
        ("drop_post_n5_n6", {"post_n5", "post_n6"}, 2.0),
        ("stage1_1.5R", set(), 1.5),
        ("drop_pn56_stage1_1.5R", {"post_n5", "post_n6"}, 1.5),
    ]
    rows = []
    yearly_rows = []
    for name, drop_modes, stage1_r in variants:
        st = run_variant(trades, m30_state, drop_modes=drop_modes, stage1_r=stage1_r)
        per = per_trade(st)
        s = summarize(per)
        s["variant"] = name
        s["cost1_test_pf"] = cost_test_pf(st, 1.0)
        rows.append(s)
        y = yearly(per)
        y["variant"] = name
        yearly_rows.append(y)
        print(f"{name}: n={s['n']} pf={s['pf']:.3f} ev={s['ev']:+.2f} test_pf={s['test_pf']:.3f} "
              f"cal24_26={s['cal_test_2024_2026_pf']:.3f} cost1_test_pf={s['cost1_test_pf']:.3f} "
              f"years={s['pos_years']} "
              f"2024={y.get(2024)} 2025={y.get(2025)} 2026={y.get(2026)}")

    df = pd.DataFrame(rows)
    ydf = pd.DataFrame(yearly_rows)
    df.to_csv(OUT_DIR / "variant_summary.csv", index=False, encoding="utf-8-sig")
    ydf.to_csv(OUT_DIR / "variant_yearly.csv", index=False, encoding="utf-8-sig")
    print(f"\nwrote: {OUT_DIR}")


if __name__ == "__main__":
    main()
