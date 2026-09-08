# -*- coding: utf-8 -*-
"""Full validation for improved 1H candidates (2020-2026).

Candidates:
  IMP  : drop post_n5/n6 + Stage1 1.5R (no guard)
  IMPG4: same + reject SELL when H4 SMMA5 > SMMA13 (uptrend veto)
Checks: walk-forward (two folds) + 6M/12M rolling windows + cost 1.0pt/stage.
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
from optimize_1h_guard_20260815 import apply_guards, per_trade  # noqa: E402
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


def cal_pf(per: pd.DataFrame, year_from: int) -> float:
    vals = per.loc[per["year"] >= year_from, "w"]
    tw = vals[vals > 0]
    tl = vals[vals < 0]
    return float((tw.sum() / abs(tl.sum())) if abs(tl.sum()) > 0 else (999.0 if tw.sum() > 0 else 0.0))


def rolling(per: pd.DataFrame, months: int) -> pd.DataFrame:
    scoped = per.sort_values("ts").reset_index(drop=True)
    first = scoped["ts"].min().to_period("M").to_timestamp()
    last = scoped["ts"].max().to_period("M").to_timestamp()
    month_ends = pd.period_range(first, last, freq="M").to_timestamp()
    rows = []
    for end_start in month_ends:
        end_excl = end_start + pd.DateOffset(months=1)
        start = end_excl - pd.DateOffset(months=months)
        g = scoped.loc[(scoped["ts"] >= start) & (scoped["ts"] < end_excl)]
        if g.empty:
            continue
        vals = g["w"]
        tw = vals[vals > 0]
        tl = vals[vals < 0]
        rows.append(
            {
                "window_start": start.strftime("%Y-%m"),
                "window_end": end_start.strftime("%Y-%m"),
                "n": int(len(vals)),
                "pf": float((tw.sum() / abs(tl.sum())) if abs(tl.sum()) > 0 else 999.0),
                "pnl": float(vals.sum()),
            }
        )
    return pd.DataFrame(rows)


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
    trades = attach_context(trades, h4, "4h")

    summary_rows = []
    for name, guard in [("IMP", "none"), ("IMPG4", "G4")]:
        scoped = apply_guards(trades, guard)
        st = replay_improved(scoped, m30_state)
        per = per_trade(st)
        row = {
            "variant": name,
            "n": int(len(per)),
            "pf": float((lambda a, b: a / b if b > 0 else 999.0)(per["w"][per["w"] > 0].sum(), abs(per["w"][per["w"] < 0].sum()))),
            "ev": float(per["w"].mean()),
            "wf_2024_2026_pf": cal_pf(per, 2024),
            "wf_2023_2026_pf": cal_pf(per, 2023),
            "cost1_test_pf": cost_test_pf(st, 1.0),
        }
        for months in [6, 12]:
            roll = rolling(per, months)
            row[f"roll{months}_positive_rate"] = float((roll["pnl"] > 0).mean() * 100.0)
            row[f"roll{months}_min"] = float(roll["pnl"].min())
            row[f"roll{months}_median"] = float(roll["pnl"].median())
        summary_rows.append(row)
        print(row)

    df = pd.DataFrame(summary_rows)
    df.to_csv(OUT_DIR / "improved_validation.csv", index=False, encoding="utf-8-sig")
    print(f"\nwrote: {OUT_DIR / 'improved_validation.csv'}")


if __name__ == "__main__":
    main()
