# -*- coding: utf-8 -*-
"""Export and optionally compare the 2H_M30_6H current candidate EA ledger.

The source of truth is the Python research candidate trades for
2H_M30_6H__6h_bias5_13_55_signed_pos.  This script writes the expected
one-trade-per-signal ledger and, when an EA ledger is supplied, produces the
Python-vs-EA alignment summary and detail files.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


STRATEGY = "2H_M30_6H"
CANDIDATE_NAME = "2H_M30_6H__6h_bias5_13_55_signed_pos"
CANDIDATE_DESC = "M30 SMA5/SMA13 cross + 6H bias5/13/55 signed > 0; StopSpec 2-10pt"
LOT_FOR_REPORT = 0.01
DATE_LABEL = "2026-08-10"

ROOT = Path(r"F:\use_code\MTA5_l")
INPUT_PATH = ROOT / "黄金" / "2H_M30_6H策略" / "data" / "signals" / "strategy_candidate_trades.csv"
OUT_DIR = ROOT / "黄金" / "2H_M30_6H策略" / "data" / "validation" / "ea_alignment_current_candidate"
ROOT_REPORT = ROOT / "黄金" / "2H_M30_6H策略" / "说明文档" / "03_验证结果" / "当前候选EA对齐记录.md"
EXPECTED_LEDGER = OUT_DIR / "python_expected_trade_ledger.csv"
EXPECTED_MINIMAL = OUT_DIR / "python_expected_trade_ledger_minimal.csv"
PARAMETER_PACK = OUT_DIR / "current_candidate_parameter_pack.json"


def read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "gbk", "utf-8"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    raise ValueError(f"cannot read {path}")


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


def metric(points: pd.Series) -> dict:
    pts = pd.to_numeric(points, errors="coerce").dropna().astype(float)
    n = int(len(pts))
    wins = pts[pts > 0]
    losses = pts[pts < 0]
    gross_win = float(wins.sum())
    gross_loss = float(-losses.sum())
    if gross_loss > 0:
        pf = gross_win / gross_loss
    else:
        pf = float("inf") if gross_win > 0 else 0.0
    maxcl = 0
    cur = 0
    for value in pts:
        cur = cur + 1 if value < 0 else 0
        maxcl = max(maxcl, cur)
    return {
        "n": n,
        "wr": float(wins.size / n * 100.0) if n else 0.0,
        "pf": pf,
        "pnl": float(pts.sum()),
        "ev": float(pts.mean()) if n else 0.0,
        "maxcl": maxcl,
    }


def split_test(points: pd.Series, dates: pd.Series, train_ratio: float = 0.7) -> dict:
    frame = pd.DataFrame(
        {
            "points": pd.to_numeric(points, errors="coerce"),
            "date": pd.to_datetime(dates, errors="coerce"),
        }
    ).dropna().sort_values("date").reset_index(drop=True)
    split = int(len(frame) * train_ratio)
    return metric(frame["points"].iloc[split:])


def build_expected(trades: pd.DataFrame) -> pd.DataFrame:
    selected = trades.loc[trades["variant"].astype(str).eq(CANDIDATE_NAME)].copy()
    selected = selected.sort_values("entry_time").reset_index(drop=True)
    stop = pd.to_numeric(selected["stop_distance"], errors="coerce")
    selected = selected.loc[stop.between(2.0, 10.0, inclusive="both")].copy().reset_index(drop=True)
    selected["trade_seq"] = np.arange(1, len(selected) + 1)
    selected["dir_key"] = selected["dir"].map(norm_dir)
    selected["signal_time_key"] = selected["date"].map(norm_time)
    selected["entry_time_key"] = selected["entry_time"].map(norm_time)
    selected["trade_key"] = selected["entry_time_key"] + "|" + selected["dir_key"]
    selected["expected_lot"] = LOT_FOR_REPORT
    selected["pnl_points"] = pd.to_numeric(selected["pnl"], errors="coerce")
    selected["expected_pnl_usd_001"] = selected["pnl_points"] * 100.0 * LOT_FOR_REPORT
    selected["candidate_name"] = CANDIDATE_NAME
    selected["candidate_desc"] = CANDIDATE_DESC
    selected["stop"] = selected["structural_stop_price"]
    selected["entry_rule"] = "fixed_delay_1"
    selected["entry_delay_bars"] = 1
    selected["stop_variant"] = "m30_prev_cross_sma13_extreme"
    selected["exit_reason"] = ""
    return selected


def minimal_ledger(expected: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "trade_seq",
        "trade_key",
        "candidate_name",
        "candidate_desc",
        "signal_time_key",
        "entry_time_key",
        "dir_key",
        "entry",
        "stop",
        "stop_distance",
        "exit_time",
        "exit",
        "exit_reason",
        "pnl_points",
        "expected_pnl_usd_001",
        "entry_rule",
        "entry_delay_bars",
        "stop_variant",
        "6h_bias5_signed_pct",
        "6h_bias13_signed_pct",
        "6h_bias55_signed_pct",
    ]
    present = [c for c in cols if c in expected.columns]
    out = expected[present].copy()
    out = out.rename(
        columns={
            "signal_time_key": "signal_time",
            "entry_time_key": "entry_time",
            "dir_key": "dir",
        }
    )
    return out


def summarize_expected(expected: pd.DataFrame) -> dict:
    m = metric(expected["pnl_points"])
    test = split_test(expected["pnl_points"], expected["entry_time"])
    side = expected["dir_key"].astype(str)
    return {
        "candidate": CANDIDATE_NAME,
        "n": m["n"],
        "long_n": int(side.eq("BUY").sum()),
        "short_n": int(side.eq("SELL").sum()),
        "pf": m["pf"],
        "test_pf": test["pf"],
        "pnl_points": m["pnl"],
        "pnl_usd_001": m["pnl"],
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
                "pnl_usd_001": m["pnl"],
            }
        )
    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame, cols: list[str], money_cols: set | None = None) -> str:
    money_cols = money_cols or set()
    if frame is None or frame.empty:
        return "_empty_"
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, row in frame.iterrows():
        cells = []
        for col in cols:
            value = row.get(col, "")
            if col in money_cols and pd.notna(value):
                cells.append(f"{float(value):.2f}")
            elif isinstance(value, float):
                cells.append(f"{value:.4f}")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_parameter_pack(expected: pd.DataFrame, alignment_status: str) -> None:
    summary = summarize_expected(expected)
    pack = {
        "strategy": STRATEGY,
        "date": DATE_LABEL,
        "status": alignment_status,
        "candidate": {
            "name": CANDIDATE_NAME,
            "description": CANDIDATE_DESC,
        },
        "timeframes": {
            "signal": "M30",
            "gate": "H6",
            "context": "H2/M30",
        },
        "entry": {
            "rule": "fixed_delay_1",
            "description": "Open on the first M30 bar after an M30 SMA5/SMA13 cross.",
        },
        "stop": {
            "variant": "m30_prev_cross_sma13_extreme",
            "distance_range_pt": [2.0, 10.0],
            "description": "Latest M30 SMA13 extreme before the cross, within 5pt tolerance.",
        },
        "filters": {
            "bias": "6H bias5_signed_pct > 0 and 6H bias13_signed_pct > 0 and 6H bias55_signed_pct > 0",
        },
        "exit": {
            "historical": "Bar-by-bar stop check first, then opposite M30 SMA5/SMA13 cross at next open.",
        },
        "reporting": {
            "lot_for_report": LOT_FOR_REPORT,
            "expected_trade_count": int(summary["n"]),
            "expected_pnl_usd_001": summary["pnl_usd_001"],
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
            "stop": "expected_stop",
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
        detail[out_col] = pd.to_numeric(detail.get(right), errors="coerce") - pd.to_numeric(
            detail.get(left), errors="coerce"
        )
    matched = detail.loc[detail["_merge"].eq("both")]
    summary = pd.DataFrame(
        [
            {
                "expected_rows": int(len(exp)),
                "actual_rows": int(len(actual)),
                "matched_rows": int(len(matched)),
                "missing_in_actual": int(detail["_merge"].eq("left_only").sum()),
                "extra_in_actual": int(detail["_merge"].eq("right_only").sum()),
                "max_abs_entry_diff": float(pd.to_numeric(matched["entry_diff"], errors="coerce").abs().max())
                if len(matched)
                else np.nan,
                "max_abs_stop_diff": float(pd.to_numeric(matched["stop_diff"], errors="coerce").abs().max())
                if len(matched)
                else np.nan,
                "max_abs_exit_diff": float(pd.to_numeric(matched["exit_diff"], errors="coerce").abs().max())
                if len(matched)
                else np.nan,
                "max_abs_pnl_points_diff": float(
                    pd.to_numeric(matched["pnl_points_diff"], errors="coerce").abs().max()
                )
                if len(matched)
                else np.nan,
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
        {"item": "ea_implementation", "status": "pending", "detail": "2H_M30_6H_CurrentCandidate_EA.mq5 v1.04"},
        {"item": "ea_strategy_tester_run", "status": "pending" if not has_actual else "done", "detail": "MT5 Strategy Tester ledger exported for the current candidate."},
        {"item": "python_vs_ea_alignment", "status": "pending" if summary is None else ("matched" if matched else "mismatch"), "detail": "Python expected ledger compared with EA-exported ledger."},
    ]
    if summary is not None:
        rows.append(
            {
                "item": "alignment_summary",
                "status": "review",
                "detail": json.dumps(summary.iloc[0].to_dict(), ensure_ascii=False),
            }
        )
    return pd.DataFrame(rows)


def make_report(expected: pd.DataFrame, actual_path: Path | None, align_summary: pd.DataFrame | None) -> str:
    overall = pd.DataFrame([summarize_expected(expected)])
    years = yearly_summary(expected)
    cols = ["candidate", "n", "long_n", "short_n", "pf", "test_pf", "pnl_usd_001", "ev_points", "max_loss_streak"]
    year_cols = ["year", "n", "long_n", "short_n", "pf", "pnl_usd_001"]
    lines = [
        "# 2H_M30_6H 当前候选 EA 对齐记录",
        "",
        f"日期：{DATE_LABEL}",
        "",
        "## 当前候选",
        "",
        f"- 主候选：`{CANDIDATE_NAME}`",
        f"- 规则：{CANDIDATE_DESC}",
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
    trades["date"] = pd.to_datetime(trades["date"])
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])
    expected = build_expected(trades)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    expected.to_csv(EXPECTED_LEDGER, index=False, encoding="utf-8-sig")
    minimal_ledger(expected).to_csv(EXPECTED_MINIMAL, index=False, encoding="utf-8-sig")

    actual_path = Path(args.ea_ledger).resolve() if args.ea_ledger else None
    align_summary = None
    if actual_path is not None:
        detail, align_summary = compare_actual(expected, actual_path)
        detail.to_csv(OUT_DIR / "python_vs_ea_alignment_detail.csv", index=False, encoding="utf-8-sig")
        align_summary.to_csv(OUT_DIR / "python_vs_ea_alignment_summary.csv", index=False, encoding="utf-8-sig")

    alignment_status = "python_expected_exported__ea_alignment_pending"
    if align_summary is not None:
        alignment_status = (
            "python_expected_exported__ea_aligned"
            if is_full_match(align_summary)
            else "python_expected_exported__ea_mismatch"
        )
    write_parameter_pack(expected, alignment_status)

    readiness = readiness_rows(actual_path is not None, align_summary)
    readiness.to_csv(OUT_DIR / "ea_alignment_readiness_current_candidate.csv", index=False, encoding="utf-8-sig")
    report = make_report(expected, actual_path, align_summary)
    (OUT_DIR / "ea_alignment_current_candidate_report.md").write_text(report, encoding="utf-8")
    ROOT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    ROOT_REPORT.write_text(report, encoding="utf-8")

    summary = summarize_expected(expected)
    print("2H_M30_6H current candidate EA alignment export")
    print(f"expected_rows={summary['n']} pf={summary['pf']:.4f} test_pf={summary['test_pf']:.4f} usd001={summary['pnl_usd_001']:.2f}")
    print(f"out_dir={OUT_DIR}")
    if actual_path is None:
        print("ea_ledger=not_provided status=python_expected_exported")
    else:
        print(f"ea_ledger={actual_path} status=alignment_computed")


if __name__ == "__main__":
    main()
