# -*- coding: utf-8 -*-

"""Walk-forward validation + weak-period diagnostics for 1H_M30_4H A+B+C.

Walk-forward:
  Fold 1: train 2020-01..2023-12, test 2024-01..2026-08
  Fold 2: train 2020-01..2022-12, test 2023-01..2026-08
  Combo grid: stop spec {5-35, 8-28} x H4 bias5 threshold {0.0..0.8}
  Selection uses TRAIN-PERIOD metrics only (n>=50, score = PF + EV + years).

Weak-period diagnostics focus on the recommended combo (5-35pt, bias5>=0.6%):
  year x mode x direction x stop/bias stats, stage PnL and exit reasons.
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

import numpy as np
import pandas as pd


SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from experiment_1h_m30_4h_combined_20260813 import build_combined_trades  # noqa: E402
from experiment_1h_m30_4h_variants_20260813 import (  # noqa: E402
    SPEC_5_35,
    SPEC_8_28,
    add_m30_state,
    attach_side_extreme,
    build_three_opportunities,
    markdown_table,
    metric,
    pool_mask,
    replay_three_stage,
    replay_signals,
    third_filter_mask,
)
from replay_1h_bias55_h1_stop_optimization import load_frames  # noqa: E402
from replay_1h_way_momentum_filter_scan import add_h1_way_and_momentum  # noqa: E402


OUT_DIR = (
    Path(r"F:\use_code\MTA5_l\黄金\1H_M30_4H策略\data\validation\experiments_20260813")
    / "combined_20260813"
    / "validation_20260814"
    / "walkforward_weak"
)
STAGE_UNITS = {1: 0.5, 2: 1.0, 3: 1.5}
GRID_SPECS = [("5_35", SPEC_5_35), ("8_28", SPEC_8_28)]
BIAS5_GRID = [0.0, 0.2, 0.4, 0.6, 0.8]
FOLDS = [
    ("2020-2023", 2023),
    ("2020-2022", 2022),
]
RECOMMENDED = ("5_35", 0.6)


def build_enriched(m30, h1_way, h4, spec_lo, spec_hi):
    sig = build_three_opportunities(m30, spec_lo=spec_lo, spec_hi=spec_hi)
    replayed = replay_signals(sig, m30)
    enriched = attach_side_extreme(replayed, h1_way, h4)
    enriched["entry_bar_idx"] = pd.to_numeric(enriched["entry_bar_idx"], errors="coerce").astype(int)
    return enriched


def gate(enriched: pd.DataFrame, bias5_thr: float) -> pd.DataFrame:
    mask = pool_mask(enriched) & third_filter_mask(enriched)
    if bias5_thr > 0:
        bias5 = pd.to_numeric(enriched["side_extreme_bias5_h4sma_pct"], errors="coerce")
        side = enriched["dir"].astype(str).str.upper()
        mask &= (side.eq("S") & bias5.ge(bias5_thr)) | (side.eq("L") & bias5.le(-bias5_thr))
    return enriched.loc[mask].copy().reset_index(drop=True)


def per_trade_points(st: pd.DataFrame) -> pd.DataFrame:
    st = st.copy()
    st["w"] = st["stage_pnl"].astype(float) * st["stage"].map(STAGE_UNITS)
    per = st.groupby(["signal_time", "dir"], sort=True).agg(
        ts=("signal_time", "first"),
        w=("w", "sum"),
        stop=("stop_distance", "first"),
        mode=("mode", "first"),
        entry=("entry", "first"),
    ).reset_index()
    per["ts"] = pd.to_datetime(per["ts"])
    per["year"] = per["ts"].dt.year
    return per


def score_train(per: pd.DataFrame) -> float:
    m = metric(per["w"])
    if m["n"] < 50:
        return -1e9
    pos_years = int((per.groupby("year")["w"].sum() > 0).sum())
    return m["pf"] * 10.0 + m["ev"] * 0.1 + pos_years * 2.0 + min(m["n"], 300) * 0.01


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _, m30, h1, contexts = load_frames()
    h4 = contexts["4H"]
    h1_way = add_h1_way_and_momentum(h1)
    m30_state = add_m30_state(m30)

    # ---- build per-combo trade sets once ----
    cache: dict[tuple[str, float], pd.DataFrame] = {}
    enriched_by_spec: dict[str, pd.DataFrame] = {}
    for spec_name, spec in GRID_SPECS:
        enriched_by_spec[spec_name] = build_enriched(m30, h1_way, h4, spec[0], spec[1])
    for spec_name, _ in GRID_SPECS:
        for bias5_thr in BIAS5_GRID:
            cache[(spec_name, bias5_thr)] = gate(enriched_by_spec[spec_name], bias5_thr)

    # ---- walk-forward ----
    fold_rows = []
    pick_rows = []
    for fold_label, train_end_year in FOLDS:
        train_masks = {}
        test_masks = {}
        for key, trades in cache.items():
            per = per_trade_points(replay_three_stage(m30_state, trades))
            train_masks[key] = per["ts"].dt.year <= train_end_year
            test_masks[key] = ~train_masks[key]
        best_key = None
        best_score = -1e9
        for key in cache:
            per = per_trade_points(replay_three_stage(m30_state, cache[key]))
            train = per.loc[per["ts"].dt.year <= train_end_year]
            sc = score_train(train)
            if sc > best_score:
                best_score = sc
                best_key = key
        spec_name, bias5_thr = best_key
        train_per = per_trade_points(replay_three_stage(m30_state, cache[best_key]))
        train = train_per.loc[train_per["ts"].dt.year <= train_end_year]
        test = train_per.loc[train_per["ts"].dt.year > train_end_year]
        m_tr = metric(train["w"])
        m_te = metric(test["w"])
        pos_years_tr = int((train.groupby("year")["w"].sum() > 0).sum())
        pos_years_te = int((test.groupby("year")["w"].sum() > 0).sum())
        fold_rows.append(
            {
                "fold": fold_label,
                "train_range": f"2020-{train_end_year}",
                "test_range": f"{train_end_year + 1}-2026",
                "picked_combo": f"{spec_name}_bias5_{bias5_thr:.1f}",
                "train_n": m_tr["n"],
                "train_pf": m_tr["pf"],
                "train_ev": m_tr["ev"],
                "train_pos_years": f"{pos_years_tr}/4",
                "test_n": m_te["n"],
                "test_pf": m_te["pf"],
                "test_ev": m_te["ev"],
                "test_pnl": m_te["pnl"],
                "test_pos_years": f"{pos_years_te}/{len(test['year'].unique())}",
            }
        )
        # pre-specified recommended combo on the same split
        rec_per = per_trade_points(replay_three_stage(m30_state, cache[RECOMMENDED]))
        rec_test = rec_per.loc[rec_per["ts"].dt.year > train_end_year]
        rec_m = metric(rec_test["w"])
        rec_pos = int((rec_test.groupby("year")["w"].sum() > 0).sum())
        pick_rows.append(
            {
                "fold": fold_label,
                "combo": "5_35_bias5_0.6 (pre-specified)",
                "test_n": rec_m["n"],
                "test_pf": rec_m["pf"],
                "test_ev": rec_m["ev"],
                "test_pnl": rec_m["pnl"],
                "test_pos_years": f"{rec_pos}/{len(rec_test['year'].unique())}",
            }
        )
        print(
            f"[{fold_label}] picked={best_key} train_pf={m_tr['pf']:.3f} "
            f"test_n={m_te['n']} test_pf={m_te['pf']:.3f} test_ev={m_te['ev']:+.2f}"
        )
        print(
            f"[{fold_label}] pre-specified 5_35/0.6 test_n={rec_m['n']} "
            f"test_pf={rec_m['pf']:.3f} test_ev={rec_m['ev']:+.2f}"
        )
    fold_df = pd.DataFrame(fold_rows)
    pick_df = pd.DataFrame(pick_rows)
    fold_df.to_csv(OUT_DIR / "walkforward_folds.csv", index=False, encoding="utf-8-sig")
    pick_df.to_csv(OUT_DIR / "walkforward_prespecified.csv", index=False, encoding="utf-8-sig")

    # ---- weak-period diagnostics on the recommended combo ----
    rec_trades = cache[RECOMMENDED]
    rec_st = replay_three_stage(m30_state, rec_trades)
    rec_per = per_trade_points(rec_st)
    year_rows = []
    for year, g in rec_per.groupby("year", sort=True):
        m = metric(g["w"])
        side = g["dir"].astype(str).str.upper()
        st_y = rec_st[rec_st["signal_time"].dt.year == year]
        stage_pnl = st_y.groupby("stage")["stage_pnl"].sum().to_dict()
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
                "avg_stop": float(g["stop"].mean()),
                "stage1_pnl": float(stage_pnl.get(1, 0.0)),
                "stage2_pnl": float(stage_pnl.get(2, 0.0)),
                "stage3_pnl": float(stage_pnl.get(3, 0.0)),
            }
        )
    year_df = pd.DataFrame(year_rows)
    year_df.to_csv(OUT_DIR / "recommended_yearly_detail.csv", index=False, encoding="utf-8-sig")

    mode_year_rows = []
    for year in [2024, 2025, 2026]:
        for mode, g in rec_per.loc[rec_per["year"] == year].groupby("mode"):
            m = metric(g["w"])
            mode_year_rows.append(
                {
                    "year": int(year),
                    "mode": mode,
                    "n": m["n"],
                    "wr": m["wr"],
                    "pf": m["pf"],
                    "ev": m["ev"],
                    "pnl": m["pnl"],
                }
            )
    mode_year_df = pd.DataFrame(mode_year_rows)
    mode_year_df.to_csv(OUT_DIR / "recommended_mode_by_year.csv", index=False, encoding="utf-8-sig")

    # filter-value profiles per year
    rec_enriched = cache[RECOMMENDED]
    prof_rows = []
    for year, g in rec_enriched.groupby(pd.to_datetime(rec_enriched["signal_time"]).dt.year, sort=True):
        prof_rows.append(
            {
                "year": int(year),
                "n": int(len(g)),
                "avg_bias55_abs": float(
                    pd.to_numeric(g["side_extreme_bias55_h4sma_pct"], errors="coerce").abs().mean()
                ),
                "avg_bias5_abs": float(
                    pd.to_numeric(g["side_extreme_bias5_h4sma_pct"], errors="coerce").abs().mean()
                ),
                "avg_stop": float(pd.to_numeric(g["stop_distance"], errors="coerce").mean()),
            }
        )
    prof_df = pd.DataFrame(prof_rows)
    prof_df.to_csv(OUT_DIR / "recommended_filter_profile_by_year.csv", index=False, encoding="utf-8-sig")

    lines = [
        "# 1H_M30_4H A+B+C Walk-forward 与弱段诊断（2020–2026）",
        "",
        "> 推荐组合：5-35pt + H4 bias5同向≥0.6% + 三段退出 + 3%风险固定余额口径。",
        "",
        "## Walk-forward",
        "",
        "### 按训练期自动挑选的组合",
        "",
        markdown_table(fold_df, [str(c) for c in fold_df.columns]),
        "",
        "### 预先指定组合（5_35/0.6）在同一划分下的样本外表现",
        "",
        markdown_table(pick_df, [str(c) for c in pick_df.columns]),
        "",
        "## 推荐组合年度明细",
        "",
        markdown_table(year_df, [str(c) for c in year_df.columns]),
        "",
        "## 推荐组合 2024/2025/2026 模式拆解",
        "",
        markdown_table(mode_year_df, [str(c) for c in mode_year_df.columns]),
        "",
        "## 推荐组合过滤特征年度画像",
        "",
        markdown_table(prof_df, [str(c) for c in prof_df.columns]),
        "",
        "## 输出文件",
        "",
        "- `walkforward_folds.csv` / `walkforward_prespecified.csv`",
        "- `recommended_yearly_detail.csv` / `recommended_mode_by_year.csv` / `recommended_filter_profile_by_year.csv`",
    ]
    (OUT_DIR / "walkforward_weak_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote report: {OUT_DIR / 'walkforward_weak_report.md'}")


if __name__ == "__main__":
    main()
