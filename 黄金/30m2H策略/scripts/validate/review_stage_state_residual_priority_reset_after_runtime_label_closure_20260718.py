# -*- coding: utf-8 -*-
"""Reset residual priorities after closing the runtime-label branch.

Diagnostic-only:
- summarizes gates from the runtime-label audit chain
- ranks the remaining residual buckets
- does not edit EA, signal builders, dynamic-risk outputs, or the canonical mapper
"""

from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

SOURCE_DIR = VALIDATION_DIR / "stage_state_ea_python_slot1_trigger_family_source_audit_20260717"
RUNTIME_DIR = VALIDATION_DIR / "stage_state_python_slot1_runtime_label_feasibility_20260717"
MODE_DIR = VALIDATION_DIR / "stage_state_mode_number_aware_runtime_label_mapping_audit_20260718"
STRICT_DIR = VALIDATION_DIR / "stage_state_relaxed_postn_mismatch_residual_audit_20260718"
LAYER3_DIR = VALIDATION_DIR / "stage_state_layer3_admission_gap_runtime_label_targets_20260718"
NO_CANDIDATE_DIR = VALIDATION_DIR / "stage_state_m15_slot1_no_candidate_source_gap_audit_20260717"

OUT_DIR = VALIDATION_DIR / "stage_state_residual_priority_reset_after_runtime_label_closure_20260718"

SOURCE_DECISION = SOURCE_DIR / "slot1_trigger_family_source_final_decision.csv"
RUNTIME_DECISION = RUNTIME_DIR / "runtime_label_final_decision.csv"
MODE_DECISION = MODE_DIR / "mode_number_final_decision.csv"
STRICT_DECISION = STRICT_DIR / "strict_plus_exclusion_final_decision.csv"
LAYER3_DECISION = LAYER3_DIR / "layer3_admission_final_decision.csv"
LAYER3_CASES = LAYER3_DIR / "layer3_admission_case_review.csv"
NO_CANDIDATE_CASES = NO_CANDIDATE_DIR / "m15_slot1_no_candidate_case_review.csv"
NO_CANDIDATE_SUMMARY = NO_CANDIDATE_DIR / "m15_slot1_no_candidate_classification_summary.csv"


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


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def text(value: object, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value)


