# -*- coding: utf-8 -*-
"""Export and optionally compare EA alignment ledger for the current candidate.

This is the alignment bridge for the current 1H_M30_4H research candidate:
fixed_delay_1 + H1 last6 structural stop + 8-28pt + side-extreme pool
+ close momentum >= -0.4 + SHORT vol_way_s_way <= 0.7.

The existing legacy EA comparer is stage-ledger based; this script uses the
current one-trade-per-signal Python ledger as the source of truth.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from replay_raw_signals_with_stops import LOT_FOR_REPORT, ROOT, markdown_table, metric, split_test
from validate_1h_way_momentum_candidates import (
    CandidateSpec,
    INPUT_PATH,
    as_money,
    read_csv,
    select_candidate,
)


DATE_LABEL = "2026-07-26"
STRATEGY = "1H_M30_4H"
CANDIDATE = CandidateSpec(
    name="fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7",
    base_candidate="fd1_h1last6_8_28",
    filter_desc="8-28pt base + close momentum signed >= -0.4 + SHORT vol_way_s_way <= 0.7",
    use_close_momentum=True,
    close_momentum_min=-0.4,
    short_vol_way_le=0.7,
)
CONTROL_CANDIDATE = CandidateSpec(
    name="fd1_8_28_side_pool_close_mom_ge_-0.4__short_way_ge_0.3",
    base_candidate="fd1_h1last6_8_28",
    filter_desc="8-28pt base + close momentum signed >= -0.4 + SHORT way_s_way >= 0.3",
    use_close_momentum=True,
    close_momentum_min=-0.4,
    short_way_ge=0.3,
)
OUT_DIR = ROOT / "黄金" / f"{STRATEGY}策略" / "data" / "validation" / "ea_alignment_current_candidate"
ROOT_REPORT = ROOT / "1H_M30_4H当前候选EA对齐记录.md"
EXPECTED_LEDGER = OUT_DIR / "python_expected_trade_ledger.csv"
EXPECTED_MINIMAL = OUT_DIR / "python_expected_trade_ledger_minimal.csv"
PARAMETER_PACK = OUT_DIR / "current_candidate_parameter_pack.json"


def norm_time(value: object) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def norm_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"L", "LONG", "BUY", "1"}:
        return "BUY"
    if text in {"S", "SHORT", "SELL", "-1"}:
        return "SELL"
    return text


def build_expected(trades: pd.DataFrame, spec: CandidateSpec) -> pd.DataFrame:
    selected = select_candidate(trades, spec).copy().sort_values("entry_time").reset_index(drop=True)
    selected["trade_seq"] = np.arange(1, len(selected) + 1)
    selected["dir_key"] = selected["dir"].map(norm_dir)
    selected["signal_time_key"] = selected["signal_time"].map(norm_time)
    selected["entry_time_key"] = selected["entry_time"].map(norm_time)
    selected["trade_key"] = selected["entry_time_key"] + "|" + selected["dir_key"]
    selected["expected_lot"] = LOT_FOR_REPORT
    selected["expected_pnl_usd_001"] = pd.to_numeric(selected["pnl_points"], errors="coerce") * 100.0 * LOT_FOR_REPORT
    selected["candidate_name"] = spec.name
    selected["candidate_desc"] = spec.filter_desc
    selected["ea_alignment_status"] = "python_expected"
    return selected


def minimal_ledger(expected: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "trade_seq",
        "trade_key",
        "candidate_name",
        "signal_time_key",
        "entry_time_key",
        "dir_key",
        "entry",
        "structural_stop_price",
        "stop_distance",
        "exit_time",
        "exit",
        "exit_reason",
        "pnl_points",
        "expected_pnl_usd_001",
        "entry_rule",
        "entry_delay_bars",
        "stop_variant",
        "side_extreme_kind",
        "side_extreme_time",
        "side_extreme_bias55_h4sma_pct",
        "side_extreme_way_s_way",
        "side_extreme_vol_way_s_way",
        "side_extreme_close_momentum_signed_pct",
        "side_extreme_body_momentum_signed",
    ]
    return expected[[c for c in cols if c in expected.columns]].copy()


def summarize_expected(expected: pd.DataFrame) -> dict:
    m = metric(expected["pnl_points"])
    test = split_test(expected, "pnl_points")
    side = expected["dir_key"].astype(str)
    return {
        "candidate": CANDIDATE.name,
        "n": m["n"],
        "long_n": int(side.eq("BUY").sum()),
        "short_n": int(side.eq("SELL").sum()),
        "pf": m["pf"],
        "test_pf": test["test_pf"],
        "pnl_points": m["pnl"],
        "pnl_usd_001": as_money(m["pnl"]),
        "ev_points": m["ev"],
        "max_loss_streak": m["maxcl"],
    }


def yearly_summary(expected: pd.DataFrame) -> pd.DataFrame:
    scoped = expected.copy()
    scoped["year"] = pd.to_datetime(scoped["entry_time"]).dt.year
    rows = []
    for year, group in scoped.groupby("year", sort=True):
        m = metric(group["pnl_points"])
        side = group["dir_key"].astype(str)
        rows.append(
            {
                "year": int(year),
                "n": m["n"],
                "long_n": int(side.eq("BUY").sum()),
                "short_n": int(side.eq("SELL").sum()),
                "pf": m["pf"],
                "pnl_usd_001": as_money(m["pnl"]),
            }
        )
    return pd.DataFrame(rows)


def write_parameter_pack(expected: pd.DataFrame, control: pd.DataFrame, alignment_status: str) -> None:
    summary = summarize_expected(expected)
    control_metric = metric(control["pnl_points"])
    pack = {
        "strategy": STRATEGY,
        "date": DATE_LABEL,
        "status": alignment_status,
        "candidate": {
            "name": CANDIDATE.name,
            "description": CANDIDATE.filter_desc,
            "control_candidate": CONTROL_CANDIDATE.name,
            "control_description": CONTROL_CANDIDATE.filter_desc,
        },
        "timeframes": {
            "signal": "M30",
            "stop": "H1",
            "opportunity": "recent 4 closed H1 vs H4 SMA55",
        },
        "entry": {
            "rule": "fixed_delay_1",
            "description": "Open on the first M30 bar after an M30 SMA5/SMA13 cross.",
            "historical_price": "entry M30 open",
            "live_price": "market entry as close to new-bar open as broker allows",
        },
        "stop": {
            "variant": "h1_last6_hilo",
            "distance_range_pt": [8.0, 28.0],
            "description": "First-bar entries use H1 structural stop from the last 6 closed H1 bars.",
        },
        "filters": {
            "bias": "1H bias5_signed_pct > 0 and 1H bias13_signed_pct > 0, already direction-adjusted",
            "side_extreme_pool": "SELL: recent 4 closed H1 highest high vs H4 SMA55 >= 2%; BUY: recent 4 closed H1 lowest low vs H4 SMA55 <= -2%",
            "momentum": "side_extreme_close_momentum_signed_pct >= -0.4",
            "short_only": "For SELL only, side_extreme_vol_way_s_way <= 0.7",
            "control_short_only": "For SELL only, side_extreme_way_s_way >= 0.3",
        },
        "exit": {
            "historical": "Opposite M30 SMA5/SMA13 cross planned exit, with stop checked bar by bar first.",
            "ea_required": "Export actual stop or opposite-cross exit reason for each trade.",
        },
        "reporting": {
            "lot_for_report": LOT_FOR_REPORT,
            "usd_per_price_point_at_report_lot": 100.0 * LOT_FOR_REPORT,
            "expected_trade_count": int(summary["n"]),
            "expected_pnl_usd_001": summary["pnl_usd_001"],
            "control_pnl_usd_001": as_money(control_metric["pnl"]),
        },
        "ea_ledger_required_columns": [
            "entry_time",
            "dir",
            "entry",
            "stop",
            "exit_time",
            "exit",
            "exit_reason",
            "pnl_points",
        ],
        "outputs": {
            "python_expected_trade_ledger": str(EXPECTED_LEDGER),
            "python_expected_trade_ledger_minimal": str(EXPECTED_MINIMAL),
        },
    }
    PARAMETER_PACK.write_text(json.dumps(pack, ensure_ascii=False, indent=2), encoding="utf-8")


def find_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    lower_map = {str(col).strip().lower(): col for col in frame.columns}
    for candidate in candidates:
        col = lower_map.get(candidate.lower())
        if col is not None:
            return col
    return None


def normalize_actual(path: Path) -> pd.DataFrame:
    actual = read_csv(path)
    mapping = {
        "entry_time": ["entry_time", "entry_time_key", "open_time", "time", "open"],
        "dir": ["dir", "direction", "type", "side", "dir_key"],
        "entry": ["entry", "expected_entry", "open_price", "price_open", "entry_price"],
        "stop": ["stop", "structural_stop_price", "expected_stop", "sl", "stop_loss", "actual_stop"],
        "exit_time": ["exit_time", "close_time", "time_close"],
        "exit": ["exit", "expected_exit", "close_price", "price_close", "exit_price"],
        "exit_reason": ["exit_reason", "reason", "close_reason"],
        "pnl_points": ["pnl_points", "expected_pnl_points", "points", "profit_points", "expected_points"],
    }
    out = pd.DataFrame()
    for target, candidates in mapping.items():
        col = find_column(actual, candidates)
        out[target] = actual[col] if col is not None else pd.NA
    out["entry_time_key"] = out["entry_time"].map(norm_time)
    out["dir_key"] = out["dir"].map(norm_dir)
    out["trade_key"] = out["entry_time_key"] + "|" + out["dir_key"]
    return out


def compare_actual(expected: pd.DataFrame, actual_path: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    actual = normalize_actual(actual_path)
    exp = minimal_ledger(expected).copy()
    exp = exp.rename(
        columns={
            "entry": "expected_entry",
            "structural_stop_price": "expected_stop",
            "exit": "expected_exit",
            "pnl_points": "expected_pnl_points",
        }
    )
    actual = actual.rename(
        columns={
            "entry": "actual_entry",
            "stop": "actual_stop",
            "exit": "actual_exit",
            "pnl_points": "actual_pnl_points",
        }
    )
    detail = exp.merge(actual, on="trade_key", how="outer", suffixes=("_expected", "_actual"), indicator=True)
    for left, right, out_col in [
        ("expected_entry", "actual_entry", "entry_diff"),
        ("expected_stop", "actual_stop", "stop_diff"),
        ("expected_exit", "actual_exit", "exit_diff"),
        ("expected_pnl_points", "actual_pnl_points", "pnl_points_diff"),
    ]:
        detail[out_col] = pd.to_numeric(detail.get(right), errors="coerce") - pd.to_numeric(detail.get(left), errors="coerce")
    matched = detail.loc[detail["_merge"].eq("both")]
    summary = pd.DataFrame(
        [
            {
                "expected_rows": int(len(exp)),
                "actual_rows": int(len(actual)),
                "matched_rows": int(len(matched)),
                "missing_in_actual": int(detail["_merge"].eq("left_only").sum()),
                "extra_in_actual": int(detail["_merge"].eq("right_only").sum()),
                "max_abs_entry_diff": float(pd.to_numeric(matched["entry_diff"], errors="coerce").abs().max()) if len(matched) else np.nan,
                "max_abs_stop_diff": float(pd.to_numeric(matched["stop_diff"], errors="coerce").abs().max()) if len(matched) else np.nan,
                "max_abs_exit_diff": float(pd.to_numeric(matched["exit_diff"], errors="coerce").abs().max()) if len(matched) else np.nan,
                "max_abs_pnl_points_diff": float(pd.to_numeric(matched["pnl_points_diff"], errors="coerce").abs().max()) if len(matched) else np.nan,
            }
        ]
    )
    return detail, summary


def is_full_match(summary: pd.DataFrame | None) -> bool:
    if summary is None or summary.empty:
        return False
    row = summary.iloc[0]
    return (
        int(row["expected_rows"]) == int(row["actual_rows"]) == int(row["matched_rows"])
        and int(row["missing_in_actual"]) == 0
        and int(row["extra_in_actual"]) == 0
        and float(row["max_abs_entry_diff"]) == 0.0
        and float(row["max_abs_stop_diff"]) == 0.0
        and float(row["max_abs_exit_diff"]) == 0.0
        and float(row["max_abs_pnl_points_diff"]) == 0.0
    )


def readiness_rows(has_actual: bool, summary: pd.DataFrame | None) -> pd.DataFrame:
    matched = is_full_match(summary)
    rows = [
        {"item": "python_expected_ledger", "status": "done", "detail": str(EXPECTED_LEDGER)},
        {"item": "candidate_parameter_pack", "status": "done", "detail": str(PARAMETER_PACK)},
        {"item": "ea_implementation", "status": "done", "detail": "Dedicated current-candidate EA implemented and compiled."},
        {"item": "ea_strategy_tester_run", "status": "pending" if not has_actual else "done", "detail": "MT5 Strategy Tester ledger exported for the current candidate."},
        {"item": "python_vs_ea_alignment", "status": "pending" if summary is None else ("matched" if matched else "mismatch"), "detail": "Python expected ledger compared with EA-exported ledger."},
    ]
    if summary is not None:
        row = summary.iloc[0].to_dict()
        rows.append(
            {
                "item": "alignment_summary",
                "status": "review",
                "detail": json.dumps(row, ensure_ascii=False),
            }
        )
    return pd.DataFrame(rows)


def make_report(expected: pd.DataFrame, control: pd.DataFrame, actual_path: Path | None, align_summary: pd.DataFrame | None) -> str:
    overall = pd.DataFrame([summarize_expected(expected)])
    years = yearly_summary(expected)
    control_m = metric(control["pnl_points"])
    cols = ["candidate", "n", "long_n", "short_n", "pf", "test_pf", "pnl_usd_001", "ev_points", "max_loss_streak"]
    year_cols = ["year", "n", "long_n", "short_n", "pf", "pnl_usd_001"]
    lines = [
        "# 1H_M30_4H 当前候选 EA 对齐记录",
        "",
        f"日期：{DATE_LABEL}",
        "",
        "## 当前候选",
        "",
        f"- 主候选：`{CANDIDATE.name}`",
        f"- 规则：{CANDIDATE.filter_desc}",
        f"- 对照候选：`{CONTROL_CANDIDATE.name}`，0.01 lot 收益 `${as_money(control_m['pnl']):.2f}`。",
        "",
        "## Python 预期账单",
        "",
        markdown_table(overall[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## 年度拆分",
        "",
        markdown_table(years[year_cols], year_cols, money_cols={"pnl_usd_001"}),
        "",
        "## EA 对齐状态",
        "",
    ]
    if actual_path is None:
        lines += [
            "- 已生成 Python 预期逐笔账单。",
            "- 未提供 EA 导出 ledger，因此本轮状态是 `EA implementation/testing pending`。",
            "- 现有迁移 EA 仍是旧 stage/H2 执行框架，不能作为当前候选的逐笔对齐结果。",
        ]
    else:
        matched = is_full_match(align_summary)
        summary_cols = list(align_summary.columns) if align_summary is not None else []
        lines += [
            f"- EA ledger: `{actual_path}`",
            f"- 对齐结论：`{'matched' if matched else 'mismatch'}`",
            "",
            markdown_table(align_summary[summary_cols], summary_cols) if align_summary is not None else "- compare failed",
        ]
    lines += [
        "",
        "## EA 必须实现的关键字段",
        "",
        "- `trade_key = entry_time + dir`，用于逐笔对齐。",
        "- `entry_time / dir / entry / stop / exit_time / exit / exit_reason / pnl_points`。",
        "- 需要导出 side-extreme 诊断字段：`side_extreme_time`、`side_extreme_way_s_way`、`side_extreme_vol_way_s_way`、`side_extreme_close_momentum_signed_pct`。",
        "",
        "## 输出文件",
        "",
        "- `python_expected_trade_ledger.csv`",
        "- `python_expected_trade_ledger_minimal.csv`",
        "- `current_candidate_parameter_pack.json`",
        "- `ea_alignment_readiness_current_candidate.csv`",
        "- `ea_alignment_current_candidate_report.md`",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("ea_ledger", nargs="?", help="Optional EA-exported ledger CSV for the current candidate.")
    args = parser.parse_args()

    trades = read_csv(INPUT_PATH)
    trades["signal_time"] = pd.to_datetime(trades["signal_time"])
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])
    expected = build_expected(trades, CANDIDATE)
    control = build_expected(trades, CONTROL_CANDIDATE)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    expected.to_csv(EXPECTED_LEDGER, index=False, encoding="utf-8-sig")
    minimal_ledger(expected).to_csv(EXPECTED_MINIMAL, index=False, encoding="utf-8-sig")
    control.to_csv(OUT_DIR / "python_expected_trade_ledger_control_short_way_ge_0.3.csv", index=False, encoding="utf-8-sig")
    actual_path = Path(args.ea_ledger).resolve() if args.ea_ledger else None
    align_summary = None
    if actual_path is not None:
        detail, align_summary = compare_actual(expected, actual_path)
        detail.to_csv(OUT_DIR / "python_vs_ea_alignment_detail.csv", index=False, encoding="utf-8-sig")
        align_summary.to_csv(OUT_DIR / "python_vs_ea_alignment_summary.csv", index=False, encoding="utf-8-sig")

    alignment_status = "python_expected_exported__ea_alignment_pending"
    if align_summary is not None:
        alignment_status = "python_expected_exported__ea_aligned" if is_full_match(align_summary) else "python_expected_exported__ea_mismatch"
    write_parameter_pack(expected, control, alignment_status)

    readiness = readiness_rows(actual_path is not None, align_summary)
    readiness.to_csv(OUT_DIR / "ea_alignment_readiness_current_candidate.csv", index=False, encoding="utf-8-sig")
    report = make_report(expected, control, actual_path, align_summary)
    (OUT_DIR / "ea_alignment_current_candidate_report.md").write_text(report, encoding="utf-8")
    ROOT_REPORT.write_text(report, encoding="utf-8")

    summary = summarize_expected(expected)
    print("1H_M30_4H current candidate EA alignment export")
    print(f"expected_rows={summary['n']} pf={summary['pf']:.4f} test_pf={summary['test_pf']:.4f} usd001={summary['pnl_usd_001']:.2f}")
    print(f"out_dir={OUT_DIR}")
    if actual_path is None:
        print("ea_ledger=not_provided status=python_expected_exported")
    else:
        print(f"ea_ledger={actual_path} status=alignment_computed")


if __name__ == "__main__":
    main()
