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
FILL_PLAN_DIR = VALIDATION_DIR / "stage_state_live_gate_evidence_fill_plan_20260721"
AUTO_SAFE_DIR = VALIDATION_DIR / "stage_state_live_gate_auto_safe_evidence_20260721"
PLAN_DIR = VALIDATION_DIR / "stage_state_manual_evidence_prerequisite_plan_20260721"
OUT_DIR = VALIDATION_DIR / "stage_state_manual_evidence_prerequisite_plan_review_20260721"

FILL_PLAN = FILL_PLAN_DIR / "live_gate_evidence_fill_plan.csv"
AUTO_SAFE_PLAN = AUTO_SAFE_DIR / "auto_safe_evidence_collection_plan.csv"
PLAN = PLAN_DIR / "manual_evidence_prerequisite_plan.csv"
DECISION = PLAN_DIR / "manual_evidence_prerequisite_plan_decision.json"


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
    return {
        "check_id": check_id,
        "passed": passed,
        "severity": severity,
        "detail": detail,
    }


def collected_auto_keys(auto_rows: List[Dict[str, str]]) -> set[tuple[str, str]]:
    return {
        (row.get("gap_id", ""), row.get("file_name", ""))
        for row in auto_rows
        if row.get("auto_safe_status") == "collected"
    }


def has_secret_assignment(text: str) -> bool:
    patterns = [
        r"(?i)\b(password|token|api[_-]?key|secret)\b\s*[:=]\s*['\"](?!PENDING|TEMPLATE|REDACTED|false|true|none|null)[^'\"]{4,}['\"]",
        r"(?i)\b(account|login)\b\s*[:=]\s*\d{5,}",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    fill_rows = read_rows(FILL_PLAN)
    auto_rows = read_rows(AUTO_SAFE_PLAN)
    plan_rows = read_rows(PLAN)
    decision = read_json(DECISION)
    collected = collected_auto_keys(auto_rows)
    expected_keys = {
        (row.get("gap_id", ""), row.get("file_name", ""))
        for row in fill_rows
        if (row.get("gap_id", ""), row.get("file_name", "")) not in collected
    }
    actual_keys = {(row.get("gap_id", ""), row.get("file_name", "")) for row in plan_rows}
    output_text = "\n".join(path.read_text(encoding="utf-8-sig", errors="ignore") for path in PLAN_DIR.glob("manual_evidence_prerequisite_plan*"))

    checks = [
        check("decision_status_live_blocked", decision.get("status") == "manual_prerequisites_drafted_live_blocked", str(decision.get("status"))),
        check("remaining_count_is_20", len(plan_rows) == 20 and decision.get("remaining_prerequisite_items") == 20, f"rows={len(plan_rows)} decision={decision.get('remaining_prerequisite_items')}"),
        check("expected_remaining_keys_match", expected_keys == actual_keys, f"missing={sorted(expected_keys - actual_keys)} extra={sorted(actual_keys - expected_keys)}"),
        check("manual_count_is_13", sum(1 for row in plan_rows if row.get("collection_method") == "manual") == 13, "manual rows"),
        check("rehearsal_count_is_4", sum(1 for row in plan_rows if row.get("collection_method") == "rehearsal") == 4, "rehearsal rows"),
        check("pending_auto_count_is_3", sum(1 for row in plan_rows if row.get("collection_method") == "auto") == 3, "pending auto rows"),
        check("all_completion_states_open", all(row.get("completion_state") == "open_prerequisite" for row in plan_rows), "completion states"),
        check("all_gate_status_open", all(row.get("gate_status") == "open" for row in plan_rows), "gate statuses"),
        check("all_ready_false", all(not boolish(row.get("ready_to_live_trade")) for row in plan_rows) and decision.get("ready_to_live_trade") is False, "ready flags"),
        check("no_collected_auto_reincluded", not any(key in collected for key in actual_keys), "collected auto keys excluded"),
        check("forbidden_content_present", all(row.get("forbidden_content", "").strip() for row in plan_rows), "forbidden content fields"),
        check("next_allowed_action_present", all(row.get("next_allowed_action", "").strip() for row in plan_rows), "next allowed action fields"),
        check("confirmer_present", all(row.get("confirmer", "").strip() for row in plan_rows), "confirmer fields"),
        check("no_secret_assignments_in_outputs", not has_secret_assignment(output_text), "secret assignment scan"),
    ]
    failures = [row for row in checks if not row["passed"]]
    review_decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_manual_evidence_prerequisite_plan_review",
        "status": "pass_manual_prerequisites_live_blocked" if not failures else "fail_manual_prerequisites_review",
        "review_completed": True,
        "remaining_prerequisite_items": len(plan_rows),
        "manual_items": sum(1 for row in plan_rows if row.get("collection_method") == "manual"),
        "rehearsal_items": sum(1 for row in plan_rows if row.get("collection_method") == "rehearsal"),
        "pending_auto_items": sum(1 for row in plan_rows if row.get("collection_method") == "auto"),
        "p0_items": sum(1 for row in plan_rows if row.get("priority") == "P0"),
        "p1_items": sum(1 for row in plan_rows if row.get("priority") == "P1"),
        "ready_to_live_trade": False,
        "blocker_failure_count": len(failures),
        "recommended_next_action": "start_p0_manual_template_fill_dry_run_with_redacted_values" if not failures else "fix_manual_prerequisite_plan",
    }

    write_csv(OUT_DIR / "manual_evidence_prerequisite_plan_review_checks.csv", checks, ["check_id", "passed", "severity", "detail"])
    write_csv(OUT_DIR / "manual_evidence_prerequisite_plan_review_decision.csv", [review_decision], list(review_decision.keys()))
    write_json(OUT_DIR / "manual_evidence_prerequisite_plan_review_decision.json", review_decision)
    lines = [
        "# Manual Evidence Prerequisite Plan Review",
        "",
        "## Decision",
        "",
        f"- status: `{review_decision['status']}`",
        f"- remaining_prerequisite_items: `{review_decision['remaining_prerequisite_items']}`",
        f"- blocker_failure_count: `{review_decision['blocker_failure_count']}`",
        f"- ready_to_live_trade: `{review_decision['ready_to_live_trade']}`",
        "",
        "## Checks",
        "",
    ]
    for row in checks:
        lines.append(f"- `{row['check_id']}`: `{row['passed']}` - {row['detail']}")
    lines.append("")
    (OUT_DIR / "manual_evidence_prerequisite_plan_review.md").write_text("\n".join(lines), encoding="utf-8-sig")

    for key, value in review_decision.items():
        print(f"{key}={value}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
