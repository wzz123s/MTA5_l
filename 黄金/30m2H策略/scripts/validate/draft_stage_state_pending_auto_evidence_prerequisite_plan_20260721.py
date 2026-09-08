from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
AUTO_SAFE_DIR = VALIDATION_DIR / "stage_state_live_gate_auto_safe_evidence_20260721"
PREREQ_DIR = VALIDATION_DIR / "stage_state_manual_evidence_prerequisite_plan_20260721"
OUT_DIR = VALIDATION_DIR / "stage_state_pending_auto_evidence_prerequisite_plan_20260721"

AUTO_SAFE_PLAN = AUTO_SAFE_DIR / "auto_safe_evidence_collection_plan.csv"
MANUAL_PREREQ_PLAN = PREREQ_DIR / "manual_evidence_prerequisite_plan.csv"


RULES: Dict[str, Dict[str, str]] = {
    "live_package_hashes.csv": {
        "collection_class": "offline_hash_after_live_package_approval",
        "manual_prerequisite": "approved live package manifest and release reviewer confirmation",
        "allowed_collection": "hash only user-approved local artifact paths from the approved manifest",
        "prohibited_action": "do not hash unreviewed artifacts; do not deploy package; do not attach package to live chart",
        "approval_phrase": "USER_APPROVES_HASHING_REVIEWED_LIVE_PACKAGE_MANIFEST_ONLY",
        "shortest_live_path_step": "confirm live package manifest, then run offline hash audit",
    },
    "parsed_live_set_template.json": {
        "collection_class": "offline_set_parse_after_transition_approval",
        "manual_prerequisite": "explicit sim-mode transition approval and reviewed inactive set template",
        "allowed_collection": "parse only the approved set template file without loading it into MT5",
        "prohibited_action": "do not create active live set; do not set InpSimMode=false in MT5; do not attach EA to chart",
        "approval_phrase": "USER_APPROVES_OFFLINE_PARSE_REVIEWED_SET_TEMPLATE_ONLY",
        "shortest_live_path_step": "confirm transition approval, then parse inactive reviewed set template",
    },
    "broker_symbol_spec.csv": {
        "collection_class": "read_only_mt5_spec_after_user_approval",
        "manual_prerequisite": "explicit user approval for read-only MT5 symbol/account-spec query",
        "allowed_collection": "query symbol/account specs read-only after approval, with orders disabled",
        "prohibited_action": "do not place orders; do not run runner; do not change chart/live set while collecting specs",
        "approval_phrase": "USER_APPROVES_READ_ONLY_MT5_SYMBOL_SPEC_QUERY_NO_ORDERS",
        "shortest_live_path_step": "approve read-only spec query, then collect broker symbol spec without order actions",
    },
}


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


