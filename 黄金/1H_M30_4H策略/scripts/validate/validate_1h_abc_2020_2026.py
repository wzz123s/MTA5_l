# -*- coding: utf-8 -*-

"""Cost sensitivity + rolling-window + compounding validation for A+B+C combos.

Data: 1H_M30_4H strategy-dedicated MT5 raw history, 2020-01-02 .. 2026-08-13.
Combos validated (from the combined matrix):
  - ABC_5_35_bias5_0.2  (previously recommended, return-oriented)
  - ABC_5_35_bias5_0.6  (best test-PF on 2020-2026, quality-oriented)
  - ABC_8_28_bias5_0.2  (previously recommended, quality-oriented)
  - ABC_8_28_bias5_0.6  (best PF on 2020-2023, quality-oriented)

Cost model: each stage is its own round trip; a cost of c price-points is
deducted from every stage's pnl (per-trade weighted cost = 3c).
Compounding: $500 start, 3% of current balance risked per trade, stage lots
0.5/1.0/1.5, lot cap [0.01, 10], no compounding of cap effects.
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

import numpy as np
import pandas as pd


SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from experiment_1h_m30_4h_combined_20260813 import (  # noqa: E402
    COMBINED_DIR,
    build_combined_trades,
)
from experiment_1h_m30_4h_variants_20260813 import (  # noqa: E402
    LOT_FOR_REPORT,
    SPEC_5_35,
    SPEC_8_28,
    add_m30_state,
    markdown_table,
    metric,
    replay_three_stage,
    split_test,
    yearly_positive_count,
)
from replay_1h_bias55_h1_stop_optimization import load_frames  # noqa: E402
from replay_1h_way_momentum_filter_scan import add_h1_way_and_momentum  # noqa: E402


OUT_DIR = COMBINED_DIR / "validation_20260814"
START_CAPITAL = 500.0
RISK_PCT = 3.0
STAGE_UNITS = {1: 0.5, 2: 1.0, 3: 1.5}
UNIT_SUM = 3.0
USD_PER_POINT_PER_LOT = 10.0
LOT_MIN = 0.01
LOT_MAX = 10.0
COSTS = [0.0, 0.5, 1.0, 1.5]
ROLLING_MONTHS = [6, 12]

COMBOS = [
    ("ABC_5_35_bias5_0.2", "5-35pt", 0.2, SPEC_5_35),
    ("ABC_5_35_bias5_0.6", "5-35pt", 0.6, SPEC_5_35),
    ("ABC_8_28_bias5_0.2", "8-28pt", 0.2, SPEC_8_28),
    ("ABC_8_28_bias5_0.6", "8-28pt", 0.6, SPEC_8_28),
]


def simulate_compounded(st: pd.DataFrame, cost: float = 0.0, risk_pct: float = RISK_PCT) -> pd.DataFrame:
    """Simulate fixed-risk-per-trade compounding; returns one row per trade."""
    rows = []
    balance = START_CAPITAL
    peak = START_CAPITAL
    max_dd = 0.0
    for (signal_time, dir_), group in st.groupby(["signal_time", "dir"], sort=True):
        entry_balance = balance
        risk_usd = balance * risk_pct / 100.0
        pnl_usd = 0.0
        for _, r in group.iterrows():
            stop_pts = float(r["stop_distance"])
            if stop_pts <= 0 or not np.isfinite(stop_pts):
                continue
            unit_lot = risk_usd / (UNIT_SUM * stop_pts * USD_PER_POINT_PER_LOT)
            unit_lot = float(np.clip(unit_lot, LOT_MIN, LOT_MAX))
            lot = unit_lot * STAGE_UNITS[int(r["stage"])]
            net_points = float(r["stage_pnl"]) - cost
            pnl_usd += lot * net_points * USD_PER_POINT_PER_LOT
        balance += pnl_usd
        peak = max(peak, balance)
        max_dd = max(max_dd, peak - balance)
        rows.append(
            {
                "signal_time": pd.Timestamp(signal_time),
                "dir": dir_,
                "entry_balance": entry_balance,
                "risk_usd": risk_usd,
                "pnl_usd": pnl_usd,
                "balance": balance,
                "peak": peak,
                "max_dd": max_dd,
                "max_dd_pct": max_dd / peak * 100.0 if peak > 0 else 0.0,
            }
        )
    return pd.DataFrame(rows)


def weighted_points_with_cost(st: pd.DataFrame, cost: float) -> pd.Series:
    units = st["stage"].map(STAGE_UNITS)
    return (st["stage_pnl"].astype(float) - cost) * units


def rolling_windows(per: pd.DataFrame, months: int) -> pd.DataFrame:
    scoped = per.copy()
    scoped["ts"] = pd.to_datetime(scoped["signal_time"])
    first = scoped["ts"].min().to_period("M").to_timestamp()
    last = scoped["ts"].max().to_period("M").to_timestamp()
    month_ends = pd.period_range(first, last, freq="M").to_timestamp()
    rows = []
    for end_start in month_ends:
        end_excl = end_start + pd.DateOffset(months=1)
        start = end_excl - pd.DateOffset(months=months)
        group = scoped.loc[(scoped["ts"] >= start) & (scoped["ts"] < end_excl)]
        if group.empty:
            continue
        m = metric(group["stage_pnl_weighted"])
        rows.append(
            {
                "window_months": months,
                "window_start": start.strftime("%Y-%m"),
                "window_end": end_start.strftime("%Y-%m"),
                "n": m["n"],
                "pf": m["pf"],
                "ev": m["ev"],
                "pnl_points": m["pnl"],
            }
        )
    return pd.DataFrame(rows)


def rolling_summary(roll: pd.DataFrame, months: int) -> dict:
    if roll.empty:
        return {}
    worst = roll.sort_values(["pnl_points", "n"], ascending=[True, False]).iloc[0]
    return {
        "window_months": months,
        "windows": int(len(roll)),
        "positive_windows": int((roll["pnl_points"] > 0).sum()),
        "positive_rate": float((roll["pnl_points"] > 0).mean() * 100.0),
        "min_pnl": float(roll["pnl_points"].min()),
        "median_pnl": float(roll["pnl_points"].median()),
        "max_pnl": float(roll["pnl_points"].max()),
        "min_pf": float(roll["pf"].min()),
        "median_pf": float(roll["pf"].median()),
        "worst_window": f"{worst['window_start']}..{worst['window_end']}",
        "worst_window_n": int(worst["n"]),
        "worst_window_pnl": float(worst["pnl_points"]),
    }


def yearly_compounded(equity: pd.DataFrame) -> pd.DataFrame:
    scoped = equity.copy()
    scoped["year"] = pd.to_datetime(scoped["signal_time"]).dt.year
    rows = []
    for year, group in scoped.groupby("year", sort=True):
        rows.append(
            {
                "year": int(year),
                "n": int(len(group)),
                "start_balance": float(group["entry_balance"].iloc[0]),
                "pnl_usd": float(group["pnl_usd"].sum()),
                "end_balance": float(group["balance"].iloc[-1]),
                "year_return_pct": float(group["pnl_usd"].sum() / group["entry_balance"].iloc[0] * 100.0),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    _, m30, h1, contexts = load_frames()
    h4 = contexts["4H"]
    h1_way = add_h1_way_and_momentum(h1)
    m30_state = add_m30_state(m30)

    cost_rows = []
    roll_summary_rows = []
    risk_rows = []
    report_sections = []
    for label, spec_label, bias5_thr, spec in COMBOS:
        trades = build_combined_trades(m30, h1_way, h4, spec[0], spec[1], bias5_thr)
        trades["entry_bar_idx"] = pd.to_numeric(trades["entry_bar_idx"], errors="coerce").astype(int)
        st = replay_three_stage(m30_state, trades)
        st.to_csv(OUT_DIR / f"{label}_stage_ledger.csv", index=False, encoding="utf-8-sig")

        # ---- base metrics (0 cost, fixed-lot weighted points) ----
        pts = weighted_points_with_cost(st, 0.0)
        per = st.copy()
        per["stage_pnl_weighted"] = pts
        per_trade = per.groupby(["signal_time", "dir"], sort=True).agg(
            entry=("entry", "first"),
            stop=("stop", "first"),
            stop_distance=("stop_distance", "first"),
            stage_pnl_sum=("stage_pnl", "sum"),
            stage_pnl_weighted=("stage_pnl_weighted", "sum"),
            mode=("mode", "first"),
        ).reset_index()
        m0 = metric(per_trade["stage_pnl_weighted"])
        test0 = split_test(per_trade, "stage_pnl_weighted")
        pos_years, total_years = yearly_positive_count(per_trade, "stage_pnl_weighted")

        equity0 = simulate_compounded(st, cost=0.0)
        final0 = float(equity0["balance"].iloc[-1])
        maxdd0 = float(equity0["max_dd"].iloc[-1])
        years0 = yearly_compounded(equity0)
        years0.to_csv(OUT_DIR / f"{label}_compounded_yearly.csv", index=False, encoding="utf-8-sig")
        equity0.to_csv(OUT_DIR / f"{label}_equity_curve.csv", index=False, encoding="utf-8-sig")

        report_sections.append(
            f"## {label}（{spec_label}pt，H4 bias5同向≥ {bias5_thr:.1f}%）"
            f"\n\n- 笔数：{m0['n']}（多 {int((per_trade['dir'].astype(str).str.upper() == 'L').sum())} / "
            f"空 {int((per_trade['dir'].astype(str).str.upper() == 'S').sum())}）"
            f"\n- 0成本：WR {m0['wr']:.1f}% / PF {m0['pf']:.2f} / EV {m0['ev']:+.2f}pt / "
            f"样本外PF {test0['test_pf']:.2f} / 正收益年 {pos_years}/{total_years}"
            f"\n- 复利($500起,3%风险,0成本)：终值 ${final0:,.0f} / 最大回撤 ${maxdd0:,.0f}"
            f"\n\n### 复利年度"
            f"\n\n{markdown_table(years0, [str(c) for c in years0.columns])}"
        )

        # ---- cost sensitivity ----
        for cost in COSTS:
            pts_c = weighted_points_with_cost(st, cost)
            per_c = st.copy()
            per_c["stage_pnl_weighted"] = pts_c
            per_trade_c = per_c.groupby(["signal_time", "dir"], sort=True).agg(
                stage_pnl_weighted=("stage_pnl_weighted", "sum"),
            ).reset_index()
            m_c = metric(per_trade_c["stage_pnl_weighted"])
            test_c = split_test(per_trade_c, "stage_pnl_weighted")
            pos_years_c, total_years_c = yearly_positive_count(per_trade_c, "stage_pnl_weighted")
            eq_c = simulate_compounded(st, cost=cost)
            cost_rows.append(
                {
                    "combo": label,
                    "cost_pt_per_stage": cost,
                    "cost_pt_per_trade_roundtrip": cost * UNIT_SUM,
                    "n": m_c["n"],
                    "wr": m_c["wr"],
                    "pf": m_c["pf"],
                    "ev": m_c["ev"],
                    "pnl_points": m_c["pnl"],
                    "test_pf": test_c["test_pf"],
                    "test_ev": test_c["test_ev"],
                    "final_balance_3pct": float(eq_c["balance"].iloc[-1]),
                    "max_dd_3pct": float(eq_c["max_dd"].iloc[-1]),
                    "positive_years": pos_years_c,
                    "total_years": total_years_c,
                }
            )
            report_sections.append(
                f"- 成本 {cost:.1f}pt/段（每笔往返 ≈{cost * UNIT_SUM:.1f}pt）：PF {m_c['pf']:.2f} / "
                f"样本外PF {test_c['test_pf']:.2f} / 复利终值 ${float(eq_c['balance'].iloc[-1]):,.0f} / "
                f"正收益年 {pos_years_c}/{total_years_c}"
            )

        # ---- rolling windows ----
        for months in ROLLING_MONTHS:
            roll = rolling_windows(per_trade, months)
            roll.to_csv(OUT_DIR / f"{label}_rolling_{months}m.csv", index=False, encoding="utf-8-sig")
            rs = rolling_summary(roll, months)
            roll_summary_rows.append({"combo": label, **rs})
            report_sections.append(
                f"- 滚动{months}个月窗口：{rs.get('positive_windows', 0)}/{rs.get('windows', 0)} 个为正 "
                f"({rs.get('positive_rate', 0):.0f}%)，最小窗口收益 {rs.get('min_pnl', 0):+.0f}pt，"
                f"中位 {rs.get('median_pnl', 0):+.0f}pt，最差窗口 {rs.get('worst_window', '')} "
                f"({rs.get('worst_window_n', 0)}笔, {rs.get('worst_window_pnl', 0):+.0f}pt)"
            )

    cost_df = pd.DataFrame(cost_rows)
    roll_df = pd.DataFrame(roll_summary_rows)
    cost_df.to_csv(OUT_DIR / "cost_sensitivity.csv", index=False, encoding="utf-8-sig")
    roll_df.to_csv(OUT_DIR / "rolling_window_summary.csv", index=False, encoding="utf-8-sig")

    # ---- risk-level compounding frontier (0-cost and 1.0pt/stage cost) ----
    risk_levels = [0.5, 1.0, 2.0, 3.0]
    for label, spec_label, bias5_thr, spec in COMBOS:
        trades = build_combined_trades(m30, h1_way, h4, spec[0], spec[1], bias5_thr)
        trades["entry_bar_idx"] = pd.to_numeric(trades["entry_bar_idx"], errors="coerce").astype(int)
        st = replay_three_stage(m30_state, trades)
        for cost in [0.0, 1.0]:
            for risk_pct in risk_levels:
                eq = simulate_compounded(st, cost=cost, risk_pct=risk_pct)
                final = float(eq["balance"].iloc[-1])
                max_dd_usd = float(eq["max_dd"].iloc[-1])
                max_dd_pct = float(eq["max_dd_pct"].iloc[-1])
                risk_rows.append(
                    {
                        "combo": label,
                        "risk_pct_per_trade": risk_pct,
                        "cost_pt_per_stage": cost,
                        "final_balance": final,
                        "total_return_pct": (final / START_CAPITAL - 1.0) * 100.0,
                        "max_dd_usd": max_dd_usd,
                        "max_dd_pct": max_dd_pct,
                    }
                )
    risk_df = pd.DataFrame(risk_rows)
    risk_df.to_csv(OUT_DIR / "compounding_risk_frontier.csv", index=False, encoding="utf-8-sig")

    lines = [
        "# 1H_M30_4H A+B+C 组合验证（2020–2026，成本/滚动窗口/复利）",
        "",
        "> 数据：2020-01-02 ~ 2026-08-13（策略专用 MT5 原始数据）。",
        "> 成本模型：每段为独立往返，成本从每段 pnl 中扣除；每笔交易往返成本 ≈ 3×单段成本。",
        "> 复利：$500 起，每笔 3% 当前余额风险，0.5/1.0/1.5 段位，手数上限 [0.01,10]，未扣点差(0成本行除外)。",
        "",
        "## 成本敏感性（含复利终值）",
        "",
        markdown_table(
            cost_df[
                [
                    "combo", "cost_pt_per_stage", "cost_pt_per_trade_roundtrip", "n", "pf",
                    "test_pf", "ev", "final_balance_3pct", "max_dd_3pct", "positive_years",
                    "total_years",
                ]
            ],
            [
                "combo", "cost_pt_per_stage", "cost_pt_per_trade_roundtrip", "n", "pf",
                "test_pf", "ev", "final_balance_3pct", "max_dd_3pct", "positive_years",
                "total_years",
            ],
            money_cols={"final_balance_3pct", "max_dd_3pct"},
        ),
        "",
        "## 滚动窗口汇总",
        "",
        markdown_table(roll_df, [str(c) for c in roll_df.columns]),
        "",
        "## 复利风险档位前沿（0 成本和 1.0pt/段成本）",
        "",
        markdown_table(
            risk_df[
                ["combo", "risk_pct_per_trade", "cost_pt_per_stage", "final_balance",
                 "total_return_pct", "max_dd_usd", "max_dd_pct"]
            ],
            ["combo", "risk_pct_per_trade", "cost_pt_per_stage", "final_balance",
             "total_return_pct", "max_dd_usd", "max_dd_pct"],
            money_cols={"final_balance", "max_dd_usd"},
        ),
        "",
        "## 各组合详情",
        "",
        "\n\n".join(report_sections),
        "",
        "## 输出文件",
        "",
        "- `cost_sensitivity.csv`",
        "- `rolling_window_summary.csv`",
        "- `compounding_risk_frontier.csv`",
        "- `*_compounded_yearly.csv` / `*_equity_curve.csv` / `*_rolling_6m.csv` / `*_rolling_12m.csv` / `*_stage_ledger.csv`",
    ]
    (OUT_DIR / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("=" * 80)
    print("Compounding risk frontier (0-cost)")
    print(risk_df[risk_df["cost_pt_per_stage"].eq(0.0)][
        ["combo", "risk_pct_per_trade", "final_balance", "max_dd_pct"]
    ].to_string(index=False))
    print("=" * 80)
    print("Cost sensitivity (compounded $500, 3% risk)")
    print(cost_df[["combo", "cost_pt_per_stage", "pf", "test_pf", "final_balance_3pct", "max_dd_3pct"]].to_string(index=False))
    print("=" * 80)
    print("Rolling windows")
    print(roll_df[["combo", "window_months", "windows", "positive_rate", "min_pnl", "median_pnl", "worst_window"]].to_string(index=False))
    print(f"\nWrote report: {OUT_DIR / 'validation_report.md'}")


if __name__ == "__main__":
    main()
