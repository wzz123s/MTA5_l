# -*- coding: utf-8 -*-
"""Prototype trigger-family equivalence for shift90 + ClosePos retry mapping."""
from __future__ import annotations


import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import prototype_trigger_family_equivalence_shift90 as base  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"

base.MAPPED_DIR = DATA_DIR / "validation" / "mapped_trade_alignment_shift90_close_retry_20260714"
base.DYNAMIC_DIR = DATA_DIR / "validation" / "dynamic_risk_alignment_shift90_close_retry_20260714"
base.OUT_DIR = DATA_DIR / "validation" / "trigger_family_equivalence_shift90_close_retry_20260714"


if __name__ == "__main__":
    base.main()
