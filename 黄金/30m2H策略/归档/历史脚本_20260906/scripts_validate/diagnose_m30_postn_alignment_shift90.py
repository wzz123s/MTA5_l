# -*- coding: utf-8 -*-
"""Run M30 post_n alignment diagnosis from the shift90 snapshots."""
from __future__ import annotations


import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import diagnose_m30_postn_alignment as base  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"

base.DYNAMIC_DIR = DATA_DIR / "validation" / "dynamic_risk_alignment_shift90_20260713"
base.MAPPED_DIR = DATA_DIR / "validation" / "mapped_trade_alignment_shift90_20260713"
base.CAUSE_DIR = DATA_DIR / "validation" / "unmatched_signal_cause_shift90_20260713"
base.OUT_DIR = DATA_DIR / "validation" / "m30_postn_alignment_diag_shift90_20260713"


if __name__ == "__main__":
    base.main()
