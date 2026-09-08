# -*- coding: utf-8 -*-
"""Evaluate gap-aware MT5 anchor remapping against Python executed signals."""
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


SESSION_DIR = VALIDATION_DIR / "mt5_log_session_diff_current_mainline_20260708" / "session_01" / "session_01"
OUTPUT_DIR = VALIDATION_DIR / "mt5_log_session_diag_current_mainline_20260708" / "session_01" / "session_01"


def make_key(anchor_time: pd.Timestamp, direction: str) -> str:
    return pd.Timestamp(anchor_time).strftime("%Y-%m-%d %H:%M:%S") + "|" + str(direction)


def remap_gap_aware(mt5: pd.DataFrame, python_times: list[pd.Timestamp]) -> pd.DataFrame:
    py_set = set(python_times)
    out = mt5.copy()
    mapped_times: list[pd.Timestamp] = []
    mapping_reason: list[str] = []
    prev_times: list[pd.Timestamp | pd.NaT] = []
    next_times: list[pd.Timestamp | pd.NaT] = []

    for anchor_time in pd.to_datetime(out["anchor_time"]):
        prev_time = max((t for t in python_times if t < anchor_time), default=pd.NaT)
        next_time = min((t for t in python_times if t > anchor_time), default=pd.NaT)
        prev_times.append(prev_time)
        next_times.append(next_time)
        if anchor_time in py_set:
            mapped_times.append(anchor_time)
            mapping_reason.append("exact")
        elif pd.notna(next_time):
            mapped_times.append(next_time)
            mapping_reason.append("next_available_m30")
        else:
            mapped_times.append(anchor_time)
            mapping_reason.append("no_future_python_bar")

    out["gap_aware_anchor_time"] = mapped_times
    out["mapping_reason"] = mapping_reason
    out["prev_python_time"] = prev_times
    out["next_python_time"] = next_times
    out["gap_aware_key"] = out.apply(
        lambda row: make_key(pd.Timestamp(row["gap_aware_anchor_time"]), str(row["dir"])),
        axis=1,
    )
    return out


def summarize_mapping(mt5: pd.DataFrame, py: pd.DataFrame, key_col: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    mt5_keys = set(mt5[key_col]) if not mt5.empty else set()
    py_keys = set(py["key"]) if not py.empty else set()
    shared_keys = mt5_keys & py_keys
    mt5_only = mt5[mt5[key_col].isin(mt5_keys - py_keys)].copy()
    shared = mt5[mt5[key_col].isin(shared_keys)].copy()
    changed = mt5[mt5["mapping_reason"] != "exact"].copy() if "mapping_reason" in mt5.columns else mt5.iloc[0:0].copy()
    return shared, mt5_only, changed


def render_markdown(summary: pd.DataFrame, changed: pd.DataFrame, fixed_only: pd.DataFrame, gap_only: pd.DataFrame) -> str:
    lines = [
        "# gap-aware 对齐候选诊断",
        "",
        "## 汇总",
        "",
        summary.to_markdown(index=False),
        "",
    ]
    if not changed.empty:
        lines.extend(
            [
                "## 发生 gap-aware 顺延的样本",
                "",
                changed[
                    [
                        "mt5_raw_anchor_time",
                        "anchor_time",
                        "gap_aware_anchor_time",
                        "dir",
                        "trigger",
                        "mode_raw",
                        "mt5_stop_dist",
                        "mapping_reason",
                        "prev_python_time",
                        "next_python_time",
                    ]
                ].to_markdown(index=False),
                "",
            ]
        )
    if not fixed_only.empty:
        lines.extend(
            [
                "## fixed +90 下仍为 MT5 独有",
                "",
                fixed_only[["anchor_time", "dir", "trigger", "mode_raw", "mt5_stop_dist"]].to_markdown(index=False),
                "",
            ]
        )
    if not gap_only.empty:
        lines.extend(
            [
                "## gap-aware 下仍为 MT5 独有",
                "",
                gap_only[
                    ["gap_aware_anchor_time", "dir", "trigger", "mode_raw", "mt5_stop_dist", "mapping_reason"]
                ].to_markdown(index=False),
                "",
            ]
        )
    lines.extend(
        [
            "## 结论",
            "",
            "- 这份诊断只验证 gap-aware anchor 映射是否改善对照，不直接改变主对照口径。",
            "- 如果 gap-aware 后样本仍是 MT5 独有，说明时间轴缺口只是第一层问题，后续仍要继续追 stop / M15 执行报价。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    mt5 = pd.read_csv(SESSION_DIR / "mt5_signals.csv", encoding="utf-8-sig")
    py = pd.read_csv(SESSION_DIR / "python_executed_signals.csv", encoding="utf-8-sig")
    mt5["anchor_time"] = pd.to_datetime(mt5["anchor_time"])
    mt5["mt5_raw_anchor_time"] = pd.to_datetime(mt5["mt5_raw_anchor_time"])
    mt5["key"] = mt5["anchor_time"].dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + mt5["dir"].astype(str)
    py["anchor_time"] = pd.to_datetime(py["anchor_time"])
    py["key"] = py["anchor_time"].dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + py["dir"].astype(str)

    df, _ = prepare("base_data/XAUUSDm30.csv", min_len=8)
    df["date"] = pd.to_datetime(df["date"])
    python_times = sorted(pd.to_datetime(df["date"]).tolist())

    mt5_gap = remap_gap_aware(mt5, python_times)

    fixed_shared, fixed_only, _ = summarize_mapping(mt5, py, "key")
    gap_shared, gap_only, changed = summarize_mapping(mt5_gap, py, "gap_aware_key")

    summary = pd.DataFrame(
        [
            {
                "fixed共享数": int(len(fixed_shared)),
                "fixed_MT5独有数": int(len(fixed_only)),
                "gap共享数": int(len(gap_shared)),
                "gap_MT5独有数": int(len(gap_only)),
                "发生顺延样本数": int((mt5_gap["mapping_reason"] != "exact").sum()),
            }
        ]
    )

    export_csv(mt5_gap, OUTPUT_DIR / "gap_aware_anchor_mapping_20260709.csv")
    export_csv(summary, OUTPUT_DIR / "gap_aware_anchor_summary_20260709.csv")
    write_text(
        OUTPUT_DIR / "gap_aware对齐候选诊断_20260709.md",
        render_markdown(summary, changed, fixed_only, gap_only),
    )
    print(f"Wrote {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
