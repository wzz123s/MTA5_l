# -*- coding: utf-8 -*-
"""Replay M30 post_n counter/anchor alternatives from shift90 diagnosis."""
from __future__ import annotations


import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import replay_postn_counter_anchor as base  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"

base.ALIGN_DIR = DATA_DIR / "validation" / "m30_postn_alignment_diag_shift90_20260713"
base.OUT_DIR = DATA_DIR / "validation" / "postn_counter_anchor_replay_shift90_20260713"
base.M30_FILES = {
    "python_only": DATA_DIR / "processed" / "m30_standardized.csv",
    "python_mt5": DATA_DIR / "signals_mt5_shift90_20260712" / "m30_prepared_with_mt5_shift90.csv",
}


if __name__ == "__main__":
    base.main()
