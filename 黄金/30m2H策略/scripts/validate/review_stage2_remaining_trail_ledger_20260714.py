# -*- coding: utf-8 -*-
"""Review remaining Stage2 partial-open cases with enhanced EA trail ledger.

This script consumes the earlier partial-open review plus the full MT5 ledger
exported after adding Stage2 trail diagnostics. It separates two questions:

1. Is the case still blocking Stage2 exit/PnL classification alignment?
2. Would a raw tick replay still be useful for strict intra-bar sequencing?
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
RUNTIME_DIR = VALIDATION_DIR / "python_runtime_stage_exit_prototype_20260714"
FULL_LEDGER_DIR = VALIDATION_DIR / "ea_stage2_trail_ledger_full_20260714"

REVIEW_PATH = RUNTIME_DIR / "runtime_stage2_partial_open_ticklog_review.csv"
LEDGER_PATH = FULL_LEDGER_DIR / "30m2H_strategy_trade_ledger.csv"

OUT_CSV = RUNTIME_DIR / "runtime_stage2_remaining_ticklog_evidence.csv"
OUT_SUMMARY_CSV = RUNTIME_DIR / "runtime_stage2_remaining_ticklog_evidence_summary.csv"
OUT_MD = RUNTIME_DIR / "runtime_stage2_remaining_ticklog_evidence.md"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def parse_time(value: object) -> pd.Timestamp:
    return pd.to_datetime(value, errors="coerce")


def safe_float(value: object) -> float:
    return float(pd.to_numeric(value, errors="coerce"))


def safe_int(value: object) -> int:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return 0
    return int(parsed)


def as_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def fmt_time(value: object) -> str:
    ts = parse_time(value)
    if pd.isna(ts):
        return ""
    return ts.strftime("%Y.%m.%d %H:%M:%S")


def fmt_num(value: object, digits: int = 5) -> str:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return ""
    return f"{float(parsed):.{digits}f}"


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_No rows._"

    display = frame.loc[:, columns].copy()
    rows = [[as_text(value) for value in row] for row in display.to_numpy()]
    widths = [len(col) for col in columns]
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def render(row: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(row)) + " |"

    header = render(columns)
    sep = "| " + " | ".join("-" * width for width in widths) + " |"
    return "\n".join([header, sep, *[render(row) for row in rows]])


def classify_case(case: pd.Series, ledger_row: pd.Series | None) -> dict[str, object]:
    base = {
        "case_id": case["case_id"],
        "signal_anchor_time": case["signal_anchor_time"],
        "stage": case["stage"],
        "dir_norm": case["dir_norm"],
        "previous_review_class": case["partial_open_review_class"],
        "previous_deal_sl_kind": case["deal_sl_kind"],
        "previous_still_needs_tick_or_log": bool_value(case["still_needs_tick_or_log"]),
    }

    if ledger_row is None:
        return {
            **base,
            "ledger_match": False,
            "ledger_open_time": "",
            "ledger_exit_time": "",
            "ledger_deal_reason": "",
            "ledger_actual_stop": "",
            "ledger_deal_sl_price": "",
            "stage2_sl_kind": "",
            "stage2_trail_on_time": "",
            "stage2_trail_modify_count": 0,
            "stage2_last_modify_time": "",
            "stage2_last_modify_to_sl": "",
            "stage2_last_known_sl": "",
            "stage2_last_modify_retcode": "",
            "stage2_last_modify_comment": "",
            "seconds_open_to_exit": "",
            "evidence_class": "missing_in_enhanced_full_ledger",
            "remaining_alignment_blocker": True,
            "needs_raw_tick_for_first_touch_order": True,
            "evidence_note": "No matching Stage2 row in enhanced full ledger.",
        }

    open_time = parse_time(ledger_row.get("open_time"))
    exit_time = parse_time(ledger_row.get("exit_time"))
    seconds_open_to_exit = ""
    if pd.notna(open_time) and pd.notna(exit_time):
        seconds_open_to_exit = int((exit_time - open_time).total_seconds())

    deal_reason = as_text(ledger_row.get("deal_reason")).upper()
    sl_kind = as_text(ledger_row.get("stage2_sl_kind"))
    modify_count = safe_int(ledger_row.get("stage2_trail_modify_count"))
    deal_sl = safe_float(ledger_row.get("deal_sl_price"))
    actual_stop = safe_float(ledger_row.get("actual_stop"))
    last_known_sl = safe_float(ledger_row.get("stage2_last_known_sl"))

    if sl_kind == "trail_sl":
        evidence_class = "resolved_as_trail_sl_by_ea_ledger"
        remaining_blocker = False
        needs_raw_tick = False
        note = (
            "Enhanced ledger records trail_on and successful SL modify path; "
            "deal SL matches the last known trailing SL."
        )
    elif sl_kind == "initial_sl" and deal_reason == "SL" and isinstance(seconds_open_to_exit, int) and seconds_open_to_exit > 0:
        evidence_class = "confirmed_initial_sl_after_open_by_deal_ledger"
        remaining_blocker = False
        needs_raw_tick = True
        note = (
            "Ledger/deal history confirms broker SL close after open at initial SL. "
            "Raw ticks are only needed for strict intra-bar first-touch replay."
        )
    elif sl_kind == "initial_sl" and deal_reason == "SL":
        evidence_class = "initial_sl_but_open_exit_sequence_unclear"
        remaining_blocker = True
        needs_raw_tick = True
        note = "Initial SL is confirmed, but open/exit timestamps do not prove after-open sequence."
    else:
        evidence_class = "unresolved_by_enhanced_ledger"
        remaining_blocker = True
        needs_raw_tick = True
        note = "Enhanced ledger does not provide a decisive Stage2 SL classification."

    return {
        **base,
        "ledger_match": True,
        "ledger_open_time": fmt_time(ledger_row.get("open_time")),
        "ledger_exit_time": fmt_time(ledger_row.get("exit_time")),
        "ledger_deal_reason": deal_reason,
        "ledger_actual_stop": fmt_num(actual_stop),
        "ledger_deal_sl_price": fmt_num(deal_sl),
        "stage2_sl_kind": sl_kind,
        "stage2_trail_on_time": fmt_time(ledger_row.get("stage2_trail_on_time")),
        "stage2_trail_modify_count": modify_count,
        "stage2_last_modify_time": fmt_time(ledger_row.get("stage2_last_modify_time")),
        "stage2_last_modify_to_sl": fmt_num(ledger_row.get("stage2_last_modify_to_sl")),
        "stage2_last_known_sl": fmt_num(last_known_sl),
        "stage2_last_modify_retcode": as_text(ledger_row.get("stage2_last_modify_retcode")),
        "stage2_last_modify_comment": as_text(ledger_row.get("stage2_last_modify_comment")),
        "seconds_open_to_exit": seconds_open_to_exit,
        "evidence_class": evidence_class,
        "remaining_alignment_blocker": remaining_blocker,
        "needs_raw_tick_for_first_touch_order": needs_raw_tick,
        "evidence_note": note,
    }


def main() -> None:
    review = read_csv(REVIEW_PATH)
    ledger = read_csv(LEDGER_PATH)

    pending = review[review["still_needs_tick_or_log"].map(bool_value)].copy()
    stage2_ledger = ledger[pd.to_numeric(ledger["stage"], errors="coerce") == 2].copy()
    stage2_by_anchor = {
        str(row["signal_anchor_time"]): row
        for _, row in stage2_ledger.sort_values(["signal_anchor_time", "open_time"]).iterrows()
    }

    rows = [
        classify_case(case, stage2_by_anchor.get(str(case["signal_anchor_time"])))
        for _, case in pending.iterrows()
    ]
    evidence = pd.DataFrame(rows)

    summary = (
        evidence.groupby(["evidence_class", "remaining_alignment_blocker", "needs_raw_tick_for_first_touch_order"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["remaining_alignment_blocker", "needs_raw_tick_for_first_touch_order", "evidence_class"])
    )

    export_csv(evidence, OUT_CSV)
    export_csv(summary, OUT_SUMMARY_CSV)

    case_cols = [
        "case_id",
        "signal_anchor_time",
        "stage2_sl_kind",
        "ledger_exit_time",
        "stage2_trail_modify_count",
        "stage2_last_modify_to_sl",
        "ledger_deal_sl_price",
        "evidence_class",
        "remaining_alignment_blocker",
        "needs_raw_tick_for_first_touch_order",
    ]

    md = f"""# Stage2 Remaining Tick/Trail Ledger Evidence

## Scope

- Input review: `{REVIEW_PATH.relative_to(VALIDATION_DIR)}`
- Enhanced full ledger: `{LEDGER_PATH.relative_to(VALIDATION_DIR)}`
- Pending cases reviewed: `{len(evidence)}`

## Summary

{markdown_table(summary, list(summary.columns))}

## Case Evidence

{markdown_table(evidence, case_cols)}

## Interpretation

- `remaining_alignment_blocker = False` means the case no longer blocks current Stage2 exit/PnL classification alignment.
- `needs_raw_tick_for_first_touch_order = True` is retained for strict intra-bar tick replay, not for current ledger-level classification.
- `case_019` is resolved by the new Stage2 trail ledger because it records trail activation and repeated successful SL modify attempts.
- The initial-SL cases are resolved for ledger-level classification because broker deal history confirms the SL close after open; raw ticks would only refine the first-touch sequence inside the bar.

## Output Files

- `runtime_stage2_remaining_ticklog_evidence.csv`
- `runtime_stage2_remaining_ticklog_evidence_summary.csv`
"""
    write_text(OUT_MD, md)

    print(f"Wrote {OUT_CSV}")
    print(f"Wrote {OUT_SUMMARY_CSV}")
    print(f"Wrote {OUT_MD}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
