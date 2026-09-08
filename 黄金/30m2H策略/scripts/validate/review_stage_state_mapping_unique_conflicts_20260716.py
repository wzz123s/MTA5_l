# -*- coding: utf-8 -*-
"""Review stage-state mapping unique-conflict clusters.

This follows the signal-set triage gate. It focuses only on rows already
classified as mapping-policy-first unique conflicts, then expands the occupied
candidate and owner pair so the next step can be chosen without changing EA or
signal logic.
"""
from __future__ import annotations


from pathlib import Path

import numpy as np
import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

TRIAGE_DIR = VALIDATION_DIR / "stage_state_signal_set_residual_triage_20260716"
MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
DYNAMIC_INPUT_DIR = VALIDATION_DIR / "dynamic_risk_inputs_shift90_metadatafix_20260714"
OUT_DIR = VALIDATION_DIR / "stage_state_mapping_unique_conflict_review_20260716"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def parse_time(value: object) -> pd.Timestamp:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.notna(parsed):
        return parsed
    return pd.to_datetime(str(value).replace(".", "-"), errors="coerce")


def safe_float(value: object, default: float = np.nan) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def priority(abs_gap: float) -> str:
    if abs_gap >= 150:
        return "P1"
    if abs_gap >= 75:
        return "P2"
    if abs_gap >= 25:
        return "P3"
    return "P4"


