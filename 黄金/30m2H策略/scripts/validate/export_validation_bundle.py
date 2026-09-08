# -*- coding: utf-8 -*-
"""Collect validation outputs for the 30m2H mainline strategy."""
from __future__ import annotations


import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_30m2h_common import (
    GLOBAL_VALIDATION_DIR,
    RESULT_SOURCES,
    VALIDATION_DIR,
    copy_source_file,
    ensure_dirs,
    export_csv,
    read_csv_with_fallback,
    write_text,
)


GLOBAL_FILES = [
    "combo_final_best_summary.csv",
    "combo_top3_stage12.csv",
    "combo_top3_position.csv",
    "组合参数总表_门区间_止损区间_中文.csv",
    "组合最终资金指标_中文_utf8.csv",
    "组合止损范围测试_中文.csv",
    "组合止损范围推荐_中文.csv",
    "组合门范围细扫_中文.csv",
    "组合门强度前3名_中文.csv",
]


LOCAL_RESULT_FILES = {
    "current_strategy": [
        "current_strategy_summary.md",
        "current_strategy_trades.csv",
    ],
    "m15_h2_early_trigger": [
        "m15_h2_combo_detail.csv",
        "m15_early_entry_detail.csv",
        "h2_early_gate_detail.csv",
    ],
    "ea_python_diff": [
        "ea_gap_diagnosis.csv",
        "ea_signals.csv",
        "python_signals.csv",
        "python_accepted_signals.csv",
        "python_picked_signals.csv",
        "python_executed_signals.csv",
        "python_missing_vs_ea.csv",
        "ea_extra_vs_python.csv",
        "python_executed_missing_vs_ea.csv",
        "ea_extra_vs_python_executed.csv",
        "shared_anchor_mode_mismatch.csv",
    ],
}


def _copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        copy_source_file(src, dst)


def _filter_global_summary(src_name: str, dst_name: str) -> None:
    src = GLOBAL_VALIDATION_DIR / src_name
    if not src.exists():
        return
    frame = read_csv_with_fallback(src)
    if "combo" in frame.columns:
        frame = frame.loc[frame["combo"] == "H1_M30_H4"].copy().reset_index(drop=True)
    export_csv(frame, VALIDATION_DIR / dst_name)


def main() -> None:
    ensure_dirs()

    for name in GLOBAL_FILES:
        _copy_if_exists(GLOBAL_VALIDATION_DIR / name, VALIDATION_DIR / name)

    # 主线验证表不在 multi-tf 矩阵里，保留原始全局表并额外输出中文改名版本。
    capital = read_csv_with_fallback(GLOBAL_VALIDATION_DIR / "组合最终资金指标_中文_utf8.csv")
    export_csv(capital, VALIDATION_DIR / "多周期总表_组合最终资金指标_中文_utf8.csv")

    for key, file_names in LOCAL_RESULT_FILES.items():
        root = RESULT_SOURCES[key]
        target_dir = VALIDATION_DIR / key
        target_dir.mkdir(parents=True, exist_ok=True)
        for file_name in file_names:
            _copy_if_exists(root / file_name, target_dir / file_name)

    manifest = [
        "# 30m2H 主线验证数据",
        "",
        "## 当前包含",
        "",
    ]
    manifest.extend(f"- `{path.relative_to(VALIDATION_DIR).as_posix()}`" for path in sorted(VALIDATION_DIR.rglob("*")) if path.is_file())
    write_text(VALIDATION_DIR / "README.md", "\n".join(manifest))
    print("Exported validation bundle for 30m2H strategy.")


if __name__ == "__main__":
    main()
