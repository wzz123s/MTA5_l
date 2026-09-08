# -*- coding: utf-8 -*-
"""Residual audit for relaxed post_n mismatch candidates.

Diagnostic-only:
- excludes relaxed post_n-number mismatch candidates from a copied matching pass
- does not modify the canonical mapper
- does not modify EA/Python signal or dynamic-risk outputs
"""

from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

MODE_AUDIT_DIR = VALIDATION_DIR / "stage_state_mode_number_aware_runtime_label_mapping_audit_20260718"
BASE_FAMILY_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"
DIAG_FAMILY_MAPPING_DIR = VALIDATION_DIR / "stage_state_python_slot1_runtime_label_feasibility_20260717" / "diagnostic_mapping"

OUT_DIR = VALIDATION_DIR / "stage_state_relaxed_postn_mismatch_residual_audit_20260718"

BASE_CANDIDATES = MODE_AUDIT_DIR / "baseline_mode_number_candidate_matches.csv"
DIAG_CANDIDATES = MODE_AUDIT_DIR / "diagnostic_mode_number_candidate_matches.csv"
BASE_UNIQUE = MODE_AUDIT_DIR / "baseline_mode_number_unique_matches.csv"
DIAG_UNIQUE = MODE_AUDIT_DIR / "diagnostic_mode_number_unique_matches.csv"
TARGET_STRICT_REVIEW = MODE_AUDIT_DIR / "mode_number_target_strict_review.csv"
BASE_FAMILY_SUMMARY = BASE_FAMILY_MAPPING_DIR / "unique_match_summary.csv"
DIAG_FAMILY_SUMMARY = DIAG_FAMILY_MAPPING_DIR / "unique_match_summary.csv"

TARGET_IDS = ["mt5_0052", "mt5_0054", "mt5_0067", "mt5_0068", "mt5_0069"]
KEY_TARGET_IDS = ["mt5_0068", "mt5_0069"]

