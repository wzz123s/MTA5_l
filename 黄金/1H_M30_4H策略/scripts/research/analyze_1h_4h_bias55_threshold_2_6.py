# -*- coding: utf-8 -*-
"""Focused 1H_M30_4H 4H-bias55 fixed-threshold scan from 2% to 6%."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



import pandas as pd

from analyze_bias_threshold_grid import (
    ROOT,
    evaluate_filter,
    fmt,
    money,
    parse_lots,
    parse_stage,
    parse_stop_range,
    read_csv,
    read_json,
    score_rows,
)


STRATEGY = "1H_M30_4H"
PREFIX = "4h"
FIELDS = (55,)
THRESHOLDS = [round(value / 10.0, 1) for value in range(20, 61, 2)]
MIN_SAMPLE = 30


def markdown_table(frame: pd.DataFrame, columns: list[str], money_cols: set[str] | None = None) -> str:
    money_cols = money_cols or set()
    if frame.empty:
        return "| empty | empty |\n| --- | --- |"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if column in money_cols:
                values.append(money(value))
            elif isinstance(value, float):
                values.append(fmt(value))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def load_base() -> tuple[pd.DataFrame, tuple[float, float, float], tuple[float, float, float], tuple[float, float] | None]:
    strategy_dir = ROOT / "黄金" / f"{STRATEGY}策略"
    validation_dir = strategy_dir / "data" / "validation"
    signals_path = strategy_dir / "data" / "signals" / "strategy_candidate_trades.csv"

    pack = read_json(validation_dir / "ea_parameter_pack.json")
    lots = parse_lots(pack.get("position", {}).get("lots"))
    stage_params = parse_stage(pack)
    stop_range = parse_stop_range(pack.get("stop_spec", {}).get("primary"))

    candidates = read_csv(signals_path)
    baseline_name = f"{STRATEGY}__baseline"
    base = candidates.loc[candidates["variant"].astype(str) == baseline_name].copy()
    if base.empty:
        base = candidates.copy()
    base["date"] = pd.to_datetime(base["date"])
    if "stop_distance" not in base.columns:
        base["stop_distance"] = (
            pd.to_numeric(base["entry"], errors="coerce") - pd.to_numeric(base["stop"], errors="coerce")
        ).abs()
    base["stop_distance"] = pd.to_numeric(base["stop_distance"], errors="coerce")
    return base, stage_params, lots, stop_range


def analyze() -> pd.DataFrame:
    base, stage_params, lots, stop_range = load_base()
    field = f"{PREFIX}_bias55_signed_pct"
    if field not in base.columns:
        raise KeyError(f"Missing required field: {field}")

    rows = [
        evaluate_filter(STRATEGY, base, PREFIX, FIELDS, threshold, stage_params, lots, stop_range)
        for threshold in THRESHOLDS
    ]
    result = score_rows(pd.DataFrame(rows)).sort_values(
        ["score", "raw_test_pf", "raw_pf", "raw_n"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    result["sample_status"] = result["raw_n"].ge(MIN_SAMPLE).map({True: "ok", False: "insufficient"})
    return result


def write_outputs(result: pd.DataFrame) -> None:
    out_dir = ROOT / "黄金" / f"{STRATEGY}策略" / "data" / "validation" / "bias55_4h_threshold_2_6"
    out_dir.mkdir(parents=True, exist_ok=True)

    result.to_csv(out_dir / "bias55_4h_threshold_2_6_summary.csv", index=False, encoding="utf-8-sig")
    by_threshold = result.sort_values("threshold_pct").reset_index(drop=True)
    by_threshold.to_csv(out_dir / "bias55_4h_threshold_2_6_by_threshold.csv", index=False, encoding="utf-8-sig")

    columns = [
        "threshold_pct",
        "raw_n",
        "raw_pf",
        "raw_test_pf",
        "raw_test_ev",
        "stage_n_after_stop",
        "stage_pnl_usd",
        "stage_test_pf",
        "positive_years",
        "total_years",
        "sample_status",
    ]
    ok = result.loc[result["raw_n"].ge(MIN_SAMPLE)].copy()
    best = ok.head(1) if not ok.empty else result.head(1)

    report_lines = [
        "# 1H_M30_4H 4H bias55 2%-6% 阈值测试",
        "",
        "日期：2026-07-25",
        "",
        "## 口径",
        "",
        "- 策略：`1H_M30_4H`。",
        "- 字段：`4h_bias55_signed_pct`。",
        "- 阈值：`2.0%` 到 `6.0%`，每 `0.2%` 一档。",
        "- 过滤方式：只保留 `4h_bias55_signed_pct >= threshold` 的 baseline M30 cross 信号。",
        "- StopSpec：继续使用规则文件中的结构止损 `stop_distance` primary 区间。",
        "",
        "## 最优摘要",
        "",
        markdown_table(best[columns], columns, money_cols={"stage_pnl_usd"}),
        "",
        "## 按阈值连续观察",
        "",
        markdown_table(by_threshold[columns], columns, money_cols={"stage_pnl_usd"}),
        "",
        "## 输出文件",
        "",
        "- `黄金/1H_M30_4H策略/data/validation/bias55_4h_threshold_2_6/bias55_4h_threshold_2_6_summary.csv`",
        "- `黄金/1H_M30_4H策略/data/validation/bias55_4h_threshold_2_6/bias55_4h_threshold_2_6_by_threshold.csv`",
    ]
    report = "\n".join(report_lines) + "\n"
    (out_dir / "bias55_4h_threshold_2_6_report.md").write_text(report, encoding="utf-8")
    (ROOT / "Python策略1H_4H_bias55_2_6测试记录.md").write_text(report, encoding="utf-8")


def main() -> None:
    result = analyze()
    write_outputs(result)
    best = result.loc[result["raw_n"].ge(MIN_SAMPLE)].head(1)
    if best.empty:
        best = result.head(1)
    row = best.iloc[0]
    print(
        f"{STRATEGY}: 4h bias55 >= {row['threshold_pct']:.1f}% "
        f"n={int(row['raw_n'])} raw_pf={float(row['raw_pf']):.4f} "
        f"test_pf={float(row['raw_test_pf']):.4f} stage_pnl=${float(row['stage_pnl_usd']):.2f}"
    )


if __name__ == "__main__":
    main()
