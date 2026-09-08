# -*- coding: utf-8 -*-
"""Analyze BUY/SELL and higher-timeframe direction filters for strategy research data."""
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
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
DEFAULT_STRATEGIES = ["1H_M30_4H", "2H_M30_6H"]
PT_VALUE_PER_LOT = 10.0
MIN_SAMPLE = 30


@dataclass(frozen=True)
class DirectionFilter:
    name: str
    desc: str
    mask: pd.Series


def read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "gbk", "ansi"):
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
    if len(values) != 3:
        return 0.01, 0.01, 0.04
    return values[0], values[1], values[2]


def parse_stop_range(text: object) -> tuple[float, float] | None:
    value = str(text or "").strip().lower().replace("pt", "")
    if "-" not in value:
        return None
    left, right = value.split("-", 1)
    try:
        return float(left), float(right)
    except ValueError:
        return None


def focus_from_variant(variant: str) -> str:
    key = variant.split("__", 1)[1] if "__" in variant else variant
    if key == "baseline":
        return "30m"
    return key.split("_", 1)[0].lower()


def trade_sign(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.upper().str.strip()
    return text.map({"L": 1, "LONG": 1, "BUY": 1, "S": -1, "SHORT": -1, "SELL": -1}).fillna(0).astype(int)


def metric(points: Iterable[float]) -> dict:
    values = pd.Series(list(points), dtype="float64").dropna()
    if values.empty:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "ev": 0.0, "pnl": 0.0, "maxcl": 0}
    wins = values[values > 0]
    losses = values[values < 0]
    gain = float(wins.sum())
    loss = float(losses.sum())
    if loss < 0:
        pf = gain / abs(loss)
    elif gain > 0:
        pf = 999.0
    else:
        pf = 0.0

    maxcl = 0
    run = 0
    for value in values:
        if value < 0:
            run += 1
            maxcl = max(maxcl, run)
        else:
            run = 0

    return {
        "n": int(len(values)),
        "wr": float((values > 0).mean() * 100.0),
        "pf": float(pf),
        "ev": float(values.mean()),
        "pnl": float(values.sum()),
        "maxcl": int(maxcl),
    }


def split_metrics(points: pd.Series, dates: pd.Series) -> tuple[dict, dict, str]:
    if len(points) == 0:
        return metric([]), metric([]), ""
    frame = pd.DataFrame({"points": pd.to_numeric(points, errors="coerce"), "date": pd.to_datetime(dates)})
    frame = frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    if frame.empty:
        return metric([]), metric([]), ""
    cutoff_idx = min(max(int(len(frame) * 0.70), 1), len(frame) - 1)
    cutoff = pd.Timestamp(frame.loc[cutoff_idx, "date"])
    train = frame.loc[frame["date"] < cutoff, "points"]
    test = frame.loc[frame["date"] >= cutoff, "points"]
    return metric(train), metric(test), cutoff.strftime("%Y-%m-%d")


def ensure_stop_distance(frame: pd.DataFrame) -> pd.DataFrame:
    """Ensure formal StopSpec fields exist for direction analysis."""
    out = frame.copy()
    if "structural_stop_price" not in out.columns:
        out["structural_stop_price"] = out["stop"] if "stop" in out.columns else pd.NA
    if "stop_distance" not in out.columns:
        out["stop_distance"] = (
            pd.to_numeric(out["entry"], errors="coerce")
            - pd.to_numeric(out["structural_stop_price"], errors="coerce")
        ).abs()
    out["stop_distance"] = pd.to_numeric(out["stop_distance"], errors="coerce")
    return out


def stage_dollars(frame: pd.DataFrame, lots: tuple[float, float, float]) -> pd.Series:
    total = pd.Series(0.0, index=frame.index)
    for idx, lot in enumerate(lots, start=1):
        col = f"stage{idx}_pnl"
        if col not in frame.columns:
            continue
        total = total + pd.to_numeric(frame[col], errors="coerce").fillna(0.0) * lot * PT_VALUE_PER_LOT
    return total


def direction_columns(frame: pd.DataFrame) -> list[str]:
    columns = []
    for col in frame.columns:
        if re.fullmatch(r"[0-9a-z]+_dir", col):
            columns.append(col)
    return sorted(columns, key=lambda item: (item == "30m_dir", item))