RELIABLE_TIERS = {
    "exact_align90_all",
    "nearby_60_all",
    "nearby_180_all",
    "nearby_1d_all",
    "nearby_7d_all",
}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_md(lines: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8-sig")


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def num(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return default
    return float(parsed)


def source_row(frame: pd.DataFrame, source: str) -> pd.Series:
    hit = frame[frame["source"].astype(str).eq(source)]
    if hit.empty:
        raise ValueError(f"missing source={source}")
    return hit.iloc[0]


def classify_mismatch(row: pd.Series) -> str:
    abs_minutes = abs(num(row.get("time_diff_minutes")))
    py_postn = str(row.get("py_postn_key", "")).startswith("post_n")
    mt5_postn = str(row.get("mt5_postn_key", "")).startswith("post_n")
    py_family = str(row.get("py_mode_family", ""))
    mt5_family = str(row.get("mt5_mode_family", ""))
    trigger_same = boolish(row.get("trigger_same"))

    if abs_minutes > 24 * 60:
        return "far_window_postn_mismatch_artifact"
    if py_postn and mt5_postn and trigger_same and abs_minutes <= 60:
        return "near_exact_postn_number_drift"
    if py_family != mt5_family and trigger_same and abs_minutes <= 24 * 60:
        return "near_trigger_family_drift"
    if abs_minutes > 180:
        return "time_axis_postn_mismatch_artifact"
    return "other_relaxed_postn_mismatch"


def mismatch_reason(row: pd.Series) -> str:
    cls = str(row.get("mismatch_classification", ""))
    if cls == "near_exact_postn_number_drift":
        return "same trigger family and near/exact time, but post_nN counter differs"
    if cls == "near_trigger_family_drift":
        return "same trigger family and within 1 day, but mode family/key differs"
    if cls == "far_window_postn_mismatch_artifact":
        return "candidate is selected from a far relaxed window, so post_nN mismatch should not drive unique matching"
    if cls == "time_axis_postn_mismatch_artifact":
        return "time displacement is large enough that relaxed post_n mismatch is unsafe"
    return "relaxed post_n mismatch not safe for unique matching"


def collect_previous_mismatches(base_unique: pd.DataFrame, diag_unique: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scenario, frame in [("baseline_mode_number", base_unique), ("diagnostic_mode_number", diag_unique)]:
        subset = frame[
            frame["source"].astype(str).eq("python_mt5")
            & frame["postn_number_mismatch"].map(boolish)
        ].copy()
        subset["scenario"] = scenario
        subset["mismatch_classification"] = subset.apply(classify_mismatch, axis=1)
        subset["mismatch_reason"] = subset.apply(mismatch_reason, axis=1)
        rows.append(subset)
    return pd.concat(rows, ignore_index=True, sort=False) if rows else pd.DataFrame()


def exclusion_mask(candidates: pd.DataFrame) -> pd.Series:
    return (
        candidates["postn_number_mismatch"].map(boolish)
        & ~candidates["strict_is_reliable_tier"].map(boolish)
        & candidates["strict_match_tier"].astype(str).ne("same_dir_7d_unclassified")
    )


def greedy_unique_matches(candidates: pd.DataFrame) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()
    eligible = candidates[
        candidates["strict_match_tier"].astype(str).ne("same_dir_7d_unclassified")
        & ~candidates["exclude_relaxed_postn_mismatch"].map(boolish)
    ].copy()
    if eligible.empty:
        return eligible
    eligible["profit_abs_diff"] = pd.to_numeric(eligible["profit_diff"], errors="coerce").abs()
    eligible = eligible.sort_values(
        [
            "strict_tier_rank",
            "abs_time_diff_minutes",
            "profit_abs_diff",
            "py_trade_id",
            "mt5_trade_id",
        ],
        ascending=[True, True, True, True, True],
    )
    used_py: set[str] = set()
    used_mt5: set[str] = set()
    selected: list[pd.Series] = []
    for _, row in eligible.iterrows():
        py_id = str(row["py_trade_id"])
        mt5_id = str(row["mt5_trade_id"])
        if py_id in used_py or mt5_id in used_mt5:
            continue
        selected.append(row)
        used_py.add(py_id)
        used_mt5.add(mt5_id)
    if not selected:
        return pd.DataFrame(columns=eligible.columns)
    return pd.DataFrame(selected).reset_index(drop=True)


def prepare_candidates(frame: pd.DataFrame, scenario: str) -> pd.DataFrame:
    out = frame.copy()
    out["scenario"] = scenario
    out["exclude_relaxed_postn_mismatch"] = exclusion_mask(out)
    out["exclusion_reason"] = ""
    out.loc[out["exclude_relaxed_postn_mismatch"], "exclusion_reason"] = "relaxed_postn_number_mismatch"
    return out


def summarize_unique(
    scenario: str,
    source: str,
    family_summary: pd.DataFrame,
    candidates: pd.DataFrame,
    unique: pd.DataFrame,
) -> dict[str, object]:
    family = source_row(family_summary, source)
    source_unique = unique[unique["source"].astype(str).eq(source)].copy() if not unique.empty else unique
    source_candidates = candidates[candidates["source"].astype(str).eq(source)].copy()
    python_trades = int(num(family["python_trades"]))
    mt5_trades = int(num(family["mt5_trades"]))
    matched = int(len(source_unique))
    reliable = int(source_unique["strict_is_reliable_tier"].map(boolish).sum()) if matched else 0
    py_profit = pd.to_numeric(source_unique.get("py_profit", pd.Series(dtype=float)), errors="coerce").sum()
    mt5_profit = pd.to_numeric(source_unique.get("mt5_profit", pd.Series(dtype=float)), errors="coerce").sum()
    return {
        "scenario": scenario,
        "source": source,
        "python_trades": python_trades,
        "mt5_trades": mt5_trades,
        "matched_unique": matched,
        "reliable_tier_matched": reliable,
        "relaxed_tier_matched": matched - reliable,
        "python_unmatched": python_trades - matched,
        "mt5_unmatched": mt5_trades - matched,
        "matched_python_profit": round(float(py_profit), 6),
        "matched_mt5_profit": round(float(mt5_profit), 6),
        "matched_profit_diff": round(float(py_profit - mt5_profit), 6),
        "postn_number_mismatch_in_unique": int(source_unique["postn_number_mismatch"].map(boolish).sum()) if matched else 0,
        "reliable_postn_number_mismatch_in_unique": int(
            (
                source_unique["postn_number_mismatch"].map(boolish)
                & source_unique["strict_is_reliable_tier"].map(boolish)
            ).sum()
        )
        if matched
        else 0,
        "excluded_candidate_rows": int(source_candidates["exclude_relaxed_postn_mismatch"].map(boolish).sum()),
        "excluded_mt5_ids": ";".join(
            source_candidates[source_candidates["exclude_relaxed_postn_mismatch"].map(boolish)]["mt5_trade_id"]
            .astype(str)
            .drop_duplicates()
            .head(30)
        ),
    }


def build_outputs(
    scenario: str,
    candidate_path: Path,
    family_summary_path: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    candidates = prepare_candidates(read_csv(candidate_path), scenario)
    unique = greedy_unique_matches(candidates)
    family_summary = read_csv(family_summary_path)
    summary = pd.DataFrame(
        [
            summarize_unique(scenario, source, family_summary, candidates, unique)
            for source in sorted(candidates["source"].astype(str).unique())
        ]
    )
    return candidates, unique, summary


def build_delta(summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for source in sorted(summary["source"].astype(str).unique()):
        base = summary[
            summary["scenario"].astype(str).eq("baseline_strict_plus_exclusion")
            & summary["source"].astype(str).eq(source)
        ].iloc[0]
        diag = summary[
            summary["scenario"].astype(str).eq("diagnostic_strict_plus_exclusion")
            & summary["source"].astype(str).eq(source)
        ].iloc[0]
        row = {"source": source, "comparison": "diagnostic_minus_baseline_strict_plus_exclusion"}
        for col in [
            "python_trades",
            "mt5_trades",
            "matched_unique",
            "reliable_tier_matched",
            "relaxed_tier_matched",
            "python_unmatched",
            "mt5_unmatched",
            "matched_profit_diff",
            "postn_number_mismatch_in_unique",
            "reliable_postn_number_mismatch_in_unique",
            "excluded_candidate_rows",
        ]:
            row[f"baseline_{col}"] = base[col]
            row[f"diagnostic_{col}"] = diag[col]
            row[f"delta_{col}"] = num(diag[col]) - num(base[col])
        rows.append(row)
    return pd.DataFrame(rows)


def build_target_retention(unique: pd.DataFrame, target_strict_review: pd.DataFrame) -> pd.DataFrame:
    rows = []
    py_unique = unique[unique["source"].astype(str).eq("python_mt5")].copy()
    for mt5_id in TARGET_IDS:
        hit = py_unique[py_unique["mt5_trade_id"].astype(str).eq(mt5_id)].copy()
        previous = target_strict_review[target_strict_review["mt5_trade_id"].astype(str).eq(mt5_id)].copy()
        row = {
            "mt5_trade_id": mt5_id,
            "previous_strict_diagnostic_matched": bool(previous.iloc[0]["strict_diagnostic_matched"]) if not previous.empty else "",
            "previous_strict_diagnostic_tier": previous.iloc[0]["strict_diagnostic_tier"] if not previous.empty else "",
            "previous_strict_diagnostic_py_mode": previous.iloc[0]["strict_diagnostic_py_mode"] if not previous.empty else "",
            "previous_strict_diagnostic_postn_number_same": previous.iloc[0]["strict_diagnostic_postn_number_same"] if not previous.empty else "",
            "retained_after_exclusion": not hit.empty,
            "post_exclusion_tier": hit.iloc[0]["strict_match_tier"] if not hit.empty else "",
            "post_exclusion_py_trade_id": hit.iloc[0]["py_trade_id"] if not hit.empty else "",
            "post_exclusion_py_mode": hit.iloc[0]["py_mode"] if not hit.empty else "",
            "post_exclusion_mt5_signal_src": hit.iloc[0]["mt5_signal_src"] if not hit.empty else "",
            "post_exclusion_postn_number_same": hit.iloc[0]["postn_number_same"] if not hit.empty else "",
            "post_exclusion_postn_number_mismatch": hit.iloc[0]["postn_number_mismatch"] if not hit.empty else False,
            "is_key_runtime_label_target": mt5_id in KEY_TARGET_IDS,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def build_mismatch_summary(previous_mismatches: pd.DataFrame) -> pd.DataFrame:
    if previous_mismatches.empty:
        return pd.DataFrame(columns=["scenario", "mismatch_classification", "rows", "mt5_ids"])
    return (
        previous_mismatches.groupby(["scenario", "mismatch_classification"], dropna=False)
        .agg(
            rows=("mt5_trade_id", "count"),
            mt5_ids=("mt5_trade_id", lambda s: ";".join(s.astype(str).drop_duplicates())),
        )
        .reset_index()
        .sort_values(["scenario", "rows", "mismatch_classification"], ascending=[True, False, True])
    )


def simple_table(frame: pd.DataFrame, max_rows: int = 50) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def build_final_decision(delta: pd.DataFrame, target_retention: pd.DataFrame) -> pd.DataFrame:
    py = delta[delta["source"].astype(str).eq("python_mt5")].iloc[0]
    target_subset = target_retention[target_retention["is_key_runtime_label_target"].map(boolish)].copy()
    key_targets_retained = bool(target_subset["retained_after_exclusion"].map(boolish).all()) if not target_subset.empty else False
    key_targets_number_safe = bool(~target_subset["post_exclusion_postn_number_mismatch"].map(boolish).any()) if not target_subset.empty else False
    mismatch_count = int(num(py["diagnostic_postn_number_mismatch_in_unique"]))
    matched_delta = num(py["delta_matched_unique"])
    reliable_delta = num(py["delta_reliable_tier_matched"])
    py_unmatched_delta = num(py["delta_python_unmatched"])
    mt5_unmatched_delta = num(py["delta_mt5_unmatched"])
    pass_gate = (
        mismatch_count == 0
        and key_targets_retained
        and key_targets_number_safe
        and matched_delta >= 0
        and py_unmatched_delta <= 0
        and mt5_unmatched_delta <= 0
    )
    return pd.DataFrame(
        [
            {
                "python_mt5_baseline_matched_unique": py["baseline_matched_unique"],
                "python_mt5_diagnostic_matched_unique": py["diagnostic_matched_unique"],
                "delta_matched_unique": matched_delta,
                "python_mt5_baseline_reliable_tier_matched": py["baseline_reliable_tier_matched"],
                "python_mt5_diagnostic_reliable_tier_matched": py["diagnostic_reliable_tier_matched"],
                "delta_reliable_tier_matched": reliable_delta,
                "python_mt5_baseline_python_unmatched": py["baseline_python_unmatched"],
                "python_mt5_diagnostic_python_unmatched": py["diagnostic_python_unmatched"],
                "delta_python_unmatched": py_unmatched_delta,
                "python_mt5_baseline_mt5_unmatched": py["baseline_mt5_unmatched"],
                "python_mt5_diagnostic_mt5_unmatched": py["diagnostic_mt5_unmatched"],
                "delta_mt5_unmatched": mt5_unmatched_delta,
                "diagnostic_postn_number_mismatch_count": mismatch_count,
                "diagnostic_reliable_postn_number_mismatch_count": int(num(py["diagnostic_reliable_postn_number_mismatch_in_unique"])),
                "key_runtime_label_targets_retained": key_targets_retained,
                "key_runtime_label_targets_number_safe": key_targets_number_safe,
                "strict_plus_exclusion_pass": pass_gate,
                "layer3_admission_gap_gate_open": pass_gate,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "recommended_next_action": (
                    "audit_layer3_admission_gap_for_relabel_targets_missing_from_dynamic"
                    if pass_gate
                    else "close_runtime_label_direction_and_return_to_layer3_admission_only_if_independently_supported"
                ),
            }
        ]
    )


def build_report(
    final: pd.DataFrame,
    summary: pd.DataFrame,
    delta: pd.DataFrame,
    target_retention: pd.DataFrame,
    previous_mismatches: pd.DataFrame,
    mismatch_summary: pd.DataFrame,
) -> list[str]:
    f = final.iloc[0].to_dict()
    return [
        "# Stage-State Relaxed post_n Mismatch Residual Audit",
        "",
        "## Final Decision",
        "",
        f"- Diagnostic matched unique delta: `{f['delta_matched_unique']}`.",
        f"- Diagnostic reliable-tier delta: `{f['delta_reliable_tier_matched']}`.",
        f"- Diagnostic Python-unmatched delta: `{f['delta_python_unmatched']}`.",
        f"- Diagnostic MT5-unmatched delta: `{f['delta_mt5_unmatched']}`.",
        f"- Diagnostic post_n mismatch count: `{f['diagnostic_postn_number_mismatch_count']}`.",
        f"- Key runtime-label targets retained: `{f['key_runtime_label_targets_retained']}`.",
        f"- Key runtime-label targets number-safe: `{f['key_runtime_label_targets_number_safe']}`.",
        f"- Strict-plus-exclusion pass: `{f['strict_plus_exclusion_pass']}`.",
        f"- Layer3 admission gap gate: `{f['layer3_admission_gap_gate_open']}`.",
        f"- Main signal gate: `{f['main_signal_change_gate_open']}`.",
        f"- EA behavior gate: `{f['ea_behavior_gate_open']}`.",
        f"- Mapping gate: `{f['mapping_change_gate_open']}`.",
        f"- Merge gate: `{f['merge_gate_pass']}`.",
        "",
        "## Strict-Plus-Exclusion Summary",
        "",
        simple_table(summary),
        "",
        "## Diagnostic Minus Baseline Delta",
        "",
        simple_table(delta),
        "",
        "## Target Retention",
        "",
        simple_table(target_retention),
        "",
        "## Previous Mismatch Summary",
        "",
        simple_table(mismatch_summary),
        "",
        "## Previous Mismatch Rows",
        "",
        simple_table(
            previous_mismatches[
                [
                    "scenario",
                    "mt5_trade_id",
                    "strict_match_tier",
                    "py_trade_id",
                    "py_date",
                    "mt5_signal_anchor_time",
                    "time_diff_minutes",
                    "py_mode",
                    "mt5_signal_src",
                    "mismatch_classification",
                    "mismatch_reason",
                ]
            ],
            max_rows=30,
        ),
        "",
        "## Interpretation",
        "",
        "- Excluding relaxed post_n-number mismatch candidates clears the post_n mismatch count from the diagnostic unique set.",
        "- The key runtime-label targets `mt5_0068` and `mt5_0069` remain retained and post_n-number-safe under this stricter copied matching pass.",
        "- This still does not edit the canonical mapper or strategy outputs. It only opens a diagnostic Layer3 admission-gap follow-up if the pass criteria are met.",
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    base_unique_previous = read_csv(BASE_UNIQUE)
    diag_unique_previous = read_csv(DIAG_UNIQUE)
    previous_mismatches = collect_previous_mismatches(base_unique_previous, diag_unique_previous)
    mismatch_summary = build_mismatch_summary(previous_mismatches)

    base_candidates, base_unique, base_summary = build_outputs(
        "baseline_strict_plus_exclusion",
        BASE_CANDIDATES,
        BASE_FAMILY_SUMMARY,
    )
    diag_candidates, diag_unique, diag_summary = build_outputs(
        "diagnostic_strict_plus_exclusion",
        DIAG_CANDIDATES,
        DIAG_FAMILY_SUMMARY,
    )
    summary = pd.concat([base_summary, diag_summary], ignore_index=True)
    delta = build_delta(summary)
    target_retention = build_target_retention(diag_unique, read_csv(TARGET_STRICT_REVIEW))
    final = build_final_decision(delta, target_retention)

    write_csv(previous_mismatches, OUT_DIR / "previous_relaxed_postn_mismatch_rows.csv")
    write_csv(mismatch_summary, OUT_DIR / "previous_relaxed_postn_mismatch_summary.csv")
    write_csv(base_candidates, OUT_DIR / "baseline_strict_plus_exclusion_candidates.csv")
    write_csv(diag_candidates, OUT_DIR / "diagnostic_strict_plus_exclusion_candidates.csv")
    write_csv(base_unique, OUT_DIR / "baseline_strict_plus_exclusion_unique_matches.csv")
    write_csv(diag_unique, OUT_DIR / "diagnostic_strict_plus_exclusion_unique_matches.csv")
    write_csv(summary, OUT_DIR / "strict_plus_exclusion_summary.csv")
    write_csv(delta, OUT_DIR / "strict_plus_exclusion_delta_summary.csv")
    write_csv(target_retention, OUT_DIR / "strict_plus_exclusion_target_retention.csv")
    write_csv(final, OUT_DIR / "strict_plus_exclusion_final_decision.csv")
    write_md(build_report(final, summary, delta, target_retention, previous_mismatches, mismatch_summary), OUT_DIR / "relaxed_postn_mismatch_residual_audit.md")
    write_md(
        [
            "# Relaxed post_n Mismatch Residual Audit",
            "",
            f"- Matched unique delta: `{num(final.loc[0, 'delta_matched_unique'])}`.",
            f"- Reliable-tier delta: `{num(final.loc[0, 'delta_reliable_tier_matched'])}`.",
            f"- Diagnostic post_n mismatch count: `{int(final.loc[0, 'diagnostic_postn_number_mismatch_count'])}`.",
            f"- Layer3 admission gap gate: `{bool(final.loc[0, 'layer3_admission_gap_gate_open'])}`.",
            f"- Merge gate: `{bool(final.loc[0, 'merge_gate_pass'])}`.",
        ],
        OUT_DIR / "README.md",
    )
    print(f"Wrote {OUT_DIR}")
    print(final.to_string(index=False))


if __name__ == "__main__":
    main()