def pending_auto_rows(auto_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [row for row in auto_rows if row.get("auto_safe_status") == "pending_manual_prerequisite"]


def prereq_by_key(rows: List[Dict[str, str]]) -> Dict[tuple[str, str], Dict[str, str]]:
    return {(row.get("gap_id", ""), row.get("file_name", "")): row for row in rows}


def build_plan_rows(auto_rows: List[Dict[str, str]], prereq_rows: List[Dict[str, str]], generated_at: str) -> List[Dict[str, object]]:
    prereq_map = prereq_by_key(prereq_rows)
    plan_rows: List[Dict[str, object]] = []
    for sequence, auto_row in enumerate(pending_auto_rows(auto_rows), start=1):
        file_name = auto_row["file_name"]
        prereq = prereq_map.get((auto_row["gap_id"], file_name), {})
        rule = RULES[file_name]
        plan_rows.append(
            {
                "pending_sequence": sequence,
                "gap_id": auto_row.get("gap_id", ""),
                "priority": prereq.get("priority", ""),
                "file_name": file_name,
                "required_fields": prereq.get("required_fields", ""),
                "collection_class": rule["collection_class"],
                "manual_prerequisite": rule["manual_prerequisite"],
                "approval_phrase_required": rule["approval_phrase"],
                "allowed_collection": rule["allowed_collection"],
                "prohibited_action": rule["prohibited_action"],
                "source_prerequisite": prereq.get("prerequisite_source", ""),
                "existing_forbidden_content": prereq.get("forbidden_content", ""),
                "next_allowed_action": prereq.get("next_allowed_action", ""),
                "shortest_live_path_step": rule["shortest_live_path_step"],
                "auto_safe_status": auto_row.get("auto_safe_status", ""),
                "contains_secret_risk": auto_row.get("contains_secret_risk", "False"),
                "live_action_risk": auto_row.get("live_action_risk", "False"),
                "requires_user_approval": auto_row.get("requires_user_approval", "False"),
                "collection_state": "not_collected_prerequisite_only",
                "hash_generated": False,
                "set_parsed": False,
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
    return plan_rows


def build_step_rows(plan_rows: List[Dict[str, object]], generated_at: str) -> List[Dict[str, object]]:
    step_templates = {
        "live_package_hashes.csv": [
            ("APPROVE-001", "User/release reviewer approves the live package manifest paths."),
            ("VERIFY-001", "Verify only approved manifest paths are in scope."),
            ("COLLECT-001", "After approval only, calculate sha256 hashes offline."),
            ("REVIEW-001", "Review hash CSV and keep live gate open until all live gates close together."),
        ],
        "parsed_live_set_template.json": [
            ("APPROVE-001", "User/release reviewer approves offline parsing of an inactive set template."),
            ("VERIFY-001", "Verify the set template is not loaded into MT5 and not attached to a chart."),
            ("COLLECT-001", "After approval only, parse requested fields from the template file offline."),
            ("REVIEW-001", "Review parsed fields and keep live gate open until all live gates close together."),
        ],
        "broker_symbol_spec.csv": [
            ("APPROVE-001", "User explicitly approves read-only MT5 symbol/spec query with no order actions."),
            ("VERIFY-001", "Verify runner is not executed and orders are disabled before any query."),
            ("COLLECT-001", "After approval only, collect read-only symbol/account spec fields."),
            ("REVIEW-001", "Review spec CSV and keep live gate open until all live gates close together."),
        ],
    }
    rows: List[Dict[str, object]] = []
    for plan in plan_rows:
        for seq, (step_id, instruction) in enumerate(step_templates[str(plan["file_name"])], start=1):
            rows.append(
                {
                    "gap_id": plan["gap_id"],
                    "file_name": plan["file_name"],
                    "step_sequence": seq,
                    "step_id": step_id,
                    "instruction": instruction,
                    "approval_phrase_required": plan["approval_phrase_required"],
                    "execution_state": "not_executed_prerequisite_only",
                    "hash_generated": False,
                    "set_parsed": False,
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
        "# Pending Auto Evidence Prerequisite Plan",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- pending_auto_items: `{decision['pending_auto_items']}`",
        f"- p0_items: `{decision['p0_items']}`",
        f"- p1_items: `{decision['p1_items']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Boundary",
        "",
        "- This plan does not collect the pending auto evidence.",
        "- No MT5 access, runner execution, order placement, active live set parsing, or live package hash is performed.",
        "- Each item remains blocked until its approval phrase and manual prerequisite are provided.",
        "",
        "## Pending Items",
        "",
    ]
    for row in plan_rows:
        lines.append(f"- `{row['file_name']}`: `{row['collection_class']}`; prerequisite: {row['manual_prerequisite']}.")
    lines.extend(["", "## Steps", ""])
    for row in step_rows:
        lines.append(f"- `{row['file_name']}` `{row['step_id']}`: {row['instruction']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")
    auto_rows = read_rows(AUTO_SAFE_PLAN)
    prereq_rows = read_rows(MANUAL_PREREQ_PLAN)
    plan_rows = build_plan_rows(auto_rows, prereq_rows, generated_at)
    step_rows = build_step_rows(plan_rows, generated_at)
    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_pending_auto_evidence_prerequisite_plan",
        "status": "pending_auto_prerequisites_drafted_live_blocked",
        "pending_auto_items": len(plan_rows),
        "p0_items": sum(1 for row in plan_rows if row["priority"] == "P0"),
        "p1_items": sum(1 for row in plan_rows if row["priority"] == "P1"),
        "planned_steps": len(step_rows),
        "hash_generated": False,
        "set_parsed": False,
        "mt5_accessed": False,
        "runner_executed": False,
        "orders_placed": False,
        "live_set_switched": False,
        "credential_values_output": False,
        "gate_status": "open",
        "ready_to_live_trade": False,
        "recommended_next_action": "review_pending_auto_evidence_prerequisite_plan_then_final_closeout",
    }
    plan_fieldnames = [
        "pending_sequence",
        "gap_id",
        "priority",
        "file_name",
        "required_fields",
        "collection_class",
        "manual_prerequisite",
        "approval_phrase_required",
        "allowed_collection",
        "prohibited_action",
        "source_prerequisite",
        "existing_forbidden_content",
        "next_allowed_action",
        "shortest_live_path_step",
        "auto_safe_status",
        "contains_secret_risk",
        "live_action_risk",
        "requires_user_approval",
        "collection_state",
        "hash_generated",
        "set_parsed",
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
        "instruction",
        "approval_phrase_required",
        "execution_state",
        "hash_generated",
        "set_parsed",
        "mt5_accessed",
        "runner_executed",
        "orders_placed",
        "live_set_switched",
        "gate_status",
        "ready_to_live_trade",
        "generated_at",
    ]
    write_csv(OUT_DIR / "pending_auto_evidence_prerequisite_plan.csv", plan_rows, plan_fieldnames)
    write_csv(OUT_DIR / "pending_auto_evidence_prerequisite_steps.csv", step_rows, step_fieldnames)
    write_csv(OUT_DIR / "pending_auto_evidence_prerequisite_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "pending_auto_evidence_prerequisite_decision.json", decision)
    (OUT_DIR / "pending_auto_evidence_prerequisite_plan.md").write_text(build_report(decision, plan_rows, step_rows), encoding="utf-8-sig")
    for key, value in decision.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
