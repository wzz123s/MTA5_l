# -*- coding: utf-8 -*-
"""Build processed market context datasets for the 30m2H mainline strategy."""
from __future__ import annotations


import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_30m2h_common import PROCESSED_DIR, build_processed_frames, ensure_dirs, export_csv, write_text


def main() -> None:
    ensure_dirs()
    frames = build_processed_frames()

    export_csv(frames["m30_standardized"], PROCESSED_DIR / "m30_standardized.csv")
    export_csv(frames["h2_context_bars"], PROCESSED_DIR / "h2_context_bars.csv")
    export_csv(frames["m15_context_bars"], PROCESSED_DIR / "m15_context_bars.csv")

    text = "\n".join(
        [
            "# 30m2H 主线处理后数据",
            "",
            "## 当前包含",
            "",
            "- `m30_standardized.csv`：标准化后的 M30 主行情数据。",
            "- `h2_context_bars.csv`：按决策时点平移后的 H2 上下文数据。",
            "- `m15_context_bars.csv`：用于拆分 M30 Layer2 的 M15 上下文数据。",
            "",
            "## 说明",
            "",
            "- 这里保留的是策略重算所需的行情与上下文层。",
            "- 候选信号、Layer3 入选信号、最终执行交易另放在 `data/signals`，避免和行情数据混层。",
        ]
    )
    write_text(PROCESSED_DIR / "README.md", text)
    print("Built processed data for 30m2H strategy.")


if __name__ == "__main__":
    main()
