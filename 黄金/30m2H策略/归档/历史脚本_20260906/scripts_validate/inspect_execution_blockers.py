# -*- coding: utf-8 -*-
"""Inspect which earlier executed trade blocked picked-but-not-executed samples."""
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
CLASSIFIED_PATH = OUTPUT_DIR / "普通剩余样本分层分类明细_20260709.csv"
EXECUTED_PATH = RESULT_SOURCES["ea_python_diff"] / "python_executed_signals.csv"


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
    detail = pd.read_csv(CLASSIFIED_PATH, encoding="utf-8-sig")
    executed = pd.read_csv(EXECUTED_PATH, encoding="utf-8-sig")

    detail["对齐后时间"] = pd.to_datetime(detail["对齐后时间"])
    executed["anchor_time"] = pd.to_datetime(executed["anchor_time"])
    executed["stage3_time"] = pd.to_datetime(executed["stage3_time"])

    blocked = detail[detail["分层分类"] == "picked存在但executed未执行"].copy().reset_index(drop=True)
    rows = []
    for _, row in blocked.iterrows():
        anchor = pd.Timestamp(row["对齐后时间"])
        prior = executed[executed["anchor_time"] < anchor].sort_values("anchor_time")
        if prior.empty:
            blocker = None
        else:
            blocker = prior.iloc[-1]

        blocked_by_open = False
        if blocker is not None and pd.notna(blocker["stage3_time"]):
            blocked_by_open = pd.Timestamp(blocker["stage3_time"]) >= anchor

        rows.append(
            {
                "对齐后时间": anchor,
                "方向": row["方向"],
                "触发类型": row["触发类型"],
                "模式": row["模式"],
                "Python_picked_variant": row.get("Python_picked_variant", ""),
                "Python_picked_sd": row.get("Python_picked_sd", ""),
                "最近已执行信号时间": blocker["anchor_time"] if blocker is not None else pd.NaT,
                "最近已执行信号方向": blocker["dir"] if blocker is not None else "",
                "最近已执行variant": blocker["variant"] if blocker is not None else "",
                "最近已执行stage3结束时间": blocker["stage3_time"] if blocker is not None else pd.NaT,
                "是否被前序持仓占用挡掉": blocked_by_open,
            }
        )

    out = pd.DataFrame(rows)
    summary = pd.DataFrame(
        [
            {
                "picked未执行样本数": int(len(out)),
                "可由前序持仓占用直接解释的样本数": int(out["是否被前序持仓占用挡掉"].sum()) if not out.empty else 0,
            }
        ]
    )

    lines = [
        "# 执行层占用逐笔复核",
        "",
        "## 总览",
        "",
        markdown_table(summary),
        "",
        "## 说明",
        "",
        "- 这份表只看 `picked存在但executed未执行` 的样本。",
        "- 诊断方法：对每笔样本，找它之前最近的一笔 `python_executed_signals`。",
        "- 如果那笔的 `stage3_time >= 当前样本对齐后时间`，则可直接视为被前序持仓占用挡掉。",
        "",
        "## 明细",
        "",
        markdown_table(out),
        "",
    ]

    export_csv(summary, OUTPUT_DIR / "执行层占用复核汇总_20260709.csv")
    export_csv(out, OUTPUT_DIR / "执行层占用复核明细_20260709.csv")
    write_text(OUTPUT_DIR / "执行层占用复核_20260709.md", "\n".join(lines))
    print(f"Wrote {OUTPUT_DIR}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
