# -*- coding: utf-8 -*-
"""Audit independent MT5 signal gaps after runtime-label and unique-conflict closure.

Diagnostic-only:
- starts from all current stage-state MT5-unmatched rows
- separates accounting/mapping/time-axis buckets from true independent signal candidates
- does not edit EA, signal builders, dynamic-risk outputs, or the canonical mapper
"""

from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

UNIQUE_AUDIT_DIR = VALIDATION_DIR / "stage_state_python_unmatched_unique_match_conflict_audit_20260718"
RESET_DIR = VALIDATION_DIR / "stage_state_residual_priority_reset_after_runtime_label_closure_20260718"
SIGNAL_TRIAGE_DIR = VALIDATION_DIR / "stage_state_signal_set_residual_triage_20260716"
NO_CANDIDATE_DIR = VALIDATION_DIR / "stage_state_no_candidate_signal_gap_triage_20260717"
TARGETED_REPLAY_DIR = VALIDATION_DIR / "stage_state_targeted_signal_replay_20260717"
RAW_REPLAY_DIR = VALIDATION_DIR / "stage_state_targeted_raw_signal_replay_20260717"
LAYER3_ADMISSION_DIR = VALIDATION_DIR / "stage_state_layer3_admission_gap_runtime_label_targets_20260718"
TARGETED_FEASIBILITY_DIR = VALIDATION_DIR / "stage_state_targeted_signal_prototype_feasibility_20260717"

OUT_DIR = VALIDATION_DIR / "stage_state_independent_mt5_signal_gap_audit_20260718"

UNIQUE_DECISION = UNIQUE_AUDIT_DIR / "python_unmatched_unique_match_conflict_final_decision.csv"
RESET_PRIORITY = RESET_DIR / "residual_bucket_priority.csv"
SIGNAL_CASES = SIGNAL_TRIAGE_DIR / "stage_state_signal_set_case_triage.csv"
NO_CANDIDATE_CASES = NO_CANDIDATE_DIR / "stage_state_no_candidate_signal_gap_cases.csv"
TARGETED_REPLAY_CASES = TARGETED_REPLAY_DIR / "targeted_signal_replay_case_review.csv"
RAW_REPLAY_CASES = RAW_REPLAY_DIR / "targeted_raw_signal_replay_case_review.csv"
LAYER3_ADMISSION_CASES = LAYER3_ADMISSION_DIR / "layer3_admission_case_review.csv"
TARGETED_FEASIBILITY_DECISION = TARGETED_FEASIBILITY_DIR / "targeted_signal_prototype_decision.csv"


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


