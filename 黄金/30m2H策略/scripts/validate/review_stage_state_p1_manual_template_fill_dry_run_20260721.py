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
DRY_RUN_DIR = VALIDATION_DIR / "stage_state_p1_manual_template_fill_dry_run_20260721"
OUT_DIR = VALIDATION_DIR / "stage_state_p1_manual_template_fill_dry_run_review_20260721"

PREREQ_PLAN = PREREQ_DIR / "manual_evidence_prerequisite_plan.csv"
MANIFEST = DRY_RUN_DIR / "p1_manual_template_fill_dry_run_manifest.csv"
DECISION = DRY_RUN_DIR / "p1_manual_template_fill_dry_run_decision.json"


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


def split_fields(value: str) -> List[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def check(check_id: str, passed: bool, detail: str, severity: str = "critical") -> Dict[str, object]:
    return {"check_id": check_id, "passed": passed, "severity": severity, "detail": detail}


def expected_rows(prereq_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        row
        for row in prereq_rows
        if row.get("priority") == "P1"
        and row.get("collection_method") == "manual"
        and row.get("completion_state") == "open_prerequisite"
    ]


def workspace_path(relative_path: str) -> Path:
    return ROOT / relative_path


def output_text() -> str:
    chunks: List[str] = []
    for path in DRY_RUN_DIR.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".csv"}:
            chunks.append(path.read_text(encoding="utf-8-sig", errors="ignore"))
    return "\n".join(chunks)


