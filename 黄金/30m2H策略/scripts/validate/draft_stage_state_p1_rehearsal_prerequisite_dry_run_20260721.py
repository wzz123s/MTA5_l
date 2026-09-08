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
OUT_DIR = VALIDATION_DIR / "stage_state_p1_rehearsal_prerequisite_dry_run_20260721"
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
    if field_name == "environment":
        return "PENDING_DEMO_OR_TESTER_OR_SIM_ONLY_ONLY"
    if field_name.endswith("status") or field_name == "status":
        return "NOT_EXECUTED_DRY_RUN_PLAN_ONLY"
    return f"PENDING_{field_token(field_name)}"


def index_by_key(index_rows: List[Dict[str, str]]) -> Dict[Tuple[str, str], Dict[str, str]]:
    return {(row.get("gap_id", ""), row.get("file_name", "")): row for row in index_rows}


def p1_rehearsal_rows(prereq_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        row
        for row in prereq_rows
        if row.get("priority") == "P1"
        and row.get("collection_method") == "rehearsal"
        and row.get("completion_state") == "open_prerequisite"
    ]


def relative_to_root(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def build_markdown_sample(row: Dict[str, str], fields: List[str], generated_at: str) -> str:
    lines = [
        f"# {row['gap_id']} P1 Rehearsal Expected Evidence Sample",
        "",
        "- sample_status: `NOT_EXECUTED_DRY_RUN_PLAN_ONLY`",
        "- priority: `P1`",
        f"- source_file: `{row['file_name']}`",
        "- gate_status: `open`",
        "- ready_to_live_trade: `false`",
        f"- generated_at: `{generated_at}`",
        "",
        "## Required Fields",
        "",
    ]
    for field in fields:
        lines.append(f"- `{field}`: `{placeholder(field)}`")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- This is an expected evidence sample only.",
            "- No demo/tester/SIM_ONLY rehearsal has been executed by this file.",
            "- Real-money accounts, real positions, real orders, live chart attachment, and live set switching are prohibited.",
            "",
        ]
    )
    return "\n".join(lines)


def write_expected_evidence_sample(row: Dict[str, str], fields: List[str], generated_at: str) -> Path:
    gap_dir = EXPECTED_EVIDENCE_DIR / row["gap_id"]
    gap_dir.mkdir(parents=True, exist_ok=True)
    out_path = gap_dir / row["file_name"]
    if row["file_name"].endswith(".csv"):
        write_csv(out_path, [{field: placeholder(field) for field in fields}], fields)
    else:
        out_path.write_text(build_markdown_sample(row, fields, generated_at), encoding="utf-8-sig")
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
        sample_path = write_expected_evidence_sample(row, fields, generated_at)
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
                "file_kind": index_row.get("file_kind", Path(row.get("file_name", "")).suffix.lstrip(".")),
                "required_fields": row.get("required_fields", ""),
                "required_field_count": len(fields),
                "source_template_relative_path": source_relative_path,
                "source_template_exists": source_path.exists() if source_relative_path else False,
                "expected_evidence_sample_path": relative_to_root(sample_path),
                "allowed_environment": "demo_account;strategy_tester;SIM_ONLY_only",
                "prohibited_environment": "real_money_account;live_chart;live_set;real_positions;real_orders",
                "preflight_checks": "confirm_not_real_money;confirm_no_open_real_positions;confirm_no_live_chart;confirm_runner_not_executed;confirm_live_set_not_switched",
                "dry_run_steps": "prepare_mock_order_case;define_expected_open_close_events;define_expected_sl_tp_events;define_expected_ledger_rows;define_expected_alert_rows;review_fail_closed_result",
                "expected_evidence_files": "nonprod_order_rehearsal_report.md;rehearsal_ledger.csv;rehearsal_alert_log.csv",
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
        ("PRECHECK-002", "Confirm no real-money positions, orders, or live chart will be touched.", "manual_review", "no_real_positions_or_orders"),
        ("PRECHECK-003", "Confirm runner files are not executed during this dry-run plan.", "static_boundary", "runner_executed_false"),
        ("DRYRUN-001", "Define the non-production open/close order rehearsal scenario.", "evidence_design", "expected_order_events_only"),
        ("DRYRUN-002", "Define expected ledger and alert rows with placeholder values.", "evidence_design", "expected_evidence_only"),
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
        "# P1 Rehearsal Prerequisite Dry Run",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- p1_rehearsal_items: `{decision['p1_rehearsal_items']}`",
        f"- planned_steps: `{decision['planned_steps']}`",
        f"- expected_evidence_samples: `{decision['expected_evidence_samples']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Boundary",
        "",
        "- This is a prerequisite dry-run plan only.",
        "- No MT5 query, runner execution, order placement, live chart attachment, or live set switching is performed.",
        "- Later rehearsal is allowed only on demo, strategy tester, or SIM_ONLY-only environments.",
        "- Real-money accounts, positions, orders, and credentials are prohibited.",
        "",
        "## Items",
        "",
    ]
    for row in plan_rows:
        lines.append(f"- `{row['gap_id']}` `{row['file_name']}` -> `{row['expected_evidence_sample_path']}`")
    lines.extend(["", "## Planned Steps", ""])
    for row in step_rows:
        lines.append(f"- `{row['gap_id']}` `{row['file_name']}` `{row['step_id']}`: {row['instruction']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EXPECTED_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")
    prereq_rows = read_rows(PREREQ_PLAN)
    index_rows = read_rows(EVIDENCE_INDEX)
    target_rows = p1_rehearsal_rows(prereq_rows)
    plan_rows = build_plan_rows(target_rows, index_by_key(index_rows), generated_at)
    step_rows = build_steps(plan_rows, generated_at)
    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_p1_rehearsal_prerequisite_dry_run",
        "status": "p1_rehearsal_dry_run_planned_live_blocked",
        "p1_rehearsal_items": len(plan_rows),
        "planned_steps": len(step_rows),
        "expected_evidence_samples": len(plan_rows),
        "mt5_accessed": False,
        "runner_executed": False,
        "orders_placed": False,
        "live_set_switched": False,
        "credential_values_output": False,
        "gate_status": "open",
        "ready_to_live_trade": False,
        "recommended_next_action": "review_p1_rehearsal_prerequisite_dry_run",
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
    write_csv(OUT_DIR / "p1_rehearsal_prerequisite_dry_run_plan.csv", plan_rows, plan_fieldnames)
    write_csv(OUT_DIR / "p1_rehearsal_prerequisite_dry_run_steps.csv", step_rows, step_fieldnames)
    write_csv(OUT_DIR / "p1_rehearsal_prerequisite_dry_run_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "p1_rehearsal_prerequisite_dry_run_decision.json", decision)
    (OUT_DIR / "p1_rehearsal_prerequisite_dry_run.md").write_text(build_report(decision, plan_rows, step_rows), encoding="utf-8-sig")

    for key, value in decision.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