def build_filters(frame: pd.DataFrame) -> list[DirectionFilter]:
    sign = trade_sign(frame["dir"])
    filters = [
        DirectionFilter("both", "双向全部", pd.Series(True, index=frame.index)),
        DirectionFilter("buy_only", "只做 BUY/LONG", sign.eq(1)),
        DirectionFilter("sell_only", "只做 SELL/SHORT", sign.eq(-1)),
    ]

    htf_align_masks = []
    for col in direction_columns(frame):
        prefix = col[: -len("_dir")]
        tf_dir = pd.to_numeric(frame[col], errors="coerce").fillna(0).astype(int)
        align = tf_dir.ne(0) & tf_dir.eq(sign)
        against = tf_dir.ne(0) & tf_dir.eq(-sign)
        neutral = tf_dir.eq(0)
        filters.extend(
            [
                DirectionFilter(f"{prefix}_dir_align", f"{prefix.upper()} 方向同向", align),
                DirectionFilter(f"{prefix}_dir_against", f"{prefix.upper()} 方向反向", against),
                DirectionFilter(f"{prefix}_dir_neutral", f"{prefix.upper()} 方向中性/缺失", neutral),
            ]
        )
        if prefix != "30m":
            htf_align_masks.append(align)

    if htf_align_masks:
        combined = htf_align_masks[0].copy()
        for mask in htf_align_masks[1:]:
            combined = combined & mask
        filters.append(DirectionFilter("all_htf_dir_align", "所有高周期方向同向", combined))

    return filters


def yearly_summary(strategy: str, variant: str, filter_name: str, frame: pd.DataFrame, value_col: str) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()
    out = frame.copy()
    out["date"] = pd.to_datetime(out["date"])
    rows = []
    for year, group in out.groupby(out["date"].dt.year):
        stats = metric(group[value_col])
        rows.append(
            {
                "strategy": strategy,
                "variant": variant,
                "filter": filter_name,
                "year": int(year),
                "trades": stats["n"],
                "wr": stats["wr"],
                "pf": stats["pf"],
                "ev": stats["ev"],
                "pnl": stats["pnl"],
            }
        )
    return pd.DataFrame(rows)


def evaluate_filter(
    strategy: str,
    variant: str,
    frame: pd.DataFrame,
    direction_filter: DirectionFilter,
    lots: tuple[float, float, float],
    stop_range: tuple[float, float] | None,
) -> tuple[dict, pd.DataFrame]:
    scoped = frame.loc[direction_filter.mask].copy()
    raw_stats = metric(pd.to_numeric(scoped["pnl"], errors="coerce")) if "pnl" in scoped.columns else metric([])
    _, raw_test, split_date = split_metrics(pd.to_numeric(scoped.get("pnl", pd.Series(dtype=float)), errors="coerce"), scoped.get("date", pd.Series(dtype=str)))

    if stop_range is not None:
        lo, hi = stop_range
        scoped_for_stage = scoped.loc[scoped["stop_distance"].between(lo, hi, inclusive="both")].copy()
    else:
        scoped_for_stage = scoped.copy()
    scoped_for_stage["stage_dollars"] = stage_dollars(scoped_for_stage, lots)
    stage_stats = metric(scoped_for_stage["stage_dollars"])
    _, stage_test, _ = split_metrics(scoped_for_stage["stage_dollars"], scoped_for_stage.get("date", pd.Series(dtype=str)))

    years = yearly_summary(strategy, variant, direction_filter.name, scoped_for_stage, "stage_dollars")
    positive_years = int((years["pnl"] > 0).sum()) if not years.empty else 0
    total_years = int(years["year"].nunique()) if not years.empty else 0

    score = (
        (1 if stage_stats["n"] >= MIN_SAMPLE else 0) * 1000.0
        + min(stage_stats["pf"], 50.0) * 10.0
        + min(stage_test["pf"], 50.0) * 2.0
        + stage_stats["ev"] * 0.05
        + positive_years * 5.0
    )
    row = {
        "strategy": strategy,
        "variant": variant,
        "filter": direction_filter.name,
        "desc": direction_filter.desc,
        "raw_trades": raw_stats["n"],
        "raw_wr": raw_stats["wr"],
        "raw_pf": raw_stats["pf"],
        "raw_ev_points": raw_stats["ev"],
        "raw_pnl_points": raw_stats["pnl"],
        "raw_test_pf": raw_test["pf"],
        "raw_test_ev_points": raw_test["ev"],
        "stage_trades_after_stop": stage_stats["n"],
        "stage_wr": stage_stats["wr"],
        "stage_pf": stage_stats["pf"],
        "stage_ev_usd": stage_stats["ev"],
        "stage_pnl_usd": stage_stats["pnl"],
        "stage_test_pf": stage_test["pf"],
        "stage_test_ev_usd": stage_test["ev"],
        "max_loss_streak": stage_stats["maxcl"],
        "positive_years": positive_years,
        "total_years": total_years,
        "split_date": split_date,
        "score": score,
    }
    return row, years


