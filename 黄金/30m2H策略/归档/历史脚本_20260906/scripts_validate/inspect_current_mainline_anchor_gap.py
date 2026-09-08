# -*- coding: utf-8 -*-
"""Inspect MT5 aligned anchors that do not exist on Python M30 timeline."""
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

from strategy_30m2h_common import VALIDATION_DIR, export_csv, write_text  # noqa: E402
from processing.prepare import prepare  # noqa: E402


CURRENT_MAINLINE_DIR = (
    VALIDATION_DIR / "mt5_log_session_diff_current_mainline_20260708" / "session_01" / "session_01"
)
OUTPUT_DIR = VALIDATION_DIR / "mt5_log_session_diag_current_mainline_20260708" / "session_01" / "session_01"


def render_markdown(summary: pd.DataFrame, detail: pd.DataFrame, missing: pd.DataFrame) -> str:
    lines = [
        "# current_mainline 锚点时间轴缺口复核",
        "",
        "## 汇总",
        "",
        summary.to_markdown(index=False),
        "",
        "## 全部 MT5 对齐锚点",
        "",
        detail.to_markdown(index=False),
        "",
    ]
    if not missing.empty:
        lines.extend(
            [
                "## Python 时间轴缺口样本",
                "",
                missing.to_markdown(index=False),
                "",
                "## 结论",
                "",
                "- 这类样本在当前逐笔对照里会先表现为 `MT5独有`，因为固定 `+90分钟` 后得出的锚点不在 Python M30 时间轴上。",
                "- 本轮 current_mainline 只有 `2026-02-03 01:00:00` 这一笔属于该类情况。",
                "- 对这笔而言，需要把“时间轴缺口”与“后续止损距离仍不一致”分开看。",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    mt5 = pd.read_csv(CURRENT_MAINLINE_DIR / "mt5_signals.csv", encoding="utf-8-sig")
    mt5["anchor_time"] = pd.to_datetime(mt5["anchor_time"])
    mt5["mt5_raw_anchor_time"] = pd.to_datetime(mt5["mt5_raw_anchor_time"])

    df, _ = prepare("base_data/XAUUSDm30.csv", min_len=8)
    df["date"] = pd.to_datetime(df["date"])
    py_times = set(df["date"])
    py_dates = list(df["date"])

    rows: list[dict[str, object]] = []
    for _, row in mt5.sort_values("anchor_time").iterrows():
        anchor_time = pd.Timestamp(row["anchor_time"])
        exact = anchor_time in py_times
        prev_time = max((d for d in py_dates if d < anchor_time), default=pd.NaT)
        next_time = min((d for d in py_dates if d > anchor_time), default=pd.NaT)
        rows.append(
            {
                "mt5_raw_anchor_time": pd.Timestamp(row["mt5_raw_anchor_time"]),
                "anchor_time": anchor_time,
                "dir": str(row["dir"]),
                "trigger": str(row["trigger"]),
                "mode_raw": str(row["mode_raw"]),
                "mt5_stop_dist": float(row["mt5_stop_dist"]),
                "exact_in_python": bool(exact),
                "prev_python_time": prev_time,
                "next_python_time": next_time,
            }
        )

    detail = pd.DataFrame(rows)
    missing = detail[~detail["exact_in_python"]].reset_index(drop=True)
    summary = pd.DataFrame(
        [
            {
                "MT5对齐锚点总数": int(len(detail)),
                "Python可直接匹配数": int(detail["exact_in_python"].sum()) if not detail.empty else 0,
                "Python时间轴缺口数": int((~detail["exact_in_python"]).sum()) if not detail.empty else 0,
            }
        ]
    )

    export_csv(detail, OUTPUT_DIR / "mt5对齐锚点时间轴复核_20260709.csv")
    write_text(OUTPUT_DIR / "mt5对齐锚点时间轴复核_20260709.md", render_markdown(summary, detail, missing))
    print(f"Wrote {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
