# -*- coding: utf-8 -*-
"""Diagnose unmatched causes from the shift90 + ClosePos retry snapshot."""
from __future__ import annotations


import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import diagnose_unmatched_signal_causes as base  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
SHIFT90_SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_20260712" / "python_h2_context_q2early"

base.MAPPED_DIR = DATA_DIR / "validation" / "mapped_trade_alignment_shift90_close_retry_20260714"
base.DYNAMIC_DIR = DATA_DIR / "validation" / "dynamic_risk_alignment_shift90_close_retry_20260714"
base.OUT_DIR = DATA_DIR / "validation" / "unmatched_signal_cause_shift90_close_retry_20260714"


def first_match(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"No file matching {pattern} in {directory}")
    return matches[0]


def load_python_layers_shift90_close_retry(source: str):
    if source == "python_only":
        signal_dir = DATA_DIR / "signals"
        exec_file = base.DYNAMIC_DIR / "python_only_dynamic_risk_trades.csv"
    elif source == "python_mt5":
        signal_dir = SHIFT90_SIGNAL_DIR
        exec_file = base.DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"
    else:
        raise ValueError(source)

    accepted = base.prepare_signal_layer(base.read_csv(first_match(signal_dir, "*Layer1_Layer2*.csv")), "accepted", source)
    picked = base.prepare_signal_layer(base.read_csv(first_match(signal_dir, "*Layer3*.csv")), "picked", source)
    executed = base.prepare_signal_layer(base.read_csv(exec_file), "executed", source)
    return {"accepted": accepted, "picked": picked, "executed": executed}


base.load_python_layers = load_python_layers_shift90_close_retry


if __name__ == "__main__":
    base.main()