def analyze_strategy(strategy: str) -> dict:
    strategy_dir = ROOT / "黄金" / f"{strategy}策略"
    validation_dir = strategy_dir / "data" / "validation"
    signals_dir = strategy_dir / "data" / "signals"
    out_dir = validation_dir / "direction_test"
    out_dir.mkdir(parents=True, exist_ok=True)

    pack = read_json(validation_dir / "ea_parameter_pack.json")
    primary_variant = str(pack.get("primary_variant") or "")
    if not primary_variant:
        final_summary = read_csv(validation_dir / "combo_final_best_summary.csv")
        primary_variant = str(final_summary["picked_variant"].iloc[0])

    lots = parse_lots(pack.get("position", {}).get("lots"))
    stop_range = parse_stop_range(pack.get("stop_spec", {}).get("primary"))
    candidates = read_csv(signals_dir / "strategy_candidate_trades.csv")
    candidates["date"] = pd.to_datetime(candidates["date"])

    primary = candidates.loc[candidates["variant"].astype(str) == primary_variant].copy().sort_values("date")
    if primary.empty:
        raise RuntimeError(f"{strategy}: no rows for primary variant {primary_variant}")
    primary = ensure_stop_distance(primary)

    rows = []
    years = []
    for direction_filter in build_filters(primary):
        row, yearly = evaluate_filter(strategy, primary_variant, primary, direction_filter, lots, stop_range)
        rows.append(row)
        if not yearly.empty:
            years.append(yearly)

    summary = pd.DataFrame(rows).sort_values(
        ["score", "stage_test_ev_usd", "stage_pnl_usd"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    yearly = pd.concat(years, ignore_index=True) if years else pd.DataFrame()

    variant_summary = read_csv(signals_dir / "strategy_variant_summary.csv")
    variant_summary["is_direction_family"] = variant_summary["variant"].astype(str).str.contains(
        "dir_align|recent2|close_side", regex=True
    )
    top_direction_variants = variant_summary.loc[variant_summary["is_direction_family"]].copy()
    top_direction_variants = top_direction_variants.sort_values(
        ["test_pf", "pf", "ev", "n"],
        ascending=[False, False, False, False],
    ).head(8)

    summary.to_csv(out_dir / "direction_filter_summary.csv", index=False, encoding="utf-8-sig")
    yearly.to_csv(out_dir / "direction_yearly_summary.csv", index=False, encoding="utf-8-sig")
    top_direction_variants.to_csv(out_dir / "direction_variant_candidates.csv", index=False, encoding="utf-8-sig")
    write_report(strategy, primary_variant, lots, stop_range, summary, yearly, top_direction_variants, out_dir)

    best = summary.iloc[0].to_dict()
    return {
        "strategy": strategy,
        "primary_variant": primary_variant,
        "best_filter": best["filter"],
        "best_desc": best["desc"],
        "stage_trades_after_stop": int(best["stage_trades_after_stop"]),
        "stage_pnl_usd": float(best["stage_pnl_usd"]),
        "stage_pf": float(best["stage_pf"]),
        "stage_test_pf": float(best["stage_test_pf"]),
        "positive_years": int(best["positive_years"]),
        "total_years": int(best["total_years"]),
    }


def fmt_money(value: float) -> str:
    return f"${value:,.2f}"


def fmt_float(value: object, digits: int = 4) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if math.isinf(number):
        return "inf"
    return f"{number:.{digits}f}"


def markdown_table(frame: pd.DataFrame, columns: list[str], money_cols: set[str] | None = None) -> str:
    money_cols = money_cols or set()
    if frame.empty:
        return "| 空 | 空 |\n| --- | --- |"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for col in columns:
            value = row[col]
            if col in money_cols:
                values.append(fmt_money(float(value)))
            elif isinstance(value, float):
                values.append(fmt_float(value))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_report(
    strategy: str,
    primary_variant: str,
    lots: tuple[float, float, float],
    stop_range: tuple[float, float] | None,
    summary: pd.DataFrame,
    yearly: pd.DataFrame,
    top_direction_variants: pd.DataFrame,
    out_dir: Path,
) -> None:
    stop_label = f"{stop_range[0]:g}-{stop_range[1]:g}pt" if stop_range else "disabled"
    top = summary.head(10).copy()
    top_cols = [
        "filter",
        "desc",
        "stage_trades_after_stop",
        "stage_pnl_usd",
        "stage_pf",
        "stage_test_pf",
        "stage_test_ev_usd",
        "positive_years",
        "total_years",
    ]
    variant_cols = ["variant", "desc", "n", "pf", "ev", "test_pf", "test_ev", "split_date"]

    focus_filters = ["both", "buy_only", "sell_only"]
    direction_yearly = yearly.loc[yearly["filter"].isin(focus_filters)].copy()
    year_cols = ["filter", "year", "trades", "pnl", "pf", "ev"]

    lines = [
        f"# {strategy} Python 方向测试",
        "",
        f"- primary variant: `{primary_variant}`",
        f"- lots: `{lots[0]:.2f}/{lots[1]:.2f}/{lots[2]:.2f}`",
        f"- StopSpec: `{stop_label}`",
        "- 口径：读取 Python 候选交易，按当前参数包 StopSpec 过滤后，用 stage1/2/3 pnl 和 lots 估算美元收益。",
        "- StopSpec source: `stop_distance`。",
        "",
        "## 方向过滤排名",
        "",
        markdown_table(top[top_cols], top_cols, money_cols={"stage_pnl_usd", "stage_test_ev_usd"}),
        "",
        "## BUY / SELL 年度拆分",
        "",
        markdown_table(direction_yearly[year_cols], year_cols, money_cols={"pnl"}),
        "",
        "## 现有方向类候选门",
        "",
        markdown_table(top_direction_variants[variant_cols], variant_cols),
        "",
        "## 备注",
        "",
        "- 这是 Python 研究层测试，不代表当前 EA 已可交易。",
        "- 方向过滤若样本数低于 30，只能作为线索，不能直接作为部署规则。",
        "- 下一步应把入选方向规则加入专用 EA 后重新做 Python vs EA 逐笔对齐。",
    ]
    (out_dir / "direction_test_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_root_report(results: list[dict]) -> None:
    frame = pd.DataFrame(results)
    out_path = ROOT / "Python策略方向测试记录.md"
    columns = [
        "strategy",
        "primary_variant",
        "best_filter",
        "best_desc",
        "stage_trades_after_stop",
        "stage_pnl_usd",
        "stage_pf",
        "stage_test_pf",
        "positive_years",
        "total_years",
    ]
    lines = [
        "# Python 策略方向测试记录",
        "",
        "日期：2026-07-25",
        "",
        "## 汇总",
        "",
        markdown_table(frame[columns], columns, money_cols={"stage_pnl_usd"}),
        "",
        "## 输出文件",
        "",
    ]
    for result in results:
        strategy = result["strategy"]
        lines.extend(
            [
                f"- `{strategy}`: `{strategy}策略/data/validation/direction_test/direction_filter_summary.csv`",
                f"- `{strategy}`: `{strategy}策略/data/validation/direction_test/direction_yearly_summary.csv`",
                f"- `{strategy}`: `{strategy}策略/data/validation/direction_test/direction_test_report.md`",
            ]
        )
    lines.extend(
        [
            "",
            "## 解释",
            "",
            "本测试只使用 Python 研究数据，目的是先判断策略方向和高周期方向门是否有收益倾向。它不代表 EA 已经对齐或可以部署。",
        ]
    )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", action="append", choices=DEFAULT_STRATEGIES, help="Strategy name to analyze. Defaults to both.")
    args = parser.parse_args()
    strategies = args.strategy or DEFAULT_STRATEGIES
    results = [analyze_strategy(strategy) for strategy in strategies]
    write_root_report(results)
    for item in results:
        print(
            f"{item['strategy']}: best={item['best_filter']} "
            f"pnl={item['stage_pnl_usd']:.2f} pf={item['stage_pf']:.4f} "
            f"test_pf={item['stage_test_pf']:.4f} years={item['positive_years']}/{item['total_years']}"
        )


if __name__ == "__main__":
    main()
