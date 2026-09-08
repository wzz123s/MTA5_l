# -*- coding: utf-8 -*-
"""Robustness validation for selected 1H_M30_4H candidates.

The input is the enriched trade file produced by
replay_1h_way_momentum_filter_scan.py. This script does not rebuild signals;
it validates the already replayed trades by month, side, cost stress, and
rolling calendar windows.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from replay_raw_signals_with_stops import LOT_FOR_REPORT, ROOT, markdown_table, metric, split_test
from replay_1h_way_momentum_filter_scan import BASE_CANDIDATES, OUT_DIR, candidate_mask, side_extreme_opportunity_mask


DATE_LABEL = "2026-07-26"
INPUT_PATH = OUT_DIR / "way_momentum_enriched_trades.csv"
OUT_DIR_ROBUST = OUT_DIR.parent / "way_momentum_robustness"
ROOT_REPORT = ROOT / "1H_M30_4H稳健性验证结论.md"
USD_PER_POINT_001 = 100.0 * LOT_FOR_REPORT
COST_POINTS = [0.0, 0.2, 0.5, 0.8, 1.0, 1.5, 2.0, 3.0]
ROLLING_WINDOWS_MONTHS = [3, 6, 12]


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    base_candidate: str
    filter_desc: str
    use_close_momentum: bool = False
    close_momentum_min: float | None = None
    use_way_le: float | None = None
    use_way_ge: float | None = None
    short_vol_way_le: float | None = None
    short_way_ge: float | None = None


CANDIDATES = [
    CandidateSpec(
        name="fd1_8_28_side_pool_base",
        base_candidate="fd1_h1last6_8_28",
        filter_desc="fixed_delay_1 + H1 last6 stop + 8-28pt + side-extreme pool",
    ),
    CandidateSpec(
        name="fd1_8_28_side_pool_close_mom_ge_-0.4",
        base_candidate="fd1_h1last6_8_28",
        filter_desc="8-28pt base + close momentum signed >= -0.4",
        use_close_momentum=True,
        close_momentum_min=-0.4,
    ),
    CandidateSpec(
        name="fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7",
        base_candidate="fd1_h1last6_8_28",
        filter_desc="8-28pt base + close momentum signed >= -0.4 + SHORT vol_way_s_way <= 0.7",
        use_close_momentum=True,
        close_momentum_min=-0.4,
        short_vol_way_le=0.7,
    ),
    CandidateSpec(
        name="fd1_8_28_side_pool_close_mom_ge_-0.4__short_way_ge_0.3",
        base_candidate="fd1_h1last6_8_28",
        filter_desc="8-28pt base + close momentum signed >= -0.4 + SHORT way_s_way >= 0.3",
        use_close_momentum=True,
        close_momentum_min=-0.4,
        short_way_ge=0.3,
    ),
    CandidateSpec(
        name="fd1_8_28_side_pool_way_le_0.6",
        base_candidate="fd1_h1last6_8_28",
        filter_desc="8-28pt base + side extreme way_s_way <= 0.6",
        use_way_le=0.6,
    ),
    CandidateSpec(
        name="fd1_6_28_side_pool_base",
        base_candidate="fd1_h1last6_6_28",
        filter_desc="fixed_delay_1 + H1 last6 stop + 6-28pt + side-extreme pool",
    ),
    CandidateSpec(
        name="fd1_6_28_side_pool_close_mom_ge_-0.4",
        base_candidate="fd1_h1last6_6_28",
        filter_desc="6-28pt base + close momentum signed >= -0.4",
        use_close_momentum=True,
        close_momentum_min=-0.4,
    ),
    CandidateSpec(
        name="fd3_6_28_side_pool_base",
        base_candidate="fd3_m30sma13_6_28",
        filter_desc="fixed_delay_3 + M30 SMA13 stop + 6-28pt + side-extreme pool",
    ),
]


def read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def candidate_cfg(name: str) -> dict:
    for cfg in BASE_CANDIDATES:
        if str(cfg["candidate"]) == name:
            return cfg
    raise KeyError(f"Unknown base candidate: {name}")


def select_candidate(frame: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    cfg = candidate_cfg(spec.base_candidate)
    mask = candidate_mask(frame, cfg) & side_extreme_opportunity_mask(frame)
    if spec.use_close_momentum:
        close_mom = pd.to_numeric(frame["side_extreme_close_momentum_signed_pct"], errors="coerce")
        mask &= close_mom.ge(float(spec.close_momentum_min))
    if spec.use_way_le is not None:
        way = pd.to_numeric(frame["side_extreme_way_s_way"], errors="coerce")
        mask &= way.le(float(spec.use_way_le))
    if spec.use_way_ge is not None:
        way = pd.to_numeric(frame["side_extreme_way_s_way"], errors="coerce")
        mask &= way.ge(float(spec.use_way_ge))
    short_side = frame["dir"].astype(str).str.upper().eq("S")
    if spec.short_vol_way_le is not None:
        vol_way = pd.to_numeric(frame["side_extreme_vol_way_s_way"], errors="coerce")
        mask &= (~short_side) | vol_way.le(float(spec.short_vol_way_le))
    if spec.short_way_ge is not None:
        way = pd.to_numeric(frame["side_extreme_way_s_way"], errors="coerce")
        mask &= (~short_side) | way.ge(float(spec.short_way_ge))
    out = frame.loc[mask].copy().sort_values("entry_time").reset_index(drop=True)
    out["candidate"] = spec.name
    out["candidate_desc"] = spec.filter_desc
    return out


def as_money(points: float) -> float:
    return float(points) * USD_PER_POINT_001


def max_drawdown(values: pd.Series) -> float:
    vals = pd.to_numeric(values, errors="coerce").fillna(0.0)
    if vals.empty:
        return 0.0
    equity = vals.cumsum()
    peak = equity.cummax()
    dd = peak - equity
    return float(dd.max())


def positive_group_count(frame: pd.DataFrame, value_col: str, freq: str) -> tuple[int, int]:
    if frame.empty:
        return 0, 0
    scoped = frame.copy()
    scoped["bucket"] = pd.to_datetime(scoped["entry_time"]).dt.to_period(freq).astype(str)
    grouped = scoped.groupby("bucket")[value_col].sum()
    return int((grouped > 0).sum()), int(len(grouped))


def summarize_candidate(frame: pd.DataFrame, spec: CandidateSpec) -> dict:
    m = metric(frame["pnl_points"])
    test = split_test(frame, "pnl_points")
    pos_years, total_years = positive_group_count(frame, "pnl_points", "Y")
    pos_months, total_months = positive_group_count(frame, "pnl_points", "M")
    side = frame["dir"].astype(str).str.upper()
    stop_dist = pd.to_numeric(frame["stop_distance"], errors="coerce")
    test_pnl_usd = as_money(float(test["test_pnl"]))
    return {
        "candidate": spec.name,
        "base_candidate": spec.base_candidate,
        "desc": spec.filter_desc,
        "n": m["n"],
        "long_n": int(side.eq("L").sum()),
        "short_n": int(side.eq("S").sum()),
        "wr_pct": m["wr"],
        "pf": m["pf"],
        "ev_points": m["ev"],
        "pnl_points": m["pnl"],
        "pnl_usd_001": as_money(m["pnl"]),
        "max_loss_streak": m["maxcl"],
        "max_drawdown_points": max_drawdown(frame["pnl_points"]),
        "max_drawdown_usd_001": as_money(max_drawdown(frame["pnl_points"])),
        "stop_hits": int(frame["stop_hit"].sum()) if "stop_hit" in frame.columns else 0,
        "stop_hit_rate_pct": float(frame["stop_hit"].mean() * 100.0) if len(frame) else 0.0,
        "avg_stop_distance": float(stop_dist.mean()) if len(frame) else 0.0,
        "median_stop_distance": float(stop_dist.median()) if len(frame) else 0.0,
        "breakeven_cost_points_per_trade": float(m["pnl"] / m["n"]) if m["n"] else 0.0,
        "split_date": test["split_date"],
        "test_n": test["test_n"],
        "test_pf": test["test_pf"],
        "test_ev_points": test["test_ev"],
        "test_pnl_points": test["test_pnl"],
        "test_pnl_usd_001": test_pnl_usd,
        "positive_years": pos_years,
        "total_years": total_years,
        "positive_months": pos_months,
        "total_months": total_months,
    }


def build_overall(selected: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    spec_by_name = {spec.name: spec for spec in CANDIDATES}
    for name, frame in selected.items():
        rows.append(summarize_candidate(frame, spec_by_name[name]))
    return pd.DataFrame(rows)


def build_monthly(selected: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, frame in selected.items():
        if frame.empty:
            continue
        scoped = frame.copy()
        scoped["month"] = pd.to_datetime(scoped["entry_time"]).dt.to_period("M").astype(str)
        for month, group in scoped.groupby("month", sort=True):
            m = metric(group["pnl_points"])
            side = group["dir"].astype(str).str.upper()
            rows.append(
                {
                    "candidate": name,
                    "month": month,
                    "n": m["n"],
                    "long_n": int(side.eq("L").sum()),
                    "short_n": int(side.eq("S").sum()),
                    "pf": m["pf"],
                    "ev_points": m["ev"],
                    "pnl_points": m["pnl"],
                    "pnl_usd_001": as_money(m["pnl"]),
                    "stop_hit_rate_pct": float(group["stop_hit"].mean() * 100.0) if len(group) else 0.0,
                }
            )
    return pd.DataFrame(rows)


def build_yearly(selected: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, frame in selected.items():
        if frame.empty:
            continue
        scoped = frame.copy()
        scoped["year"] = pd.to_datetime(scoped["entry_time"]).dt.year
        for year, group in scoped.groupby("year", sort=True):
            m = metric(group["pnl_points"])
            side = group["dir"].astype(str).str.upper()
            rows.append(
                {
                    "candidate": name,
                    "year": int(year),
                    "n": m["n"],
                    "long_n": int(side.eq("L").sum()),
                    "short_n": int(side.eq("S").sum()),
                    "pf": m["pf"],
                    "ev_points": m["ev"],
                    "pnl_points": m["pnl"],
                    "pnl_usd_001": as_money(m["pnl"]),
                    "stop_hit_rate_pct": float(group["stop_hit"].mean() * 100.0) if len(group) else 0.0,
                }
            )
    return pd.DataFrame(rows)


def build_side_summary(selected: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, frame in selected.items():
        if frame.empty:
            continue
        for side_name, group in frame.groupby(frame["dir"].astype(str).str.upper(), sort=True):
            m = metric(group["pnl_points"])
            pos_years, total_years = positive_group_count(group, "pnl_points", "Y")
            pos_months, total_months = positive_group_count(group, "pnl_points", "M")
            rows.append(
                {
                    "candidate": name,
                    "dir": side_name,
                    "n": m["n"],
                    "wr_pct": m["wr"],
                    "pf": m["pf"],
                    "ev_points": m["ev"],
                    "pnl_points": m["pnl"],
                    "pnl_usd_001": as_money(m["pnl"]),
                    "max_loss_streak": m["maxcl"],
                    "positive_years": pos_years,
                    "total_years": total_years,
                    "positive_months": pos_months,
                    "total_months": total_months,
                }
            )
    return pd.DataFrame(rows)


def build_cost_yearly(selected: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, frame in selected.items():
        if frame.empty:
            continue
        for cost in COST_POINTS:
            scoped = frame.copy()
            scoped["year"] = pd.to_datetime(scoped["entry_time"]).dt.year
            scoped["pnl_points_net"] = pd.to_numeric(scoped["pnl_points"], errors="coerce") - cost
            for year, group in scoped.groupby("year", sort=True):
                m = metric(group["pnl_points_net"])
                rows.append(
                    {
                        "candidate": name,
                        "round_trip_cost_points": cost,
                        "year": int(year),
                        "n": m["n"],
                        "pf": m["pf"],
                        "ev_points": m["ev"],
                        "pnl_points": m["pnl"],
                        "pnl_usd_001": as_money(m["pnl"]),
                    }
                )
    return pd.DataFrame(rows)


def build_cost_sensitivity(selected: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for name, frame in selected.items():
        for cost in COST_POINTS:
            scoped = frame.copy()
            scoped["pnl_points_net"] = pd.to_numeric(scoped["pnl_points"], errors="coerce") - cost
            m = metric(scoped["pnl_points_net"])
            test = split_test(scoped, "pnl_points_net")
            pos_years, total_years = positive_group_count(scoped, "pnl_points_net", "Y")
            pos_months, total_months = positive_group_count(scoped, "pnl_points_net", "M")
            rows.append(
                {
                    "candidate": name,
                    "round_trip_cost_points": cost,
                    "round_trip_cost_usd_001": as_money(cost),
                    "n": m["n"],
                    "pf": m["pf"],
                    "ev_points": m["ev"],
                    "pnl_points": m["pnl"],
                    "pnl_usd_001": as_money(m["pnl"]),
                    "test_pf": test["test_pf"],
                    "test_pnl_usd_001": as_money(float(test["test_pnl"])),
                    "positive_years": pos_years,
                    "total_years": total_years,
                    "positive_months": pos_months,
                    "total_months": total_months,
                    "max_drawdown_points": max_drawdown(scoped["pnl_points_net"]),
                }
            )
    return pd.DataFrame(rows)


def rolling_windows_for_candidate(name: str, frame: pd.DataFrame, months: int) -> list[dict]:
    if frame.empty:
        return []
    scoped = frame.copy()
    scoped["entry_time"] = pd.to_datetime(scoped["entry_time"])
    first_month = scoped["entry_time"].min().to_period("M").to_timestamp()
    last_month = scoped["entry_time"].max().to_period("M").to_timestamp()
    month_ends = pd.period_range(first_month, last_month, freq="M").to_timestamp()
    rows = []
    for end_start in month_ends:
        end_exclusive = end_start + pd.DateOffset(months=1)
        start = end_exclusive - pd.DateOffset(months=months)
        group = scoped.loc[(scoped["entry_time"] >= start) & (scoped["entry_time"] < end_exclusive)].copy()
        if group.empty:
            continue
        m = metric(group["pnl_points"])
        rows.append(
            {
                "candidate": name,
                "window_months": months,
                "window_start": start.strftime("%Y-%m"),
                "window_end": end_start.strftime("%Y-%m"),
                "n": m["n"],
                "pf": m["pf"],
                "ev_points": m["ev"],
                "pnl_points": m["pnl"],
                "pnl_usd_001": as_money(m["pnl"]),
            }
        )
    return rows


def build_rolling_windows(selected: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    window_rows = []
    summary_rows = []
    for name, frame in selected.items():
        for months in ROLLING_WINDOWS_MONTHS:
            rows = rolling_windows_for_candidate(name, frame, months)
            window_rows.extend(rows)
            if not rows:
                continue
            scoped = pd.DataFrame(rows)
            worst = scoped.sort_values(["pnl_points", "n"], ascending=[True, False]).iloc[0]
            summary_rows.append(
                {
                    "candidate": name,
                    "window_months": months,
                    "windows": int(len(scoped)),
                    "positive_windows": int((scoped["pnl_points"] > 0).sum()),
                    "positive_window_rate_pct": float((scoped["pnl_points"] > 0).mean() * 100.0),
                    "min_pnl_points": float(scoped["pnl_points"].min()),
                    "median_pnl_points": float(scoped["pnl_points"].median()),
                    "max_pnl_points": float(scoped["pnl_points"].max()),
                    "min_pf": float(scoped["pf"].min()),
                    "median_pf": float(scoped["pf"].median()),
                    "worst_window_start": worst["window_start"],
                    "worst_window_end": worst["window_end"],
                    "worst_window_n": int(worst["n"]),
                    "worst_window_pnl_usd_001": as_money(float(worst["pnl_points"])),
                }
            )
    return pd.DataFrame(window_rows), pd.DataFrame(summary_rows)


def top_negative_months(monthly: pd.DataFrame, candidate: str, limit: int = 8) -> pd.DataFrame:
    scoped = monthly.loc[monthly["candidate"].eq(candidate)].copy()
    return scoped.sort_values(["pnl_points", "n"], ascending=[True, False]).head(limit)


def make_report(
    overall: pd.DataFrame,
    yearly: pd.DataFrame,
    monthly: pd.DataFrame,
    side_summary: pd.DataFrame,
    cost: pd.DataFrame,
    cost_yearly: pd.DataFrame,
    rolling_summary: pd.DataFrame,
) -> str:
    overall_cols = [
        "candidate",
        "n",
        "long_n",
        "short_n",
        "pf",
        "test_pf",
        "pnl_usd_001",
        "test_pnl_usd_001",
        "positive_years",
        "total_years",
        "positive_months",
        "total_months",
        "max_drawdown_usd_001",
        "breakeven_cost_points_per_trade",
    ]
    side_cols = ["candidate", "dir", "n", "pf", "pnl_usd_001", "positive_years", "total_years", "positive_months", "total_months"]
    yearly_cols = ["candidate", "year", "n", "long_n", "short_n", "pf", "pnl_usd_001"]
    cost_cols = [
        "candidate",
        "round_trip_cost_points",
        "pf",
        "test_pf",
        "pnl_usd_001",
        "test_pnl_usd_001",
        "positive_years",
        "total_years",
    ]
    cost_yearly_cols = ["candidate", "round_trip_cost_points", "year", "n", "pf", "pnl_usd_001"]
    rolling_cols = [
        "candidate",
        "window_months",
        "windows",
        "positive_windows",
        "positive_window_rate_pct",
        "min_pnl_points",
        "median_pnl_points",
        "worst_window_start",
        "worst_window_end",
        "worst_window_pnl_usd_001",
    ]

    best = overall.sort_values(["pnl_usd_001", "test_pf", "n"], ascending=[False, False, False]).iloc[0]
    stable = overall.sort_values(["n", "test_pf", "pnl_usd_001"], ascending=[False, False, False]).iloc[0]

    important_cost = cost.loc[cost["round_trip_cost_points"].isin([0.5, 1.0, 1.5, 2.0])].copy()
    important_cost = important_cost.loc[important_cost["candidate"].isin([best["candidate"], stable["candidate"]])]
    important_yearly = yearly.loc[yearly["candidate"].isin([best["candidate"], stable["candidate"]])].copy()
    important_cost_yearly = cost_yearly.loc[
        cost_yearly["candidate"].isin([best["candidate"], stable["candidate"]])
        & cost_yearly["round_trip_cost_points"].isin([0.5, 1.0, 2.0])
    ].copy()

    lines = [
        "# 1H_M30_4H 稳健性验证",
        "",
        f"日期：{DATE_LABEL}",
        "",
        "## 验证范围",
        "",
        "- 输入：上一轮极值 way / 动能扫描生成的 `way_momentum_enriched_trades.csv`。",
        "- 本步骤只做稳健性验证，不重建信号、不改止损。",
        "- 成本压力测试为每笔交易扣除固定往返成本。按当前报告口径，0.01 lot 下 1.0 price point 约等于 $1.00。",
        "",
        "## 总体结果",
        "",
        markdown_table(overall[overall_cols], overall_cols, money_cols={"pnl_usd_001", "test_pnl_usd_001", "max_drawdown_usd_001"}),
        "",
        "## 年度拆分",
        "",
        markdown_table(important_yearly[yearly_cols], yearly_cols, money_cols={"pnl_usd_001"}),
        "",
        "## 多空拆分",
        "",
        markdown_table(side_summary[side_cols], side_cols, money_cols={"pnl_usd_001"}),
        "",
        "## 成本压力测试",
        "",
        markdown_table(important_cost[cost_cols], cost_cols, money_cols={"pnl_usd_001", "test_pnl_usd_001"}),
        "",
        "## 成本后的年度拆分",
        "",
        markdown_table(important_cost_yearly[cost_yearly_cols], cost_yearly_cols, money_cols={"pnl_usd_001"}),
        "",
        "## 滚动窗口汇总",
        "",
        markdown_table(rolling_summary[rolling_cols], rolling_cols, money_cols={"worst_window_pnl_usd_001"}),
        "",
        "## 当前最佳候选的最差月份",
        "",
        markdown_table(
            top_negative_months(monthly, str(best["candidate"])),
            ["candidate", "month", "n", "long_n", "short_n", "pf", "pnl_usd_001"],
            money_cols={"pnl_usd_001"},
        ),
        "",
        "## 当前判断",
        "",
        f"- 当前最高实际收益候选：`{best['candidate']}`。",
        f"- 当前最大样本候选：`{stable['candidate']}`。",
        "- `8-28pt + close_momentum >= -0.4` 是当前主候选；`6-28pt + close_momentum >= -0.4` 更适合作为样本对照。",
        "- 多头 PF 明显高于空头，空头交易数更多但效率偏低；下一轮优化应优先做多空分侧，尤其先压缩空头弱月份。",
        "- 2021/2022 的边际仍薄，加入成本后年度正收益数会下降；因此还不能直接进入实盘，只能进入 EA 逐笔对齐/模拟验证阶段。",
        "",
        "## 输出文件",
        "",
        "- `robustness_overall_summary.csv`",
        "- `robustness_yearly_summary.csv`",
        "- `robustness_monthly_summary.csv`",
        "- `robustness_side_summary.csv`",
        "- `robustness_cost_sensitivity.csv`",
        "- `robustness_cost_yearly_summary.csv`",
        "- `robustness_rolling_windows.csv`",
        "- `robustness_rolling_summary.csv`",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input: {INPUT_PATH}")

    trades = read_csv(INPUT_PATH)
    trades["signal_time"] = pd.to_datetime(trades["signal_time"])
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])

    selected = {spec.name: select_candidate(trades, spec) for spec in CANDIDATES}
    all_selected = pd.concat(selected.values(), ignore_index=True)
    overall = build_overall(selected)
    yearly = build_yearly(selected)
    monthly = build_monthly(selected)
    side_summary = build_side_summary(selected)
    cost = build_cost_sensitivity(selected)
    cost_yearly = build_cost_yearly(selected)
    rolling_windows, rolling_summary = build_rolling_windows(selected)

    OUT_DIR_ROBUST.mkdir(parents=True, exist_ok=True)
    all_selected.to_csv(OUT_DIR_ROBUST / "robustness_selected_trades.csv", index=False, encoding="utf-8-sig")
    overall.to_csv(OUT_DIR_ROBUST / "robustness_overall_summary.csv", index=False, encoding="utf-8-sig")
    yearly.to_csv(OUT_DIR_ROBUST / "robustness_yearly_summary.csv", index=False, encoding="utf-8-sig")
    monthly.to_csv(OUT_DIR_ROBUST / "robustness_monthly_summary.csv", index=False, encoding="utf-8-sig")
    side_summary.to_csv(OUT_DIR_ROBUST / "robustness_side_summary.csv", index=False, encoding="utf-8-sig")
    cost.to_csv(OUT_DIR_ROBUST / "robustness_cost_sensitivity.csv", index=False, encoding="utf-8-sig")
    cost_yearly.to_csv(OUT_DIR_ROBUST / "robustness_cost_yearly_summary.csv", index=False, encoding="utf-8-sig")
    rolling_windows.to_csv(OUT_DIR_ROBUST / "robustness_rolling_windows.csv", index=False, encoding="utf-8-sig")
    rolling_summary.to_csv(OUT_DIR_ROBUST / "robustness_rolling_summary.csv", index=False, encoding="utf-8-sig")

    report = make_report(overall, yearly, monthly, side_summary, cost, cost_yearly, rolling_summary)
    (OUT_DIR_ROBUST / "robustness_validation_report.md").write_text(report, encoding="utf-8")
    ROOT_REPORT.write_text(report, encoding="utf-8")

    print("1H_M30_4H robustness validation")
    print(f"input={INPUT_PATH}")
    print(f"out_dir={OUT_DIR_ROBUST}")
    for _, row in overall.sort_values(["pnl_usd_001"], ascending=False).iterrows():
        print(
            f"{row['candidate']}: n={int(row['n'])} pf={float(row['pf']):.4f} "
            f"test_pf={float(row['test_pf']):.4f} usd001={float(row['pnl_usd_001']):.2f} "
            f"pos_years={int(row['positive_years'])}/{int(row['total_years'])}"
        )


if __name__ == "__main__":
    main()
