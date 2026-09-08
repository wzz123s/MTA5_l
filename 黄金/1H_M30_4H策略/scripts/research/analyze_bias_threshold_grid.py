# -*- coding: utf-8 -*-
"""Run signed-bias fixed-threshold grids for strategy candidates."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



import itertools
import json
import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGIES = ["1H_M30_4H", "2H_M30_6H"]
BIAS_PERIODS = [5, 13, 55]
THRESHOLDS = [round(value / 10.0, 1) for value in range(30, 61, 2)]
PT_VALUE_PER_LOT = 10.0
MIN_SAMPLE = 30


def read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def read_json(path: Path) -> dict:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
    return json.loads(path.read_text())


def parse_lots(text: object) -> tuple[float, float, float]:
    values = [float(item) for item in str(text or "").split("/") if item != ""]
    if len(values) == 3:
        return values[0], values[1], values[2]
    return 0.01, 0.01, 0.04


def parse_stage(pack: dict) -> tuple[float, float, float]:
    stage = pack.get("stage", {})
    return (
        float(stage.get("stage1_r", 2.0)),
        float(stage.get("stage2_trail_r", 2.5)),
        float(stage.get("stage2_force_r", 4.0)),
    )


def parse_stop_range(text: object) -> tuple[float, float] | None:
    value = str(text or "").strip().lower().replace("pt", "")
    if "-" not in value:
        return None
    left, right = value.split("-", 1)
    try:
        return float(left), float(right)
    except ValueError:
        return None


def metric(values: pd.Series) -> dict:
    vals = pd.to_numeric(values, errors="coerce").dropna()
    if vals.empty:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "ev": 0.0, "pnl": 0.0, "maxcl": 0}
    wins = vals[vals > 0]
    losses = vals[vals < 0]
    gross_win = float(wins.sum())
    gross_loss = abs(float(losses.sum()))
    pf = gross_win / gross_loss if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0)
    maxcl = 0
    run = 0
    for value in vals:
        if value < 0:
            run += 1
            maxcl = max(maxcl, run)
        else:
            run = 0
    return {
        "n": int(len(vals)),
        "wr": float((vals > 0).mean() * 100.0),
        "pf": float(pf),
        "ev": float(vals.mean()),
        "pnl": float(vals.sum()),
        "maxcl": int(maxcl),
    }


def split_metrics(values: pd.Series, dates: pd.Series) -> tuple[dict, dict, str]:
    frame = pd.DataFrame({"value": pd.to_numeric(values, errors="coerce"), "date": pd.to_datetime(dates)})
    frame = frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    if frame.empty:
        return metric(pd.Series(dtype=float)), metric(pd.Series(dtype=float)), ""
    cutoff_idx = min(max(int(len(frame) * 0.70), 1), len(frame) - 1)
    cutoff = pd.Timestamp(frame.loc[cutoff_idx, "date"])
    train = frame.loc[frame["date"] < cutoff, "value"]
    test = frame.loc[frame["date"] >= cutoff, "value"]
    return metric(train), metric(test), cutoff.strftime("%Y-%m-%d")


def apply_stage_proxy(frame: pd.DataFrame, stage_params: tuple[float, float, float], lots: tuple[float, float, float]) -> pd.Series:
    stage1_r, trail_r, force_r = stage_params
    pnl = pd.to_numeric(frame["pnl"], errors="coerce").fillna(0.0)
    risk = pd.to_numeric(frame["stop_distance"], errors="coerce").abs().replace(0, math.nan)
    stage1_target = stage1_r * risk
    trail_target = trail_r * risk
    force_target = force_r * risk
    stage1 = pnl.where(pnl <= stage1_target, stage1_target)
    stage2 = pnl.where(pnl <= force_target, trail_target)
    stage3 = pnl
    return (stage1 * lots[0] + stage2 * lots[1] + stage3 * lots[2]) * PT_VALUE_PER_LOT


def yearly_positive_count(frame: pd.DataFrame, value_col: str) -> tuple[int, int]:
    if frame.empty:
        return 0, 0
    scoped = frame.copy()
    scoped["date"] = pd.to_datetime(scoped["date"])
    by_year = scoped.groupby(scoped["date"].dt.year)[value_col].sum()
    return int((by_year > 0).sum()), int(len(by_year))


def timeframe_prefixes(frame: pd.DataFrame) -> list[str]:
    prefixes = set()
    pattern = re.compile(r"^([0-9a-z]+)_bias(?:5|13|55)_signed_pct$")
    for column in frame.columns:
        match = pattern.match(column)
        if match:
            prefixes.add(match.group(1))
    return sorted(prefixes, key=lambda item: (item != "30m", item))


def ensure_formal_fields(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "stop_distance" not in out.columns:
        out["stop_distance"] = (
            pd.to_numeric(out["entry"], errors="coerce")
            - pd.to_numeric(out["stop"], errors="coerce")
        ).abs()
    out["stop_distance"] = pd.to_numeric(out["stop_distance"], errors="coerce")
    return out


def evaluate_filter(
    strategy: str,
    base: pd.DataFrame,
    prefix: str,
    fields: tuple[int, ...],
    threshold: float,
    stage_params: tuple[float, float, float],
    lots: tuple[float, float, float],
    stop_range: tuple[float, float] | None,
) -> dict:
    mask = pd.Series(True, index=base.index)
    field_names = []
    for period in fields:
        field = f"{prefix}_bias{period}_signed_pct"
        field_names.append(field)
        mask &= pd.to_numeric(base[field], errors="coerce").ge(threshold)
    scoped = base.loc[mask].copy()

    raw_total = metric(scoped["pnl"])
    _, raw_test, split_date = split_metrics(scoped["pnl"], scoped["date"])

    if stop_range is not None:
        lo, hi = stop_range
        stage_scoped = scoped.loc[scoped["stop_distance"].between(lo, hi, inclusive="both")].copy()
    else:
        stage_scoped = scoped.copy()
    if stage_scoped.empty:
        stage_scoped["stage_dollars"] = pd.Series(dtype=float)
    else:
        stage_scoped["stage_dollars"] = apply_stage_proxy(stage_scoped, stage_params, lots)
    stage_total = metric(stage_scoped["stage_dollars"])
    _, stage_test, _ = split_metrics(stage_scoped["stage_dollars"], stage_scoped["date"])
    positive_years, total_years = yearly_positive_count(stage_scoped, "stage_dollars")

    filter_type = "single" if len(fields) == 1 else "pair"
    return {
        "strategy": strategy,
        "filter_type": filter_type,
        "timeframe": prefix,
        "bias_fields": "+".join(f"bias{period}" for period in fields),
        "field_names": "+".join(field_names),
        "threshold_pct": threshold,
        "raw_n": raw_total["n"],
        "raw_pf": raw_total["pf"],
        "raw_ev": raw_total["ev"],
        "raw_pnl": raw_total["pnl"],
        "raw_test_pf": raw_test["pf"],
        "raw_test_ev": raw_test["ev"],
        "raw_maxcl": raw_total["maxcl"],
        "stage_n_after_stop": stage_total["n"],
        "stage_pf": stage_total["pf"],
        "stage_ev_usd": stage_total["ev"],
        "stage_pnl_usd": stage_total["pnl"],
        "stage_test_pf": stage_test["pf"],
        "stage_test_ev_usd": stage_test["ev"],
        "positive_years": positive_years,
        "total_years": total_years,
        "split_date": split_date,
    }


def score_rows(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["sample_ok"] = out["raw_n"].astype(float) >= MIN_SAMPLE
    out["score"] = (
        out["sample_ok"].astype(int) * 1000.0
        + out["raw_test_pf"].clip(upper=50) * 10.0
        + out["raw_pf"].clip(upper=50) * 4.0
        + out["raw_test_ev"] * 0.05
        + out["positive_years"] * 2.0
    )
    return out


def analyze_strategy(strategy: str) -> pd.DataFrame:
    strategy_dir = ROOT / "黄金" / f"{strategy}策略"
    signals_path = strategy_dir / "data" / "signals" / "strategy_candidate_trades.csv"
    validation_dir = strategy_dir / "data" / "validation"
    out_dir = validation_dir / "bias_threshold_grid"
    out_dir.mkdir(parents=True, exist_ok=True)

    pack = read_json(validation_dir / "ea_parameter_pack.json")
    lots = parse_lots(pack.get("position", {}).get("lots"))
    stage_params = parse_stage(pack)
    stop_range = parse_stop_range(pack.get("stop_spec", {}).get("primary"))

    candidates = read_csv(signals_path)
    baseline_name = f"{strategy}__baseline"
    base = candidates.loc[candidates["variant"].astype(str) == baseline_name].copy()
    if base.empty:
        base = candidates.copy()
    base["date"] = pd.to_datetime(base["date"])
    base = ensure_formal_fields(base)

    rows = []
    for prefix in timeframe_prefixes(base):
        required = [f"{prefix}_bias{period}_signed_pct" for period in BIAS_PERIODS]
        if not all(column in base.columns for column in required):
            continue
        for threshold in THRESHOLDS:
            for period in BIAS_PERIODS:
                rows.append(evaluate_filter(strategy, base, prefix, (period,), threshold, stage_params, lots, stop_range))
            for pair in itertools.combinations(BIAS_PERIODS, 2):
                rows.append(evaluate_filter(strategy, base, prefix, pair, threshold, stage_params, lots, stop_range))

    result = score_rows(pd.DataFrame(rows)).sort_values(
        ["score", "raw_test_pf", "raw_pf", "raw_n"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    result.to_csv(out_dir / "bias_threshold_grid_summary.csv", index=False, encoding="utf-8-sig")
    result.loc[result["filter_type"].eq("single")].head(20).to_csv(
        out_dir / "bias_threshold_top_single.csv",
        index=False,
        encoding="utf-8-sig",
    )
    result.loc[result["filter_type"].eq("pair")].head(20).to_csv(
        out_dir / "bias_threshold_top_pair.csv",
        index=False,
        encoding="utf-8-sig",
    )
    write_strategy_report(strategy, result, out_dir)
    return result


def fmt(value: object, digits: int = 4) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def money(value: object) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return str(value)


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
            values.append(money(value) if column in money_cols else fmt(value) if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def top_rows(result: pd.DataFrame, filter_type: str, limit: int = 8) -> pd.DataFrame:
    scoped = result.loc[(result["filter_type"] == filter_type) & (result["raw_n"] >= MIN_SAMPLE)].copy()
    if scoped.empty:
        scoped = result.loc[result["filter_type"] == filter_type].copy().sort_values(
            ["raw_n", "raw_test_pf", "raw_pf"],
            ascending=[False, False, False],
        )
    return scoped.head(limit)


def write_strategy_report(strategy: str, result: pd.DataFrame, out_dir: Path) -> None:
    columns = [
        "timeframe",
        "bias_fields",
        "threshold_pct",
        "raw_n",
        "raw_pf",
        "raw_test_pf",
        "raw_test_ev",
        "stage_n_after_stop",
        "stage_pnl_usd",
        "stage_test_pf",
    ]
    lines = [
        f"# {strategy} Bias 阈值网格测试",
        "",
        "- 阈值：`3.0%` 到 `6.0%`，步长 `0.2%`。",
        "- 字段：`bias5_signed_pct`、`bias13_signed_pct`、`bias55_signed_pct`。",
        "- 两两组合：同一周期内两个 bias 字段同时大于等于同一阈值。",
        "- 排名：优先 raw 测试 PF；同时保留当前 StopSpec 后 stage 估算收益。",
        "",
        "## 单项 Top",
        "",
        markdown_table(top_rows(result, "single"), columns, money_cols={"stage_pnl_usd"}),
        "",
        "## 两两组合 Top",
        "",
        markdown_table(top_rows(result, "pair"), columns, money_cols={"stage_pnl_usd"}),
    ]
    (out_dir / "bias_threshold_grid_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_root_report(all_results: dict[str, pd.DataFrame]) -> None:
    rows = []
    for strategy, result in all_results.items():
        for filter_type in ["single", "pair"]:
            scoped = top_rows(result, filter_type, limit=1)
            if scoped.empty:
                continue
            row = scoped.iloc[0].to_dict()
            row["strategy"] = strategy
            row["best_scope"] = "single" if filter_type == "single" else "pair"
            row["sample_status"] = "ok" if float(row["raw_n"]) >= MIN_SAMPLE else "insufficient"
            rows.append(row)
    summary = pd.DataFrame(rows)
    columns = [
        "strategy",
        "best_scope",
        "timeframe",
        "bias_fields",
        "threshold_pct",
        "raw_n",
        "raw_pf",
        "raw_test_pf",
        "raw_test_ev",
        "stage_n_after_stop",
        "stage_pnl_usd",
        "stage_test_pf",
        "sample_status",
    ]
    lines = [
        "# Python Bias 固定阈值网格测试记录",
        "",
        "日期：2026-07-25",
        "",
        "## 口径",
        "",
        "- 阈值范围：`3.0%` 到 `6.0%`，每 `0.2%` 一档。",
        "- 单项过滤：`bias5`、`bias13`、`bias55` 分别测试。",
        "- 两两组合：`bias5+bias13`、`bias5+bias55`、`bias13+bias55`，同周期、同阈值同时满足。",
        "- 过滤字段全部使用 `*_signed_pct`，不是 top30%，不是 abs。",
        "",
        "## 最优摘要",
        "",
        markdown_table(summary[columns], columns, money_cols={"stage_pnl_usd"}),
        "",
        "## 输出文件",
        "",
    ]
    for strategy in all_results:
        lines.append(f"- `{strategy}`: `{strategy}策略/data/validation/bias_threshold_grid/bias_threshold_grid_summary.csv`")
        lines.append(f"- `{strategy}`: `{strategy}策略/data/validation/bias_threshold_grid/bias_threshold_grid_report.md`")
    (ROOT / "Python策略Bias固定阈值测试记录.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    all_results = {strategy: analyze_strategy(strategy) for strategy in STRATEGIES}
    write_root_report(all_results)
    for strategy, result in all_results.items():
        single = top_rows(result, "single", 1).iloc[0]
        pair = top_rows(result, "pair", 1).iloc[0]
        print(
            f"{strategy}: single={single['timeframe']} {single['bias_fields']} >= {single['threshold_pct']:.1f}% "
            f"n={int(single['raw_n'])} test_pf={float(single['raw_test_pf']):.4f}; "
            f"pair={pair['timeframe']} {pair['bias_fields']} >= {pair['threshold_pct']:.1f}% "
            f"n={int(pair['raw_n'])} test_pf={float(pair['raw_test_pf']):.4f}"
        )


if __name__ == "__main__":
    main()
