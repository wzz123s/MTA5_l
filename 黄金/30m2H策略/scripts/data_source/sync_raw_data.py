# -*- coding: utf-8 -*-
"""Sync raw upstream files required by the 30m2H strategy."""
from __future__ import annotations


import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_30m2h_common import ROOT, RAW_DIR, copy_source_file, ensure_dirs, write_text


RAW_FILES = [
    ("base_data/XAUUSDm30.csv", "XAUUSDm30.csv"),
    ("base_data/XAUUSDm15.csv", "XAUUSDm15.csv"),
    ("base_data/H2_XAUUSDm_39col.csv", "H2_XAUUSDm_39col.csv"),
    ("base_data/full_data_30m2h.csv", "full_data_30m2h.csv"),
    ("base_data/README.md", "上游原始数据说明.md"),
]


def main() -> None:
    ensure_dirs()
    copied = []
    for src_rel, dst_name in RAW_FILES:
        src = ROOT / src_rel
        dst = RAW_DIR / dst_name
        copy_source_file(src, dst)
        copied.append(dst_name)

    lines = [
        "# 30m2H 主线原始数据",
        "",
        "## 当前包含",
        "",
    ]
    lines.extend(f"- `{name}`" for name in copied)
    lines.extend(
        [
            "",
            "## 说明",
            "",
            "- `XAUUSDm30.csv`：M30 主行情原始数据。",
            "- `XAUUSDm15.csv`：用于 M30 分解成两个 M15 时段的原始数据。",
            "- `H2_XAUUSDm_39col.csv`：H2 Layer1 上下文原始数据。",
            "- `full_data_30m2h.csv`：历史汇总宽表，保留给老流程复核。",
            "- 后续如果增加下载或更新脚本，先更新 `base_data`，再执行本脚本同步到策略目录。",
        ]
    )
    write_text(RAW_DIR / "README.md", "\n".join(lines))
    print("Synced raw data for 30m2H strategy.")


if __name__ == "__main__":
    main()
