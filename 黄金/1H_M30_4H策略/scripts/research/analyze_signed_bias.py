# -*- coding: utf-8 -*-
"""Summarize directional signed-bias variants for rebuilt strategies."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



from pathlib import Path

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGIES = ["1H_M30_4H", "2H_M30_6H"]


def read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def fmt_float(value: object, digits: int = 4) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "| empty | empty |\n| --- | --- |"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for col in columns:
            value = row[col]
            values.append(fmt_float(value) if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def analyze_strategy(strategy: str) -> pd.DataFrame:
    strategy_dir = ROOT / "黄金" / f"{strategy}策略"
    signals_dir = strategy_dir / "data" / "signals"
    out_dir = strategy_dir / "data" / "validation" / "bias_signed_test"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = read_csv(signals_dir / "strategy_variant_summary.csv")
    scoped = summary.loc[summary["variant"].astype(str).str.contains("bias", case=False, regex=False)].copy()
    scoped.insert(0, "strategy", strategy)
    scoped = scoped.sort_values(
        ["test_pf", "pf", "ev", "n"],
        ascending=[False, False, False, False],
    ).reset_index(drop=True)
    scoped.to_csv(out_dir / "bias_signed_variant_summary.csv", index=False, encoding="utf-8-sig")
    scoped.head(20).to_csv(out_dir / "bias_signed_top20.csv", index=False, encoding="utf-8-sig")
    return scoped


def main() -> None:
    frames = [analyze_strategy(strategy) for strategy in STRATEGIES]
    combined = pd.concat(frames, ignore_index=True)
    top = combined.groupby("strategy", group_keys=False).head(10).reset_index(drop=True)
    columns = ["strategy", "variant", "desc", "n", "pf", "ev", "test_pf", "test_ev", "split_date"]
    lines = [
        "# Python 带方向 Bias 测试记录",
        "",
        "日期：2026-07-25",
        "",
        "## 口径",
        "",
        "- `bias5/bias13/bias55` 使用带方向偏离。",
        "- 排名基于 Python 候选交易表现，优先看 `test_pf`，再看全样本 `pf/ev`。",
        "- `recent2_any` 和 ATR 不进入本表。",
        "",
        "## Top Signed-Bias 候选",
        "",
        markdown_table(top[columns], columns),
        "",
        "## 输出文件",
        "",
    ]
    for strategy in STRATEGIES:
        lines.append(f"- `{strategy}`: `{strategy}策略/data/validation/bias_signed_test/bias_signed_variant_summary.csv`")
        lines.append(f"- `{strategy}`: `{strategy}策略/data/validation/bias_signed_test/bias_signed_top20.csv`")
    (ROOT / "Python策略带方向Bias测试记录.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for strategy, frame in combined.groupby("strategy"):
        row = frame.iloc[0]
        print(
            f"{strategy}: best_bias={row['variant']} n={int(row['n'])} "
            f"pf={float(row['pf']):.4f} test_pf={float(row['test_pf']):.4f}"
        )


if __name__ == "__main__":
    main()
