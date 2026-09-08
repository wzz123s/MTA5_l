# -*- coding: utf-8 -*-

"""1H_M30_4H combined experiment: Variant A + B + C (2026-08-13).

Chain under test:
  A. Entry: pre_cross / cross / post_n(2-6), previous-segment SMA13 extreme
     stops (post_n uses current-bar SMA13), entry at next M30 open.
  Gate: 4H side-extreme pool (bias55 >= 2.0%) + 1H bias5&13 signed > 0.
  C. H4 bias5 same-direction filter (scanned: 0.0 / 0.2 / 0.4 / 0.6 / 0.8).
  B. Exit: three-stage 2.0R / 1.5R trail + 4.0R force / M30 merged cross,
     stop spec [5,35] or [8,28] pt, position sizing = 3% balance risk with
     0.5/1.0/1.5 stage units (fixed $500 balance, no compounding).

Regression check: bias5 threshold 0.0 + spec 5-35 must reproduce the earlier
B2 result (458 trades, PF 1.7102, $1,718.78, test PF 2.1854).
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)


from pathlib import Path
import sys

import pandas as pd


SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from experiment_1h_m30_4h_variants_20260813 import (  # noqa: E402
    LOT_FOR_REPORT,
    OUT_DIR,
    SPEC_5_35,
    SPEC_8_28,
    add_m30_state,
    attach_side_extreme,
    build_three_opportunities,
    markdown_table,
    metric,
    per_trade_from_stages,
    pool_mask,
    replay_three_stage,
    replay_signals,
    split_test,
    summarize_trades,
    third_filter_mask,
    yearly_positive_count,
)
from replay_1h_bias55_h1_stop_optimization import load_frames  # noqa: E402
from replay_1h_way_momentum_filter_scan import add_h1_way_and_momentum  # noqa: E402


COMBINED_DIR = OUT_DIR / "combined_20260813"
BIAS5_THRESHOLDS = [0.0, 0.2, 0.4, 0.6, 0.8]
SPECS = [
    ("5_35", SPEC_5_35),
    ("8_28", SPEC_8_28),
]


def build_combined_trades(m30, h1_way, h4, spec_lo, spec_hi, bias5_thr):
    sig = build_three_opportunities(m30, spec_lo=spec_lo, spec_hi=spec_hi)
    replayed = replay_signals(sig, m30)
    enriched_a = attach_side_extreme(replayed, h1_way, h4)
    mask = pool_mask(enriched_a) & third_filter_mask(enriched_a)
    if bias5_thr is not None and bias5_thr > 0:
        bias5 = pd.to_numeric(enriched_a["side_extreme_bias5_h4sma_pct"], errors="coerce")
        side = enriched_a["dir"].astype(str).str.upper()
        mask &= (side.eq("S") & bias5.ge(bias5_thr)) | (side.eq("L") & bias5.le(-bias5_thr))
    return enriched_a.loc[mask].copy().reset_index(drop=True)


def combined_row(trades, m30_state, *, label, desc) -> dict:
    st = replay_three_stage(m30_state, trades)
    per = per_trade_from_stages(st)
    m = metric(per["stage_pnl_weighted"])
    test = split_test(per, "stage_pnl_weighted")
    pos_years, total_years = yearly_positive_count(per, "stage_pnl_weighted")
    side = per["dir"].astype(str).str.upper()
    return {
        "label": label,
        "desc": desc,
        "n": m["n"],
        "long_n": int(side.eq("L").sum()),
        "short_n": int(side.eq("S").sum()),
        "wr": m["wr"],
        "pf": m["pf"],
        "ev": m["ev"],
        "pnl_points": m["pnl"],
        "pnl_usd_dynamic": float(per["pnl_usd_dynamic"].sum()),
        "test_pf": test["test_pf"],
        "test_ev": test["test_ev"],
        "test_n": test["test_n"],
        "losing_trades": int((per["stage_pnl_sum"] < 0).sum()),
        "losing_rate": float((per["stage_pnl_sum"] < 0).mean() * 100.0) if len(per) else 0.0,
        "avg_stop": float(pd.to_numeric(per["stop_distance"], errors="coerce").mean()) if len(per) else 0.0,
        "positive_years": pos_years,
        "total_years": total_years,
    }


def main() -> None:
    COMBINED_DIR.mkdir(parents=True, exist_ok=True)
    _, m30, h1, contexts = load_frames()
    h4 = contexts["4H"]
    h1_way = add_h1_way_and_momentum(h1)
    m30_state = add_m30_state(m30)

    rows = []
    best_candidate: tuple[dict, pd.DataFrame] | None = None
    for spec_name, spec in SPECS:
        for bias5_thr in BIAS5_THRESHOLDS:
            trades = build_combined_trades(m30, h1_way, h4, spec[0], spec[1], bias5_thr)
            trades["entry_bar_idx"] = pd.to_numeric(trades["entry_bar_idx"], errors="coerce").astype(int)
            if bias5_thr == 0.0:
                thr_desc = "不加bias5过滤"
            else:
                thr_desc = f"H4 bias5同向>= {bias5_thr:.1f}%"
            row = combined_row(
                trades,
                m30_state,
                label=f"ABC_{spec_name}_bias5_{bias5_thr:.1f}",
                desc=f"A+B+C: 三机会+段SMA13止损 [{spec[0]:.0f}-{spec[1]:.0f}]pt + 三段退出+3%风险 + {thr_desc}",
            )
            rows.append(row)
            st = replay_three_stage(m30_state, trades)
            st.to_csv(COMBINED_DIR / f"{row['label']}_stage_ledger.csv", index=False, encoding="utf-8-sig")
            print(
                f"{row['label']}: n={row['n']} pf={row['pf']:.4f} ev={row['ev']:.2f} "
                f"usd3pct={row['pnl_usd_dynamic']:.2f} test_pf={row['test_pf']:.4f}"
            )
            # track best by score: sample ok + test_pf + pnl
            if row["n"] >= 30 and row["test_pf"] >= 1.0 and (best_candidate is None or row["pnl_usd_dynamic"] > best_candidate[0]["pnl_usd_dynamic"]):
                best_candidate = (row, trades.copy())

    summary = pd.DataFrame(rows)
    summary.to_csv(COMBINED_DIR / "combined_summary.csv", index=False, encoding="utf-8-sig")

    # ---- best candidate deep dive ----
    best_row, best_trades = best_candidate if best_candidate is not None else (rows[0], None)
    assert best_trades is not None
    st_best = replay_three_stage(m30_state, best_trades)
    per_best = per_trade_from_stages(st_best)
    per_best["year"] = pd.to_datetime(per_best["signal_time"]).dt.year
    yearly = per_best.groupby("year", sort=True)["stage_pnl_weighted"].agg(
        lambda v: (len(v), float((v > 0).mean() * 100.0), float(v.sum()), float(v.mean()))
    )
    yearly_df = pd.DataFrame(
        [
            {"year": int(y), "n": r[0], "wr": r[1], "pnl_weighted_pts": r[2], "ev": r[3]}
            for y, r in yearly.items()
        ]
    )
    yearly_df.to_csv(COMBINED_DIR / "best_combo_yearly.csv", index=False, encoding="utf-8-sig")

    mode_rows = []
    for mode, g in st_best.groupby("mode"):
        mm = metric(g["stage_pnl"])
        mode_rows.append({"mode": mode, **mm})
    mode_split = pd.DataFrame(mode_rows)
    mode_split.to_csv(COMBINED_DIR / "best_combo_mode_split.csv", index=False, encoding="utf-8-sig")

    reason_split = st_best.groupby("stage")["stage_reason"].value_counts().rename("n").reset_index()
    reason_split.to_csv(COMBINED_DIR / "best_combo_exit_reasons.csv", index=False, encoding="utf-8-sig")

    cols = [
        "label", "n", "long_n", "short_n", "wr", "pf", "ev", "pnl_points",
        "pnl_usd_dynamic", "test_pf", "test_ev", "test_n", "losing_trades",
        "losing_rate", "avg_stop", "positive_years", "total_years", "desc",
    ]
    lines = [
        "# 1H_M30_4H A+B+C 组合测试（2026-08-13）",
        "",
        "> 链路：三机会入场(pre_cross/cross/post_n) + 段SMA13极值止损 + 4H机会池(bias55≥2%) + 1H bias5&13 > 0 + "
        "H4 bias5同向过滤(扫描) + 三段退出(2.0R/1.5R trail+4.0R/合并段反向) + 3%余额风险动态手数(0.5/1.0/1.5)。",
        "> 收益口径：pnl_usd_dynamic = 固定 $500 余额、单笔 3% 风险、不复利；points 为 0.5/1.0/1.5 加权点数。",
        "",
        "## 组合矩阵",
        "",
        markdown_table(summary[cols], [str(c) for c in cols], money_cols={"pnl_usd_dynamic"}),
        "",
        "## 推荐组合年度拆分",
        "",
        f"推荐组合：`{best_row['label']}`（{best_row['desc']}）",
        "",
        markdown_table(yearly_df, [str(c) for c in yearly_df.columns]),
        "",
        "## 推荐组合模式拆解",
        "",
        markdown_table(mode_split, [str(c) for c in mode_split.columns]),
        "",
        "## 推荐组合出场原因分布",
        "",
        markdown_table(reason_split, [str(c) for c in reason_split.columns]),
        "",
        "## 输出文件",
        "",
        "- `combined_summary.csv`",
        "- `best_combo_yearly.csv` / `best_combo_mode_split.csv` / `best_combo_exit_reasons.csv`",
        "- `*_stage_ledger.csv`（每个组合的三段逐笔台账）",
    ]
    report = "\n".join(lines) + "\n"
    (COMBINED_DIR / "combined_report.md").write_text(report, encoding="utf-8")
    print(f"\nBest combo: {best_row['label']} -> {best_row['desc']}")
    print(f"Wrote report: {COMBINED_DIR / 'combined_report.md'}")


if __name__ == "__main__":
    main()
