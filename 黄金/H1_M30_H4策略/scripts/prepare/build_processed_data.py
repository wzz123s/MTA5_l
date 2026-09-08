# -*- coding: utf-8 -*-
"""Build processed timeframe and context datasets for H1_M30_H4."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from h1_m30_h4_common import COMBO, PROCESSED_DIR, RAW_DIR, ensure_dirs, export_csv, strategy_spec
from h1_m30_h4_common import read_csv_with_fallback  # noqa: F401
from _multi_tf_matrix_common import attach_all_context, build_tf, load_m30_raw, load_mainline_bundle


def main() -> None:
    ensure_dirs()
    spec = strategy_spec()
    raw_path = RAW_DIR / "XAUUSDm30.csv"
    raw_m30 = load_m30_raw(str(raw_path))

    export_csv(raw_m30, PROCESSED_DIR / "raw_m30_standardized.csv")
    for label in spec["frames"]:
        frame = build_tf(raw_m30, label)
        export_csv(frame, PROCESSED_DIR / f"{label.lower()}_bars.csv")

    bundle = load_mainline_bundle()
    ctx = attach_all_context(bundle["signals"], spec["frames"]).sort_values("date").reset_index(drop=True)
    export_csv(ctx, PROCESSED_DIR / "h1_m30_h4_context_trades.csv")

    print(f"Built processed data for {COMBO}.")


if __name__ == "__main__":
    main()
