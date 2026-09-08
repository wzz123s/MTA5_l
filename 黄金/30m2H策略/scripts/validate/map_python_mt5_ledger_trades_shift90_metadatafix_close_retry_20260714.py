# -*- coding: utf-8 -*-
"""Map metadata-fixed shift90 dynamic-risk trades to the ClosePos retry MT5 ledger."""
from __future__ import annotations


import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import map_python_mt5_ledger_trades as base  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"

base.INPUT_DIR = DATA_DIR / "validation" / "dynamic_risk_alignment_shift90_metadatafix_close_retry_20260714"
base.OUT_DIR = DATA_DIR / "validation" / "mapped_trade_alignment_shift90_metadatafix_close_retry_20260714"


if __name__ == "__main__":
    base.main()
