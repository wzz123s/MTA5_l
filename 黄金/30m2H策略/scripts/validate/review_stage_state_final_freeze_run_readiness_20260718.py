from __future__ import annotations


import csv
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(r"F:\use_code\MTA5_l")
VALIDATION_DIR = ROOT / "黄金" / "30m2H策略" / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_final_freeze_run_readiness_20260718"


DECISION_FILES: List[Tuple[str, str, str]] = [
    (
        "112",
        "slot1_trigger_family_source",
        "stage_state_ea_python_slot1_trigger_family_source_audit_20260717/slot1_trigger_family_source_final_decision.csv",
    ),
    (
        "113",
        "runtime_label_feasibility",
        "stage_state_python_slot1_runtime_label_feasibility_20260717/runtime_label_final_decision.csv",
    ),
    (
        "114",
        "mode_number_aware_runtime_label_mapping",
        "stage_state_mode_number_aware_runtime_label_mapping_audit_20260718/mode_number_final_decision.csv",
    ),
    (
        "115",
        "strict_plus_exclusion_residual",
        "stage_state_relaxed_postn_mismatch_residual_audit_20260718/strict_plus_exclusion_final_decision.csv",
    ),
    (
        "116",
        "layer3_admission_gap",
        "stage_state_layer3_admission_gap_runtime_label_targets_20260718/layer3_admission_final_decision.csv",
    ),
    (
        "117",
        "residual_priority_reset",
        "stage_state_residual_priority_reset_after_runtime_label_closure_20260718/residual_priority_reset_final_decision.csv",
    ),
    (
        "118",
        "python_unmatched_unique_match_conflict",
        "stage_state_python_unmatched_unique_match_conflict_audit_20260718/python_unmatched_unique_match_conflict_final_decision.csv",
    ),
    (
        "119",
        "independent_mt5_signal_gap",
        "stage_state_independent_mt5_signal_gap_audit_20260718/independent_mt5_signal_gap_final_decision.csv",
    ),
    (
        "120",
        "m30_close_postn_true_no_candidate_source",
        "stage_state_m30_close_postn_true_no_candidate_source_audit_20260718/m30_close_postn_source_final_decision.csv",
    ),
]


CRITICAL_GATE_COLUMNS = [
    "main_signal_change_gate_open",
    "ea_behavior_gate_open",
    "mapping_change_gate_open",
    "dynamic_risk_change_gate_open",
    "prototype_gate_open",
    "low_blast_signal_prototype_gate_open",
    "layer3_admission_prototype_gate_open",
    "merge_gate_pass",
    "duplicate_full_chain_merge_gate_pass",
    "stage_exit_logic_changed",
]


FINAL_CHECKLIST = [
    (
        "1",
        "python_mt5_dynamic_risk_baseline_review",
        "Review dynamic_risk_compare_summary.csv against the frozen MT5 ledger baseline.",
        "pending",
    ),
    (
        "2",
        "mapped_alignment_summary_review",
        "Review unique_match_summary.csv and unresolved unmatched buckets without changing mapper policy.",
        "pending",
    ),
    (
        "3",
        "mt5_full_stage_state_ledger_closure_review",
        "Verify MT5 deal history, trade ledger, final balance and deinit rows are internally closed.",
        "pending",
    ),
    (
        "4",
        "three_version_unified_report_refresh",
        "Refresh the Python-only, Python-MT5 and MT5-only unified comparison report from frozen inputs.",
        "pending",
    ),
    (
        "5",
        "ea_ex5_set_run_package_check",
        "Check the EA .ex5, .set, terminal path, account parameters and smoke/full tester run commands.",
        "pending",
    ),
]


def read_first_row(path: Path) -> Dict[str, str]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            return {k: (v or "") for k, v in row.items()}
    return {}


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def truthy(value: object) -> bool:
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def falsey_or_blank(value: object) -> bool:
    text = str(value).strip().lower()
    return text in {"", "false", "0", "no", "n", "none", "nan"}


def float_or_zero(value: object) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return 0.0


def bool_text(value: object) -> str:
    return "True" if truthy(value) else "False"


