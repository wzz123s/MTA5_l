# -*- coding: utf-8 -*-
"""Classify non-gap EA extra samples by divergence stage."""
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
NORMAL_EXTRA_PATH = OUTPUT_DIR / "普通剩余样本明细_20260709.csv"
RESULT_ROOT = RESULT_SOURCES["ea_python_diff"]
ACCEPTED_PATH = RESULT_ROOT / "python_accepted_signals.csv"
PICKED_PATH = RESULT_ROOT / "python_picked_signals.csv"
EXECUTED_PATH = RESULT_ROOT / "python_executed_signals.csv"


def _build_key(df: pd.DataFrame, time_col: str) -> pd.Series:
    t = pd.to_datetime(df[time_col])
    return t.dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + df["dir"].astype(str)


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
    normal = pd.read_csv(NORMAL_EXTRA_PATH, encoding="utf-8-sig")
    accepted = pd.read_csv(ACCEPTED_PATH, encoding="utf-8-sig")
    picked = pd.read_csv(PICKED_PATH, encoding="utf-8-sig")
    executed = pd.read_csv(EXECUTED_PATH, encoding="utf-8-sig")

    normal = normal.rename(columns={"对齐后时间": "aligned_time", "方向": "dir"}).copy()
    normal["aligned_time"] = pd.to_datetime(normal["aligned_time"])
    normal["key"] = _build_key(normal, "aligned_time")

    accepted["anchor_time"] = pd.to_datetime(accepted["anchor_time"])
    picked["anchor_time"] = pd.to_datetime(picked["anchor_time"])
    executed["anchor_time"] = pd.to_datetime(executed["anchor_time"])

    accepted["key"] = _build_key(accepted, "anchor_time")
    picked["key"] = _build_key(picked, "anchor_time")
    executed["key"] = _build_key(executed, "anchor_time")

    acc_cols = ["key", "spec_reason", "sd", "variant", "Bias_5"]
    pick_cols = ["key", "spec_reason", "sd", "variant", "Bias_5_ea", "layer3_threshold_ea", "layer3_pass_ea"]
    exe_cols = ["key", "variant", "sd", "stage3_time"]

    merged = normal.merge(
        accepted[[c for c in acc_cols if c in accepted.columns]].add_prefix("accepted_"),
        left_on="key",
        right_on="accepted_key",
        how="left",
    )
    merged = merged.merge(
        picked[[c for c in pick_cols if c in picked.columns]].add_prefix("picked_"),
        left_on="key",
        right_on="picked_key",
        how="left",
    )
    merged = merged.merge(
        executed[[c for c in exe_cols if c in executed.columns]].add_prefix("executed_"),
        left_on="key",
        right_on="executed_key",
        how="left",
    )

    classes = []
    for _, row in merged.iterrows():
        has_acc = pd.notna(row.get("accepted_key"))
        has_pick = pd.notna(row.get("picked_key"))
        has_exe = pd.notna(row.get("executed_key"))
        if not has_acc:
            classes.append("accepted层缺失")
        elif not has_pick:
            classes.append("accepted存在但picked未通过")
        elif not has_exe:
            classes.append("picked存在但executed未执行")
        else:
            classes.append("已共享_需复核")
    merged["分层分类"] = classes

    summary = (
        merged.groupby("分层分类", as_index=False)
        .size()
        .rename(columns={"size": "样本数"})
        .sort_values("样本数", ascending=False)
        .reset_index(drop=True)
    )
    summary["占比(%)"] = (summary["样本数"] / len(merged) * 100.0).round(4) if len(merged) else 0.0

    detail = merged[
        [
            "EA日志时间",
            "EA信号锚点",
            "aligned_time",
            "dir",
            "触发类型",
            "模式",
            "分层分类",
            "accepted_spec_reason",
            "accepted_sd",
            "accepted_variant",
            "accepted_Bias_5",
            "picked_sd",
            "picked_variant",
            "picked_Bias_5_ea",
            "picked_layer3_threshold_ea",
            "picked_layer3_pass_ea",
            "executed_variant",
            "executed_sd",
            "executed_stage3_time",
        ]
    ].rename(
        columns={
            "aligned_time": "对齐后时间",
            "dir": "方向",
            "accepted_spec_reason": "Python_accepted_spec原因",
            "accepted_sd": "Python_accepted_sd",
            "accepted_variant": "Python_accepted_variant",
            "accepted_Bias_5": "Python_accepted_Bias5",
            "picked_sd": "Python_picked_sd",
            "picked_variant": "Python_picked_variant",
            "picked_Bias_5_ea": "Python_picked_Bias5_ea",
            "picked_layer3_threshold_ea": "Python_picked_Layer3阈值",
            "picked_layer3_pass_ea": "Python_picked_Layer3是否通过",
            "executed_variant": "Python_executed_variant",
            "executed_sd": "Python_executed_sd",
            "executed_stage3_time": "Python_stage3结束时间",
        }
    )

    lines = [
        "# 全历史普通剩余样本分层分类",
        "",
        "## 总览",
        "",
        markdown_table(summary),
        "",
        "## 说明",
        "",
        "- 只统计已经排除时间轴缺口样本后的 `15` 笔普通剩余样本。",
        "- `accepted层缺失`：Python 连 accepted 都没有，优先看 spec / 候选生成。",
        "- `accepted存在但picked未通过`：accepted 有，但 Layer3 / picked 被刷掉。",
        "- `picked存在但executed未执行`：picked 有，但执行层被持仓占用等规则挡掉。",
        "",
        "## 明细",
        "",
        markdown_table(detail),
        "",
    ]

    export_csv(summary, OUTPUT_DIR / "普通剩余样本分层分类汇总_20260709.csv")
    export_csv(detail, OUTPUT_DIR / "普通剩余样本分层分类明细_20260709.csv")
    write_text(OUTPUT_DIR / "普通剩余样本分层分类_20260709.md", "\n".join(lines))
    print(f"Wrote {OUTPUT_DIR}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
