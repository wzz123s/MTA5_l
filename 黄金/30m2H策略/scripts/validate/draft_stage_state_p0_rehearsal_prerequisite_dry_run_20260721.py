from __future__ import annotations


import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
PREREQ_DIR = VALIDATION_DIR / "stage_state_manual_evidence_prerequisite_plan_20260721"
TEMPLATE_DIR = VALIDATION_DIR / "stage_state_live_gate_evidence_templates_20260721"
OUT_DIR = VALIDATION_DIR / "stage_state_p0_rehearsal_prerequisite_dry_run_20260721"
EXPECTED_EVIDENCE_DIR = OUT_DIR / "expected_evidence_samples"

PREREQ_PLAN = PREREQ_DIR / "manual_evidence_prerequisite_plan.csv"
EVIDENCE_INDEX = TEMPLATE_DIR / "live_gate_evidence_index.csv"


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def split_fields(value: str) -> List[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def field_token(field_name: str) -> str:
    token = re.sub(r"[^A-Za-z0-9]+", "_", field_name).strip("_").upper()
    return token or "FIELD"


def placeholder(field_name: str) -> str:
    if field_name == "status":
        return "NOT_EXECUTED_DRY_RUN_PLAN_ONLY"
    if field_name == "environment":
        return "PENDING_DEMO_OR_TESTER_OR_SIM_ONLY_ONLY"
    return f"PENDING_{field_token(field_name)}"


def index_by_key(index_rows: List[Dict[str, str]]) -> Dict[Tuple[str, str], Dict[str, str]]:
    return {(row.get("gap_id", ""), row.get("file_name", "")): row for row in index_rows}


def p0_rehearsal_rows(prereq_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        row
        for row in prereq_rows
        if row.get("priority") == "P0"
        and row.get("collection_method") == "rehearsal"
        and row.get("completion_state") == "open_prerequisite"
    ]


def relative_to_root(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def write_expected_evidence_sample(row: Dict[str, str], fields: List[str]) -> Path:
    gap_dir = EXPECTED_EVIDENCE_DIR / row["gap_id"]
    gap_dir.mkdir(parents=True, exist_ok=True)
    out_path = gap_dir / row["file_name"]
    write_csv(out_path, [{field: placeholder(field) for field in fields}], fields)
    return out_path


def build_plan_rows(
    target_rows: List[Dict[str, str]],
    index_rows: Dict[Tuple[str, str], Dict[str, str]],
    generated_at: str,
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for sequence, row in enumerate(target_rows, start=1):
        key = (row.get("gap_id", ""), row.get("file_name", ""))
        index_row = index_rows.get(key, {})
        fields = split_fields(row.get("required_fields", ""))
        sample_path = write_expected_evidence_sample(row, fields)
        source_relative_path = index_row.get("relative_path", "")
        source_path = TEMPLATE_DIR / source_relative_path if source_relative_path else Path("")
        rows.append(
            {
                "dry_run_sequence": sequence,
                "gap_id": row.get("gap_id", ""),
                "priority": row.get("priority", ""),
                "category": row.get("category", ""),
                "severity": row.get("severity", ""),
                "file_name": row.get("file_name", ""),
                "file_kind": index_row.get("file_kind", "csv"),
                "required_fields": row.get("required_fields", ""),
                "required_field_count": len(fields),
                "source_template_relative_path": source_relative_path,
                "source_template_exists": source_path.exists() if source_relative_path else False,
                "expected_evidence_sample_path": relative_to_root(sample_path),
                "allowed_environment": "demo_account;strategy_tester;SIM_ONLY_only",
                "prohibited_environment": "real_money_account;live_chart;live_set;real_positions",
                "preflight_checks": "confirm_not_real_money;confirm_no_open_real_positions;confirm_InpSimMode_true_or_demo;confirm_runner_not_executed",
                "dry_run_steps": "prepare_mock_emergency_case;walk_through_disable_auto_trading_steps;walk_through_close_position_steps;record_expected_evidence_paths;review_fail_closed_result",
                "expected_evidence_files": "emergency_rehearsal_report.csv;supporting_screenshots_or_logs_redacted",
                "execution_state": "not_executed_plan_only",
                "forbidden_content": row.get("forbidden_content", ""),
                "next_allowed_action": row.get("next_allowed_action", ""),
                "mt5_accessed": False,
                "runner_executed": False,
                "orders_placed": False,
                "live_set_switched": False,
                "credential_values_output": False,
                "gate_status": "open",
                "ready_to_live_trade": False,
                "generated_at": generated_at,
            }
        )
    return rows


def build_steps(plan_rows: List[Dict[str, object]], generated_at: str) -> List[Dict[str, object]]:
    step_defs = [
        ("PRECHECK-001", "Confirm rehearsal environment is demo, tester, or SIM_ONLY-only.", "manual_review", "no_real_money_account"),
        ("PRECHECK-002", "Confirm no real-money positions or orders will be touched.", "manual_review", "no_real_positions_or_orders"),
        ("PRECHECK-003", "Confirm runner files are not executed during this dry run.", "static_boundary", "runner_executed_false"),
        ("DRYRUN-001", "Walk through emergency disable and rollback procedure as a document-only scenario.", "tabletop", "not_executed_plan_only"),
        ("DRYRUN-002", "Define expected redacted evidence files and reviewer fields.", "evidence_design", "expected_evidence_only"),
        ("REVIEW-001", "Review that gate remains open and ready_to_live_trade remains false.", "review", "live_blocked"),
    ]
    rows: List[Dict[str, object]] = []
    for plan in plan_rows:
        for sequence, (step_id, instruction, step_type, expected_state) in enumerate(step_defs, start=1):
            rows.append(
                {
                    "gap_id": plan["gap_id"],
                    "file_name": plan["file_name"],
                    "step_sequence": sequence,
                    "step_id": step_id,
                    "step_type": step_type,
                    "instruction": instruction,
                    "allowed_environment": plan["allowed_environment"],
                    "expected_state": expected_state,
                    "execution_state": "not_executed_plan_only",
                    "mt5_accessed": False,
                    "runner_executed": False,
                    "orders_placed": False,
                    "live_set_switched": False,
                    "gate_status": "open",
                    "ready_to_live_trade": False,
                    "generated_at": generated_at,
                }
            )
    return rows


def build_report(decision: Dict[str, object], plan_rows: List[Dict[str, object]], step_rows: List[Dict[str, object]]) -> str:
    lines = [
        "# P0 Rehearsal Prerequisite Dry Run",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- p0_rehearsal_items: `{decision['p0_rehearsal_items']}`",
        f"- planned_steps: `{decision['planned_steps']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Boundary",
        "",
        "- This is a prerequisite dry-run plan only.",
        "- No MT5 query, runner execution, order placement, live chart attachment, or live set switching is performed.",
        "- Only demo, strategy tester, or SIM_ONLY-only environments are allowed for later rehearsal.",
        "- Real-money accounts, positions, and credentials are prohibited.",
        "",
        "## Items",
        "",
    ]
    for row in plan_rows:
        lines.append(f"- `{row['gap_id']}` `{row['file_name']}` -> `{row['expected_evidence_sample_path']}`")
    lines.extend(["", "## Planned Steps", ""])
    for row in step_rows:
        lines.append(f"- `{row['gap_id']}` `{row['step_id']}`: {row['instruction']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EXPECTED_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")
    prereq_rows = read_rows(PREREQ_PLAN)
    index_rows = read_rows(EVIDENCE_INDEX)
    target_rows = p0_rehearsal_rows(prereq_rows)
    plan_rows = build_plan_rows(target_rows, index_by_key(index_rows), generated_at)
    step_rows = build_steps(plan_rows, generated_at)
    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_p0_rehearsal_prerequisite_dry_run",
        "status": "p0_rehearsal_dry_run_planned_live_blocked",
        "p0_rehearsal_items": len(plan_rows),
        "planned_steps": len(step_rows),
        "expected_evidence_samples": len(plan_rows),
        "mt5_accessed": False,
        "runner_executed": False,
        "orders_placed": False,
        "live_set_switched": False,
        "credential_values_output": False,
        "gate_status": "open",
        "ready_to_live_trade": False,
        "recommended_next_action": "review_p0_rehearsal_prerequisite_dry_run",
    }

    plan_fieldnames = [
        "dry_run_sequence",
        "gap_id",
        "priority",
        "category",
        "severity",
        "file_name",
        "file_kind",
        "required_fields",
        "required_field_count",
        "source_template_relative_path",
        "source_template_exists",
        "expected_evidence_sample_path",
        "allowed_environment",
        "prohibited_environment",
        "preflight_checks",
        "dry_run_steps",
        "expected_evidence_files",
        "execution_state",
        "forbidden_content",
        "next_allowed_action",
        "mt5_accessed",
        "runner_executed",
        "orders_placed",
        "live_set_switched",
        "credential_values_output",
        "gate_status",
        "ready_to_live_trade",
        "generated_at",
    ]
    step_fieldnames = [
        "gap_id",
        "file_name",
        "step_sequence",
        "step_id",
        "step_type",
        "instruction",
        "allowed_environment",
        "expected_state",
        "execution_state",
        "mt5_accessed",
        "runner_executed",
        "orders_placed",
        "live_set_switched",
        "gate_status",
        "ready_to_live_trade",
        "generated_at",
    ]
    write_csv(OUT_DIR / "p0_rehearsal_prerequisite_dry_run_plan.csv", plan_rows, plan_fieldnames)
    write_csv(OUT_DIR / "p0_rehearsal_prerequisite_dry_run_steps.csv", step_rows, step_fieldnames)
    write_csv(OUT_DIR / "p0_rehearsal_prerequisite_dry_run_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "p0_rehearsal_prerequisite_dry_run_decision.json", decision)
    (OUT_DIR / "p0_rehearsal_prerequisite_dry_run.md").write_text(build_report(decision, plan_rows, step_rows), encoding="utf-8-sig")

    for key, value in decision.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
