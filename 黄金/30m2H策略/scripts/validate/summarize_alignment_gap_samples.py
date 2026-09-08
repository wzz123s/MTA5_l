# -*- coding: utf-8 -*-
"""Summarize EA extra samples that are caused by missing aligned M30 bars."""
from __future__ import annotations


import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
ROOT_SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(STRATEGY_SCRIPTS_DIR))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT_SCRIPTS_DIR))

from strategy_30m2h_common import RESULT_SOURCES, VALIDATION_DIR, export_csv, write_text  # noqa: E402


OUTPUT_DIR = VALIDATION_DIR / "ea_python_full_history_alignment_20260709"
EA_EXTRA_PATH = RESULT_SOURCES["ea_python_diff"] / "ea_extra_vs_python_executed.csv"
ALIGN_DIAG_PATH = RESULT_SOURCES["ea_python_diff"] / "ea_signal_alignment_diag.csv"


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "| 空 | 空 |\n| --- | --- |"
    headers = list(frame.columns)
    lines = [
        "| " + " | ".join(str(x) for x in headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in headers) + " |")
    return "\n".join(lines)


def main() -> None:
    ea_extra = pd.read_csv(EA_EXTRA_PATH, encoding="utf-8-sig")
    align = pd.read_csv(ALIGN_DIAG_PATH, encoding="utf-8-sig")

    for col in [
        "log_time",
        "anchor_time",
        "aligned_time",
        "market_prev_time",
        "market_next_time",
    ]:
        if col in ea_extra.columns:
            ea_extra[col] = pd.to_datetime(ea_extra[col], errors="coerce")
        if col in align.columns:
            align[col] = pd.to_datetime(align[col], errors="coerce")

    if "align_status" in ea_extra.columns:
        merged = ea_extra.copy()
    else:
        join_cols = [
            "log_time",
            "anchor_time",
            "aligned_time",
            "dir",
            "trigger",
            "mode_raw",
            "mode_norm",
            "aligned_in_market",
            "market_prev_time",
            "market_next_time",
            "align_status",
        ]
        merged = ea_extra.merge(
            align[join_cols],
            on=["log_time", "anchor_time", "aligned_time", "dir", "trigger", "mode_raw", "mode_norm"],
            how="left",
        )

    gap_mask = merged["align_status"].eq("missing_align_bar_next_available")
    gap_samples = merged[gap_mask].copy().reset_index(drop=True)
    normal_samples = merged[~gap_mask].copy().reset_index(drop=True)

    summary = pd.DataFrame(
        [
            {
                "EA额外样本总数": int(len(merged)),
                "时间轴缺口样本数": int(len(gap_samples)),
                "普通剩余样本数": int(len(normal_samples)),
                "时间轴缺口样本占比(%)": round(len(gap_samples) / len(merged) * 100.0, 4) if len(merged) else 0.0,
            }
        ]
    )

    gap_export = gap_samples[
        [
            c
            for c in [
                "log_time",
                "anchor_time",
                "aligned_time",
                "dir",
                "trigger",
                "mode_raw",
                "aligned_in_market",
                "market_prev_time",
                "market_next_time",
                "align_status",
            ]
            if c in gap_samples.columns
        ]
    ].rename(
        columns={
            "log_time": "EA日志时间",
            "anchor_time": "EA信号锚点",
            "aligned_time": "对齐后时间",
            "dir": "方向",
            "trigger": "触发类型",
            "mode_raw": "模式",
            "aligned_in_market": "对齐时间是否存在于Python_M30",
            "market_prev_time": "Python上一根M30",
            "market_next_time": "Python下一根M30",
            "align_status": "时间轴诊断标签",
        }
    )

    normal_export = normal_samples[
        [
            c
            for c in [
                "log_time",
                "anchor_time",
                "aligned_time",
                "dir",
                "trigger",
                "mode_raw",
                "aligned_in_market",
                "align_status",
            ]
            if c in normal_samples.columns
        ]
    ].rename(
        columns={
            "log_time": "EA日志时间",
            "anchor_time": "EA信号锚点",
            "aligned_time": "对齐后时间",
            "dir": "方向",
            "trigger": "触发类型",
            "mode_raw": "模式",
            "aligned_in_market": "对齐时间是否存在于Python_M30",
            "align_status": "时间轴诊断标签",
        }
    )

    lines = [
        "# 全历史 EA 对齐缺口样本汇总",
        "",
        "## 总览",
        "",
        markdown_table(summary),
        "",
        "## 结论",
        "",
        "- 这份汇总只看 `EA extra vs Python executed` 集合。",
        "- `时间轴缺口样本` 指：EA 对齐后的 `aligned_time` 不存在于 Python prepared M30 时间轴，标签为 `missing_align_bar_next_available`。",
        "- 这类样本应先从普通 `Layer3 / spec / 执行占用` 残差中拆开，避免继续混判。",
        "",
        "## 时间轴缺口样本",
        "",
        markdown_table(gap_export),
        "",
        "## 普通剩余样本",
        "",
        markdown_table(normal_export.head(20)),
        "",
    ]

    export_csv(summary, OUTPUT_DIR / "全历史EA对齐缺口样本汇总_20260709.csv")
    export_csv(gap_export, OUTPUT_DIR / "时间轴缺口样本明细_20260709.csv")
    export_csv(normal_export, OUTPUT_DIR / "普通剩余样本明细_20260709.csv")
    write_text(OUTPUT_DIR / "全历史EA对齐缺口样本汇总_20260709.md", "\n".join(lines))
    print(f"Wrote {OUTPUT_DIR}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
