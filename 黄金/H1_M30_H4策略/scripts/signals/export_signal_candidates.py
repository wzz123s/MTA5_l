# -*- coding: utf-8 -*-
"""Export strategy signal candidates and per-variant trade sets."""
from __future__ import annotations

import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from h1_m30_h4_common import COMBO, PROCESSED_DIR, SIGNALS_DIR, ensure_dirs, export_csv, strategy_spec
from _multi_tf_matrix_common import build_combo_variant_frames, summarize_variant_item


def main() -> None:
    ensure_dirs()
    ctx = pd.read_csv(PROCESSED_DIR / "h1_m30_h4_context_trades.csv", encoding="utf-8-sig")
    ctx["date"] = pd.to_datetime(ctx["date"])
    combo = strategy_spec()

    variants = build_combo_variant_frames(combo, ctx)
    summary = pd.DataFrame([summarize_variant_item(item) for item in variants]).sort_values(
        ["pf", "test_pf", "n"], ascending=[False, False, False]
    )
    export_csv(summary, SIGNALS_DIR / "strategy_variant_summary.csv")

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

    top3 = summary.head(3).copy()
    export_csv(top3, SIGNALS_DIR / "strategy_variant_top3.csv")
    print(f"Exported signal candidates for {COMBO}.")


if __name__ == "__main__":
    main()
