# -*- coding: utf-8 -*-
"""Export strategy signal candidates and per-variant trade sets."""
from __future__ import annotations


from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strategy_workspace_common import (  # noqa: E402
    COMBO,
    CONTEXT_FILE,
    SIGNALS_DIR,
    build_combo_variant_frames,
    ensure_dirs,
    export_csv,
    strategy_spec,
    summarize_variant_item,
    write_text,
)


def main() -> None:
    ensure_dirs()
    ctx = pd.read_csv(CONTEXT_FILE, encoding="utf-8-sig")
    ctx["date"] = pd.to_datetime(ctx["date"])

    variants = build_combo_variant_frames(strategy_spec(), ctx)
    summary = pd.DataFrame([summarize_variant_item(item) for item in variants]).sort_values(
        ["pf", "test_pf", "n"],
        ascending=[False, False, False],
    )
    export_csv(summary, SIGNALS_DIR / "strategy_variant_summary.csv")
    export_csv(summary.head(3).copy(), SIGNALS_DIR / "strategy_variant_top3.csv")

    trade_frames = []
    for item in variants:
        frame = item["frame"].copy()
        if "variant" in frame.columns:
            frame = frame.rename(columns={"variant": "source_variant"})
        frame.insert(0, "combo", COMBO)
        frame.insert(1, "variant", item["variant"])
        frame.insert(2, "variant_desc", item["desc"])
        trade_frames.append(frame)
    export_csv(pd.concat(trade_frames, ignore_index=True), SIGNALS_DIR / "strategy_candidate_trades.csv")

    write_text(
        "data/signals/README.md",
        """# 1H_M30_4H 信号数据

## 当前包含

- `strategy_variant_summary.csv`
- `strategy_variant_top3.csv`
- `strategy_candidate_trades.csv`

## 说明

- 候选信号沿用 `30m2H` 主线最终入选信号，再叠加 30M / 1H / 4H 上下文门。
- 当前输出是研究层信号候选，不包含 EA 实盘执行适配。
""",
    )
    print(f"Exported signal candidates for {COMBO}.")


if __name__ == "__main__":
    main()
