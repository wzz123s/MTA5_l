# -*- coding: utf-8 -*-
"""Rebuild shift90 Python-MT5 signals after rescue metadata recomputation.

This wrapper keeps the original 20260712 snapshot untouched.
"""
from __future__ import annotations


import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import rebuild_python_mt5_shift90 as base  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
OUT_ROOT = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714"
VALIDATION_OUT = DATA_DIR / "validation" / "python_mt5_shift90_metadatafix_20260714"


def main() -> None:
    base.OUT_ROOT = OUT_ROOT
    base.VALIDATION_DIR = VALIDATION_OUT
    VALIDATION_OUT.mkdir(parents=True, exist_ok=True)
    base.main()


if __name__ == "__main__":
    main()
