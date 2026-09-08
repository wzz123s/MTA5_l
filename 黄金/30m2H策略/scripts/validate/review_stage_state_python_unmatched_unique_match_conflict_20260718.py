# -*- coding: utf-8 -*-
"""Audit Python-unmatched unique-match conflicts after runtime-label closure.

Diagnostic-only:
- reviews the current stage-state unique-conflict bucket
- checks whether any P1 row supports EA/stage-exit behavior changes
- does not edit EA, signal builders, dynamic-risk outputs, or the canonical mapper
"""

from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

RESET_DIR = VALIDATION_DIR / "stage_state_residual_priority_reset_after_runtime_label_closure_20260718"
UNIQUE_CONFLICT_DIR = VALIDATION_DIR / "stage_state_mapping_unique_conflict_review_20260716"
DUPLICATE_PROTO_DIR = VALIDATION_DIR / "stage_state_duplicate_continuation_suppression_prototype_20260716"
DUPLICATE_FULL_DIR = VALIDATION_DIR / "stage_state_duplicate_suppression_full_chain_20260717"
TARGETED_FEASIBILITY_DIR = VALIDATION_DIR / "stage_state_targeted_signal_prototype_feasibility_20260717"

OUT_DIR = VALIDATION_DIR / "stage_state_python_unmatched_unique_match_conflict_audit_20260718"

RESET_DECISION = RESET_DIR / "residual_priority_reset_final_decision.csv"
UNIQUE_DECISION = UNIQUE_CONFLICT_DIR / "stage_state_unique_conflict_decision.csv"
UNIQUE_CASES = UNIQUE_CONFLICT_DIR / "stage_state_unique_conflict_case_review.csv"
UNIQUE_ACTION_SUMMARY = UNIQUE_CONFLICT_DIR / "stage_state_unique_conflict_action_summary.csv"
DUPLICATE_PROTO_DECISION = DUPLICATE_PROTO_DIR / "duplicate_suppression_decision.csv"
DUPLICATE_FULL_DECISION = DUPLICATE_FULL_DIR / "stage_state_duplicate_suppression_full_chain_decision.csv"
TARGETED_FEASIBILITY_DECISION = TARGETED_FEASIBILITY_DIR / "targeted_signal_prototype_decision.csv"

