# -*- coding: utf-8 -*-
"""Integrate runtime-style Stage exit evidence with enhanced EA ledger.

The source Stage exit alignment marks 18 matched trades as
``stage_exit_detail_diff``. Earlier prototype scripts then explain the highest
priority stage rows with M30/M15 approximations and the enhanced Stage2 EA
ledger. This script merges those evidence layers into a single residual table.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
RUNTIME_DIR = VALIDATION_DIR / "python_runtime_stage_exit_prototype_20260714"
LEDGER_DIR = VALIDATION_DIR / "ea_stage2_trail_ledger_full_20260714"

INPUT_CASES = RUNTIME_DIR / "runtime_stage_input_cases.csv"
M30_REPLAY = RUNTIME_DIR / "runtime_stage_priority1_replay.csv"
M15_REFINE = RUNTIME_DIR / "runtime_stage_priority1_m15_refine.csv"
STAGE2_TRAIL = RUNTIME_DIR / "runtime_stage2_trail_refine.csv"
REMAINING_EVIDENCE = RUNTIME_DIR / "runtime_stage2_remaining_ticklog_evidence.csv"
ENHANCED_LEDGER = LEDGER_DIR / "30m2H_strategy_trade_ledger.csv"

OUT_STAGE = RUNTIME_DIR / "runtime_stage_exit_integrated_alignment.csv"
OUT_STAGE_SUMMARY = RUNTIME_DIR / "runtime_stage_exit_integrated_stage_summary.csv"
OUT_TRADE = RUNTIME_DIR / "runtime_stage_exit_integrated_trade_summary.csv"
OUT_MD = RUNTIME_DIR / "runtime_stage_exit_integrated_alignment.md"


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


def as_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def safe_int(value: object) -> int:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return 0
    return int(parsed)


def safe_float_text(value: object, digits: int = 5) -> str:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return ""
    return f"{float(parsed):.{digits}f}"


def key_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def build_ledger_key(row: pd.Series) -> tuple[str, str, str, str]:
    return (
        key_text(row.get("signal_anchor_time")),
        key_text(row.get("stage")),
        key_text(row.get("ticket")),
        key_text(row.get("position_id")),
    )


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


def load_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return read_csv(path)


def enrich_with_ledger(cases: pd.DataFrame, ledger: pd.DataFrame) -> pd.DataFrame:
    if ledger.empty:
        return cases.copy()

    ledger = ledger.copy()
    ledger["_ledger_key"] = ledger.apply(build_ledger_key, axis=1)
    ledger_cols = [
        "_ledger_key",
        "stage2_trail_on_time",
        "stage2_trail_modify_count",
        "stage2_trail_modify_fail_count",
        "stage2_first_modify_time",
        "stage2_last_modify_time",
        "stage2_last_modify_to_sl",
        "stage2_last_known_sl",
        "stage2_sl_kind",
        "deal_sl_price",
    ]
    keep = ledger[[c for c in ledger_cols if c in ledger.columns]].drop_duplicates("_ledger_key")

    out = cases.copy()
    out["_ledger_key"] = out.apply(build_ledger_key, axis=1)
    out = out.merge(keep, on="_ledger_key", how="left")
    out = out.drop(columns=["_ledger_key"])
    return out


def classify_case(row: pd.Series) -> dict[str, object]:
    priority = safe_int(row.get("runtime_priority"))
    stage = safe_int(row.get("stage"))
    deal_reason = as_text(row.get("mt5_deal_reason")).upper()

    if priority != 1:
        return {
            "runtime_residual_class": "not_priority1_reprocessed",
            "runtime_resolution_level": "out_of_scope",
            "remaining_priority1_blocker": False,
            "requires_strict_tick_replay": False,
            "runtime_evidence_note": "Lower-priority/control stage row was not part of the current runtime residual pass.",
        }

    remaining_class = as_text(row.get("evidence_class"))
    if remaining_class:
        return {
            "runtime_residual_class": remaining_class,
            "runtime_resolution_level": "confirmed_ledger",
            "remaining_priority1_blocker": bool_value(row.get("remaining_alignment_blocker")),
            "requires_strict_tick_replay": bool_value(row.get("needs_raw_tick_for_first_touch_order")),
            "runtime_evidence_note": as_text(row.get("evidence_note")),
        }

    if stage == 2 and as_text(row.get("stage2_sl_kind")):
        sl_kind = as_text(row.get("stage2_sl_kind"))
        modify_count = safe_int(row.get("stage2_trail_modify_count"))
        deal_sl = safe_float_text(row.get("deal_sl_price"))
        last_sl = safe_float_text(row.get("stage2_last_known_sl"))
        if sl_kind == "trail_sl":
            note = f"Enhanced ledger classifies Stage2 as trail_sl; modify_count={modify_count}; deal_sl={deal_sl}; last_known_sl={last_sl}."
        else:
            note = f"Enhanced ledger classifies Stage2 as {sl_kind}; deal_sl={deal_sl}."
        return {
            "runtime_residual_class": f"enhanced_stage2_ledger_{sl_kind}",
            "runtime_resolution_level": "confirmed_ledger",
            "remaining_priority1_blocker": False,
            "requires_strict_tick_replay": False,
            "runtime_evidence_note": note,
        }

    stage2_class = as_text(row.get("stage2_trail_refine_class"))
    if stage == 2 and stage2_class and not bool_value(row.get("needs_log_or_tick")):
        return {
            "runtime_residual_class": f"stage2_trail_refine_{stage2_class}",
            "runtime_resolution_level": "confirmed_bar_model",
            "remaining_priority1_blocker": False,
            "requires_strict_tick_replay": False,
            "runtime_evidence_note": as_text(row.get("stage2_trail_refine_reason")),
        }

    m15_class = as_text(row.get("m15_refine_class"))
    if m15_class in {"mt5_sl_before_python_event", "mt5_sl_before_no_python_event"}:
        still_tick = bool_value(row.get("still_needs_tick"))
        return {
            "runtime_residual_class": f"m15_{m15_class}",
            "runtime_resolution_level": "plausible_needs_tick" if still_tick else "confirmed_m15_bar",
            "remaining_priority1_blocker": False,
            "requires_strict_tick_replay": still_tick,
            "runtime_evidence_note": as_text(row.get("m15_refine_reason")),
        }

    if m15_class == "stage3_m15_sl_seen_cross_not_refined":
        return {
            "runtime_residual_class": "stage3_broker_sl_seen_cross_chronology_pending",
            "runtime_resolution_level": "plausible_needs_stage3_cross_replay",
            "remaining_priority1_blocker": False,
            "requires_strict_tick_replay": True,
            "runtime_evidence_note": as_text(row.get("m15_refine_reason")),
        }

    if m15_class == "python_event_before_mt5_sl":
        return {
            "runtime_residual_class": "python_event_before_mt5_sl_session_or_close_retry_candidate",
            "runtime_resolution_level": "unresolved",
            "remaining_priority1_blocker": True,
            "requires_strict_tick_replay": False,
            "runtime_evidence_note": as_text(row.get("m15_refine_reason")),
        }

    if bool_value(row.get("explains_mt5_sl")):
        needs_tick = bool_value(row.get("needs_tick_for_order"))
        return {
            "runtime_residual_class": f"m30_{as_text(row.get('predicted_runtime_class'))}",
            "runtime_resolution_level": "plausible_needs_tick" if needs_tick else "confirmed_m30_bar",
            "remaining_priority1_blocker": False,
            "requires_strict_tick_replay": needs_tick,
            "runtime_evidence_note": as_text(row.get("first_m30_event_details")),
        }

    if deal_reason == "EXPERT" and as_text(row.get("predicted_runtime_class")) == "broker_sl_first":
        return {
            "runtime_residual_class": "expert_close_after_broker_sl_candidate_needs_journal",
            "runtime_resolution_level": "unresolved",
            "remaining_priority1_blocker": True,
            "requires_strict_tick_replay": True,
            "runtime_evidence_note": "M30 saw broker SL first, but MT5 deal reason is EXPERT; tester journal/session close path is needed.",
        }

    if bool_value(row.get("contradicts_mt5_sl")):
        return {
            "runtime_residual_class": "runtime_model_contradicts_mt5_sl",
            "runtime_resolution_level": "unresolved",
            "remaining_priority1_blocker": True,
            "requires_strict_tick_replay": True,
            "runtime_evidence_note": as_text(row.get("first_m30_event_details")),
        }

    return {
        "runtime_residual_class": "unresolved_no_runtime_evidence",
        "runtime_resolution_level": "unresolved",
        "remaining_priority1_blocker": True,
        "requires_strict_tick_replay": True,
        "runtime_evidence_note": "No decisive runtime evidence layer matched this priority-1 case.",
    }


def main() -> None:
    cases = read_csv(INPUT_CASES)
    replay = load_optional(M30_REPLAY)
    m15 = load_optional(M15_REFINE)
    stage2 = load_optional(STAGE2_TRAIL)
    remaining = load_optional(REMAINING_EVIDENCE)
    ledger = load_optional(ENHANCED_LEDGER)

    merged = enrich_with_ledger(cases, ledger)

    for frame, suffix_cols in [
        (replay, []),
        (m15, []),
        (stage2, []),
        (remaining, []),
    ]:
        if frame.empty:
            continue
        drop_cols = [c for c in frame.columns if c in merged.columns and c != "case_id"]
        merged = merged.merge(frame.drop(columns=drop_cols + suffix_cols, errors="ignore"), on="case_id", how="left")

    classification = pd.DataFrame([classify_case(row) for _, row in merged.iterrows()])
    out = pd.concat([merged, classification], axis=1)

    stage_summary = (
        out.groupby(
            [
                "runtime_priority",
                "stage",
                "runtime_resolution_level",
                "runtime_residual_class",
                "remaining_priority1_blocker",
                "requires_strict_tick_replay",
            ],
            dropna=False,
        )
        .size()
        .reset_index(name="rows")
        .sort_values(["runtime_priority", "stage", "runtime_resolution_level", "runtime_residual_class"])
    )

    trade_summary = (
        out.groupby(["py_trade_id", "mt5_trade_id"], dropna=False)
        .agg(
            priority1_stage_rows=("runtime_priority", lambda s: int((pd.to_numeric(s, errors="coerce") == 1).sum())),
            priority1_blockers=("remaining_priority1_blocker", lambda s: int(sum(bool_value(v) for v in s))),
            strict_tick_replay_rows=("requires_strict_tick_replay", lambda s: int(sum(bool_value(v) for v in s))),
            residual_classes=("runtime_residual_class", lambda s: "; ".join(sorted(set(as_text(v) for v in s if as_text(v))))),
        )
        .reset_index()
    )
    trade_summary["trade_runtime_status"] = trade_summary.apply(
        lambda row: "has_priority1_blocker"
        if int(row["priority1_blockers"]) > 0
        else (
            "priority1_explained_but_strict_replay_pending"
            if int(row["strict_tick_replay_rows"]) > 0 and int(row["priority1_stage_rows"]) > 0
            else ("priority1_resolved" if int(row["priority1_stage_rows"]) > 0 else "no_priority1_stage")
        ),
        axis=1,
    )

    trade_status_summary = (
        trade_summary.groupby("trade_runtime_status", dropna=False)
        .size()
        .reset_index(name="trades")
        .sort_values(["trade_runtime_status"])
    )

    export_csv(out, OUT_STAGE)
    export_csv(stage_summary, OUT_STAGE_SUMMARY)
    export_csv(trade_summary, OUT_TRADE)

    priority1_total = int((pd.to_numeric(out["runtime_priority"], errors="coerce") == 1).sum())
    priority1_blockers = int(sum(bool_value(v) for v in out["remaining_priority1_blocker"]))
    strict_tick_rows = int(
        sum(
            bool_value(v)
            for _, v in out.loc[pd.to_numeric(out["runtime_priority"], errors="coerce") == 1, "requires_strict_tick_replay"].items()
        )
    )

    focus_cols = [
        "case_id",
        "stage",
        "exit_relation",
        "sign_pair",
        "runtime_resolution_level",
        "runtime_residual_class",
        "remaining_priority1_blocker",
        "requires_strict_tick_replay",
    ]
    focus = out[pd.to_numeric(out["runtime_priority"], errors="coerce") == 1].copy()

    md = f"""# Runtime Stage Exit Integrated Alignment

