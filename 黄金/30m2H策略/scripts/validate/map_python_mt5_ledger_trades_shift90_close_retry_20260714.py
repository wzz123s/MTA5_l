# -*- coding: utf-8 -*-
"""Run mapped trade alignment from shift90 inputs and the ClosePos retry MT5 ledger."""
from __future__ import annotations


import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import map_python_mt5_ledger_trades as base  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))

base.INPUT_DIR = STRATEGY_DIR / "data" / "validation" / "dynamic_risk_alignment_shift90_close_retry_20260714"
base.OUT_DIR = STRATEGY_DIR / "data" / "validation" / "mapped_trade_alignment_shift90_close_retry_20260714"


if __name__ == "__main__":
    base.main()