def has_secret_assignment(text: str) -> bool:
    patterns = [
        r"(?i)\b(password|token|api[_-]?key|secret)\b\s*[:=]\s*['\"](?!PENDING|TEMPLATE|REDACTED|false|true|none|null)[^'\"]{4,}['\"]",
        r"(?i)\b(account|login)\b\s*[:=]\s*\d{5,}",
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def json_fields_valid(path: Path, fields: List[str], secret_risk: bool) -> bool:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    values = payload.get("fields", {})
    if not isinstance(values, dict):
        return False
    expected_prefix = "REDACTED_" if secret_risk else "PENDING_"
    for field in fields:
        if not str(values.get(field, "")).startswith(expected_prefix):
            return False
    return payload.get("ready_to_live_trade") is False and payload.get("gate_status") == "open"


def csv_fields_valid(path: Path, fields: List[str], secret_risk: bool) -> bool:
    rows = read_rows(path)
    if len(rows) != 1:
        return False
    expected_prefix = "REDACTED_" if secret_risk else "PENDING_"
    row = rows[0]
    for field in fields:
        if not str(row.get(field, "")).startswith(expected_prefix):
            return False
    return True


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    prereq_rows = read_rows(PREREQ_PLAN)
    manifest_rows = read_rows(MANIFEST)
    decision = read_json(DECISION)
    expected = expected_rows(prereq_rows)
    expected_keys = {(row.get("gap_id", ""), row.get("file_name", "")) for row in expected}
    actual_keys = {(row.get("gap_id", ""), row.get("file_name", "")) for row in manifest_rows}

    missing_files: List[str] = []
    outside_outputs: List[str] = []
    field_failures: List[str] = []
    for row in manifest_rows:
        path = workspace_path(row.get("dry_run_relative_path", ""))
        try:
            path.relative_to(DRY_RUN_DIR)
        except ValueError:
            outside_outputs.append(str(path))
        if not path.exists():
            missing_files.append(str(path))
            continue
        fields = split_fields(row.get("required_fields", ""))
        secret_risk = boolish(row.get("contains_secret_risk"))
        if path.suffix.lower() == ".json":
            valid = json_fields_valid(path, fields, secret_risk)
        elif path.suffix.lower() == ".csv":
            valid = csv_fields_valid(path, fields, secret_risk)
        else:
            valid = False
        if not valid:
            field_failures.append(f"{row.get('gap_id')}:{row.get('file_name')}")

    all_text = output_text()
    checks = [
        check("decision_status_live_blocked", decision.get("status") == "p1_manual_dry_run_generated_live_blocked", str(decision.get("status"))),
        check("expected_p1_manual_count_is_3", len(expected) == 3, f"expected={len(expected)}"),
        check("manifest_count_matches_expected", len(manifest_rows) == len(expected), f"manifest={len(manifest_rows)} expected={len(expected)}"),
        check("expected_keys_match_manifest", expected_keys == actual_keys, f"missing={sorted(expected_keys - actual_keys)} extra={sorted(actual_keys - expected_keys)}"),
        check("dry_run_files_exist", not missing_files, f"missing={missing_files}"),
        check("dry_run_outputs_inside_dir", not outside_outputs, f"outside={outside_outputs}"),
        check("all_required_fields_placeholder_filled", not field_failures, f"field_failures={field_failures}"),
        check("file_type_counts", sum(1 for row in manifest_rows if row.get("file_kind") == "json") == 2 and sum(1 for row in manifest_rows if row.get("file_kind") == "csv") == 1, "json/csv counts"),
        check("source_templates_not_overwritten", all(not boolish(row.get("original_template_overwritten")) for row in manifest_rows) and decision.get("original_templates_overwritten") is False, "overwrite flags"),
        check("no_secret_assignments_in_outputs", not has_secret_assignment(all_text), "secret assignment scan"),
        check("all_gate_status_open", all(row.get("gate_status") == "open" for row in manifest_rows) and decision.get("gate_status") == "open", "gate statuses"),
        check("all_ready_false", all(not boolish(row.get("ready_to_live_trade")) for row in manifest_rows) and decision.get("ready_to_live_trade") is False, "ready flags"),
        check("no_runner_mt5_order_live_set_actions", decision.get("runner_executed") is False and decision.get("mt5_accessed") is False and decision.get("orders_placed") is False and decision.get("live_set_switched") is False, "action flags"),
    ]
    failures = [row for row in checks if not row["passed"]]
    review_decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_p1_manual_template_fill_dry_run_review",
        "status": "pass_p1_manual_dry_run_live_blocked" if not failures else "fail_p1_manual_dry_run_review",
        "review_completed": True,
        "p1_manual_items": len(expected),
        "dry_run_files_reviewed": len(manifest_rows),
        "json_files": sum(1 for row in manifest_rows if row.get("file_kind") == "json"),
        "csv_files": sum(1 for row in manifest_rows if row.get("file_kind") == "csv"),
        "required_fields_total": sum(len(split_fields(row.get("required_fields", ""))) for row in manifest_rows),
        "ready_to_live_trade": False,
        "blocker_failure_count": len(failures),
        "recommended_next_action": "draft_p1_rehearsal_prerequisite_dry_run" if not failures else "fix_p1_manual_dry_run",
    }

    write_csv(OUT_DIR / "p1_manual_template_fill_dry_run_review_checks.csv", checks, ["check_id", "passed", "severity", "detail"])
    write_csv(OUT_DIR / "p1_manual_template_fill_dry_run_review_decision.csv", [review_decision], list(review_decision.keys()))
    write_json(OUT_DIR / "p1_manual_template_fill_dry_run_review_decision.json", review_decision)
    lines = [
        "# P1 Manual Template Fill Dry Run Review",
        "",
        "## Decision",
        "",
        f"- status: `{review_decision['status']}`",
        f"- p1_manual_items: `{review_decision['p1_manual_items']}`",
        f"- dry_run_files_reviewed: `{review_decision['dry_run_files_reviewed']}`",
        f"- blocker_failure_count: `{review_decision['blocker_failure_count']}`",
        f"- ready_to_live_trade: `{review_decision['ready_to_live_trade']}`",
        "",
        "## Checks",
        "",
    ]
    for row in checks:
        lines.append(f"- `{row['check_id']}`: `{row['passed']}` - {row['detail']}")
    lines.append("")
    (OUT_DIR / "p1_manual_template_fill_dry_run_review.md").write_text("\n".join(lines), encoding="utf-8-sig")

    for key, value in review_decision.items():
        print(f"{key}={value}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
