# -*- coding: utf-8 -*-
"""Review stage exit rule differences for shift90 + ClosePos retry matched trades."""
from __future__ import annotations


import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import review_stage_exit_rule_alignment_shift90 as base  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"

base.MATCHED_DIR = DATA_DIR / "validation" / "matched_profit_exit_diff_shift90_close_retry_20260714"
base.DYNAMIC_DIR = DATA_DIR / "validation" / "dynamic_risk_alignment_shift90_close_retry_20260714"
base.MT5_LEDGER_DIR = DATA_DIR / "validation" / "mt5_full_close_retry_fix_20260714"
base.OUT_DIR = DATA_DIR / "validation" / "stage_exit_rule_alignment_shift90_close_retry_20260714"


def main() -> None:
    base.main()
    report_path = base.OUT_DIR / "stage_exit_rule_alignment_report.md"
    text = report_path.read_text(encoding="utf-8-sig")
    text = text.replace(
        "matched_profit_exit_diff_shift90_20260713/matched_profit_exit_diff_details.csv",
        "matched_profit_exit_diff_shift90_close_retry_20260714/matched_profit_exit_diff_details.csv",
    )
    text = text.replace(
        "# Stage Exit Rule Alignment Review - shift90",
        "# Stage Exit Rule Alignment Review - shift90 + ClosePos Retry",
    )
    report_path.write_text(text, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