def read_optional(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return read_csv(path)


def latest_override_ids() -> dict[str, str]:
    overrides: dict[str, str] = {}
    layer3 = read_optional(LAYER3_ADMISSION_CASES)
    if not layer3.empty and "mt5_trade_id" in layer3.columns:
        missing = layer3[layer3.get("is_missing_layer3_target", "").astype(str).str.lower().eq("true")]
        for trade_id in missing["mt5_trade_id"].astype(str):
            overrides[trade_id] = "runtime_label_layer3_threshold_closed"
    reset_priority = read_optional(RESET_PRIORITY)
    if not reset_priority.empty and "bucket" in reset_priority.columns:
        for bucket in reset_priority["bucket"].astype(str):
            if "base_sequence_reset_gap_mt5_0067" in bucket:
                overrides["mt5_0067"] = "base_sequence_reset_gap_defer"
            if "raw_present_layer12_filtered_mt5_0072" in bucket:
                overrides["mt5_0072"] = "raw_present_layer12_filtered_defer"
    return overrides


def classify_case(row: pd.Series, override: str) -> tuple[str, bool, str, str]:
    action_bucket = str(val(row, "action_bucket"))
    no_candidate_bucket = str(val(row, "no_candidate_action_bucket"))
    raw_loss = str(val(row, "raw_chain_loss_point"))
    replay_class = str(val(row, "replay_classification"))

    if override:
        if override == "base_sequence_reset_gap_defer":
            return (
                override,
                False,
                "defer_single_negative_or_sequence_gap",
                "Latest residual reset keeps this as base sequence reset gap, not a direct signal-change candidate.",
            )
        if override == "raw_present_layer12_filtered_defer":
            return (
                override,
                False,
                "defer_single_negative_filter_gap",
                "Latest residual reset keeps this as raw-present but Layer1/2-filtered single negative sample.",
            )
        return (
            override,
            False,
            "closed_by_latest_runtime_label_layer3_admission_audit",
            "Latest runtime-label audit showed this path would need broad Layer3 threshold bypass.",
        )

    if action_bucket == "mapping_policy_first_unique_conflict":
        return (
            "mapping_policy_unique_conflict_accounting",
            False,
            "closed_by_unique_conflict_audit",
            "Unique-conflict audit found no EA/stage-exit behavior evidence.",
        )

    if action_bucket == "time_axis_diagnostic_only":
        return (
            "time_axis_diagnostic_only",
            False,
            "accounting_or_time_axis",
            "Time-axis bridge/window diagnostic only; do not use to widen mapping or change EA.",
        )

    if no_candidate_bucket.startswith("outside_7d"):
        return (
            "outside_7d_mapping_window_accounting",
            False,
            "mapping_window_accounting_only",
            "Outside-7d candidate remains accounting/window evidence, not independent signal proof.",
        )

    if no_candidate_bucket == "m30_post_n_true_no_candidate_signal_gap":
        return (
            "m30_close_postn_true_no_candidate_candidate",
            True,
            "python_raw_generation_audit",
            "This is the narrowest remaining true independent MT5 signal candidate cohort.",
        )

    if raw_loss == "raw_absent_for_mt5_signal":
        return (
            "raw_absent_for_mt5_signal_candidate",
            True,
            "python_raw_generation_audit",
            "Targeted raw replay found no Python raw equivalent at the MT5 signal.",
        )

    if raw_loss == "raw_absent_nearby_opposite_selected":
        return (
            "base_sequence_or_raw_absent_gap_defer",
            False,
            "defer_single_negative_or_sequence_gap",
            "Raw replay points to sequence/opposite-selection structure, not a low-blast direct rule.",
        )

    if raw_loss == "layer12_trigger_family_drift_after_raw_parent":
        return (
            "layer12_trigger_family_drift_high_blast_defer",
            False,
            "defer_high_blast_trigger_transform",
            "Parent-preserve/trigger transform has high blast radius and cannot be direct next fix.",
        )

    if raw_loss == "layer3_displaced_by_nearby_opposite_selection":
        return (
            "layer3_displacement_prototype_not_mergeable",
            False,
            "prototype_already_diagnostic",
            "Layer3 prototype path was diagnostic and later runtime-label/counter audits did not open merge.",
        )

    if no_candidate_bucket == "nearby_opposite_direction_signal_divergence":
        return (
            "nearby_opposite_direction_divergence_defer",
            False,
            "needs_source_replay_or_low_priority",
            "Nearby opposite-direction evidence prevents treating this as independent MT5 signal yet.",
        )

    if "mt5_only_true_signal" in replay_class:
        return (
            "mt5_only_true_signal_needs_python_replay",
            True,
            "python_raw_generation_audit",
            "Targeted replay already marked this as true MT5-only needing Python replay.",
        )

    return (
        "unclassified_mt5_signal_gap_defer",
        False,
        "manual_review",
        "No safe merge or behavior evidence.",
    )


def merge_optional(
    base: pd.DataFrame,
    extra: pd.DataFrame,
    cols: list[str],
    suffix: str,
) -> pd.DataFrame:
    if extra.empty or "trade_id" not in extra.columns:
        return base
    keep = ["trade_id"] + [col for col in cols if col in extra.columns]
    renamed = extra[keep].copy()
    rename_map = {col: f"{col}{suffix}" for col in keep if col != "trade_id" and col in base.columns}
    renamed = renamed.rename(columns=rename_map)
    return base.merge(renamed, on="trade_id", how="left")


def build_case_audit() -> pd.DataFrame:
    signal = read_csv(SIGNAL_CASES)
    mt5 = signal[signal["side"].astype(str).eq("mt5_unmatched")].copy()

    no_candidate = read_optional(NO_CANDIDATE_CASES)
    targeted = read_optional(TARGETED_REPLAY_CASES)
    raw = read_optional(RAW_REPLAY_CASES)

    mt5 = merge_optional(
        mt5,
        no_candidate,
        [
            "no_candidate_action_bucket",
            "next_action_group",
            "review_priority",
            "nearest_same_dir_minutes",
            "same_dir_nearest_trade_id",
            "same_dir_nearest_trigger_family",
            "same_dir_nearest_mode_family",
        ],
        "_no_candidate",
    )
    mt5 = merge_optional(
        mt5,
        targeted,
        [
            "case_review_bucket",
            "replay_classification",
            "recommended_next_action",
            "target_case_id",
            "python_raw_exact_same_family",
            "python_layer12_exact_same_family",
            "python_layer3_exact_same_family",
            "python_dynamic_exact_same_family",
        ],
        "_targeted",
    )
    mt5 = merge_optional(
        mt5,
        raw,
        [
            "raw_chain_loss_point",
            "recommended_next_action",
            "raw_replay_note",
            "main_signal_change_gate_open",
            "ea_behavior_gate_open",
            "merge_gate_pass",
        ],
        "_raw",
    )

    overrides = latest_override_ids()
    classes = []
    for _, row in mt5.iterrows():
        classes.append(classify_case(row, overrides.get(str(row.get("trade_id")), "")))
    mt5["independent_gap_classification"] = [item[0] for item in classes]
    mt5["true_independent_signal_candidate"] = [item[1] for item in classes]
    mt5["recommended_followup_group"] = [item[2] for item in classes]
    mt5["classification_note"] = [item[3] for item in classes]

    mt5["abs_gap_numeric"] = pd.to_numeric(mt5.get("abs_gap_effect_$"), errors="coerce").fillna(0.0)
    mt5["gap_numeric"] = pd.to_numeric(mt5.get("gap_effect_$"), errors="coerce").fillna(0.0)

    preferred = [
        "trade_id",
        "target_time",
        "raw_anchor",
        "dir_norm",
        "trigger_family",
        "mode_family",
        "mode_or_signal_src",
        "gap_effect_$",
        "abs_gap_effect_$",
        "action_bucket",
        "action_note",
        "no_candidate_action_bucket",
        "case_review_bucket",
        "replay_classification",
        "raw_chain_loss_point",
        "true_independent_signal_candidate",
        "independent_gap_classification",
        "recommended_followup_group",
        "classification_note",
        "best_candidate_tier",
        "best_candidate_abs_minutes",
        "best_candidate_py_trade_id",
        "time_axis_candidate",
        "time_axis_has_gap",
        "time_axis_plus120_available",
        "time_axis_current_plus90_layer3_pass",
        "time_axis_raw_plus120_layer3_pass",
        "nearest_same_dir_minutes",
        "same_dir_nearest_trade_id",
        "same_dir_nearest_trigger_family",
        "same_dir_nearest_mode_family",
    ]
    cols = [col for col in preferred if col in mt5.columns]
    return mt5[cols].sort_values(
        by=["true_independent_signal_candidate", "abs_gap_effect_$"], ascending=[False, False]
    )


def build_bucket_summary(case_audit: pd.DataFrame) -> pd.DataFrame:
    work = case_audit.copy()
    work["abs_gap_numeric"] = pd.to_numeric(work["abs_gap_effect_$"], errors="coerce").fillna(0.0)
    work["gap_numeric"] = pd.to_numeric(work["gap_effect_$"], errors="coerce").fillna(0.0)
    summary = (
        work.groupby(["true_independent_signal_candidate", "independent_gap_classification"], dropna=False)
        .agg(
            rows=("trade_id", "size"),
            gap_effect_sum=("gap_numeric", "sum"),
            abs_gap_effect_sum=("abs_gap_numeric", "sum"),
            max_abs_gap_effect=("abs_gap_numeric", "max"),
            trade_ids=("trade_id", lambda values: ";".join(map(str, values))),
        )
        .reset_index()
        .sort_values(["true_independent_signal_candidate", "abs_gap_effect_sum"], ascending=[False, False])
    )
    for col in ["gap_effect_sum", "abs_gap_effect_sum", "max_abs_gap_effect"]:
        summary[col] = summary[col].round(6)
    return summary


def build_final_decision(case_audit: pd.DataFrame, bucket_summary: pd.DataFrame) -> pd.DataFrame:
    unique_decision = first_row(UNIQUE_DECISION)
    targeted_decision = first_row(TARGETED_FEASIBILITY_DECISION)

    true_cases = case_audit[case_audit["true_independent_signal_candidate"].astype(bool)].copy()
    true_ids = ";".join(true_cases["trade_id"].astype(str).tolist())
    true_abs = float(pd.to_numeric(true_cases["abs_gap_effect_$"], errors="coerce").fillna(0.0).sum())

    m30_true = true_cases[
        true_cases["independent_gap_classification"].astype(str).eq(
            "m30_close_postn_true_no_candidate_candidate"
        )
    ]

    return pd.DataFrame(
        [
            {
                "mt5_unmatched_rows_reviewed": int(len(case_audit)),
                "true_independent_signal_candidate_rows": int(len(true_cases)),
                "true_independent_signal_candidate_abs_gap": round(true_abs, 6),
                "true_independent_signal_candidate_ids": true_ids,
                "m30_close_postn_true_no_candidate_rows": int(len(m30_true)),
                "m30_close_postn_true_no_candidate_abs_gap": round(
                    float(pd.to_numeric(m30_true["abs_gap_effect_$"], errors="coerce").fillna(0.0).sum()),
                    6,
                ),
                "unique_conflict_behavior_blocker_closed": boolish(
                    val(unique_decision, "unique_match_conflict_behavior_blocker_closed")
                ),
                "targeted_signal_downstream_decision": val(targeted_decision, "decision"),
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "dynamic_risk_change_gate_open": False,
                "merge_gate_pass": False,
                "recommended_next_bucket": "m30_close_postn_true_no_candidate_source_audit",
                "recommended_next_task": "Stage-state M30 CLOSE post_n true no-candidate source audit",
                "recommended_next_action": "audit_python_raw_generation_for_mt5_0026_and_mt5_0061_before_any_signal_prototype",
            }
        ]
    )


def build_report(case_audit: pd.DataFrame, bucket_summary: pd.DataFrame, final_decision: pd.DataFrame) -> list[str]:
    decision = final_decision.iloc[0]
    true_cases = case_audit[case_audit["true_independent_signal_candidate"].astype(bool)].copy()
    lines = [
        "# Stage-state independent MT5 signal gap audit",
        "",
        "## Decision",
        "",
        f"- MT5-unmatched rows reviewed: `{decision['mt5_unmatched_rows_reviewed']}`",
        f"- True independent signal candidate rows: `{decision['true_independent_signal_candidate_rows']}`",
        f"- True independent signal candidate abs gap: `{decision['true_independent_signal_candidate_abs_gap']}`",
        f"- Candidate ids: `{decision['true_independent_signal_candidate_ids']}`",
        f"- Recommended next task: `{decision['recommended_next_task']}`",
        "- Main signal / EA behavior / mapping / dynamic-risk / merge gates all remain `False`.",
        "",
        "## True Candidate Rows",
        "",
    ]
    for _, row in true_cases.sort_values("abs_gap_effect_$", ascending=False).iterrows():
        lines.append(
            f"- `{row['trade_id']}` `{row['target_time']}` `{row['trigger_family']}/{row['mode_family']}` "
            f"abs gap `{row['abs_gap_effect_$']}`, class `{row['independent_gap_classification']}`, "
            f"next `{row['recommended_followup_group']}`"
        )
    lines += ["", "## Bucket Summary", ""]
    for _, row in bucket_summary.iterrows():
        lines.append(
            f"- candidate `{row['true_independent_signal_candidate']}` `{row['independent_gap_classification']}`: "
            f"rows `{row['rows']}`, abs `{row['abs_gap_effect_sum']}`, ids `{row['trade_ids']}`"
        )
    lines += [
        "",
        "## Interpretation",
        "",
        "- Mapping-policy, time-axis, outside-7d, runtime-label threshold, and high-blast trigger-family buckets remain diagnostic/accounting only.",
        "- The only narrow remaining independent-signal candidate cohort is `M30 CLOSE/post_n` true no-candidate, currently `mt5_0026` and `mt5_0061`.",
        "- This does not open a signal-change gate; it only selects the next source audit.",
    ]
    return lines


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    case_audit = build_case_audit()
    bucket_summary = build_bucket_summary(case_audit)
    final_decision = build_final_decision(case_audit, bucket_summary)

    write_csv(case_audit, OUT_DIR / "independent_mt5_signal_gap_case_audit.csv")
    write_csv(bucket_summary, OUT_DIR / "independent_mt5_signal_gap_bucket_summary.csv")
    write_csv(final_decision, OUT_DIR / "independent_mt5_signal_gap_final_decision.csv")
    write_md(
        build_report(case_audit, bucket_summary, final_decision),
        OUT_DIR / "independent_mt5_signal_gap_audit.md",
    )
    write_md(
        [
            "# Independent MT5 signal gap audit output",
            "",
            "- `independent_mt5_signal_gap_audit.md`",
            "- `independent_mt5_signal_gap_final_decision.csv`",
            "- `independent_mt5_signal_gap_case_audit.csv`",
            "- `independent_mt5_signal_gap_bucket_summary.csv`",
        ],
        OUT_DIR / "README.md",
    )

    print(f"wrote {OUT_DIR}")
    print(final_decision.to_string(index=False))


if __name__ == "__main__":
    main()
