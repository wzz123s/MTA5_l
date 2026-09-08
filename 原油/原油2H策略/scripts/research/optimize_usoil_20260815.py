# -*- coding: utf-8 -*-
"""Single-position exit + percent-stop variants for the three USOIL strategies.

Motivation: the 3-stage exit pays ~3x cost and oil per-trade EV is ~1pt.
This test uses the single-position replay (stop-first, else opposite M30
cross next-open) already embedded in the signal builders, and scans:
  - absolute stop specs (0.5-3.5 / 1-5 / 2-8 price units)
  - percent-of-entry stop specs (0.05-0.5% / 0.1-1.0% / 0.2-2.0%)
Cost is a single round trip per trade.
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

from combined_abc_usoil_20260815 import (  # noqa: E402
    CONFIGS,
    build_1h_oil,
    build_1h_trades,
    build_2h_trades,
    build_30m2h_trades,
    markdown_table,
)


COSTS = [0.0, 0.5, 1.0, 1.5]
ABS_SPECS = [(0.5, 3.5), (1.0, 5.0), (2.0, 8.0)]
PCT_SPECS = [(0.05, 0.5), (0.1, 1.0), (0.2, 2.0)]


def single_metrics(pnl: pd.Series) -> dict:
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    gw = wins.sum()
    gl = abs(losses.sum())
    pf = gw / gl if gl > 0 else (999.0 if gw > 0 else 0.0)
    return {
        "n": int(len(pnl)),
        "wr": float((pnl > 0).mean() * 100.0),
        "pf": float(pf),
        "ev": float(pnl.mean()),
        "pnl": float(pnl.sum()),
    }


def test_split_pf(pnl: pd.Series, ts: pd.Series) -> float:
    df = pd.DataFrame({"ts": ts, "pnl": pnl}).sort_values("ts").reset_index(drop=True)
    cutoff_idx = min(max(int(len(df) * 0.70), 1), len(df) - 1)
    cutoff = df.loc[cutoff_idx, "ts"]
    test = df.loc[df["ts"] >= cutoff, "pnl"]
    tw = test[test > 0]
    tl = test[test < 0]
    return float((tw.sum() / abs(tl.sum())) if abs(tl.sum()) > 0 else (999.0 if tw.sum() > 0 else 0.0))


def apply_pct_spec(trades: pd.DataFrame, lo_pct: float, hi_pct: float) -> pd.DataFrame:
    pct = pd.to_numeric(trades["stop_distance"], errors="coerce") / pd.to_numeric(trades["entry"], errors="coerce") * 100.0
    return trades.loc[pct.between(lo_pct, hi_pct)].copy().reset_index(drop=True)


def build_variants(name: str):
    cfg = CONFIGS[name]
    out = []
    if cfg["kind"] == "1h":
        m30, h1, h4 = build_1h_oil(cfg)
        for bias5 in [0.2, 0.4]:
            for spec_lo, spec_hi in ABS_SPECS:
                t = build_1h_trades(m30, h1, h4, spec_lo, spec_hi, bias5)
                out.append((f"abs_{spec_lo:g}-{spec_hi:g}", bias5, t))
            t_wide = build_1h_trades(m30, h1, h4, 0.05, 10.0, bias5)
            for lo, hi in PCT_SPECS:
                out.append((f"pct_{lo:g}-{hi:g}%", bias5, apply_pct_spec(t_wide, lo, hi)))
    elif cfg["kind"] == "2h":
        for bias5 in [0.0, 0.4]:
            for spec_lo, spec_hi in ABS_SPECS:
                t, _ = build_2h_trades(cfg, spec_lo, spec_hi, bias5)
                out.append((f"abs_{spec_lo:g}-{spec_hi:g}", bias5, t))
            t_wide, _ = build_2h_trades(cfg, 0.05, 10.0, bias5)
            for lo, hi in PCT_SPECS:
                out.append((f"pct_{lo:g}-{hi:g}%", bias5, apply_pct_spec(t_wide, lo, hi)))
    else:
        for bias5 in [0.0, 0.6]:
            for spec_lo, spec_hi in ABS_SPECS:
                t, _ = build_30m2h_trades(cfg, spec_lo, spec_hi, bias5)
                out.append((f"abs_{spec_lo:g}-{spec_hi:g}", bias5, t))
            t_wide, _ = build_30m2h_trades(cfg, 0.05, 10.0, bias5)
            for lo, hi in PCT_SPECS:
                out.append((f"pct_{lo:g}-{hi:g}%", bias5, apply_pct_spec(t_wide, lo, hi)))
    return out


def main() -> None:
    for name, cfg in CONFIGS.items():
        out_dir = cfg["dir"] / "data" / "validation" / "experiments_20260815" / "single_position"
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n==== {name} single-position ====")
        rows = []
        for label, bias5, trades in build_variants(name):
            pnl = pd.to_numeric(trades["pnl_points"], errors="coerce")
            ts = pd.to_datetime(trades["signal_time"])
            if len(pnl) < 30:
                continue
            base = single_metrics(pnl)
            year_sum = pd.DataFrame({"ts": ts, "pnl": pnl}).assign(y=ts.dt.year).groupby("y")["pnl"].sum()
            cost_row = {"variant": f"{label}|bias5={bias5:.1f}", "n": base["n"], "pf0": base["pf"],
                        "ev0": base["ev"], "test_pf0": test_split_pf(pnl, ts),
                        "pos_years": f"{int((year_sum > 0).sum())}/{len(year_sum)}"}
            for cost in COSTS[1:]:
                m = single_metrics(pnl - cost)
                cost_row[f"pf_{cost:g}"] = m["pf"]
                cost_row[f"test_pf_{cost:g}"] = test_split_pf(pnl - cost, ts)
            rows.append(cost_row)
            print(
                f"  {cost_row['variant']}: n={base['n']} pf0={base['pf']:.3f} ev0={base['ev']:+.2f} "
                f"test0={cost_row['test_pf0']:.3f} pf1.0={cost_row['pf_1']:.3f} "
                f"test1.0={cost_row['test_pf_1']:.3f} years={cost_row['pos_years']}"
            )
        df = pd.DataFrame(rows)
        df.to_csv(out_dir / "single_position_matrix.csv", index=False, encoding="utf-8-sig")
        if not df.empty:
            sc = df.copy()
            sc["_score"] = sc["pos_years"].str.split("/").str[0].astype(int) * 1000.0 + sc["test_pf_1"] * 10.0 + sc["pf_1"] * 5.0
            best = sc.sort_values(["_score", "test_pf_1", "pf_1"], ascending=[False, False, False]).iloc[0]
            print(f"  >> best single-position: {best['variant']} pf1.0={best['pf_1']:.3f} test1.0={best['test_pf_1']:.3f}")
            cols = ["variant", "n", "pf0", "ev0", "test_pf0", "pf_0.5", "test_pf_0.5", "pf_1", "test_pf_1", "pf_1.5", "test_pf_1.5", "pos_years"]
            (out_dir / "single_position_report.md").write_text(
                f"# {name} 单段退出 + 百分比止损变体\n\n"
                + markdown_table(df[cols], cols)
                + "\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    main()
