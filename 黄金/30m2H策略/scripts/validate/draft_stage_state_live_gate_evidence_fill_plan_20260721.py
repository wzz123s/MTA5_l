from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
TEMPLATE_DIR = VALIDATION_DIR / "stage_state_live_gate_evidence_templates_20260721"
REVIEW_DIR = VALIDATION_DIR / "stage_state_live_gate_evidence_templates_review_20260721"
OUT_DIR = VALIDATION_DIR / "stage_state_live_gate_evidence_fill_plan_20260721"

INDEX = TEMPLATE_DIR / "live_gate_evidence_index.csv"
SCHEMA = TEMPLATE_DIR / "live_gate_evidence_schema.csv"
TEMPLATE_REVIEW_DECISION = REVIEW_DIR / "live_gate_evidence_templates_review_decision.json"


FILL_PLAN_RULES: Dict[str, Dict[str, object]] = {
    "live_trade_approval_record.md": {
        "collection_method": "manual",
        "risk_tags": ["requires_user_approval"],
        "owner_role": "approver",
        "fill_sequence": 1,
        "allowed_source": "manual approval document",
        "blocked_action": "do not infer approval from SIM_ONLY results",
    },
    "live_package_manifest.json": {
        "collection_method": "manual",
        "risk_tags": ["live_action_risk", "requires_user_approval"],
        "owner_role": "release reviewer",
        "fill_sequence": 2,
        "allowed_source": "reviewed live artifact manifest",
        "blocked_action": "do not reuse SIM_ONLY package as live package",
    },
    "live_package_hashes.csv": {
        "collection_method": "auto",
        "risk_tags": ["live_action_risk"],
        "owner_role": "release reviewer",
        "fill_sequence": 3,
        "allowed_source": "local file hash audit after live package exists",
        "blocked_action": "do not hash or deploy unreviewed live artifacts",
    },
    "live_package_deployment_proof.md": {
        "collection_method": "manual",
        "risk_tags": ["live_action_risk", "requires_user_approval"],
        "owner_role": "release reviewer",
        "fill_sequence": 4,
        "allowed_source": "deployment proof captured after package audit",
        "blocked_action": "do not attach live package to chart",
    },
    "sim_mode_transition_approval.md": {
        "collection_method": "manual",
        "risk_tags": ["live_action_risk", "requires_user_approval"],
        "owner_role": "approver",
        "fill_sequence": 5,
        "allowed_source": "explicit transition approval",
        "blocked_action": "do not set InpSimMode=false",
    },
    "parsed_live_set_template.json": {
        "collection_method": "auto",
        "risk_tags": ["live_action_risk"],
        "owner_role": "release reviewer",
        "fill_sequence": 6,
        "allowed_source": "parsed live set after transition approval",
        "blocked_action": "do not create or use active live set in this step",
    },
    "secret_policy.md": {
        "collection_method": "manual",
        "risk_tags": ["contains_secret_risk", "requires_user_approval"],
        "owner_role": "operator",
        "fill_sequence": 7,
        "allowed_source": "secret handling policy without secret values",
        "blocked_action": "do not write account/password/token values",
    },
    "credential_scan_report.csv": {
        "collection_method": "auto",
        "risk_tags": ["contains_secret_risk"],
        "owner_role": "operator",
        "fill_sequence": 8,
        "allowed_source": "source scan result with file names only",
        "blocked_action": "do not print or copy credential values",
    },
    "env_example_review.md": {
        "collection_method": "manual",
        "risk_tags": ["contains_secret_risk"],
        "owner_role": "operator",
        "fill_sequence": 9,
        "allowed_source": ".env.example structural review",
        "blocked_action": "do not add real values to .env.example",
    },
    "production_runner_decision.md": {
        "collection_method": "manual",
        "risk_tags": ["live_action_risk", "requires_user_approval"],
        "owner_role": "reviewer",
        "fill_sequence": 10,
        "allowed_source": "runner architecture decision",
        "blocked_action": "do not approve auto_trade/auto_trader.py by default",
    },
    "runner_source_audit.csv": {
        "collection_method": "auto",
        "risk_tags": ["live_action_risk"],
        "owner_role": "reviewer",
        "fill_sequence": 11,
        "allowed_source": "static source audit",
        "blocked_action": "do not execute runner files",
    },
    "live_risk_policy.json": {
        "collection_method": "manual",
        "risk_tags": ["requires_user_approval"],
        "owner_role": "operator",
        "fill_sequence": 12,
        "allowed_source": "operator-defined risk policy",
        "blocked_action": "do not infer live risk from SIM_ONLY observation",
    },
    "risk_policy_manual_confirmation.md": {
        "collection_method": "manual",
        "risk_tags": ["requires_user_approval"],
        "owner_role": "operator",
        "fill_sequence": 13,
        "allowed_source": "manual confirmation",
        "blocked_action": "do not use broad account defaults",
    },
    "emergency_runbook.md": {
        "collection_method": "manual",
        "risk_tags": ["live_action_risk", "requires_user_approval"],
        "owner_role": "operator",
        "fill_sequence": 14,
        "allowed_source": "documented emergency runbook",
        "blocked_action": "do not rely only on RUNNER_STOP.flag",
    },
    "emergency_rehearsal_report.csv": {
        "collection_method": "rehearsal",
        "risk_tags": ["live_action_risk", "requires_user_approval"],
        "owner_role": "operator",
        "fill_sequence": 15,
        "allowed_source": "non-production emergency rehearsal",
        "blocked_action": "do not rehearse on real-money positions",
    },
    "live_monitoring_policy.json": {
        "collection_method": "manual",
        "risk_tags": ["requires_user_approval"],
        "owner_role": "operator",
        "fill_sequence": 16,
        "allowed_source": "monitoring policy",
        "blocked_action": "do not start live without watched alert channels",
    },
    "reconciliation_checklist.csv": {
        "collection_method": "manual",
        "risk_tags": ["requires_user_approval"],
        "owner_role": "operator",
        "fill_sequence": 17,
        "allowed_source": "reconciliation checklist",
        "blocked_action": "do not skip ledger/account reconciliation",
    },
    "live_account_spec_snapshot.json": {
        "collection_method": "manual",
        "risk_tags": ["contains_secret_risk", "requires_user_approval"],
        "owner_role": "operator",
        "fill_sequence": 18,
        "allowed_source": "account/spec snapshot without account password",
        "blocked_action": "do not store account password or token",
    },
    "broker_symbol_spec.csv": {
        "collection_method": "auto",
        "risk_tags": ["requires_user_approval"],
        "owner_role": "operator",
        "fill_sequence": 19,
        "allowed_source": "MT5 symbol spec read-only query after approval",
        "blocked_action": "do not place orders while collecting symbol spec",
    },
    "nonprod_order_rehearsal_report.md": {
        "collection_method": "rehearsal",
        "risk_tags": ["live_action_risk", "requires_user_approval"],
        "owner_role": "reviewer",
        "fill_sequence": 20,
        "allowed_source": "demo/tester order rehearsal",
        "blocked_action": "do not use real-money account",
    },
    "rehearsal_ledger.csv": {
        "collection_method": "rehearsal",
        "risk_tags": ["live_action_risk"],
        "owner_role": "reviewer",
        "fill_sequence": 21,
        "allowed_source": "demo/tester rehearsal ledger",
        "blocked_action": "do not import real-money ledger as rehearsal evidence",
    },
    "rehearsal_alert_log.csv": {
        "collection_method": "rehearsal",
        "risk_tags": ["live_action_risk"],
        "owner_role": "reviewer",
        "fill_sequence": 22,
        "allowed_source": "demo/tester rehearsal alert log",
        "blocked_action": "do not send live alert drills without approval",
    },
}


