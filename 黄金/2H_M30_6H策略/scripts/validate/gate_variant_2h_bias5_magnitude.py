# -*- coding: utf-8 -*-

"""Test replacing the 2H_M30_6H pool gate with a 6H bias5 magnitude filter.

Current gate: 6H bias5+13+55 signed > 0 (all three on the trade side).
Proposed variants:
  V1 bias5-only : 6H bias5 signed >= thr        (drop bias13/bias55 direction)
  V2 bias5+55   : 6H bias5 signed >= thr AND 6H bias55 signed > 0 (keep trend side)
Reference: current gate with no magnitude filter.

Rest of the chain is fixed (same as the recommended combo):
  5-35pt, three opportunities, segment SMA13 stops, three-stage exit.
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

from combined_abc_30m2h_2h_20260814 import (  # noqa: E402
    STRATS,
    add_m30_state,
    attach_context,
    build_three_opportunities,
    load_strategy,
    markdown_table,
    metric,
    replay_signals,
    replay_three_stage,
    split_test,
    yearly_positive_count,
)


OUT_DIR = (
    Path(r"F:\use_code\MTA5_l\黄金\2H_M30_6H策略\data\validation\experiments_20260814")
    / "combined_abc"
    / "gate_variant_bias5_magnitude"
)
STAGE_UNITS = {1: 0.5, 2: 1.0, 3: 1.5}
THRESHOLDS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]


def weighted_points(st: pd.DataFrame) -> pd.Series:
    return st["stage_pnl"].astype(float) * st["stage"].map(STAGE_UNITS)


def per_trade(st: pd.DataFrame) -> pd.DataFrame:
    st = st.copy()
    st["w"] = weighted_points(st)
    per = st.groupby(["signal_time", "dir"], sort=True).agg(
        ts=("signal_time", "first"),
        w=("w", "sum"),
        stop=("stop_distance", "first"),
        mode=("mode", "first"),
    ).reset_index()
    per["ts"] = pd.to_datetime(per["ts"])
    per["year"] = per["ts"].dt.year
    return per


def summarize(st: pd.DataFrame) -> dict:
    per = per_trade(st)
    m = metric(per["w"])
    test = split_test(per, "w")
    pos_years, total_years = yearly_positive_count(per, "w")
    side = per["dir"].astype(str).str.upper()
    return {
        "n": m["n"],
        "long_n": int(side.eq("L").sum()),
        "short_n": int(side.eq("S").sum()),
        "wr": m["wr"],
        "pf": m["pf"],
        "ev": m["ev"],
        "pnl_points": m["pnl"],
        "test_pf": test["test_pf"],
        "test_ev": test["test_ev"],
        "positive_years": pos_years,
        "total_years": total_years,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cfg = STRATS["2H_M30_6H"]
    m30, gate_tf = load_strategy(cfg)
    m30_state = add_m30_state(m30)
    sig = build_three_opportunities(m30, spec_lo=5.0, spec_hi=35.0)
    replayed = replay_signals(sig, m30)
    enriched = attach_context(replayed, gate_tf, "h6")
    enriched["entry_bar_idx"] = pd.to_numeric(enriched["entry_bar_idx"], errors="coerce").astype(int)

    b5 = pd.to_numeric(enriched["h6_bias5_signed_pct"], errors="coerce")
    b13 = pd.to_numeric(enriched["h6_bias13_signed_pct"], errors="coerce")
    b55 = pd.to_numeric(enriched["h6_bias55_signed_pct"], errors="coerce")
    year_ok = pd.to_datetime(enriched["signal_time"]).dt.year.ge(2020)
    full_gate = (b5 > 0) & (b13 > 0) & (b55 > 0) & year_ok

    rows = []
    st_cache = {}
    # reference: current gate, no magnitude
    trades_ref = enriched.loc[full_gate].copy().reset_index(drop=True)
    st_ref = replay_three_stage(m30_state, trades_ref)
    st_cache[("full_gate", None)] = st_ref
    rows.append({"variant": "full_gate(bias5+13+55>0)", "thr": None, **summarize(st_ref)})

    for thr in THRESHOLDS:
        mask_v1 = year_ok & b5.ge(thr)
        trades_v1 = enriched.loc[mask_v1].copy().reset_index(drop=True)
        st_v1 = replay_three_stage(m30_state, trades_v1)
        st_cache[("bias5_only", thr)] = st_v1
        rows.append({"variant": "bias5_only", "thr": thr, **summarize(st_v1)})

        mask_v2 = year_ok & b5.ge(thr) & b55.gt(0)
        trades_v2 = enriched.loc[mask_v2].copy().reset_index(drop=True)
        st_v2 = replay_three_stage(m30_state, trades_v2)
        st_cache[("bias5_55", thr)] = st_v2
        rows.append({"variant": "bias5+bias55", "thr": thr, **summarize(st_v2)})

    summary = pd.DataFrame(rows)
    summary.to_csv(OUT_DIR / "gate_variant_summary.csv", index=False, encoding="utf-8-sig")
    print(summary[["variant", "thr", "n", "long_n", "short_n", "wr", "pf", "ev",
                   "pnl_points", "test_pf", "positive_years", "total_years"]].to_string(index=False))

    # walk-forward for the best bias5-only variant and reference
    wf_rows = []
    for label, key in [("full_gate_ref", ("full_gate", None)),
                       ("bias5_only_0.2", ("bias5_only", 0.2)),
                       ("bias5_only_0.4", ("bias5_only", 0.4)),
                       ("bias5_55_0.2", ("bias5_55", 0.2))]:
        st = st_cache[key]
        per = per_trade(st)
        for train_end in [2023, 2022]:
            train = per[per["year"] <= train_end]
            test = per[per["year"] > train_end]
            if len(train) < 50 or len(test) == 0:
                continue
            m_tr = metric(train["w"])
            m_te = metric(test["w"])
            wf_rows.append(
                {
                    "variant": label,
                    "train": f"2020-{train_end}",
                    "test": f"{train_end + 1}-2026",
                    "train_n": m_tr["n"],
                    "train_pf": m_tr["pf"],
                    "test_n": m_te["n"],
                    "test_pf": m_te["pf"],
                    "test_ev": m_te["ev"],
                    "test_pos_years": f"{int((test.groupby('year')['w'].sum() > 0).sum())}/{len(test['year'].unique())}",
                }
            )
    wf = pd.DataFrame(wf_rows)
    wf.to_csv(OUT_DIR / "gate_variant_walkforward.csv", index=False, encoding="utf-8-sig")
    print("\nwalk-forward:")
    print(wf.to_string(index=False))

    # yearly detail for bias5-only 0.2 (if exists) and full gate
    yearly_sections = []
    for label, key in [
        ("full_gate_ref", ("full_gate", None)),
        ("bias5_only_0.0", ("bias5_only", 0.0)),
        ("bias5_55_0.0", ("bias5_55", 0.0)),
    ]:
        per = per_trade(st_cache[key])
        year_rows = []
        for year, g in per.groupby("year", sort=True):
            m = metric(g["w"])
            side = g["dir"].astype(str).str.upper()
            year_rows.append(
                {
                    "year": int(year),
                    "n": m["n"],
                    "long_n": int(side.eq("L").sum()),
                    "short_n": int(side.eq("S").sum()),
                    "wr": m["wr"],
                    "pf": m["pf"],
                    "ev": m["ev"],
                    "pnl_points": m["pnl"],
                }
            )
        yearly_df = pd.DataFrame(year_rows)
        yearly_df.to_csv(OUT_DIR / f"{label}_yearly.csv", index=False, encoding="utf-8-sig")
        yearly_sections.append(f"### {label} 分年\n\n{markdown_table(yearly_df, [str(c) for c in yearly_df.columns])}")

    lines = [
        "# 2H_M30_6H 门控变体：6H bias5 幅度过滤替代 bias5+13+55 全同向门",
        "",
        "> 固定链路：5-35pt + 三机会 + 段SMA13止损 + 三段退出（与推荐组合一致）。",
        "> bias5_only = 仅要求 6H bias5 signed ≥ thr（去掉 bias13/bias55 方向约束）；",
        "> bias5+55 = 保留 bias55 signed > 0 方向，再加 bias5 幅度。",
        "",
        "## 汇总",
        "",
        markdown_table(
            summary[["variant", "thr", "n", "long_n", "short_n", "wr", "pf", "ev",
                     "pnl_points", "test_pf", "positive_years", "total_years"]],
            ["variant", "thr", "n", "long_n", "short_n", "wr", "pf", "ev",
             "pnl_points", "test_pf", "positive_years", "total_years"],
        ),
        "",
        "## Walk-forward",
        "",
        markdown_table(wf, [str(c) for c in wf.columns]),
        "",
        *yearly_sections,
    ]
    (OUT_DIR / "gate_variant_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nreport: {OUT_DIR / 'gate_variant_report.md'}")


if __name__ == "__main__":
    main()