def add_py_ids(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["py_trade_id"] = [f"python_mt5_{idx + 1:04d}" for idx in range(len(out))]
    return out


def load_py_metadata() -> pd.DataFrame:
    trades = add_py_ids(read_csv(DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"))
    inputs = add_py_ids(read_csv(DYNAMIC_INPUT_DIR / "python_mt5_dynamic_risk_inputs.csv"))
    keep_input = [
        "py_trade_id",
        "spec_pass",
        "spec_reason",
        "sd",
        "stage1_exit",
        "stage2_exit",
        "stage3_exit",
        "stage3_time",
        "layer3_pass_ea",
    ]
    keep_trade = [
        "py_trade_id",
        "date",
        "dir",
        "trigger_family",
        "mode_family",
        "mode",
        "variant",
        "dynamic_total_$",
        "balance_after",
        "stage1_exit",
        "stage2_exit",
        "stage3_exit",
    ]
    meta = trades[[c for c in keep_trade if c in trades.columns]].merge(
        inputs[[c for c in keep_input if c in inputs.columns]],
        on="py_trade_id",
        how="left",
        suffixes=("", "_input"),
    )
    if "sd" in meta.columns:
        meta["actual_spec_pass"] = pd.to_numeric(meta["sd"], errors="coerce").between(5.0, 35.0)
    else:
        meta["actual_spec_pass"] = False
    meta["spec_flag_stale"] = (
        meta.get("spec_pass", pd.Series(dtype=object)).astype(str).str.lower().eq("false")
        & meta["actual_spec_pass"].fillna(False)
    )
    return meta


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cases = read_csv(TRIAGE_DIR / "mapping_policy_first_signal_cases.csv").copy()
    cases = cases[cases["action_bucket"].astype(str) == "mapping_policy_first_unique_conflict"].copy()
    candidates = read_csv(MAPPING_DIR / "python_mt5_mt5_candidate_matches.csv").copy()
    unique = read_csv(MAPPING_DIR / "python_mt5_mt5_unique_matches.csv").copy()
    unmatched_py = read_csv(MAPPING_DIR / "python_mt5_unmatched_python_trades.csv").copy()
    unmatched_mt5 = read_csv(MAPPING_DIR / "python_mt5_unmatched_mt5_trades.csv").copy()

    for frame in [cases, candidates, unique]:
        if "is_reliable_tier" in frame.columns:
            frame["is_reliable_tier"] = frame["is_reliable_tier"].map(bool_value)
        for col in [
            "tier_rank",
            "abs_time_diff_minutes",
            "time_diff_minutes",
            "profit_diff",
            "profit_abs_diff",
            "py_profit",
            "mt5_profit",
            "gap_effect_$",
            "abs_gap_effect_$",
        ]:
            if col in frame.columns:
                frame[col] = pd.to_numeric(frame[col], errors="coerce")
    if "profit_abs_diff" not in candidates.columns:
        candidates["profit_abs_diff"] = candidates["profit_diff"].abs()
    if "profit_abs_diff" not in unique.columns:
        unique["profit_abs_diff"] = unique["profit_diff"].abs()
    return cases, candidates, unique, unmatched_py, unmatched_mt5


def classify_case(row: dict[str, object]) -> tuple[str, str]:
    side = str(row.get("side", ""))
    tier = str(row.get("best_candidate_tier", ""))
    abs_min = safe_float(row.get("best_candidate_abs_minutes"))
    trigger_same = bool_value(row.get("best_candidate_trigger_same"))
    mode_same = bool_value(row.get("best_candidate_mode_same"))
    reliable = bool_value(row.get("best_candidate_reliable"))
    owner_tier = str(row.get("selected_owner_match_tier", ""))
    owner_abs_min = safe_float(row.get("selected_owner_abs_minutes"))
    spec_stale = bool_value(row.get("spec_flag_stale"))
    actual_spec_pass = bool_value(row.get("actual_spec_pass"))

    if spec_stale:
        return (
            "stale_spec_metadata_review",
            "Current sd is inside StopSpec while spec_pass is false; refresh metadata before using this row for signal changes.",
        )
    if side == "python_unmatched" and pd.notna(abs_min) and abs_min <= 60 and trigger_same and mode_same:
        return (
            "duplicate_continuation_suppression_candidate",
            "Nearby same trigger/mode Python row competes with an occupied MT5 trade; test one-cluster/one-trade suppression as a prototype.",
        )
    if pd.notna(abs_min) and abs_min > 1440:
        return (
            "far_candidate_accounting_only",
            "Best occupied candidate is more than one day away; keep as accounting risk unless a tighter cluster rule proves otherwise.",
        )
    if not reliable or not trigger_same or not mode_same:
        return (
            "relaxed_mapping_policy_review",
            "Conflict depends on relaxed trigger/mode/family matching; tighten or parameterize mapping before treating as shared.",
        )
    if actual_spec_pass and owner_tier and pd.notna(owner_abs_min):
        return (
            "mapping_rule_adjust_candidate",
            "Reliable nearby conflict; a mapping reassignment prototype can estimate shared/only/gap impact.",
        )
    return (
        "mapping_policy_review_required",
        "Conflict is occupied by another unique match; review cluster ownership before signal or EA changes.",
    )


def build_case_review() -> tuple[pd.DataFrame, pd.DataFrame]:
    cases, candidates, unique, _, _ = load_data()
    py_meta = load_py_metadata()

    selected_by_mt5 = {str(row["mt5_trade_id"]): row for _, row in unique.iterrows()}
    selected_by_py = {str(row["py_trade_id"]): row for _, row in unique.iterrows()}
    py_meta_by_id = {str(row["py_trade_id"]): row for _, row in py_meta.iterrows()}

    rows: list[dict[str, object]] = []
    occupancy_rows: list[dict[str, object]] = []
    for _, case in cases.iterrows():
        side = str(case["side"])
        trade_id = str(case["trade_id"])
        best_py = str(case.get("best_candidate_py_trade_id", ""))
        best_mt5 = str(case.get("best_candidate_mt5_trade_id", ""))
        if side == "python_unmatched":
            selected_owner = selected_by_mt5.get(best_mt5)
            owner_id = str(selected_owner.get("py_trade_id", "")) if selected_owner is not None else ""
            owner_counterpart = best_mt5
            owner_profit = safe_float(selected_owner.get("py_profit")) if selected_owner is not None else np.nan
            challenger_profit = safe_float(case.get("source_profit_$"))
            reassign_delta = owner_profit - challenger_profit if pd.notna(owner_profit) else np.nan
            cluster_key = f"mt5:{best_mt5}"
            meta = py_meta_by_id.get(trade_id)
        else:
            selected_owner = selected_by_py.get(best_py)
            owner_id = str(selected_owner.get("mt5_trade_id", "")) if selected_owner is not None else ""
            owner_counterpart = best_py
            owner_profit = safe_float(selected_owner.get("mt5_profit")) if selected_owner is not None else np.nan
            challenger_profit = safe_float(case.get("source_profit_$"))
            reassign_delta = challenger_profit - owner_profit if pd.notna(owner_profit) else np.nan
            cluster_key = f"py:{best_py}"
            meta = py_meta_by_id.get(best_py)

        out = case.to_dict()
        out.update(
            {
                "cluster_key": cluster_key,
                "selected_owner_trade_id": owner_id,
                "selected_owner_counterpart": owner_counterpart,
                "selected_owner_match_tier": selected_owner.get("match_tier", "") if selected_owner is not None else "",
                "selected_owner_abs_minutes": safe_float(selected_owner.get("abs_time_diff_minutes")) if selected_owner is not None else np.nan,
                "selected_owner_py_profit": safe_float(selected_owner.get("py_profit")) if selected_owner is not None else np.nan,
                "selected_owner_mt5_profit": safe_float(selected_owner.get("mt5_profit")) if selected_owner is not None else np.nan,
                "selected_owner_profit_diff": safe_float(selected_owner.get("profit_diff")) if selected_owner is not None else np.nan,
                "mapping_reassign_signal_gap_delta_estimate": reassign_delta,
            }
        )
        if meta is not None:
            out.update(
                {
                    "spec_pass": meta.get("spec_pass", ""),
                    "spec_reason": meta.get("spec_reason", ""),
                    "sd": meta.get("sd", ""),
                    "actual_spec_pass": bool_value(meta.get("actual_spec_pass")),
                    "spec_flag_stale": bool_value(meta.get("spec_flag_stale")),
                    "stage1_exit": meta.get("stage1_exit", ""),
                    "stage2_exit": meta.get("stage2_exit", ""),
                    "stage3_exit": meta.get("stage3_exit", ""),
                }
            )
        else:
            out.update(
                {
                    "spec_pass": "",
                    "spec_reason": "",
                    "sd": np.nan,
                    "actual_spec_pass": False,
                    "spec_flag_stale": False,
                    "stage1_exit": "",
                    "stage2_exit": "",
                    "stage3_exit": "",
                }
            )
        action, note = classify_case(out)
        out["review_action_bucket"] = action
        out["review_action_note"] = note
        out["review_priority"] = priority(safe_float(out.get("abs_gap_effect_$"), 0.0))
        rows.append(out)

        if side == "python_unmatched":
            cand = candidates[candidates["py_trade_id"].astype(str) == trade_id].copy()
        else:
            cand = candidates[candidates["mt5_trade_id"].astype(str) == trade_id].copy()
        cand = cand.sort_values(["tier_rank", "abs_time_diff_minutes", "profit_abs_diff"], na_position="last").head(8)
        for _, cand_row in cand.iterrows():
            owner_py = selected_by_mt5.get(str(cand_row["mt5_trade_id"]))
            owner_mt5 = selected_by_py.get(str(cand_row["py_trade_id"]))
            occupancy_rows.append(
                {
                    "case_side": side,
                    "case_trade_id": trade_id,
                    "case_gap_effect_$": case.get("gap_effect_$"),
                    "candidate_py_trade_id": cand_row.get("py_trade_id", ""),
                    "candidate_mt5_trade_id": cand_row.get("mt5_trade_id", ""),
                    "candidate_tier": cand_row.get("match_tier", ""),
                    "candidate_rank": cand_row.get("tier_rank", ""),
                    "candidate_reliable": cand_row.get("is_reliable_tier", ""),
                    "candidate_abs_minutes": cand_row.get("abs_time_diff_minutes", ""),
                    "candidate_trigger_same": cand_row.get("trigger_same", ""),
                    "candidate_mode_same": cand_row.get("mode_same", ""),
                    "candidate_py_profit": cand_row.get("py_profit", ""),
                    "candidate_mt5_profit": cand_row.get("mt5_profit", ""),
                    "candidate_profit_diff": cand_row.get("profit_diff", ""),
                    "selected_owner_for_candidate_mt5_py": owner_py.get("py_trade_id", "") if owner_py is not None else "",
                    "selected_owner_for_candidate_mt5_tier": owner_py.get("match_tier", "") if owner_py is not None else "",
                    "selected_owner_for_candidate_py_mt5": owner_mt5.get("mt5_trade_id", "") if owner_mt5 is not None else "",
                    "selected_owner_for_candidate_py_tier": owner_mt5.get("match_tier", "") if owner_mt5 is not None else "",
                }
            )

    case_review = pd.DataFrame(rows)
    occupancy = pd.DataFrame(occupancy_rows)
    return case_review.sort_values("abs_gap_effect_$", ascending=False).reset_index(drop=True), occupancy


def build_cluster_summary(case_review: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        case_review.groupby("cluster_key", dropna=False)
        .agg(
            rows=("trade_id", "count"),
            sides=("side", lambda s: ";".join(sorted(set(s.astype(str))))),
            trade_ids=("trade_id", lambda s: ";".join(s.astype(str))),
            review_buckets=("review_action_bucket", lambda s: ";".join(sorted(set(s.astype(str))))),
            gap_effect_sum=("gap_effect_$", "sum"),
            abs_gap_effect_sum=("abs_gap_effect_$", "sum"),
            max_abs_gap_effect=("abs_gap_effect_$", "max"),
            reassign_signal_gap_delta_estimate_sum=("mapping_reassign_signal_gap_delta_estimate", "sum"),
            best_candidate_min_abs_minutes=("best_candidate_abs_minutes", "min"),
            best_candidate_reliable_count=("best_candidate_reliable", lambda s: int(pd.Series(s).map(bool_value).sum())),
        )
        .reset_index()
    )
    for col in [
        "gap_effect_sum",
        "abs_gap_effect_sum",
        "max_abs_gap_effect",
        "reassign_signal_gap_delta_estimate_sum",
        "best_candidate_min_abs_minutes",
    ]:
        grouped[col] = pd.to_numeric(grouped[col], errors="coerce").round(6)
    return grouped.sort_values(["abs_gap_effect_sum", "rows"], ascending=[False, False]).reset_index(drop=True)


def build_action_summary(case_review: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        case_review.groupby(["review_action_bucket", "side"], dropna=False)
        .agg(
            rows=("trade_id", "count"),
            gap_effect_sum=("gap_effect_$", "sum"),
            abs_gap_effect_sum=("abs_gap_effect_$", "sum"),
            max_abs_gap_effect=("abs_gap_effect_$", "max"),
            reassign_signal_gap_delta_estimate_sum=("mapping_reassign_signal_gap_delta_estimate", "sum"),
        )
        .reset_index()
    )
    for col in [
        "gap_effect_sum",
        "abs_gap_effect_sum",
        "max_abs_gap_effect",
        "reassign_signal_gap_delta_estimate_sum",
    ]:
        grouped[col] = pd.to_numeric(grouped[col], errors="coerce").round(6)
    return grouped.sort_values(["abs_gap_effect_sum", "rows"], ascending=[False, False]).reset_index(drop=True)


def build_decision(case_review: pd.DataFrame, action_summary: pd.DataFrame) -> pd.DataFrame:
    duplicate_abs = safe_float(
        case_review[case_review["review_action_bucket"] == "duplicate_continuation_suppression_candidate"][
            "abs_gap_effect_$"
        ].sum(),
        0.0,
    )
    far_abs = safe_float(
        case_review[case_review["review_action_bucket"] == "far_candidate_accounting_only"]["abs_gap_effect_$"].sum(),
        0.0,
    )
    relaxed_abs = safe_float(
        case_review[case_review["review_action_bucket"] == "relaxed_mapping_policy_review"]["abs_gap_effect_$"].sum(),
        0.0,
    )
    stale_abs = safe_float(
        case_review[case_review["review_action_bucket"] == "stale_spec_metadata_review"]["abs_gap_effect_$"].sum(),
        0.0,
    )
    mapping_adjust_abs = safe_float(
        case_review[case_review["review_action_bucket"] == "mapping_rule_adjust_candidate"]["abs_gap_effect_$"].sum(),
        0.0,
    )
    top = action_summary.iloc[0] if not action_summary.empty else pd.Series(dtype=object)
    return pd.DataFrame(
        [
            {
                "gate": "stage_state_mapping_unique_conflict_review",
                "input_unique_conflict_rows": int(len(case_review)),
                "input_unique_conflict_abs_gap": round(safe_float(case_review["abs_gap_effect_$"].sum(), 0.0), 6),
                "duplicate_continuation_abs_gap": round(duplicate_abs, 6),
                "far_candidate_accounting_abs_gap": round(far_abs, 6),
                "relaxed_mapping_policy_abs_gap": round(relaxed_abs, 6),
                "stale_spec_metadata_abs_gap": round(stale_abs, 6),
                "mapping_rule_adjust_abs_gap": round(mapping_adjust_abs, 6),
                "top_action_bucket": top.get("review_action_bucket", ""),
                "top_action_abs_gap": top.get("abs_gap_effect_sum", 0),
                "mapping_rule_change_gate_pass": False,
                "python_signal_change_gate_pass": False,
                "ea_behavior_gate_open": False,
                "recommended_next_action": "prototype_duplicate_continuation_suppression_for_nearby_same_family_clusters",
                "decision": "do_not_change_mapping_or_signal_yet",
                "reason": (
                    "Unique conflicts split into duplicate-continuation, far-candidate, relaxed-family, and stale-metadata buckets; "
                    "only a non-destructive prototype can quantify whether suppressing nearby duplicate continuations improves the current stage-state gap."
                ),
            }
        ]
    )


def markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def build_report(
    case_review: pd.DataFrame,
    occupancy: pd.DataFrame,
    cluster_summary: pd.DataFrame,
    action_summary: pd.DataFrame,
    decision: pd.DataFrame,
) -> str:
    case_cols = [
        "side",
        "trade_id",
        "target_time",
        "dir_norm",
        "trigger_family",
        "mode_family",
        "gap_effect_$",
        "best_candidate_tier",
        "best_candidate_abs_minutes",
        "selected_owner_trade_id",
        "selected_owner_match_tier",
        "mapping_reassign_signal_gap_delta_estimate",
        "spec_pass",
        "spec_reason",
        "sd",
        "review_action_bucket",
    ]
    occupancy_cols = [
        "case_side",
        "case_trade_id",
        "candidate_py_trade_id",
        "candidate_mt5_trade_id",
        "candidate_tier",
        "candidate_abs_minutes",
        "candidate_trigger_same",
        "candidate_mode_same",
        "selected_owner_for_candidate_mt5_py",
        "selected_owner_for_candidate_py_mt5",
    ]
    decision_row = decision.iloc[0]
    lines = [
        "# Stage-state mapping unique-conflict review",
        "",
        "## Scope",
        "",
        "- Input: current stage-state metadatafix mapping-policy-first unique-conflict rows.",
        "- This is a read-only mapping audit; it does not change mapping, Python signals, fund curves, or EA behavior.",
        "",
        "## Decision",
        "",
        f"- Rows reviewed: `{decision_row['input_unique_conflict_rows']}`.",
        f"- Unique-conflict abs gap: `{decision_row['input_unique_conflict_abs_gap']}`.",
        f"- Mapping rule change gate pass: `{decision_row['mapping_rule_change_gate_pass']}`.",
        f"- Python signal change gate pass: `{decision_row['python_signal_change_gate_pass']}`.",
        f"- EA behavior gate open: `{decision_row['ea_behavior_gate_open']}`.",
        f"- Decision: `{decision_row['decision']}`.",
        f"- Next action: `{decision_row['recommended_next_action']}`.",
        "",
        "## Action Summary",
        "",
        markdown_table(action_summary, 20),
        "",
        "## Cluster Summary",
        "",
        markdown_table(cluster_summary, 20),
        "",
        "## Top Cases",
        "",
        markdown_table(case_review[[c for c in case_cols if c in case_review.columns]], 24),
        "",
        "## Candidate Occupancy",
        "",
        markdown_table(occupancy[[c for c in occupancy_cols if c in occupancy.columns]], 30),
        "",
        "## Interpretation",
        "",
        "- Far candidates remain accounting-only unless a tighter cluster rule proves they are true shared trades.",
        "- Relaxed trigger/mode conflicts are mapping-policy work, not EA behavior evidence.",
        "- Nearby same trigger/mode conflicts are the only current bucket that merits a non-destructive duplicate-continuation suppression prototype.",
        "- The `mapping_reassign_signal_gap_delta_estimate` column is only a first-order estimate because reassigning a candidate may displace its current owner.",
        "",
        "## Output Files",
        "",
        "- `stage_state_unique_conflict_case_review.csv`",
        "- `stage_state_unique_conflict_candidate_occupancy.csv`",
        "- `stage_state_unique_conflict_cluster_summary.csv`",
        "- `stage_state_unique_conflict_action_summary.csv`",
        "- `stage_state_unique_conflict_decision.csv`",
    ]
    return "\n".join(lines)


def write_readme() -> None:
    lines = [
        "# Stage-state mapping unique-conflict review 20260716",
        "",
        "Generated by `review_stage_state_mapping_unique_conflicts_20260716.py`.",
        "",
        "Purpose: expand current stage-state mapping-policy-first unique conflicts into occupied-candidate clusters and route the next work item.",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    case_review, occupancy = build_case_review()
    cluster_summary = build_cluster_summary(case_review)
    action_summary = build_action_summary(case_review)
    decision = build_decision(case_review, action_summary)

    export_csv(case_review, OUT_DIR / "stage_state_unique_conflict_case_review.csv")
    export_csv(occupancy, OUT_DIR / "stage_state_unique_conflict_candidate_occupancy.csv")
    export_csv(cluster_summary, OUT_DIR / "stage_state_unique_conflict_cluster_summary.csv")
    export_csv(action_summary, OUT_DIR / "stage_state_unique_conflict_action_summary.csv")
    export_csv(decision, OUT_DIR / "stage_state_unique_conflict_decision.csv")
    write_text(
        OUT_DIR / "stage_state_mapping_unique_conflict_review.md",
        build_report(case_review, occupancy, cluster_summary, action_summary, decision),
    )
    write_readme()

    print(decision.to_string(index=False))
    print()
    print(action_summary.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
