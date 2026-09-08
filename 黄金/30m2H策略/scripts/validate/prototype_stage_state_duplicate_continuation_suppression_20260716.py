# -*- coding: utf-8 -*-
"""First-order duplicate continuation suppression prototype.

This is intentionally non-destructive. It only estimates the effect of removing
nearby same-family duplicate continuation rows identified by the stage-state
unique-conflict review. It does not rerun signal generation, dynamic risk, or
mapping.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

UNIQUE_CONFLICT_DIR = VALIDATION_DIR / "stage_state_mapping_unique_conflict_review_20260716"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
TRIAGE_DIR = VALIDATION_DIR / "stage_state_signal_set_residual_triage_20260716"
OUT_DIR = VALIDATION_DIR / "stage_state_duplicate_continuation_suppression_prototype_20260716"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def safe_float(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def add_py_ids(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["py_trade_id"] = [f"python_mt5_{idx + 1:04d}" for idx in range(len(out))]
    return out


def build_candidates() -> pd.DataFrame:
    cases = read_csv(UNIQUE_CONFLICT_DIR / "stage_state_unique_conflict_case_review.csv").copy()
    dup = cases[cases["review_action_bucket"] == "duplicate_continuation_suppression_candidate"].copy()
    trades = add_py_ids(read_csv(DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"))
    keep = [
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
    dup = dup.merge(trades[[c for c in keep if c in trades.columns]], left_on="trade_id", right_on="py_trade_id", how="left")
    dup["suppression_reason"] = (
        "nearby same trigger/mode unique-conflict continuation; non-destructive first-order estimate only"
    )
    return dup.sort_values("abs_gap_effect_$", ascending=False).reset_index(drop=True)


def build_cluster_impact(candidates: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        candidates.groupby("cluster_key", dropna=False)
        .agg(
            rows=("trade_id", "count"),
            trade_ids=("trade_id", lambda s: ";".join(s.astype(str))),
            removed_profit_sum=("dynamic_total_$", "sum"),
            abs_removed_profit_sum=("dynamic_total_$", lambda s: pd.to_numeric(s, errors="coerce").abs().sum()),
            max_abs_removed_profit=("dynamic_total_$", lambda s: pd.to_numeric(s, errors="coerce").abs().max()),
            best_candidate_mt5_ids=("best_candidate_mt5_trade_id", lambda s: ";".join(sorted(set(s.astype(str))))),
            selected_owner_ids=("selected_owner_trade_id", lambda s: ";".join(sorted(set(s.astype(str))))),
            min_best_candidate_abs_minutes=("best_candidate_abs_minutes", "min"),
        )
        .reset_index()
    )
    for col in ["removed_profit_sum", "abs_removed_profit_sum", "max_abs_removed_profit", "min_best_candidate_abs_minutes"]:
        grouped[col] = pd.to_numeric(grouped[col], errors="coerce").round(6)
    return grouped.sort_values("abs_removed_profit_sum", ascending=False).reset_index(drop=True)


def build_before_after(candidates: pd.DataFrame) -> pd.DataFrame:
    trades = add_py_ids(read_csv(DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"))
    decision = read_csv(TRIAGE_DIR / "stage_state_signal_set_residual_triage_decision.csv").iloc[0]
    removed_ids = set(candidates["trade_id"].astype(str))
    removed_profit = safe_float(candidates["dynamic_total_$"].sum())
    current_python_final = safe_float(trades["balance_after"].iloc[-1])
    current_trade_count = int(len(trades))
    mt5_final = safe_float(decision["current_mt5_final_balance"])
    current_direct_gap = safe_float(decision["metadatafix_direct_gap_py_minus_mt5"])
    current_matched_profit_diff = safe_float(decision["metadatafix_matched_profit_diff_py_minus_mt5"])
    current_signal_set_gap = safe_float(decision["metadatafix_signal_set_gap_py_minus_mt5"])

    after_trade_count = current_trade_count - len(removed_ids)
    after_python_final_first_order = current_python_final - removed_profit
    after_direct_gap_first_order = after_python_final_first_order - mt5_final
    after_signal_set_gap_first_order = current_signal_set_gap - removed_profit
    after_direct_gap_from_components = current_matched_profit_diff + after_signal_set_gap_first_order

    return pd.DataFrame(
        [
            {
                "scenario": "current_stage_state_metadatafix",
                "python_trade_count": current_trade_count,
                "python_final_balance": current_python_final,
                "mt5_final_balance": mt5_final,
                "direct_gap_py_minus_mt5": current_direct_gap,
                "matched_profit_diff_py_minus_mt5": current_matched_profit_diff,
                "signal_set_gap_py_minus_mt5": current_signal_set_gap,
                "removed_duplicate_rows": 0,
                "removed_duplicate_profit_sum": 0.0,
                "first_order_only": False,
            },
            {
                "scenario": "first_order_duplicate_suppression_estimate",
                "python_trade_count": after_trade_count,
                "python_final_balance": round(after_python_final_first_order, 6),
                "mt5_final_balance": mt5_final,
                "direct_gap_py_minus_mt5": round(after_direct_gap_first_order, 6),
                "matched_profit_diff_py_minus_mt5": current_matched_profit_diff,
                "signal_set_gap_py_minus_mt5": round(after_signal_set_gap_first_order, 6),
                "direct_gap_from_components": round(after_direct_gap_from_components, 6),
                "removed_duplicate_rows": int(len(removed_ids)),
                "removed_duplicate_profit_sum": round(removed_profit, 6),
                "direct_gap_improvement": round(current_direct_gap - after_direct_gap_first_order, 6),
                "signal_set_gap_improvement": round(current_signal_set_gap - after_signal_set_gap_first_order, 6),
                "first_order_only": True,
            },
        ]
    )


def build_decision(summary: pd.DataFrame, candidates: pd.DataFrame) -> pd.DataFrame:
    after = summary[summary["scenario"] == "first_order_duplicate_suppression_estimate"].iloc[0]
    current = summary[summary["scenario"] == "current_stage_state_metadatafix"].iloc[0]
    improvement = safe_float(after.get("direct_gap_improvement"))
    remaining_gap = safe_float(after.get("direct_gap_py_minus_mt5"))
    return pd.DataFrame(
        [
            {
                "gate": "stage_state_duplicate_continuation_suppression_prototype",
                "suppression_rows": int(len(candidates)),
                "removed_profit_sum": after["removed_duplicate_profit_sum"],
                "current_direct_gap": current["direct_gap_py_minus_mt5"],
                "first_order_direct_gap_after": after["direct_gap_py_minus_mt5"],
                "first_order_direct_gap_improvement": improvement,
                "first_order_signal_set_gap_after": after["signal_set_gap_py_minus_mt5"],
                "remaining_direct_gap_after_estimate": remaining_gap,
                "full_chain_rerun_required_before_merge": True,
                "merge_gate_pass": False,
                "prototype_value": bool(improvement > 0),
                "recommended_next_action": "run_full_chain_duplicate_suppression_mapping_rerun_if_prioritizing_gap_reduction",
                "decision": "diagnostic_improvement_not_mergeable",
                "reason": (
                    "Suppressing the nearby duplicate continuation candidates improves the first-order gap, "
                    "but the remaining direct gap is still large and dynamic risk/mapping were not rerun."
                ),
            }
        ]
    )


def markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def build_report(candidates: pd.DataFrame, cluster: pd.DataFrame, summary: pd.DataFrame, decision: pd.DataFrame) -> str:
    candidate_cols = [
        "trade_id",
        "target_time",
        "dir_norm",
        "trigger_family",
        "mode_family",
        "dynamic_total_$",
        "cluster_key",
        "best_candidate_mt5_trade_id",
        "best_candidate_abs_minutes",
        "selected_owner_trade_id",
        "selected_owner_match_tier",
    ]
    decision_row = decision.iloc[0]
    lines = [
        "# Stage-state duplicate continuation suppression prototype",
        "",
        "## Scope",
        "",
        "- Input: `duplicate_continuation_suppression_candidate` rows from the stage-state unique-conflict review.",
        "- This is a first-order estimate only; it does not rerun dynamic risk, mapping, Stage exits, or EA.",
        "",
        "## Decision",
        "",
        f"- Suppression rows: `{decision_row['suppression_rows']}`.",
        f"- Removed duplicate profit sum: `{decision_row['removed_profit_sum']}`.",
        f"- First-order direct gap improvement: `{decision_row['first_order_direct_gap_improvement']}`.",
        f"- First-order direct gap after: `{decision_row['first_order_direct_gap_after']}`.",
        f"- Merge gate pass: `{decision_row['merge_gate_pass']}`.",
        f"- Decision: `{decision_row['decision']}`.",
        "",
        "## Before/After Estimate",
        "",
        markdown_table(summary, 10),
        "",
        "## Suppression Candidates",
        "",
        markdown_table(candidates[[c for c in candidate_cols if c in candidates.columns]], 20),
        "",
        "## Cluster Impact",
        "",
        markdown_table(cluster, 20),
        "",
        "## Interpretation",
        "",
        "- The first-order estimate improves the current stage-state direct gap by the sum of removed duplicate Python profit.",
        "- Because later dynamic-risk lot sizing depends on balance path, this is not a mergeable result.",
        "- The remaining direct gap is still much larger than the merge threshold, so the result is useful as a diagnostic/prototype direction only.",
        "",
        "## Output Files",
        "",
        "- `duplicate_suppression_candidates.csv`",
        "- `duplicate_suppression_cluster_impact.csv`",
        "- `duplicate_suppression_before_after_summary.csv`",
        "- `duplicate_suppression_decision.csv`",
    ]
    return "\n".join(lines)


def write_readme() -> None:
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# Stage-state duplicate continuation suppression prototype 20260716",
                "",
                "Generated by `prototype_stage_state_duplicate_continuation_suppression_20260716.py`.",
                "",
                "This is a first-order, non-destructive estimate for the nearby duplicate-continuation rows.",
            ]
        ),
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = build_candidates()
    cluster = build_cluster_impact(candidates)
    summary = build_before_after(candidates)
    decision = build_decision(summary, candidates)

    export_csv(candidates, OUT_DIR / "duplicate_suppression_candidates.csv")
    export_csv(cluster, OUT_DIR / "duplicate_suppression_cluster_impact.csv")
    export_csv(summary, OUT_DIR / "duplicate_suppression_before_after_summary.csv")
    export_csv(decision, OUT_DIR / "duplicate_suppression_decision.csv")
    write_text(
        OUT_DIR / "stage_state_duplicate_continuation_suppression_prototype_review.md",
        build_report(candidates, cluster, summary, decision),
    )
    write_readme()

    print(decision.to_string(index=False))
    print()
    print(summary.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
