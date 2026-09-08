from __future__ import annotations


import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
AUTO_SAFE_DIR = VALIDATION_DIR / "stage_state_live_gate_auto_safe_evidence_20260721"
PLAN_DIR = VALIDATION_DIR / "stage_state_pending_auto_evidence_prerequisite_plan_20260721"
OUT_DIR = VALIDATION_DIR / "stage_state_pending_auto_evidence_prerequisite_plan_review_20260721"

AUTO_SAFE_PLAN = AUTO_SAFE_DIR / "auto_safe_evidence_collection_plan.csv"
PLAN = PLAN_DIR / "pending_auto_evidence_prerequisite_plan.csv"
STEPS = PLAN_DIR / "pending_auto_evidence_prerequisite_steps.csv"
DECISION = PLAN_DIR / "pending_auto_evidence_prerequisite_decision.json"


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def boolish(value: object) -> bool:
    return str(value).strip().lower() == "true"


def check(check_id: str, passed: bool, detail: str, severity: str = "critical") -> Dict[str, object]:
    return {"check_id": check_id, "passed": passed, "severity": severity, "detail": detail}


def has_secret_assignment(text: str) -> bool:
    patterns = [
        r"(?i)\b(password|token|api[_-]?key|secret)\b\s*[:=]\s*['\"](?!PENDING|TEMPLATE|REDACTED|false|true|none|null)[^'\"]{4,}['\"]",
        r"(?i)\b(account|login)\b\s*[:=]\s*\d{5,}",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def output_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8-sig", errors="ignore") for path in PLAN_DIR.glob("pending_auto_evidence_prerequisite*"))


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    auto_rows = read_rows(AUTO_SAFE_PLAN)
    plan_rows = read_rows(PLAN)
    step_rows = read_rows(STEPS)
    decision = read_json(DECISION)
    expected = [row for row in auto_rows if row.get("auto_safe_status") == "pending_manual_prerequisite"]
    expected_keys = {(row.get("gap_id", ""), row.get("file_name", "")) for row in expected}
    actual_keys = {(row.get("gap_id", ""), row.get("file_name", "")) for row in plan_rows}
    all_rows = plan_rows + step_rows
    all_no_actions = (
        decision.get("hash_generated") is False
        and decision.get("set_parsed") is False
        and decision.get("mt5_accessed") is False
        and decision.get("runner_executed") is False
        and decision.get("orders_placed") is False
        and decision.get("live_set_switched") is False
        and all(not boolish(row.get("hash_generated")) for row in all_rows)
        and all(not boolish(row.get("set_parsed")) for row in all_rows)
        and all(not boolish(row.get("mt5_accessed")) for row in all_rows)
        and all(not boolish(row.get("runner_executed")) for row in all_rows)
        and all(not boolish(row.get("orders_placed")) for row in all_rows)
        and all(not boolish(row.get("live_set_switched")) for row in all_rows)
    )
    approval_phrases_ok = all(row.get("approval_phrase_required", "").startswith("USER_APPROVES_") for row in plan_rows)
    class_set = {row.get("collection_class") for row in plan_rows}
    required_classes = {
        "offline_hash_after_live_package_approval",
        "offline_set_parse_after_transition_approval",
        "read_only_mt5_spec_after_user_approval",
    }
    checks = [
        check("decision_status_live_blocked", decision.get("status") == "pending_auto_prerequisites_drafted_live_blocked", str(decision.get("status"))),
        check("expected_pending_auto_count_is_3", len(expected) == 3, f"expected={len(expected)}"),
        check("plan_count_matches_expected", len(plan_rows) == len(expected), f"plan={len(plan_rows)} expected={len(expected)}"),
        check("expected_keys_match_plan", expected_keys == actual_keys, f"missing={sorted(expected_keys - actual_keys)} extra={sorted(actual_keys - expected_keys)}"),
        check("planned_steps_present", len(step_rows) == len(plan_rows) * 4 and decision.get("planned_steps") == len(step_rows), f"steps={len(step_rows)}"),
        check("collection_classes_complete", class_set == required_classes, f"classes={sorted(class_set)}"),
        check("approval_phrases_present", approval_phrases_ok, "approval phrases"),
        check("collection_state_not_collected", all(row.get("collection_state") == "not_collected_prerequisite_only" for row in plan_rows), "collection states"),
        check("no_hash_parse_mt5_runner_order_live_set_actions", all_no_actions, "action flags"),
        check("no_secret_assignments_in_outputs", not has_secret_assignment(output_text()), "secret assignment scan"),
        check("all_gate_status_open", all(row.get("gate_status") == "open" for row in all_rows) and decision.get("gate_status") == "open", "gate statuses"),
        check("all_ready_false", all(not boolish(row.get("ready_to_live_trade")) for row in all_rows) and decision.get("ready_to_live_trade") is False, "ready flags"),
    ]
    failures = [row for row in checks if not row["passed"]]
    review_decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_pending_auto_evidence_prerequisite_plan_review",
        "status": "pass_pending_auto_prerequisites_live_blocked" if not failures else "fail_pending_auto_prerequisites_review",
        "review_completed": True,
        "pending_auto_items": len(plan_rows),
        "planned_steps_reviewed": len(step_rows),
        "ready_to_live_trade": False,
        "blocker_failure_count": len(failures),
        "recommended_next_action": "generate_final_strategy_closeout_report" if not failures else "fix_pending_auto_prerequisite_plan",
    }
    write_csv(OUT_DIR / "pending_auto_evidence_prerequisite_review_checks.csv", checks, ["check_id", "passed", "severity", "detail"])
    write_csv(OUT_DIR / "pending_auto_evidence_prerequisite_review_decision.csv", [review_decision], list(review_decision.keys()))
    write_json(OUT_DIR / "pending_auto_evidence_prerequisite_review_decision.json", review_decision)
    lines = [
        "# Pending Auto Evidence Prerequisite Plan Review",
        "",
        "## Decision",
        "",
        f"- status: `{review_decision['status']}`",
        f"- pending_auto_items: `{review_decision['pending_auto_items']}`",
        f"- planned_steps_reviewed: `{review_decision['planned_steps_reviewed']}`",
        f"- blocker_failure_count: `{review_decision['blocker_failure_count']}`",
        f"- ready_to_live_trade: `{review_decision['ready_to_live_trade']}`",
        "",
        "## Checks",
        "",
    ]
    for row in checks:
        lines.append(f"- `{row['check_id']}`: `{row['passed']}` - {row['detail']}")
    lines.append("")
    (OUT_DIR / "pending_auto_evidence_prerequisite_review.md").write_text("\n".join(lines), encoding="utf-8-sig")
    for key, value in review_decision.items():
        print(f"{key}={value}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
