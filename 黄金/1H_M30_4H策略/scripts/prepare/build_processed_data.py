# -*- coding: utf-8 -*-
"""Build processed timeframe and context datasets for 1H_M30_4H."""
from __future__ import annotations


from pathlib import Path
import sys

ROOT = Path(r"F:\use_code\MTA5_l")
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mt5.strategy_signals import build_basic_cross_signals  # noqa: E402

from strategy_workspace_common import (  # noqa: E402
    COMBO,
    CONTEXT_FILE,
    FRAMES,
    PROCESSED_DIR,
    RAW_M30_FILE,
    build_context_trades,
    build_tf,
    ensure_dirs,
    export_csv,
    ensure_strategy_raw_data_ready,
    load_strategy_raw_m30,
    tf_slug,
    write_text,
)


def main() -> None:
    ensure_dirs()
    ensure_strategy_raw_data_ready()
    raw_m30 = load_strategy_raw_m30()
    export_csv(raw_m30, PROCESSED_DIR / "raw_m30_standardized.csv")

    for label in FRAMES:
        export_csv(build_tf(raw_m30, label), PROCESSED_DIR / f"{tf_slug(label)}_bars.csv")

    m30_tf = build_tf(raw_m30, "30M")
    signals = build_basic_cross_signals(m30_tf)
    export_csv(signals, PROCESSED_DIR / "mt5_basic_cross_signals.csv")

    ctx = build_context_trades(raw_m30, signals)
    export_csv(ctx, CONTEXT_FILE)

    files = (
        ["raw_m30_standardized.csv"]
        + [f"{tf_slug(label)}_bars.csv" for label in FRAMES]
        + ["mt5_basic_cross_signals.csv", CONTEXT_FILE.name]
    )
    write_text(
        "data/processed/README.md",
        "# 1H_M30_4H processed data\n\n## Files\n\n"
        + "\n".join(f"- `{name}`" for name in files)
        + "\n\n## Notes\n\n"
        "- Raw data is read from this strategy's MT5 manifest, not from the reference strategy raw folder.\n"
        "- `mt5_basic_cross_signals.csv` is a baseline research candidate set using SMA5/SMA13 crosses.\n"
        "- StopSpec filtering is deferred to validation and must use `stop_distance`, not `focus_sd`.\n"
        "- Final Stage, StopSpec, position sizing, EA parameters and Python-vs-EA alignment still require dedicated validation.\n",
    )
    print(f"Built processed data for {COMBO}; baseline_signals={len(signals)}.")


if __name__ == "__main__":
    main()
