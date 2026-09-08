# -*- coding: utf-8 -*-
"""Break down matched profit/exit differences for shift90 + ClosePos retry."""
from __future__ import annotations


import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import review_matched_profit_exit_diff_shift90 as base  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"

base.EQ_DIR = DATA_DIR / "validation" / "trigger_family_equivalence_shift90_close_retry_20260714"
base.DYNAMIC_DIR = DATA_DIR / "validation" / "dynamic_risk_alignment_shift90_close_retry_20260714"
base.MT5_LEDGER_DIR = DATA_DIR / "validation" / "mt5_full_close_retry_fix_20260714"
base.OUT_DIR = DATA_DIR / "validation" / "matched_profit_exit_diff_shift90_close_retry_20260714"
base.POLICY_FILE = base.EQ_DIR / "bidirectional_m30_m15_90_profit20_selected_matches.csv"


if __name__ == "__main__":
    base.main()