## Scope

- Base cases: `{INPUT_CASES.relative_to(VALIDATION_DIR)}`
- Enhanced ledger: `{ENHANCED_LEDGER.relative_to(VALIDATION_DIR)}`
- Evidence layers: M30 replay, M15 refine, Stage2 trail refine, remaining Stage2 trail ledger evidence.

## Key Counts

- Stage exit detail trades before runtime integration: `18`
- Priority 1 stage rows before runtime integration: `{priority1_total}`
- Remaining Priority 1 blockers after runtime integration: `{priority1_blockers}`
- Priority 1 rows still requiring strict tick/journal replay: `{strict_tick_rows}`

## Trade Status

{markdown_table(trade_status_summary, list(trade_status_summary.columns))}

## Stage Summary

{markdown_table(stage_summary, list(stage_summary.columns))}

## Priority 1 Case View

{markdown_table(focus, focus_cols)}

## Interpretation

- `remaining_priority1_blocker=False` means the row no longer blocks current Stage exit/PnL alignment.
- `requires_strict_tick_replay=True` means the row is explained enough for current classification, but raw ticks or tester journal would still be needed for strict event-order replay.
- Stage2 rows are now primarily resolved by the enhanced EA ledger instead of M30/M15 approximation.
- Remaining blockers are reserved for session/journal style cases where broker SL evidence and MT5 deal reason/time still conflict.

## Output Files

- `runtime_stage_exit_integrated_alignment.csv`
- `runtime_stage_exit_integrated_stage_summary.csv`
- `runtime_stage_exit_integrated_trade_summary.csv`
"""
    write_text(OUT_MD, md)

    print(f"Wrote {OUT_STAGE}")
    print(f"Wrote {OUT_STAGE_SUMMARY}")
    print(f"Wrote {OUT_TRADE}")
    print(f"Wrote {OUT_MD}")
    print("\nTrade status:")
    print(trade_status_summary.to_string(index=False))
    print("\nPriority 1 blockers:", priority1_blockers)
    print("Priority 1 strict tick/journal replay rows:", strict_tick_rows)


if __name__ == "__main__":
    main()
