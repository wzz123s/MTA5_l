# -*- coding: utf-8 -*-
"""Short-side filter optimization for the current 1H_M30_4H candidate.

The long side is kept unchanged. Only short trades from the current main
candidate are filtered, then the combined strategy is re-evaluated.
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
from typing import Callable

import numpy as np
import pandas as pd

from replay_raw_signals_with_stops import LOT_FOR_REPORT, ROOT, markdown_table, metric, split_test
from replay_1h_way_momentum_filter_scan import BASE_CANDIDATES, OUT_DIR, candidate_mask, side_extreme_opportunity_mask


DATE_LABEL = "2026-07-26"
INPUT_PATH = OUT_DIR / "way_momentum_enriched_trades.csv"
OUT_DIR_SHORT = OUT_DIR.parent / "short_side_optimization"
ROOT_REPORT = ROOT / "1H_M30_4H空头分侧优化结论.md"
USD_PER_POINT_001 = 100.0 * LOT_FOR_REPORT
BASE_CANDIDATE = "fd1_h1last6_8_28"
BASE_CLOSE_MOM_MIN = -0.4
MIN_SHORT_SAMPLE = 40
MIN_TOTAL_SAMPLE = 75
COST_POINTS = [0.0, 0.5, 1.0, 1.5, 2.0]


@dataclass(frozen=True)
class FilterSpec:
    name: str
    desc: str
    fn: Callable[[pd.DataFrame], pd.Series]
    family: str


def read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def as_num(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def as_money(points: float) -> float:
    return float(points) * USD_PER_POINT_001


def candidate_cfg(name: str) -> dict:
    for cfg in BASE_CANDIDATES:
        if str(cfg["candidate"]) == name:
            return cfg
    raise KeyError(f"Unknown base candidate: {name}")


def max_drawdown(values: pd.Series) -> float:
    vals = pd.to_numeric(values, errors="coerce").fillna(0.0)
    if vals.empty:
        return 0.0
    equity = vals.cumsum()
    peak = equity.cummax()
    return float((peak - equity).max())


def positive_group_count(frame: pd.DataFrame, value_col: str, freq: str) -> tuple[int, int]:
    if frame.empty:
        return 0, 0
    scoped = frame.copy()
    scoped["bucket"] = pd.to_datetime(scoped["entry_time"]).dt.to_period(freq).astype(str)
    grouped = scoped.groupby("bucket")[value_col].sum()
    return int((grouped > 0).sum()), int(len(grouped))


def rolling_summary(frame: pd.DataFrame, months: int) -> dict:
    if frame.empty:
        return {
            f"roll{months}_windows": 0,
            f"roll{months}_positive_rate_pct": 0.0,
            f"roll{months}_min_pnl_points": 0.0,
            f"roll{months}_median_pnl_points": 0.0,
        }
    scoped = frame.copy()
    scoped["entry_time"] = pd.to_datetime(scoped["entry_time"])
    first_month = scoped["entry_time"].min().to_period("M").to_timestamp()
    last_month = scoped["entry_time"].max().to_period("M").to_timestamp()
    rows = []
    for end_start in pd.period_range(first_month, last_month, freq="M").to_timestamp():
        end_exclusive = end_start + pd.DateOffset(months=1)
        start = end_exclusive - pd.DateOffset(months=months)
        group = scoped.loc[(scoped["entry_time"] >= start) & (scoped["entry_time"] < end_exclusive)]
        if group.empty:
            continue
        rows.append(float(pd.to_numeric(group["pnl_points"], errors="coerce").sum()))
    if not rows:
        return {
            f"roll{months}_windows": 0,
            f"roll{months}_positive_rate_pct": 0.0,
            f"roll{months}_min_pnl_points": 0.0,
            f"roll{months}_median_pnl_points": 0.0,
        }
    vals = pd.Series(rows)
    return {
        f"roll{months}_windows": int(len(vals)),
        f"roll{months}_positive_rate_pct": float((vals > 0).mean() * 100.0),
        f"roll{months}_min_pnl_points": float(vals.min()),
        f"roll{months}_median_pnl_points": float(vals.median()),
    }


def summarize_frame(prefix: str, frame: pd.DataFrame, value_col: str = "pnl_points") -> dict:
    m = metric(frame[value_col])
    test = split_test(frame, value_col)
    pos_years, total_years = positive_group_count(frame, value_col, "Y")
    pos_months, total_months = positive_group_count(frame, value_col, "M")
    return {
        f"{prefix}_n": m["n"],
        f"{prefix}_wr_pct": m["wr"],
        f"{prefix}_pf": m["pf"],
        f"{prefix}_ev_points": m["ev"],
        f"{prefix}_pnl_points": m["pnl"],
        f"{prefix}_pnl_usd_001": as_money(m["pnl"]),
        f"{prefix}_test_pf": test["test_pf"],
        f"{prefix}_test_pnl_usd_001": as_money(float(test["test_pnl"])),
        f"{prefix}_positive_years": pos_years,
        f"{prefix}_total_years": total_years,
        f"{prefix}_positive_months": pos_months,
        f"{prefix}_total_months": total_months,
        f"{prefix}_max_loss_streak": m["maxcl"],
        f"{prefix}_max_drawdown_usd_001": as_money(max_drawdown(frame[value_col])),
    }


def cost_metric(frame: pd.DataFrame, cost_points: float) -> dict:
    scoped = frame.copy()
    scoped["pnl_net"] = pd.to_numeric(scoped["pnl_points"], errors="coerce") - cost_points
    m = metric(scoped["pnl_net"])
    test = split_test(scoped, "pnl_net")
    pos_years, total_years = positive_group_count(scoped, "pnl_net", "Y")
    return {
        f"cost_{cost_points:g}_pf": m["pf"],
        f"cost_{cost_points:g}_test_pf": test["test_pf"],
        f"cost_{cost_points:g}_pnl_usd_001": as_money(m["pnl"]),
        f"cost_{cost_points:g}_positive_years": pos_years,
        f"cost_{cost_points:g}_total_years": total_years,
    }


def base_mask(frame: pd.DataFrame) -> pd.Series:
    cfg = candidate_cfg(BASE_CANDIDATE)
    close_mom = as_num(frame, "side_extreme_close_momentum_signed_pct")
    return candidate_mask(frame, cfg) & side_extreme_opportunity_mask(frame) & close_mom.ge(BASE_CLOSE_MOM_MIN)


def threshold_specs(column: str, label: str, thresholds: list[float], family: str, *, ge: bool = True, le: bool = True) -> list[FilterSpec]:
    specs: list[FilterSpec] = []
    for threshold in thresholds:
        if ge:
            specs.append(
                FilterSpec(
                    name=f"{column}_ge_{threshold:g}",
                    desc=f"{label} >= {threshold:g}",
                    family=family,
                    fn=lambda frame, c=column, t=threshold: as_num(frame, c).ge(t),
                )
            )
        if le:
            specs.append(
                FilterSpec(
                    name=f"{column}_le_{threshold:g}",
                    desc=f"{label} <= {threshold:g}",
                    family=family,
                    fn=lambda frame, c=column, t=threshold: as_num(frame, c).le(t),
                )
            )
    return specs


def stop_range_specs() -> list[FilterSpec]:
    specs: list[FilterSpec] = []
    for lo in [8, 9, 10, 11, 12, 13, 14, 15]:
        for hi in [18, 20, 22, 24, 26, 28]:
            if lo >= hi:
                continue
            specs.append(
                FilterSpec(
                    name=f"stop_{lo}_{hi}",
                    desc=f"stop_distance between {lo}-{hi}pt",
                    family="stop_distance",
                    fn=lambda frame, a=lo, b=hi: as_num(frame, "stop_distance").between(a, b, inclusive="both"),
                )
            )
    return specs


def categorical_specs() -> list[FilterSpec]:
    specs: list[FilterSpec] = [
        FilterSpec(
            name="h1_dir_align",
            desc="closed H1 direction aligns with short side",
            family="h1_context",
            fn=lambda frame: as_num(frame, "1h_dir").eq(-1),
        ),
        FilterSpec(
            name="h1_prev1_dir_align",
            desc="previous closed H1 direction aligns with short side",
            family="h1_context",
            fn=lambda frame: as_num(frame, "1h_dir_prev1").eq(-1),
        ),
    ]
    for value in ["up", "down", "good", "bad"]:
        specs.append(
            FilterSpec(
                name=f"extreme_h1_direction_{value}",
                desc=f"side extreme H1 merged direction == {value}",
                family="h1_way_state",
                fn=lambda frame, v=value: frame["side_extreme_h1_direction"].astype(str).eq(v),
            )
        )
    return specs


def combo_specs(single_specs: list[FilterSpec]) -> list[FilterSpec]:
    by_name = {spec.name: spec for spec in single_specs}
    requested = [
        ("side_extreme_way_s_way_le_0.6", "side_extreme_close_momentum_signed_pct_ge_0"),
        ("side_extreme_way_s_way_le_0.8", "side_extreme_close_momentum_signed_pct_ge_0"),
        ("side_extreme_way_s_way_ge_0.3", "side_extreme_close_momentum_signed_pct_ge_0"),
        ("side_extreme_way_s_way_le_0.6", "side_extreme_body_momentum_signed_ge_0"),
        ("side_extreme_way_s_way_ge_0.3", "side_extreme_body_momentum_signed_le_0"),
        ("side_extreme_bias55_h4sma_pct_ge_2.6", "side_extreme_close_momentum_signed_pct_ge_0"),
        ("side_extreme_bias55_h4sma_pct_ge_3", "side_extreme_close_momentum_signed_pct_ge_0"),
        ("stop_8_24", "side_extreme_close_momentum_signed_pct_ge_0"),
        ("stop_10_28", "side_extreme_close_momentum_signed_pct_ge_0"),
        ("h1_dir_align", "side_extreme_close_momentum_signed_pct_ge_0"),
    ]
    specs: list[FilterSpec] = []
    for left_name, right_name in requested:
        if left_name not in by_name or right_name not in by_name:
            continue
        left = by_name[left_name]
        right = by_name[right_name]
        specs.append(
            FilterSpec(
                name=f"{left.name}__{right.name}",
                desc=f"{left.desc} AND {right.desc}",
                family=f"combo:{left.family}+{right.family}",
                fn=lambda frame, a=left, b=right: a.fn(frame) & b.fn(frame),
            )
        )
    return specs


def build_filter_specs() -> list[FilterSpec]:
    specs = [
        FilterSpec(name="baseline", desc="no extra short-side filter", family="baseline", fn=lambda frame: pd.Series(True, index=frame.index)),
    ]
    specs += threshold_specs("side_extreme_way_s_way", "side extreme way_s_way", [round(x / 10.0, 1) for x in range(1, 10)], "way")
    specs += threshold_specs("side_extreme_vol_way_s_way", "side extreme vol_way_s_way", [round(x / 10.0, 1) for x in range(1, 10)], "way_volume")
    specs += threshold_specs(
        "side_extreme_close_momentum_signed_pct",
        "side extreme close momentum signed pct",
        [round(x / 10.0, 1) for x in range(-3, 7)],
        "momentum_close",
    )
    specs += threshold_specs(
        "side_extreme_body_momentum_signed",
        "side extreme body momentum signed",
        [round(x / 10.0, 1) for x in range(-6, 7)],
        "momentum_body",
    )
    specs += threshold_specs(
        "side_extreme_sma13_gap_momentum_signed_pct",
        "side extreme SMA13 gap momentum signed pct",
        [round(x / 10.0, 1) for x in range(-6, 7)],
        "momentum_gap",
    )
    specs += threshold_specs(
        "side_extreme_bias55_h4sma_pct",
        "short extreme high vs H4 SMA55 pct",
        [round(x / 10.0, 1) for x in range(20, 61, 2)],
        "extreme_bias55",
        ge=True,
        le=False,
    )
    specs += threshold_specs(
        "1h_bias55_signed_pct",
        "1H bias55 signed pct",
        [round(x / 10.0, 1) for x in range(-5, 16, 2)],
        "h1_bias55",
    )
    specs += threshold_specs(
        "4h_bias55_signed_pct",
        "4H bias55 signed pct",
        [round(x / 10.0, 1) for x in range(-5, 21, 2)],
        "h4_bias55",
    )
    specs += stop_range_specs()
    specs += categorical_specs()
    specs += combo_specs(specs)
    return specs


def evaluate_filter(long_base: pd.DataFrame, short_base: pd.DataFrame, spec: FilterSpec) -> tuple[dict, pd.DataFrame]:
    mask = spec.fn(short_base).fillna(False).astype(bool)
    short_selected = short_base.loc[mask].copy()
    combined = pd.concat([long_base, short_selected], ignore_index=True).sort_values("entry_time").reset_index(drop=True)

    row = {
        "filter_name": spec.name,
        "filter_desc": spec.desc,
        "family": spec.family,
        "long_n": int(len(long_base)),
        "short_n": int(len(short_selected)),
        "removed_short_n": int(len(short_base) - len(short_selected)),
    }
    row.update(summarize_frame("total", combined))
    row.update(summarize_frame("short", short_selected))
    for cost in COST_POINTS:
        row.update(cost_metric(combined, cost))
    row.update(rolling_summary(combined, 3))
    row.update(rolling_summary(combined, 6))
    row.update(rolling_summary(combined, 12))
    row["sample_ok"] = int(row["short_n"]) >= MIN_SHORT_SAMPLE and int(row["total_n"]) >= MIN_TOTAL_SAMPLE
    row["quality_ok"] = (
        bool(row["sample_ok"])
        and float(row["total_pf"]) > 1.8
        and float(row["total_test_pf"]) > 1.2
        and float(row["short_pf"]) > 1.5
        and float(row["total_pnl_usd_001"]) > 0
        and int(row["total_positive_years"]) >= 4
    )
    row["score"] = score_row(row)
    return row, combined


def score_row(row: dict) -> float:
    if not row.get("sample_ok", False):
        return float(row.get("short_n", 0)) + float(row.get("total_pnl_usd_001", 0)) * 0.002
    score = 1000.0
    score += float(row["total_pnl_usd_001"]) * 0.035
    score += float(row["total_test_pf"]) * 18.0
    score += float(row["short_pf"]) * 16.0
    score += float(row["cost_1_test_pf"]) * 12.0
    score += float(row["roll12_positive_rate_pct"]) * 0.45
    score += min(float(row["short_n"]), 70.0) * 0.12
    score -= max(0.0, 40.0 - float(row["roll12_min_pnl_points"])) * 0.35
    return score


def scan_filters(trades: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    base = trades.loc[base_mask(trades)].copy().sort_values("entry_time").reset_index(drop=True)
    long_base = base.loc[base["dir"].astype(str).str.upper().eq("L")].copy()
    short_base = base.loc[base["dir"].astype(str).str.upper().eq("S")].copy()

    rows = []
    selected_trades: dict[str, pd.DataFrame] = {}
    for spec in build_filter_specs():
        row, combined = evaluate_filter(long_base, short_base, spec)
        rows.append(row)
        selected_trades[spec.name] = combined

    summary = pd.DataFrame(rows)
    summary = summary.sort_values(["score", "total_pnl_usd_001", "total_test_pf", "short_n"], ascending=[False, False, False, False]).reset_index(drop=True)
    return summary, selected_trades


def build_short_yearly(selected: dict[str, pd.DataFrame], names: list[str]) -> pd.DataFrame:
    rows = []
    for name in names:
        frame = selected[name]
        short = frame.loc[frame["dir"].astype(str).str.upper().eq("S")].copy()
        if short.empty:
            continue
        short["year"] = pd.to_datetime(short["entry_time"]).dt.year
        for year, group in short.groupby("year", sort=True):
            m = metric(group["pnl_points"])
            rows.append(
                {
                    "filter_name": name,
                    "year": int(year),
                    "n": m["n"],
                    "pf": m["pf"],
                    "pnl_usd_001": as_money(m["pnl"]),
                }
            )
    return pd.DataFrame(rows)


def build_short_monthly(selected: dict[str, pd.DataFrame], names: list[str]) -> pd.DataFrame:
    rows = []
    for name in names:
        frame = selected[name]
        short = frame.loc[frame["dir"].astype(str).str.upper().eq("S")].copy()
        if short.empty:
            continue
        short["month"] = pd.to_datetime(short["entry_time"]).dt.to_period("M").astype(str)
        for month, group in short.groupby("month", sort=True):
            m = metric(group["pnl_points"])
            rows.append(
                {
                    "filter_name": name,
                    "month": month,
                    "n": m["n"],
                    "pf": m["pf"],
                    "pnl_usd_001": as_money(m["pnl"]),
                }
            )
    return pd.DataFrame(rows)


def make_report(summary: pd.DataFrame, short_yearly: pd.DataFrame, short_monthly: pd.DataFrame) -> str:
    quality = summary.loc[summary["quality_ok"].astype(bool)].copy()
    baseline = summary.loc[summary["filter_name"].eq("baseline")].iloc[0]
    top_score = quality.head(15) if not quality.empty else summary.head(15)
    top_pnl = quality.sort_values(["total_pnl_usd_001", "total_test_pf", "short_n"], ascending=[False, False, False]).head(15)
    if top_pnl.empty:
        top_pnl = summary.sort_values(["total_pnl_usd_001", "total_test_pf", "short_n"], ascending=[False, False, False]).head(15)

    score_best = top_score.iloc[0]
    pnl_best = top_pnl.iloc[0]
    selected_names = ["baseline"]
    for name in [score_best["filter_name"], pnl_best["filter_name"]]:
        if name not in selected_names:
            selected_names.append(str(name))
    selected_names += [name for name in top_score["filter_name"].head(3).tolist() if name not in selected_names]
    yearly_view = short_yearly.loc[short_yearly["filter_name"].isin(selected_names)].copy()
    monthly_view = short_monthly.loc[short_monthly["filter_name"].eq(str(pnl_best["filter_name"]))].copy()
    monthly_view = monthly_view.sort_values(["pnl_usd_001", "n"], ascending=[True, False]).head(10)

    main_cols = [
        "filter_name",
        "family",
        "short_n",
        "removed_short_n",
        "short_pf",
        "short_pnl_usd_001",
        "total_n",
        "total_pf",
        "total_test_pf",
        "total_pnl_usd_001",
        "cost_1_test_pf",
        "cost_1_pnl_usd_001",
        "roll12_positive_rate_pct",
        "roll12_min_pnl_points",
        "quality_ok",
    ]
    yearly_cols = ["filter_name", "year", "n", "pf", "pnl_usd_001"]
    monthly_cols = ["filter_name", "month", "n", "pf", "pnl_usd_001"]

    lines = [
        "# 1H_M30_4H 空头分侧优化",
        "",
        f"日期：{DATE_LABEL}",
        "",
        "## 口径",
        "",
        "- 多头保留当前主候选规则，不参与本轮优化。",
        "- 空头基线：`fixed_delay_1 + H1 last6 stop + stop_distance 8-28pt + side-extreme pool + close_momentum_signed_pct >= -0.4`。",
        "- 本轮只对空头增加过滤条件，再把“原多头 + 过滤后空头”合成总策略评估。",
        "- 最小样本约束：空头不少于 40 笔，总交易不少于 75 笔。",
        "",
        "## 空头基线",
        "",
        markdown_table(pd.DataFrame([baseline])[main_cols], main_cols, money_cols={"short_pnl_usd_001", "total_pnl_usd_001", "cost_1_pnl_usd_001"}),
        "",
        "## 按评分排序",
        "",
        markdown_table(top_score[main_cols], main_cols, money_cols={"short_pnl_usd_001", "total_pnl_usd_001", "cost_1_pnl_usd_001"}),
        "",
        "## 按实际收益排序",
        "",
        markdown_table(top_pnl[main_cols], main_cols, money_cols={"short_pnl_usd_001", "total_pnl_usd_001", "cost_1_pnl_usd_001"}),
        "",
        "## 空头年度拆分",
        "",
        markdown_table(yearly_view[yearly_cols], yearly_cols, money_cols={"pnl_usd_001"}),
        "",
        "## 收益候选的空头最差月份",
        "",
        markdown_table(monthly_view[monthly_cols], monthly_cols, money_cols={"pnl_usd_001"}),
        "",
        "## 当前判断",
        "",
        f"- 当前实际收益最高的空头过滤：`{pnl_best['filter_name']}`，含义：{pnl_best['filter_desc']}。",
        f"- 当前稳健评分最高的空头过滤：`{score_best['filter_name']}`，含义：{score_best['filter_desc']}。",
        "- 主推先看实际收益候选；若后续成本/EA 对齐发现滑点更高，再降级到稳健评分候选。",
        "- 如果某个最优项样本刚好卡在 40 笔附近，需要把它视为研究候选，而不是正式参数。",
        "",
        "## 输出文件",
        "",
        "- `short_side_filter_summary.csv`",
        "- `short_side_selected_trades_top.csv`",
        "- `short_side_yearly.csv`",
        "- `short_side_monthly.csv`",
        "- `short_side_optimization_report.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    trades = read_csv(INPUT_PATH)
    trades["signal_time"] = pd.to_datetime(trades["signal_time"])
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])
    summary, selected = scan_filters(trades)

    quality = summary.loc[summary["quality_ok"].astype(bool)].copy()
    ranked = quality if not quality.empty else summary
    top_names = ["baseline"]
    for name in ranked["filter_name"].head(10).tolist():
        if name not in top_names:
            top_names.append(name)
    top_selected = []
    for name in top_names:
        frame = selected[name].copy()
        frame["short_filter_name"] = name
        top_selected.append(frame)
    top_trades = pd.concat(top_selected, ignore_index=True)
    short_yearly = build_short_yearly(selected, top_names)
    short_monthly = build_short_monthly(selected, top_names)
    report = make_report(summary, short_yearly, short_monthly)

    OUT_DIR_SHORT.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUT_DIR_SHORT / "short_side_filter_summary.csv", index=False, encoding="utf-8-sig")
    top_trades.to_csv(OUT_DIR_SHORT / "short_side_selected_trades_top.csv", index=False, encoding="utf-8-sig")
    short_yearly.to_csv(OUT_DIR_SHORT / "short_side_yearly.csv", index=False, encoding="utf-8-sig")
    short_monthly.to_csv(OUT_DIR_SHORT / "short_side_monthly.csv", index=False, encoding="utf-8-sig")
    (OUT_DIR_SHORT / "short_side_optimization_report.md").write_text(report, encoding="utf-8")
    ROOT_REPORT.write_text(report, encoding="utf-8")

    baseline = summary.loc[summary["filter_name"].eq("baseline")].iloc[0]
    best = ranked.iloc[0]
    pnl_best = ranked.sort_values(["total_pnl_usd_001", "total_test_pf", "short_n"], ascending=[False, False, False]).iloc[0]
    print("1H_M30_4H short-side optimization")
    print(
        f"baseline short_n={int(baseline['short_n'])} short_pf={float(baseline['short_pf']):.4f} "
        f"total_pf={float(baseline['total_pf']):.4f} total_usd001={float(baseline['total_pnl_usd_001']):.2f}"
    )
    print(
        f"best filter={best['filter_name']} short_n={int(best['short_n'])} "
        f"short_pf={float(best['short_pf']):.4f} total_pf={float(best['total_pf']):.4f} "
        f"test_pf={float(best['total_test_pf']):.4f} total_usd001={float(best['total_pnl_usd_001']):.2f}"
    )
    print(
        f"best_pnl filter={pnl_best['filter_name']} short_n={int(pnl_best['short_n'])} "
        f"short_pf={float(pnl_best['short_pf']):.4f} total_pf={float(pnl_best['total_pf']):.4f} "
        f"test_pf={float(pnl_best['total_test_pf']):.4f} total_usd001={float(pnl_best['total_pnl_usd_001']):.2f}"
    )
    print(f"out_dir={OUT_DIR_SHORT}")


if __name__ == "__main__":
    main()
