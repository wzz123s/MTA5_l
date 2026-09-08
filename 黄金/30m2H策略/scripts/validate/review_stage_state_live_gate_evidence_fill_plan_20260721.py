from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
PLAN_DIR = VALIDATION_DIR / "stage_state_live_gate_evidence_fill_plan_20260721"
OUT_DIR = VALIDATION_DIR / "stage_state_live_gate_evidence_fill_plan_review_20260721"

PLAN = PLAN_DIR / "live_gate_evidence_fill_plan.csv"
PLAN_DECISION = PLAN_DIR / "live_gate_evidence_fill_plan_decision.json"
TEMPLATE_REVIEW_DECISION = VALIDATION_DIR / "stage_state_live_gate_evidence_templates_review_20260721" / "live_gate_evidence_templates_review_decision.json"
STOP_FLAG = ROOT / "auto_trade" / "RUNNER_STOP.flag"


EXPECTED_FILES = {
    "live_trade_approval_record.md",
    "live_package_manifest.json",
    "live_package_hashes.csv",
    "live_package_deployment_proof.md",
    "sim_mode_transition_approval.md",
    "parsed_live_set_template.json",
    "secret_policy.md",
    "credential_scan_report.csv",
    "env_example_review.md",
    "production_runner_decision.md",
    "runner_source_audit.csv",
    "live_risk_policy.json",
    "risk_policy_manual_confirmation.md",
    "emergency_runbook.md",
    "emergency_rehearsal_report.csv",
    "live_monitoring_policy.json",
    "reconciliation_checklist.csv",
    "live_account_spec_snapshot.json",
    "broker_symbol_spec.csv",
    "nonprod_order_rehearsal_report.md",
    "rehearsal_ledger.csv",
    "rehearsal_alert_log.csv",
}


def read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
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


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def add_check(
    checks: List[Dict[str, object]],
    check_id: str,
    passed: bool,
    actual: object,
    expected: object,
    severity: str = "blocker",
    note: str = "",
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "status": "pass" if passed else "fail",
            "pass": passed,
            "actual": actual,
            "expected": expected,
            "severity": severity,
            "note": note,
        }
    )


def build_report(decision: Dict[str, object], checks: List[Dict[str, object]]) -> str:
    failed = [row for row in checks if row["status"] != "pass"]
    lines = [
        "# Live Gate Evidence Fill Plan Review",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- review_completed: `{decision['review_completed']}`",
        f"- fill_plan_item_count: `{decision['fill_plan_item_count']}`",
        f"- auto_item_count: `{decision['auto_item_count']}`",
        f"- manual_item_count: `{decision['manual_item_count']}`",
        f"- rehearsal_item_count: `{decision['rehearsal_item_count']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        f"- blocker_failure_count: `{decision['blocker_failure_count']}`",
        "",
        "## Boundary",
        "",
        "- This review validates the fill plan only.",
        "- It does not fill evidence values.",
        "- It does not close any live gate.",
        "- It does not execute live or rehearsal actions.",
        "",
        "## Failed Checks",
        "",
    ]
    if not failed:
        lines.append("- None.")
    else:
        for row in failed:
            lines.append(f"- `{row['check_id']}`: {row['actual']} (expected {row['expected']})")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    plan_rows = read_rows(PLAN)
    plan_decision = read_json(PLAN_DECISION)
    template_review = read_json(TEMPLATE_REVIEW_DECISION)

    file_names = {row.get("file_name", "") for row in plan_rows}
    auto_count = sum(1 for row in plan_rows if row.get("collection_method") == "auto")
    manual_count = sum(1 for row in plan_rows if row.get("collection_method") == "manual")
    rehearsal_count = sum(1 for row in plan_rows if row.get("collection_method") == "rehearsal")
    secret_risk_count = sum(1 for row in plan_rows if truthy(row.get("contains_secret_risk")))
    live_action_risk_count = sum(1 for row in plan_rows if truthy(row.get("live_action_risk")))
    approval_count = sum(1 for row in plan_rows if truthy(row.get("requires_user_approval")))
    missing_required_fields = [row.get("file_name", "") for row in plan_rows if not row.get("required_fields", "").strip()]

    checks: List[Dict[str, object]] = []
    add_check(checks, "plan_exists", PLAN.exists(), PLAN, "exists")
    add_check(checks, "plan_decision_complete", plan_decision.get("status") == "fill_plan_draft_complete", plan_decision.get("status"), "fill_plan_draft_complete")
    add_check(checks, "template_review_pass", template_review.get("status") == "pass_templates_open_live_blocked", template_review.get("status"), "pass_templates_open_live_blocked")
    add_check(checks, "all_22_files_present", file_names == EXPECTED_FILES, ";".join(sorted(file_names)), ";".join(sorted(EXPECTED_FILES)))
    add_check(checks, "plan_item_count_22", len(plan_rows) == 22, len(plan_rows), 22)
    add_check(checks, "auto_item_count_5", auto_count == 5, auto_count, 5)
    add_check(checks, "manual_item_count_13", manual_count == 13, manual_count, 13)
    add_check(checks, "rehearsal_item_count_4", rehearsal_count == 4, rehearsal_count, 4)
    add_check(checks, "secret_risk_items_marked", secret_risk_count == 4, secret_risk_count, 4)
    add_check(checks, "live_action_risk_items_marked", live_action_risk_count == 12, live_action_risk_count, 12)
    add_check(checks, "approval_items_marked", approval_count == 15, approval_count, 15)
    add_check(checks, "all_required_fields_present", not missing_required_fields, ";".join(missing_required_fields), "no missing required fields")
    add_check(checks, "all_gate_status_open", all(row.get("gate_status") == "open" for row in plan_rows), "all open", "all open")
    add_check(checks, "all_fill_status_not_started", all(row.get("fill_status") == "not_started" for row in plan_rows), "all not_started", "all not_started")
    add_check(checks, "all_ready_to_live_trade_false", all(not truthy(row.get("ready_to_live_trade")) for row in plan_rows), "all false", "all false")
    add_check(checks, "stop_flag_absent", not STOP_FLAG.exists(), STOP_FLAG, "absent")

    blocker_failures = [row for row in checks if row["status"] == "fail" and row["severity"] == "blocker"]
    review_pass = not blocker_failures
    decision = {
        "decision_time": datetime.now().isoformat(timespec="seconds"),
        "check_id": "stage_state_live_gate_evidence_fill_plan_review",
        "status": "pass_fill_plan_ready_live_blocked" if review_pass else "fail",
        "review_completed": review_pass,
        "fill_plan_item_count": len(plan_rows),
        "auto_item_count": auto_count,
        "manual_item_count": manual_count,
        "rehearsal_item_count": rehearsal_count,
        "contains_secret_risk_count": secret_risk_count,
        "live_action_risk_count": live_action_risk_count,
        "requires_user_approval_count": approval_count,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "recommended_next_action": "collect_auto_safe_evidence_without_live_or_secret_values",
    }

    write_csv(
        OUT_DIR / "live_gate_evidence_fill_plan_review_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(OUT_DIR / "live_gate_evidence_fill_plan_review_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "live_gate_evidence_fill_plan_review_decision.json", decision)
    (OUT_DIR / "live_gate_evidence_fill_plan_review.md").write_text(build_report(decision, checks), encoding="utf-8-sig")

    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0 if review_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
