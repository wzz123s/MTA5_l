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
PREREQ_DIR = VALIDATION_DIR / "stage_state_manual_evidence_prerequisite_plan_20260721"
PLAN_DIR = VALIDATION_DIR / "stage_state_p1_rehearsal_prerequisite_dry_run_20260721"
OUT_DIR = VALIDATION_DIR / "stage_state_p1_rehearsal_prerequisite_dry_run_review_20260721"

PREREQ_PLAN = PREREQ_DIR / "manual_evidence_prerequisite_plan.csv"
PLAN = PLAN_DIR / "p1_rehearsal_prerequisite_dry_run_plan.csv"
STEPS = PLAN_DIR / "p1_rehearsal_prerequisite_dry_run_steps.csv"
DECISION = PLAN_DIR / "p1_rehearsal_prerequisite_dry_run_decision.json"


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


def expected_rows(prereq_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        row
        for row in prereq_rows
        if row.get("priority") == "P1"
        and row.get("collection_method") == "rehearsal"
        and row.get("completion_state") == "open_prerequisite"
    ]


def workspace_path(relative_path: str) -> Path:
    return ROOT / relative_path


def output_text() -> str:
    chunks: List[str] = []
    for path in PLAN_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".csv"}:
            chunks.append(path.read_text(encoding="utf-8-sig", errors="ignore"))
    return "\n".join(chunks)