P1_ABS_GAP_THRESHOLD = 150.0


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_md(lines: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8-sig")


def first_row(path: Path) -> pd.Series:
    frame = read_csv(path)
    if frame.empty:
        raise ValueError(f"empty csv: {path}")
    return frame.iloc[0]


def num(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return default
    return float(parsed)


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def val(row: pd.Series, name: str, default: object = "") -> object:
    if name not in row.index:
        return default
    value = row[name]
    if pd.isna(value):
        return default
    return value


def classify_behavior(row: pd.Series) -> tuple[str, bool, bool, str]:
    bucket = str(row.get("review_action_bucket", ""))
    if bucket == "far_candidate_accounting_only":
        return (
            "far_candidate_accounting_only",
            False,
            False,
            "candidate is outside reliable behavior window; keep as accounting/window evidence",
        )
    if bucket == "duplicate_continuation_suppression_candidate":
        return (
            "duplicate_continuation_diagnostic_only",
            False,
            True,
            "nearby duplicate continuation was already tested by filtered dynamic/mapping rerun; merge gate stayed closed",
        )
    if bucket == "relaxed_mapping_policy_review":
        return (
            "relaxed_mapping_policy_review",
            False,
            False,
            "conflict depends on relaxed trigger/mode policy; not stage-exit or EA price-side evidence",
        )
    return (
        "unclassified_unique_conflict",
        False,
        False,
        "no behavior-change evidence",
    )


def prepare_case_audit(cases: pd.DataFrame) -> pd.DataFrame:
    out = cases.copy()
    out["abs_gap_numeric"] = pd.to_numeric(out.get("abs_gap_effect_$"), errors="coerce").fillna(0.0)
    out["is_p1"] = out["abs_gap_numeric"].ge(P1_ABS_GAP_THRESHOLD)

    classifications = [classify_behavior(row) for _, row in out.iterrows()]
    out["conflict_classification"] = [item[0] for item in classifications]
    out["ea_or_stage_exit_behavior_evidence"] = [item[1] for item in classifications]
    out["python_signal_diagnostic_candidate"] = [item[2] for item in classifications]
    out["conflict_interpretation"] = [item[3] for item in classifications]

    preferred = [
        "side",
        "trade_id",
        "target_time",
        "raw_anchor",
        "dir_norm",
        "trigger_family",
        "mode_family",
        "mode_or_signal_src",
        "source_profit_$",
        "gap_effect_$",
        "abs_gap_effect_$",
        "is_p1",
        "action_priority",
        "review_priority",
        "action_bucket",
        "review_action_bucket",
        "conflict_classification",
        "ea_or_stage_exit_behavior_evidence",
        "python_signal_diagnostic_candidate",
        "best_candidate_tier",
        "best_candidate_reliable",
        "best_candidate_abs_minutes",
        "best_candidate_py_trade_id",
        "best_candidate_mt5_trade_id",
        "best_candidate_unique_conflict",
        "best_candidate_unique_conflict_with",
        "selected_owner_trade_id",
        "selected_owner_counterpart",
        "selected_owner_match_tier",
        "selected_owner_abs_minutes",
        "mapping_reassign_signal_gap_delta_estimate",
        "spec_pass",
        "spec_reason",
        "sd",
        "stage1_exit",
        "stage2_exit",
        "stage3_exit",
        "conflict_interpretation",
    ]
    return out[[col for col in preferred if col in out.columns]].sort_values(
        by=["is_p1", "abs_gap_effect_$"], ascending=[False, False]
    )


def build_bucket_summary(case_audit: pd.DataFrame) -> pd.DataFrame:
    work = case_audit.copy()
    work["abs_gap_numeric"] = pd.to_numeric(work["abs_gap_effect_$"], errors="coerce").fillna(0.0)
    work["gap_numeric"] = pd.to_numeric(work["gap_effect_$"], errors="coerce").fillna(0.0)
    summary = (
        work.groupby(["is_p1", "side", "conflict_classification"], dropna=False)
        .agg(
            rows=("trade_id", "size"),
            gap_effect_sum=("gap_numeric", "sum"),
            abs_gap_effect_sum=("abs_gap_numeric", "sum"),
            max_abs_gap_effect=("abs_gap_numeric", "max"),
            behavior_evidence_rows=("ea_or_stage_exit_behavior_evidence", "sum"),
            python_signal_diagnostic_rows=("python_signal_diagnostic_candidate", "sum"),
            trade_ids=("trade_id", lambda values: ";".join(map(str, values))),
        )
        .reset_index()
        .sort_values(["is_p1", "abs_gap_effect_sum"], ascending=[False, False])
    )
    for col in ["gap_effect_sum", "abs_gap_effect_sum", "max_abs_gap_effect"]:
        summary[col] = summary[col].round(6)
    return summary


def build_final_decision(case_audit: pd.DataFrame, bucket_summary: pd.DataFrame) -> pd.DataFrame:
    reset = first_row(RESET_DECISION)
    unique = first_row(UNIQUE_DECISION)
    duplicate_proto = first_row(DUPLICATE_PROTO_DECISION)
    duplicate_full = first_row(DUPLICATE_FULL_DECISION)
    targeted = first_row(TARGETED_FEASIBILITY_DECISION)

    p1 = case_audit[case_audit["is_p1"].astype(bool)].copy()
    p1_behavior_rows = int(p1["ea_or_stage_exit_behavior_evidence"].astype(bool).sum())
    p1_duplicate_rows = int(
        p1["conflict_classification"].astype(str).eq("duplicate_continuation_diagnostic_only").sum()
    )
    p1_far_rows = int(p1["conflict_classification"].astype(str).eq("far_candidate_accounting_only").sum())
    p1_relaxed_rows = int(p1["conflict_classification"].astype(str).eq("relaxed_mapping_policy_review").sum())
    p1_abs = float(pd.to_numeric(p1["abs_gap_effect_$"], errors="coerce").fillna(0.0).sum())

    duplicate_full_merge = boolish(val(duplicate_full, "merge_gate_pass"))
    duplicate_full_improved = boolish(val(duplicate_full, "signal_set_gap_improved")) and boolish(
        val(duplicate_full, "unmatched_count_reduced")
    )

    return pd.DataFrame(
        [
            {
                "selected_bucket_from_reset": val(reset, "selected_next_bucket"),
                "unique_conflict_rows_reviewed": int(len(case_audit)),
                "p1_unique_conflict_rows": int(len(p1)),
                "p1_abs_gap_sum": round(p1_abs, 6),
                "p1_far_candidate_accounting_rows": p1_far_rows,
                "p1_duplicate_continuation_rows": p1_duplicate_rows,
                "p1_relaxed_mapping_policy_rows": p1_relaxed_rows,
                "p1_ea_or_stage_exit_behavior_evidence_rows": p1_behavior_rows,
                "duplicate_full_chain_improved_gap": duplicate_full_improved,
                "duplicate_full_chain_merge_gate_pass": duplicate_full_merge,
                "unique_conflict_original_decision": val(unique, "decision"),
                "duplicate_original_decision": val(duplicate_proto, "decision"),
                "duplicate_full_chain_decision": val(duplicate_full, "decision"),
                "targeted_signal_downstream_decision": val(targeted, "decision"),
                "unique_match_conflict_behavior_blocker_closed": p1_behavior_rows == 0,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "dynamic_risk_change_gate_open": False,
                "merge_gate_pass": False,
                "recommended_next_bucket": "independent_mt5_signal_gap",
                "recommended_next_task": "Stage-state independent MT5 signal gap audit",
                "recommended_next_action": "quantify_independent_mt5_signal_gap_after_runtime_label_and_unique_conflict_closure",
            }
        ]
    )


def build_report(
    case_audit: pd.DataFrame,
    bucket_summary: pd.DataFrame,
    final_decision: pd.DataFrame,
    action_summary: pd.DataFrame,
) -> list[str]:
    decision = final_decision.iloc[0]
    p1 = case_audit[case_audit["is_p1"].astype(bool)].copy()
    lines = [
        "# Stage-state Python-unmatched unique-match conflict audit",
        "",
        "## Decision",
        "",
        f"- Reviewed unique-conflict rows: `{decision['unique_conflict_rows_reviewed']}`",
        f"- P1 rows: `{decision['p1_unique_conflict_rows']}`",
        f"- P1 abs gap sum: `{decision['p1_abs_gap_sum']}`",
        f"- Behavior evidence rows: `{decision['p1_ea_or_stage_exit_behavior_evidence_rows']}`",
        f"- Unique-match behavior blocker closed: `{decision['unique_match_conflict_behavior_blocker_closed']}`",
        f"- Recommended next task: `{decision['recommended_next_task']}`",
        "- Main signal / EA behavior / mapping / dynamic-risk / merge gates all remain `False`.",
        "",
        "## P1 Shape",
        "",
        f"- Far candidate accounting-only rows: `{decision['p1_far_candidate_accounting_rows']}`",
        f"- Duplicate continuation diagnostic-only rows: `{decision['p1_duplicate_continuation_rows']}`",
        f"- Relaxed mapping-policy rows: `{decision['p1_relaxed_mapping_policy_rows']}`",
        "",
        "## Top P1 Cases",
        "",
    ]
    for _, row in p1.sort_values("abs_gap_effect_$", ascending=False).iterrows():
        lines.append(
            f"- `{row['trade_id']}` `{row['target_time']}` `{row['side']}` `{row['trigger_family']}/{row['mode_family']}`: "
            f"abs gap `{row['abs_gap_effect_$']}`, class `{row['conflict_classification']}`, "
            f"best candidate `{row.get('best_candidate_mt5_trade_id', '') or row.get('best_candidate_py_trade_id', '')}` "
            f"tier `{row.get('best_candidate_tier', '')}`, interpretation `{row['conflict_interpretation']}`"
        )
    lines += [
        "",
        "## Prior Prototype Status",
        "",
        f"- Duplicate full-chain improved gap: `{decision['duplicate_full_chain_improved_gap']}`",
        f"- Duplicate full-chain merge gate pass: `{decision['duplicate_full_chain_merge_gate_pass']}`",
        f"- Targeted signal downstream decision: `{decision['targeted_signal_downstream_decision']}`",
        "",
        "## Bucket Summary",
        "",
    ]
    for _, row in bucket_summary.iterrows():
        lines.append(
            f"- P1 `{row['is_p1']}` `{row['side']}` `{row['conflict_classification']}`: rows `{row['rows']}`, abs `{row['abs_gap_effect_sum']}`"
        )
    return lines


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cases = read_csv(UNIQUE_CASES)
    action_summary = read_csv(UNIQUE_ACTION_SUMMARY)
    case_audit = prepare_case_audit(cases)
    bucket_summary = build_bucket_summary(case_audit)
    final_decision = build_final_decision(case_audit, bucket_summary)

    write_csv(case_audit, OUT_DIR / "python_unmatched_unique_match_conflict_case_audit.csv")
    write_csv(bucket_summary, OUT_DIR / "python_unmatched_unique_match_conflict_bucket_summary.csv")
    write_csv(action_summary, OUT_DIR / "source_unique_conflict_action_summary.csv")
    write_csv(final_decision, OUT_DIR / "python_unmatched_unique_match_conflict_final_decision.csv")
    write_md(
        build_report(case_audit, bucket_summary, final_decision, action_summary),
        OUT_DIR / "python_unmatched_unique_match_conflict_audit.md",
    )
    write_md(
        [
            "# Python-unmatched unique-match conflict audit output",
            "",
            "- `python_unmatched_unique_match_conflict_audit.md`",
            "- `python_unmatched_unique_match_conflict_final_decision.csv`",
            "- `python_unmatched_unique_match_conflict_case_audit.csv`",
            "- `python_unmatched_unique_match_conflict_bucket_summary.csv`",
            "- `source_unique_conflict_action_summary.csv`",
        ],
        OUT_DIR / "README.md",
    )

    print(f"wrote {OUT_DIR}")
    print(final_decision.to_string(index=False))


if __name__ == "__main__":
    main()