def read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def build_rows(index_rows: List[Dict[str, str]], schema_rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    schema_by_key = {(row["gap_id"], row["file_name"]): row for row in schema_rows}
    out: List[Dict[str, object]] = []
    for row in index_rows:
        rule = FILL_PLAN_RULES[row["file_name"]]
        schema = schema_by_key[(row["gap_id"], row["file_name"])]
        risk_tags = list(rule["risk_tags"])
        out.append(
            {
                "fill_sequence": rule["fill_sequence"],
                "gap_id": row["gap_id"],
                "priority": row["priority"],
                "category": row["category"],
                "severity": row["severity"],
                "file_name": row["file_name"],
                "relative_path": row["relative_path"],
                "file_kind": row["file_kind"],
                "collection_method": rule["collection_method"],
                "owner_role": rule["owner_role"],
                "required_fields": schema["required_fields"],
                "contains_secret_risk": "contains_secret_risk" in risk_tags,
                "live_action_risk": "live_action_risk" in risk_tags,
                "requires_user_approval": "requires_user_approval" in risk_tags,
                "allowed_source": rule["allowed_source"],
                "blocked_action": rule["blocked_action"],
                "gate_status": "open",
                "fill_status": "not_started",
                "ready_to_live_trade": False,
            }
        )
    return sorted(out, key=lambda item: int(item["fill_sequence"]))


def build_report(decision: Dict[str, object], rows: List[Dict[str, object]]) -> str:
    lines = [
        "# Live Gate Evidence Fill Plan",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- fill_plan_item_count: `{decision['fill_plan_item_count']}`",
        f"- auto_item_count: `{decision['auto_item_count']}`",
        f"- manual_item_count: `{decision['manual_item_count']}`",
        f"- rehearsal_item_count: `{decision['rehearsal_item_count']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Boundary",
        "",
        "- This is a fill plan only.",
        "- It does not fill real credential values.",
        "- It does not close any gate.",
        "- It does not execute live or rehearsal actions.",
        "",
        "## Fill Plan",
        "",
    ]
    for row in rows:
        lines.append(
            "- `{fill_sequence}` `{gap_id}` `{file_name}`: method `{collection_method}`, owner `{owner_role}`, "
            "secret_risk `{contains_secret_risk}`, live_action_risk `{live_action_risk}`, approval `{requires_user_approval}`".format(
                **row
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_rows = read_rows(INDEX)
    schema_rows = read_rows(SCHEMA)
    review = read_json(TEMPLATE_REVIEW_DECISION)
    rows = build_rows(index_rows, schema_rows)

    auto_count = sum(1 for row in rows if row["collection_method"] == "auto")
    manual_count = sum(1 for row in rows if row["collection_method"] == "manual")
    rehearsal_count = sum(1 for row in rows if row["collection_method"] == "rehearsal")
    secret_risk_count = sum(1 for row in rows if row["contains_secret_risk"])
    live_action_risk_count = sum(1 for row in rows if row["live_action_risk"])
    approval_count = sum(1 for row in rows if row["requires_user_approval"])
    missing_rules = [row["file_name"] for row in index_rows if row["file_name"] not in FILL_PLAN_RULES]

    decision = {
        "decision_time": datetime.now().isoformat(timespec="seconds"),
        "check_id": "stage_state_live_gate_evidence_fill_plan",
        "status": "fill_plan_draft_complete" if not missing_rules and len(rows) == 22 else "fill_plan_draft_incomplete",
        "fill_plan_item_count": len(rows),
        "auto_item_count": auto_count,
        "manual_item_count": manual_count,
        "rehearsal_item_count": rehearsal_count,
        "contains_secret_risk_count": secret_risk_count,
        "live_action_risk_count": live_action_risk_count,
        "requires_user_approval_count": approval_count,
        "missing_rule_count": len(missing_rules),
        "missing_rules": ";".join(missing_rules),
        "template_review_status": review.get("status", ""),
        "all_gate_status": "open",
        "ready_to_live_trade": False,
        "recommended_next_action": "review_fill_plan_without_filling_live_values",
    }

    write_csv(
        OUT_DIR / "live_gate_evidence_fill_plan.csv",
        rows,
        [
            "fill_sequence",
            "gap_id",
            "priority",
            "category",
            "severity",
            "file_name",
            "relative_path",
            "file_kind",
            "collection_method",
            "owner_role",
            "required_fields",
            "contains_secret_risk",
            "live_action_risk",
            "requires_user_approval",
            "allowed_source",
            "blocked_action",
            "gate_status",
            "fill_status",
            "ready_to_live_trade",
        ],
    )
    write_json(OUT_DIR / "live_gate_evidence_fill_plan_decision.json", decision)
    write_csv(OUT_DIR / "live_gate_evidence_fill_plan_decision.csv", [decision], list(decision.keys()))
    (OUT_DIR / "live_gate_evidence_fill_plan.md").write_text(build_report(decision, rows), encoding="utf-8-sig")
    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0 if decision["status"] == "fill_plan_draft_complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