def has_secret_assignment(text: str) -> bool:
    patterns = [
        r"(?i)\b(password|token|api[_-]?key|secret)\b\s*[:=]\s*['\"](?!PENDING|TEMPLATE|REDACTED|false|true|none|null)[^'\"]{4,}['\"]",
        r"(?i)\b(account|login)\b\s*[:=]\s*\d{5,}",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def markdown_sample_ok(path: Path) -> bool:
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    return "NOT_EXECUTED_DRY_RUN_PLAN_ONLY" in text and "ready_to_live_trade: `false`" in text


def csv_sample_ok(path: Path) -> bool:
    rows = read_rows(path)
    if len(rows) != 1:
        return False
    row = rows[0]
    return any(value == "NOT_EXECUTED_DRY_RUN_PLAN_ONLY" for value in row.values())


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    prereq_rows = read_rows(PREREQ_PLAN)
    plan_rows = read_rows(PLAN)
    step_rows = read_rows(STEPS)
    decision = read_json(DECISION)
    expected = expected_rows(prereq_rows)
    expected_keys = {(row.get("gap_id", ""), row.get("file_name", "")) for row in expected}
    actual_keys = {(row.get("gap_id", ""), row.get("file_name", "")) for row in plan_rows}

    missing_samples: List[str] = []
    bad_samples: List[str] = []
    outside_samples: List[str] = []
    for row in plan_rows:
        path = workspace_path(row.get("expected_evidence_sample_path", ""))
        try:
            path.relative_to(PLAN_DIR)
        except ValueError:
            outside_samples.append(str(path))
        if not path.exists():
            missing_samples.append(str(path))
            continue
        if path.suffix.lower() == ".csv":
            ok = csv_sample_ok(path)
        else:
            ok = markdown_sample_ok(path)
        if not ok:
            bad_samples.append(str(path))

    all_text = output_text()
    nonprod_text_ok = all(
        "demo_account" in row.get("allowed_environment", "")
        and "strategy_tester" in row.get("allowed_environment", "")
        and "SIM_ONLY_only" in row.get("allowed_environment", "")
        for row in plan_rows
    )
    prohibited_text_ok = all(
        "real_money_account" in row.get("prohibited_environment", "")
        and "live_set" in row.get("prohibited_environment", "")
        and "real_positions" in row.get("prohibited_environment", "")
        and "real_orders" in row.get("prohibited_environment", "")
        for row in plan_rows
    )
    no_actions = (
        decision.get("mt5_accessed") is False
        and decision.get("runner_executed") is False
        and decision.get("orders_placed") is False
        and decision.get("live_set_switched") is False
        and all(not boolish(row.get("mt5_accessed")) for row in plan_rows + step_rows)
        and all(not boolish(row.get("runner_executed")) for row in plan_rows + step_rows)
        and all(not boolish(row.get("orders_placed")) for row in plan_rows + step_rows)
        and all(not boolish(row.get("live_set_switched")) for row in plan_rows + step_rows)
    )

    checks = [
        check("decision_status_live_blocked", decision.get("status") == "p1_rehearsal_dry_run_planned_live_blocked", str(decision.get("status"))),
        check("expected_p1_rehearsal_count_is_3", len(expected) == 3, f"expected={len(expected)}"),
        check("plan_count_matches_expected", len(plan_rows) == len(expected), f"plan={len(plan_rows)} expected={len(expected)}"),
        check("expected_keys_match_plan", expected_keys == actual_keys, f"missing={sorted(expected_keys - actual_keys)} extra={sorted(actual_keys - expected_keys)}"),
        check("planned_steps_present", len(step_rows) == len(plan_rows) * 6 and decision.get("planned_steps") == len(step_rows), f"steps={len(step_rows)}"),
        check("sample_files_exist", not missing_samples, f"missing={missing_samples}"),
        check("sample_outputs_inside_dir", not outside_samples, f"outside={outside_samples}"),
        check("sample_status_not_executed", not bad_samples, f"bad_samples={bad_samples}"),
        check("allowed_environments_nonprod_only", nonprod_text_ok, "allowed environment text"),
        check("prohibited_live_environment_present", prohibited_text_ok, "prohibited environment text"),
        check("execution_state_not_executed", all(row.get("execution_state") == "not_executed_plan_only" for row in plan_rows + step_rows), "execution states"),
        check("no_mt5_runner_order_live_set_actions", no_actions, "action flags"),
        check("no_secret_assignments_in_outputs", not has_secret_assignment(all_text), "secret assignment scan"),
        check("all_gate_status_open", all(row.get("gate_status") == "open" for row in plan_rows + step_rows) and decision.get("gate_status") == "open", "gate statuses"),
        check("all_ready_false", all(not boolish(row.get("ready_to_live_trade")) for row in plan_rows + step_rows) and decision.get("ready_to_live_trade") is False, "ready flags"),
    ]
    failures = [row for row in checks if not row["passed"]]
    review_decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_p1_rehearsal_prerequisite_dry_run_review",
        "status": "pass_p1_rehearsal_dry_run_live_blocked" if not failures else "fail_p1_rehearsal_dry_run_review",
        "review_completed": True,
        "p1_rehearsal_items": len(plan_rows),
        "planned_steps_reviewed": len(step_rows),
        "expected_evidence_samples": len(plan_rows),
        "ready_to_live_trade": False,
        "blocker_failure_count": len(failures),
        "recommended_next_action": "draft_pending_auto_evidence_prerequisite_plan" if not failures else "fix_p1_rehearsal_dry_run",
    }

    write_csv(OUT_DIR / "p1_rehearsal_prerequisite_dry_run_review_checks.csv", checks, ["check_id", "passed", "severity", "detail"])
    write_csv(OUT_DIR / "p1_rehearsal_prerequisite_dry_run_review_decision.csv", [review_decision], list(review_decision.keys()))
    write_json(OUT_DIR / "p1_rehearsal_prerequisite_dry_run_review_decision.json", review_decision)
    lines = [
        "# P1 Rehearsal Prerequisite Dry Run Review",
        "",
        "## Decision",
        "",
        f"- status: `{review_decision['status']}`",
        f"- p1_rehearsal_items: `{review_decision['p1_rehearsal_items']}`",
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
    (OUT_DIR / "p1_rehearsal_prerequisite_dry_run_review.md").write_text("\n".join(lines), encoding="utf-8-sig")

    for key, value in review_decision.items():
        print(f"{key}={value}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