def num(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return default
    return float(parsed)


def value(row: pd.Series, name: str, default: object = "") -> object:
    if name not in row.index:
        return default
    return row[name]


def profit_for_ids(cases: pd.DataFrame, ids: list[str]) -> float:
    if "mt5_trade_id" not in cases.columns or "mt5_net_profit" not in cases.columns:
        return 0.0
    selected = cases[cases["mt5_trade_id"].astype(str).isin(ids)].copy()
    return float(pd.to_numeric(selected["mt5_net_profit"], errors="coerce").fillna(0.0).sum())


def count_for_class(summary: pd.DataFrame, name: str) -> int:
    if "primary_classification" not in summary.columns:
        return 0
    hit = summary[summary["primary_classification"].astype(str).eq(name)]
    if hit.empty:
        return 0
    return int(num(hit.iloc[0].get("count", 0), 0))


def profit_for_class(summary: pd.DataFrame, name: str) -> float:
    if "primary_classification" not in summary.columns:
        return 0.0
    hit = summary[summary["primary_classification"].astype(str).eq(name)]
    if hit.empty:
        return 0.0
    return num(hit.iloc[0].get("mt5_net_profit_sum", 0.0), 0.0)


def build_gate_summary() -> pd.DataFrame:
    source = first_row(SOURCE_DECISION)
    runtime = first_row(RUNTIME_DECISION)
    mode = first_row(MODE_DECISION)
    strict = first_row(STRICT_DECISION)
    layer3 = first_row(LAYER3_DECISION)

    rows = [
        {
            "step_order": 1,
            "chain_step": "source_generation_audit",
            "evidence_status": "source_gap_explained",
            "key_metric": f"python_relabel_gap={value(source, 'python_relabel_gap_count')}; base_sequence_reset_gap={value(source, 'base_sequence_reset_gap_count')}",
            "blocking_reason": "diagnostic source evidence only; no merge gate opened",
            "gate_pass_for_merge": False,
            "next_gate_opened": False,
        },
        {
            "step_order": 2,
            "chain_step": "target_only_runtime_label",
            "evidence_status": "target_only_pass" if boolish(value(runtime, "target_only_pass")) else "target_only_fail",
            "key_metric": f"target_explained={value(runtime, 'target_explained_count')}; dynamic_relabelable={value(runtime, 'dynamic_relabelable_target_count')}; full_chain_delta={value(runtime, 'delta_matched_unique')}",
            "blocking_reason": "full-chain widened/unmatched worsened and post_n number mismatch appeared",
            "gate_pass_for_merge": False,
            "next_gate_opened": False,
        },
        {
            "step_order": 3,
            "chain_step": "mode_number_aware_mapping",
            "evidence_status": "target_number_safe_but_global_relaxed_mismatch",
            "key_metric": f"matched_delta={value(mode, 'delta_matched_unique')}; global_postn_mismatch={value(mode, 'diagnostic_postn_number_mismatch_count')}",
            "blocking_reason": "global relaxed post_n mismatch remained",
            "gate_pass_for_merge": boolish(value(mode, "mode_number_aware_pass")),
            "next_gate_opened": False,
        },
        {
            "step_order": 4,
            "chain_step": "strict_plus_exclusion",
            "evidence_status": "target_improvement_retained",
            "key_metric": f"matched_delta={value(strict, 'delta_matched_unique')}; postn_mismatch={value(strict, 'diagnostic_postn_number_mismatch_count')}",
            "blocking_reason": "only opened Layer3 admission diagnostics, not merge",
            "gate_pass_for_merge": False,
            "next_gate_opened": boolish(value(strict, "layer3_admission_gap_gate_open")),
        },
        {
            "step_order": 5,
            "chain_step": "layer3_admission",
            "evidence_status": "runtime_label_branch_closed",
            "key_metric": f"missing_layer3_targets={value(layer3, 'missing_layer3_target_count')}; reason={value(layer3, 'missing_layer3_failure_reasons')}; low_blast={value(layer3, 'low_blast_admission_rule_supported')}",
            "blocking_reason": "missing targets fail Layer3 threshold before max-position; rescue requires broad Layer3 admission change",
            "gate_pass_for_merge": boolish(value(layer3, "merge_gate_pass")),
            "next_gate_opened": False,
        },
    ]
    return pd.DataFrame(rows)


def build_residual_priority() -> pd.DataFrame:
    no_candidate_cases = read_csv(NO_CANDIDATE_CASES)
    no_candidate_summary = read_csv(NO_CANDIDATE_SUMMARY)
    layer3_cases = read_csv(LAYER3_CASES)

    missing_layer3_ids = (
        layer3_cases[layer3_cases["is_missing_layer3_target"].astype(str).str.lower().eq("true")][
            "mt5_trade_id"
        ]
        .astype(str)
        .tolist()
    )

    rows = [
        {
            "priority_rank": 0,
            "bucket": "runtime_label_layer3_threshold_gap",
            "status": "closed",
            "sample_count": len(missing_layer3_ids),
            "mt5_net_profit_sum": round(profit_for_ids(no_candidate_cases, missing_layer3_ids), 6),
            "risk_level": "high_blast_if_forced",
            "why": "mt5_0052/0054 need Layer3 threshold bypass; no low-blast admission rule",
            "next_action": "do_not_modify_layer3_or_runtime_label_mainline",
        },
        {
            "priority_rank": 1,
            "bucket": "stage_exit_python_unmatched_unique_match_conflict",
            "status": "active_next",
            "sample_count": 1,
            "mt5_net_profit_sum": "",
            "risk_level": "diagnostic_first",
            "why": "current plan already notes one remaining P1 Stage-exit/Python-unmatched conflict after bridge; can audit without EA behavior change",
            "next_action": "run_stage_state_python_unmatched_unique_match_conflict_audit",
        },
        {
            "priority_rank": 2,
            "bucket": "independent_mt5_signal_gap",
            "status": "active_after_p1",
            "sample_count": "",
            "mt5_net_profit_sum": "",
            "risk_level": "medium",
            "why": "Layer3 final decision recommends returning to EA stage-exit or independent signal gap after runtime-label closure",
            "next_action": "quantify_independent_signal_gap_after_p1_conflict",
        },
        {
            "priority_rank": 3,
            "bucket": "time_axis_far_window_artifact_mt5_0050",
            "status": "defer",
            "sample_count": count_for_class(no_candidate_summary, "time_axis_drift"),
            "mt5_net_profit_sum": round(profit_for_class(no_candidate_summary, "time_axis_drift"), 6),
            "risk_level": "high_mapping_blast",
            "why": "positive single sample, but prior audits classify it as time-axis/far-window artifact; widening mapping risks false matches",
            "next_action": "do_not_widen_mapping_window_without_new_cohort",
        },
        {
            "priority_rank": 4,
            "bucket": "base_sequence_reset_gap_mt5_0067",
            "status": "defer",
            "sample_count": 1,
            "mt5_net_profit_sum": round(profit_for_ids(no_candidate_cases, ["mt5_0067"]), 6),
            "risk_level": "low_value_single_negative",
            "why": "single negative MT5 sample; not part of runtime-label relabel cluster",
            "next_action": "keep_as_evidence_bucket_not_main_fix",
        },
        {
            "priority_rank": 5,
            "bucket": "raw_present_layer12_filtered_mt5_0072",
            "status": "defer",
            "sample_count": count_for_class(no_candidate_summary, "raw_present_layer12_filtered"),
            "mt5_net_profit_sum": round(profit_for_class(no_candidate_summary, "raw_present_layer12_filtered"), 6),
            "risk_level": "low_value_single_negative",
            "why": "single negative MT5 sample; opening Layer1/2 filter for it is not justified",
            "next_action": "keep_as_filter_evidence_not_main_fix",
        },
    ]
    return pd.DataFrame(rows)


def build_final_decision(priority: pd.DataFrame) -> pd.DataFrame:
    next_row = priority[priority["status"].eq("active_next")].iloc[0]
    return pd.DataFrame(
        [
            {
                "runtime_label_branch_closed": True,
                "closure_reason": "layer3_threshold_fail_no_low_blast_admission_rule",
                "closed_target_ids": "mt5_0052;mt5_0054",
                "retained_diagnostic_target_ids": "mt5_0068;mt5_0069",
                "selected_next_bucket": next_row["bucket"],
                "selected_next_action": next_row["next_action"],
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "dynamic_risk_change_gate_open": False,
                "merge_gate_pass": False,
                "recommended_next_task": "Stage-state Python-unmatched unique-match conflict audit",
            }
        ]
    )


def build_report(gates: pd.DataFrame, priority: pd.DataFrame, final_decision: pd.DataFrame) -> list[str]:
    decision = final_decision.iloc[0]
    lines = [
        "# Stage-state residual priority reset after runtime-label closure",
        "",
        "## Decision",
        "",
        f"- Runtime-label branch closed: `{decision['runtime_label_branch_closed']}`",
        f"- Closure reason: `{decision['closure_reason']}`",
        f"- Selected next bucket: `{decision['selected_next_bucket']}`",
        f"- Recommended next task: `{decision['recommended_next_task']}`",
        "- Main signal / EA behavior / mapping / dynamic-risk / merge gates all remain `False`.",
        "",
        "## Runtime-label gate chain",
        "",
    ]
    for _, row in gates.sort_values("step_order").iterrows():
        lines.append(
            f"- `{row['chain_step']}`: {row['evidence_status']}; {row['key_metric']}; blocker `{row['blocking_reason']}`"
        )
    lines += ["", "## Residual priority", ""]
    for _, row in priority.sort_values("priority_rank").iterrows():
        lines.append(
            f"- `{row['priority_rank']}` `{row['bucket']}`: status `{row['status']}`, samples `{row['sample_count']}`, risk `{row['risk_level']}`, next `{row['next_action']}`"
        )
    return lines


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gates = build_gate_summary()
    priority = build_residual_priority()
    final_decision = build_final_decision(priority)

    write_csv(gates, OUT_DIR / "runtime_label_gate_chain_summary.csv")
    write_csv(priority, OUT_DIR / "residual_bucket_priority.csv")
    write_csv(final_decision, OUT_DIR / "residual_priority_reset_final_decision.csv")
    write_md(build_report(gates, priority, final_decision), OUT_DIR / "residual_priority_reset_audit.md")
    write_md(
        [
            "# Residual priority reset output",
            "",
            "- `residual_priority_reset_audit.md`",
            "- `residual_priority_reset_final_decision.csv`",
            "- `runtime_label_gate_chain_summary.csv`",
            "- `residual_bucket_priority.csv`",
        ],
        OUT_DIR / "README.md",
    )

    print(f"wrote {OUT_DIR}")
    print(final_decision.to_string(index=False))


if __name__ == "__main__":
    main()