def load_gate_summary() -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    source_rows: List[Dict[str, object]] = []
    gate_rows: List[Dict[str, object]] = []

    for conclusion_no, label, rel_path in DECISION_FILES:
        path = VALIDATION_DIR / rel_path
        row = read_first_row(path)
        if not row:
            raise RuntimeError(f"Empty decision file: {path}")

        present_critical = [col for col in CRITICAL_GATE_COLUMNS if col in row]
        open_critical = [col for col in present_critical if truthy(row.get(col))]

        source_rows.append(
            {
                "conclusion_no": conclusion_no,
                "audit_label": label,
                "decision_file": str(path.relative_to(ROOT)),
                "critical_gate_columns_present": ";".join(present_critical),
                "open_critical_gate_columns": ";".join(open_critical),
                "critical_gate_open": bool(open_critical),
                "recommended_next_action": row.get("recommended_next_action", ""),
                "recommended_next_task": row.get("recommended_next_task", ""),
            }
        )

        for col in present_critical:
            gate_rows.append(
                {
                    "conclusion_no": conclusion_no,
                    "audit_label": label,
                    "gate_column": col,
                    "gate_value": bool_text(row.get(col)),
                    "is_critical_open": truthy(row.get(col)),
                    "decision_file": str(path.relative_to(ROOT)),
                }
            )

    return source_rows, gate_rows


def load_dynamic_summary() -> List[Dict[str, object]]:
    path = (
        VALIDATION_DIR
        / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
        / "dynamic_risk_compare_summary.csv"
    )
    rows = read_rows(path)
    out: List[Dict[str, object]] = []
    for row in rows:
        out.append(
            {
                "section": "dynamic_risk_compare",
                "source": row.get("source", ""),
                "trade_count": row.get("trade_count", ""),
                "final_balance": row.get("final_balance", ""),
                "total_profit": row.get("dynamic_total_profit", ""),
                "win_count": row.get("win_count", ""),
                "win_rate_pct": row.get("win_rate_pct", ""),
                "any_stage_sl_count": row.get("any_stage_sl_count", ""),
                "all_stage_sl_count": row.get("all_stage_sl_count", ""),
                "avg_stop_pts_spec": row.get("avg_stop_pts_spec", ""),
                "exec_model": row.get("exec_model", ""),
                "source_variant": row.get("source_variant", ""),
            }
        )
    return out


def load_mapping_summary() -> List[Dict[str, object]]:
    path = (
        VALIDATION_DIR
        / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"
        / "unique_match_summary.csv"
    )
    rows = read_rows(path)
    out: List[Dict[str, object]] = []
    for row in rows:
        out.append(
            {
                "source": row.get("source", ""),
                "python_trades": row.get("python_trades", ""),
                "mt5_trades": row.get("mt5_trades", ""),
                "matched_unique": row.get("matched_unique", ""),
                "reliable_tier_matched": row.get("reliable_tier_matched", ""),
                "relaxed_tier_matched": row.get("relaxed_tier_matched", ""),
                "python_unmatched": row.get("python_unmatched", ""),
                "mt5_unmatched": row.get("mt5_unmatched", ""),
                "matched_python_profit": row.get("matched_python_profit", ""),
                "matched_mt5_profit": row.get("matched_mt5_profit", ""),
                "matched_profit_diff": row.get("matched_profit_diff", ""),
                "any_sl_same_count": row.get("any_sl_same_count", ""),
                "all_sl_same_count": row.get("all_sl_same_count", ""),
            }
        )
    return out


def load_mt5_ledger_check() -> Dict[str, object]:
    path = (
        VALIDATION_DIR
        / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
        / "mt5_ledger_unique_signals.csv"
    )
    rows = read_rows(path)
    net_profit_sum = sum(float_or_zero(row.get("net_profit")) for row in rows)
    win_count = sum(1 for row in rows if float_or_zero(row.get("net_profit")) > 0)
    any_sl_count = sum(1 for row in rows if truthy(row.get("any_sl")))
    all_sl_count = sum(1 for row in rows if truthy(row.get("all_sl")))
    final_balance = rows[-1].get("balance_after", "") if rows else ""
    initial_balance = rows[0].get("balance_before", "") if rows else ""
    trade_count = len(rows)
    win_rate = (win_count / trade_count * 100.0) if trade_count else 0.0
    return {
        "section": "mt5_ledger_unique_signals_recomputed",
        "source": "mt5_ledger",
        "trade_count": trade_count,
        "initial_balance": initial_balance,
        "final_balance": final_balance,
        "net_profit_sum": round(net_profit_sum, 6),
        "win_count": win_count,
        "win_rate_pct": round(win_rate, 6),
        "any_stage_sl_count": any_sl_count,
        "all_stage_sl_count": all_sl_count,
        "ledger_file": str(path.relative_to(ROOT)),
    }


