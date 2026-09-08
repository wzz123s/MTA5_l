# -*- coding: utf-8 -*-
"""A+B+C combined validation for the three USOIL strategies (2020-2026).

Same chain as the gold trio, with oil-appropriate stop spec scans:
  USOIL_1H_M30_4H : 4H pool + H4 bias5 same-side + 1H bias5&13 -> 3-opp -> 3-stage
  USOIL_2H_M30_6H : 6H bias5>0 + bias55>0 -> 3-opp -> 3-stage
  USOIL_30m2H     : |H2 bias55|>3% + |H2 bias5| same-sign -> 3-opp -> 3-stage
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


ROOT = Path(r"F:\use_code\MTA5_l")
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from combined_abc_30m2h_2h_20260814 import (  # noqa: E402
    STRATS as GOLD_STRATS,
    add_m30_state,
    attach_context,
    build_combo as build_combo_generic,
    build_three_opportunities,
    load_strategy as load_strategy_generic,
    markdown_table,
    metric,
    replay_three_stage,
    replay_signals,
    split_test,
    yearly_positive_count,
)
from experiment_1h_m30_4h_variants_20260813 import (  # noqa: E402
    attach_side_extreme,
    pool_mask,
    third_filter_mask,
)
from replay_1h_way_momentum_filter_scan import add_h1_way_and_momentum  # noqa: E402
from replay_raw_signals_with_stops import (  # noqa: E402
    add_indicators,
    manifest_file,
    manifest_timeframe,
    read_json,
    standardize_mt5_csv,
)


STAGE_UNITS = {1: 0.5, 2: 1.0, 3: 1.5}
OIL_SPECS = [(0.5, 3.5), (1.0, 5.0), (2.0, 8.0)]

CONFIGS = {
    "USOIL_1H_M30_4H": {
        "dir": ROOT / "原油" / "USOIL_1H_M30_4H策略",
        "kind": "1h",
        "specs": OIL_SPECS,
        "bias5_grid": [0.2, 0.4, 0.6],
    },
    "USOIL_2H_M30_6H": {
        "dir": ROOT / "原油" / "USOIL_2H_M30_6H策略",
        "kind": "2h",
        "specs": OIL_SPECS,
        "bias5_grid": [0.0, 0.2, 0.4],
    },
    "USOIL_30m2H": {
        "dir": ROOT / "原油" / "USOIL_30m2H策略",
        "kind": "30m2h",
        "specs": OIL_SPECS,
        "bias5_grid": [0.0, 0.2, 0.4, 0.6],
    },
}


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


def build_1h_oil(cfg):
    manifest = read_json(cfg["dir"] / "data" / "raw" / "raw_source_manifest.json")
    m30 = add_indicators(standardize_mt5_csv(manifest_file(manifest, "M30"), "30M", closed_time=False))
    h1 = add_indicators(standardize_mt5_csv(manifest_file(manifest, "H1"), "1H", closed_time=True))
    h4 = add_indicators(standardize_mt5_csv(manifest_file(manifest, "H4"), "4H", closed_time=True))
    return m30, h1, h4


def build_1h_trades(m30, h1, h4, spec_lo, spec_hi, bias5_thr):
    h1_way = add_h1_way_and_momentum(h1)
    sig = build_three_opportunities(m30, spec_lo=spec_lo, spec_hi=spec_hi)
    replayed = replay_signals(sig, m30)
    enriched = attach_side_extreme(replayed, h1_way, h4)
    enriched["entry_bar_idx"] = pd.to_numeric(enriched["entry_bar_idx"], errors="coerce").astype(int)
    mask = pool_mask(enriched) & third_filter_mask(enriched)
    if bias5_thr > 0:
        b5 = pd.to_numeric(enriched["side_extreme_bias5_h4sma_pct"], errors="coerce")
        side = enriched["dir"].astype(str).str.upper()
        mask &= (side.eq("S") & b5.ge(bias5_thr)) | (side.eq("L") & b5.le(-bias5_thr))
    return enriched.loc[mask].copy().reset_index(drop=True)


def build_2h_trades(cfg, spec_lo, spec_hi, bias5_thr):
    gc = {
        "strategy_dir": cfg["dir"],
        "gate_tf": "H6",
        "gate_type": "bias5_55_pos",
        "c_tf": "H6",
        "preferred": None,
    }
    m30, gate_tf = load_strategy_generic(gc)
    m30_state = add_m30_state(m30)
    sig = build_three_opportunities(m30, spec_lo=spec_lo, spec_hi=spec_hi)
    replayed = replay_signals(sig, m30)
    enriched = attach_context(replayed, gate_tf, "h6")
    trades = build_combo_generic(enriched, gc, bias5_thr)
    return trades, m30_state


def build_30m2h_trades(cfg, spec_lo, spec_hi, bias5_thr):
    gc = {
        "strategy_dir": cfg["dir"],
        "gate_tf": "H2",
        "gate_type": "abs_bias55_gt_3",
        "c_tf": "H2",
        "preferred": None,
    }
    m30, gate_tf = load_strategy_generic(gc)
    m30_state = add_m30_state(m30)
    sig = build_three_opportunities(m30, spec_lo=spec_lo, spec_hi=spec_hi)
    replayed = replay_signals(sig, m30)
    enriched = attach_context(replayed, gate_tf, "h2")
    trades = build_combo_generic(enriched, gc, bias5_thr)
    return trades, m30_state


def main() -> None:
    for name, cfg in CONFIGS.items():
        out_dir = cfg["dir"] / "data" / "validation" / "experiments_20260815" / "combined_abc"
        out_dir.mkdir(parents=True, exist_ok=True)
        rows = []
        st_cache = {}
        print(f"\n==== {name} ====")
        for spec_lo, spec_hi in cfg["specs"]:
            for bias5_thr in cfg["bias5_grid"]:
                if cfg["kind"] == "1h":
                    m30, h1, h4 = build_1h_oil(cfg)
                    trades = build_1h_trades(m30, h1, h4, spec_lo, spec_hi, bias5_thr)
                    m30_state = add_m30_state(m30)
                elif cfg["kind"] == "2h":
                    trades, m30_state = build_2h_trades(cfg, spec_lo, spec_hi, bias5_thr)
                else:
                    trades, m30_state = build_30m2h_trades(cfg, spec_lo, spec_hi, bias5_thr)
                st = replay_three_stage(m30_state, trades)
                per = per_trade(st)
                s = summarize(per)
                s.update(
                    {
                        "spec": f"{spec_lo:g}-{spec_hi:g}",
                        "bias5_thr": bias5_thr,
                        "cost1_test_pf": cost_test_pf(st, 1.0),
                    }
                )
                rows.append(s)
                st_cache[(spec_lo, spec_hi, bias5_thr)] = st
                print(
                    f"  spec={s['spec']} bias5>={bias5_thr:.1f}: n={s['n']} pf={s['pf']:.3f} "
                    f"ev={s['ev']:+.2f} test_pf={s['test_pf']:.3f} cost1={s['cost1_test_pf']:.3f} "
                    f"years={s['pos_years']}"
                )
        df = pd.DataFrame(rows)
        df.to_csv(out_dir / "combined_matrix.csv", index=False, encoding="utf-8-sig")

        # recommended: robust score = years*1000 + test_pf*10 + pf*5 + ev*0.05, n>=30
        qual = df[df["n"] >= 30]
        sc = qual.copy()
        sc["_score"] = (
            sc["pos_years"].str.split("/").str[0].astype(int) * 1000.0
            + sc["test_pf"] * 10.0
            + sc["pf"] * 5.0
            + sc["ev"] * 0.05
        )
        rec = sc.sort_values(["_score", "test_pf", "pf"], ascending=[False, False, False]).iloc[0]
        rec_st = st_cache[(float(rec["spec"].split("-")[0]), float(rec["spec"].split("-")[1]), float(rec["bias5_thr"]))]
        per_rec = per_trade(rec_st)
        print(f"  >> recommended: spec={rec['spec']} bias5>={rec['bias5_thr']:.1f} "
              f"n={rec['n']} pf={rec['pf']:.3f} test_pf={rec['test_pf']:.3f}")
        rec.to_frame().T.to_csv(out_dir / "recommended_row.csv", index=False, encoding="utf-8-sig")

        year_rows = []
        for year, g in per_rec.groupby("year", sort=True):
            m = metric(g["w"])
            year_rows.append({"year": int(year), "n": m["n"], "pf": m["pf"], "ev": m["ev"], "pnl": m["pnl"]})
        year_df = pd.DataFrame(year_rows)
        year_df.to_csv(out_dir / "recommended_yearly.csv", index=False, encoding="utf-8-sig")
        print("  yearly:", {int(r["year"]): round(r["pnl"], 1) for r in year_rows})

        lines = [
            f"# {name} A+B+C 组合验证（2020-2026，USOILm）",
            "",
            "> 链路与黄金三策略一致；止损规格为原油适配扫描（价格单位）。",
            "",
            "## 组合矩阵",
            "",
            markdown_table(df[["spec", "bias5_thr", "n", "wr", "pf", "ev", "pnl_points",
                               "test_pf", "cost1_test_pf", "pos_years"]],
                           ["spec", "bias5_thr", "n", "wr", "pf", "ev", "pnl_points",
                            "test_pf", "cost1_test_pf", "pos_years"]),
            "",
            f"## 推荐组合：{rec['spec']}pt / bias5≥{rec['bias5_thr']:.1f}%",
            "",
            "### 分年",
            "",
            markdown_table(year_df, [str(c) for c in year_df.columns]),
        ]
        (out_dir / "combined_abc_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  wrote: {out_dir / 'combined_abc_report.md'}")


if __name__ == "__main__":
    main()
