# -*- coding: utf-8 -*-
"""Prepare dynamic-risk inputs from the metadata-fixed shift90 signal snapshot."""
from __future__ import annotations


import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import prepare_dynamic_risk_inputs_shift90 as base  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
SIGNAL_ROOT = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714"
OUT_DIR = DATA_DIR / "validation" / "dynamic_risk_inputs_shift90_metadatafix_20260714"


def main() -> None:
    base.OUT_DIR = OUT_DIR
    base.SHIFT90_SIGNAL_DIR = SIGNAL_ROOT / "python_h2_context_q2early"
    base.SHIFT90_M30 = SIGNAL_ROOT / "m30_prepared_with_mt5_shift90.csv"
    base.SOURCES = [
        base.SourceConfig("python_only", DATA_DIR / "signals"),
        base.SourceConfig("python_mt5", base.SHIFT90_SIGNAL_DIR, base.SHIFT90_M30),
    ]
    base.main()


if __name__ == "__main__":
    main()