def write_audit_md(
    source_rows: List[Dict[str, object]],
    decision_rows: List[Dict[str, object]],
    dynamic_rows: List[Dict[str, object]],
    mapping_rows: List[Dict[str, object]],
    mt5_ledger_check: Dict[str, object],
) -> None:
    decision = decision_rows[0]
    lines: List[str] = []
    lines.append("# Stage-state Final Freeze / Run Readiness Gate")
    lines.append("")
    lines.append(f"- Decision date: {decision['decision_date']}")
    lines.append(f"- Freeze current MT5 stage-state baseline: `{decision['freeze_current_stage_state_baseline']}`")
    lines.append(f"- Frozen baseline: `{decision['frozen_baseline_id']}`")
    lines.append(f"- Ready to final regression: `{decision['ready_to_final_regression']}`")
    lines.append(f"- Ready to live/full run now: `{decision['ready_to_live_run_now']}`")
    lines.append(f"- Reason: `{decision['reason']}`")
    lines.append("")
    lines.append("## Critical Gate Summary")
    lines.append("")
    lines.append("| conclusion | audit | open critical gates | next |")
    lines.append("|---:|---|---|---|")
    for row in source_rows:
        open_cols = row.get("open_critical_gate_columns") or "none"
        next_action = row.get("recommended_next_task") or row.get("recommended_next_action") or ""
        lines.append(
            f"| {row['conclusion_no']} | {row['audit_label']} | `{open_cols}` | `{next_action}` |"
        )
    lines.append("")
    lines.append("## Baseline Snapshot")
    lines.append("")
    lines.append("| source | trades | final balance | profit | win rate | any SL | all SL |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for row in dynamic_rows:
        lines.append(
            "| {source} | {trade_count} | {final_balance} | {total_profit} | {win_rate_pct} | {any_stage_sl_count} | {all_stage_sl_count} |".format(
                **row
            )
        )
    lines.append("")
    lines.append("## MT5 Ledger Recompute")
    lines.append("")
    lines.append("| trades | initial | final | net profit | wins | win rate | any SL | all SL |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|")
    lines.append(
        "| {trade_count} | {initial_balance} | {final_balance} | {net_profit_sum} | {win_count} | {win_rate_pct} | {any_stage_sl_count} | {all_stage_sl_count} |".format(
            **mt5_ledger_check
        )
    )
    lines.append("")
    lines.append("## Mapping Snapshot")
    lines.append("")
    lines.append(
        "| source | python trades | mt5 trades | matched | reliable | relaxed | python unmatched | mt5 unmatched | matched profit diff |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in mapping_rows:
        lines.append(
            "| {source} | {python_trades} | {mt5_trades} | {matched_unique} | {reliable_tier_matched} | {relaxed_tier_matched} | {python_unmatched} | {mt5_unmatched} | {matched_profit_diff} |".format(
                **row
            )
        )
    lines.append("")
    lines.append("## Final Regression Checklist")
    lines.append("")
    lines.append("| order | check | status |")
    lines.append("|---:|---|---|")
    for order, check_id, _desc, status in FINAL_CHECKLIST:
        lines.append(f"| {order} | `{check_id}` | `{status}` |")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append(
        "The current decision freezes the MT5 stage-state baseline for final regression. It does not declare the strategy fully run-ready yet."
    )
    lines.append(
        "Subsequent work should be regression, report refresh, and run package checks only, unless a new regression failure opens an explicit gate."
    )
    lines.append("")

    (OUT_DIR / "final_freeze_run_readiness_audit.md").write_text(
        "\n".join(lines), encoding="utf-8-sig"
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    source_rows, gate_rows = load_gate_summary()
    dynamic_rows = load_dynamic_summary()
    mapping_rows = load_mapping_summary()
    mt5_ledger_check = load_mt5_ledger_check()

    open_sources = [row for row in source_rows if truthy(row["critical_gate_open"])]
    open_gate_fields = sorted(
        {
            row["gate_column"]
            for row in gate_rows
            if truthy(row["is_critical_open"])
        }
    )

    freeze = len(open_sources) == 0
    decision_rows = [
        {
            "decision_date": date.today().isoformat(),
            "freeze_current_stage_state_baseline": freeze,
            "frozen_baseline_id": "mt5_stage_state_full_2018_20260707_20260716" if freeze else "",
            "ready_to_final_regression": freeze,
            "ready_to_live_run_now": False,
            "final_regression_required": True,
            "critical_gate_open_count": len(open_sources),
            "critical_gate_open_fields": ";".join(open_gate_fields),
            "reason": "conclusions_112_120_change_gates_closed"
            if freeze
            else "critical_change_gate_still_open",
            "next_task": "Stage-state final regression / run package check"
            if freeze
            else "Resolve open critical gates before freezing",
            "no_main_logic_changes_in_this_step": True,
        }
    ]

    write_csv(
        OUT_DIR / "readiness_gate_source_summary.csv",
        source_rows,
        [
            "conclusion_no",
            "audit_label",
            "decision_file",
            "critical_gate_columns_present",
            "open_critical_gate_columns",
            "critical_gate_open",
            "recommended_next_action",
            "recommended_next_task",
        ],
    )
    write_csv(
        OUT_DIR / "readiness_gate_summary.csv",
        gate_rows,
        [
            "conclusion_no",
            "audit_label",
            "gate_column",
            "gate_value",
            "is_critical_open",
            "decision_file",
        ],
    )
    write_csv(
        OUT_DIR / "baseline_snapshot_summary.csv",
        dynamic_rows,
        [
            "section",
            "source",
            "trade_count",
            "final_balance",
            "total_profit",
            "win_count",
            "win_rate_pct",
            "any_stage_sl_count",
            "all_stage_sl_count",
            "avg_stop_pts_spec",
            "exec_model",
            "source_variant",
        ],
    )
    write_csv(
        OUT_DIR / "mapping_snapshot_summary.csv",
        mapping_rows,
        [
            "source",
            "python_trades",
            "mt5_trades",
            "matched_unique",
            "reliable_tier_matched",
            "relaxed_tier_matched",
            "python_unmatched",
            "mt5_unmatched",
            "matched_python_profit",
            "matched_mt5_profit",
            "matched_profit_diff",
            "any_sl_same_count",
            "all_sl_same_count",
        ],
    )
    write_csv(
        OUT_DIR / "mt5_ledger_recomputed_check.csv",
        [mt5_ledger_check],
        [
            "section",
            "source",
            "trade_count",
            "initial_balance",
            "final_balance",
            "net_profit_sum",
            "win_count",
            "win_rate_pct",
            "any_stage_sl_count",
            "all_stage_sl_count",
            "ledger_file",
        ],
    )
    write_csv(
        OUT_DIR / "final_regression_checklist.csv",
        [
            {
                "order": order,
                "check_id": check_id,
                "description": desc,
                "status": status,
            }
            for order, check_id, desc, status in FINAL_CHECKLIST
        ],
        ["order", "check_id", "description", "status"],
    )
    write_csv(
        OUT_DIR / "final_freeze_run_readiness_decision.csv",
        decision_rows,
        [
            "decision_date",
            "freeze_current_stage_state_baseline",
            "frozen_baseline_id",
            "ready_to_final_regression",
            "ready_to_live_run_now",
            "final_regression_required",
            "critical_gate_open_count",
            "critical_gate_open_fields",
            "reason",
            "next_task",
            "no_main_logic_changes_in_this_step",
        ],
    )

    readme = "\n".join(
        [
            "# stage_state_final_freeze_run_readiness_20260718",
            "",
            "Final freeze and run-readiness gate output.",
            "",
            "- `final_freeze_run_readiness_decision.csv`: top-level freeze decision.",
            "- `readiness_gate_source_summary.csv`: conclusion-level source decisions.",
            "- `readiness_gate_summary.csv`: critical gate values from conclusions 112-120.",
            "- `baseline_snapshot_summary.csv`: three-version dynamic-risk baseline snapshot.",
            "- `mapping_snapshot_summary.csv`: mapped alignment snapshot.",
            "- `mt5_ledger_recomputed_check.csv`: MT5 ledger recomputed statistics.",
            "- `final_regression_checklist.csv`: remaining checks before run package readiness.",
            "- `final_freeze_run_readiness_audit.md`: human-readable summary.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8-sig")

    write_audit_md(source_rows, decision_rows, dynamic_rows, mapping_rows, mt5_ledger_check)

    print(f"wrote {OUT_DIR}")
    print(f"freeze_current_stage_state_baseline={freeze}")
    print(f"critical_gate_open_count={len(open_sources)}")
    print("ready_to_final_regression=True" if freeze else "ready_to_final_regression=False")


if __name__ == "__main__":
    main()
