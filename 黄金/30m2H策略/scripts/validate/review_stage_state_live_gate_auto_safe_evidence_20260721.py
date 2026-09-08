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
COLLECT_DIR = VALIDATION_DIR / "stage_state_live_gate_auto_safe_evidence_20260721"
OUT_DIR = VALIDATION_DIR / "stage_state_live_gate_auto_safe_evidence_review_20260721"

DECISION = COLLECT_DIR / "auto_safe_evidence_collection_decision.json"
PLAN = COLLECT_DIR / "auto_safe_evidence_collection_plan.csv"
CREDENTIAL_REPORT = COLLECT_DIR / "credential_scan_report.csv"
RUNNER_AUDIT = COLLECT_DIR / "runner_source_audit.csv"
STOP_FLAG = ROOT / "auto_trade" / "RUNNER_STOP.flag"


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


def output_secret_hit(path: Path) -> List[str]:
    text = path.read_text(encoding="utf-8-sig", errors="ignore") if path.exists() else ""
    hits: List[str] = []
    patterns = {
        "password_value": re.compile(r"(?i)\bpassword\b\s*[,=:]\s*['\"]?(?!True|False|TEMPLATE|PENDING|redacted|values_redacted)[^,'\"\r\n]+"),
        "account_value": re.compile(r"(?i)\baccount\b\s*[,=:]\s*['\"]?\d{5,}"),
        "token_value": re.compile(r"(?i)\b(api[_-]?key|token|secret)\b\s*[,=:]\s*['\"]?(?!True|False|TEMPLATE|PENDING|redacted)[A-Za-z0-9_\-]{16,}"),
    }
    for label, pattern in patterns.items():
        if pattern.search(text):
            hits.append(label)
    return hits


def build_report(decision: Dict[str, object], checks: List[Dict[str, object]]) -> str:
    failed = [row for row in checks if row["status"] != "pass"]
    lines = [
        "# Live Gate Auto-safe Evidence Review",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- review_completed: `{decision['review_completed']}`",
        f"- auto_items_total: `{decision['auto_items_total']}`",
        f"- auto_items_collected: `{decision['auto_items_collected']}`",
        f"- auto_items_pending: `{decision['auto_items_pending']}`",
        f"- credential_pattern_file_count: `{decision['credential_pattern_file_count']}`",
        f"- runner_executed: `{decision['runner_executed']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        f"- blocker_failure_count: `{decision['blocker_failure_count']}`",
        "",
        "## Boundary",
        "",
        "- Credential report contains pattern booleans only, not values.",
        "- Runner source audit is static only.",
        "- Live package hash, live set parsing, and broker symbol spec remain pending.",
        "- No live gate is closed.",
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
    decision = read_json(DECISION)
    plan_rows = read_rows(PLAN)
    credential_rows = read_rows(CREDENTIAL_REPORT)
    runner_rows = read_rows(RUNNER_AUDIT)

    collected = [row for row in plan_rows if row.get("auto_safe_status") == "collected"]
    pending = [row for row in plan_rows if row.get("auto_safe_status") != "collected"]
    collected_files = {row.get("file_name", "") for row in collected}
    pending_files = {row.get("file_name", "") for row in pending}
    credential_secret_hits = output_secret_hit(CREDENTIAL_REPORT)
    runner_secret_hits = output_secret_hit(RUNNER_AUDIT)
    credential_pattern_count = sum(
        1
        for row in credential_rows
        if truthy(row.get("hardcoded_account_pattern"))
        or truthy(row.get("hardcoded_password_pattern"))
        or truthy(row.get("mt5_login_pattern"))
        or truthy(row.get("api_token_pattern"))
    )

    checks: List[Dict[str, object]] = []
    add_check(checks, "collection_decision_exists", DECISION.exists(), DECISION, "exists")
    add_check(checks, "collection_status_expected", decision.get("status") == "auto_safe_evidence_collected_live_blocked", decision.get("status"), "auto_safe_evidence_collected_live_blocked")
    add_check(checks, "auto_items_total_5", len(plan_rows) == 5, len(plan_rows), 5)
    add_check(checks, "auto_items_collected_2", len(collected) == 2, len(collected), 2)
    add_check(checks, "auto_items_pending_3", len(pending) == 3, len(pending), 3)
    add_check(checks, "collected_files_expected", collected_files == {"credential_scan_report.csv", "runner_source_audit.csv"}, ";".join(sorted(collected_files)), "credential_scan_report.csv;runner_source_audit.csv")
    add_check(checks, "pending_files_expected", pending_files == {"live_package_hashes.csv", "parsed_live_set_template.json", "broker_symbol_spec.csv"}, ";".join(sorted(pending_files)), "broker_symbol_spec.csv;live_package_hashes.csv;parsed_live_set_template.json")
    add_check(checks, "credential_report_exists", CREDENTIAL_REPORT.exists(), CREDENTIAL_REPORT, "exists")
    add_check(checks, "credential_report_rows_4", len(credential_rows) == 4, len(credential_rows), 4)
    add_check(checks, "credential_values_redacted", all(truthy(row.get("values_redacted")) for row in credential_rows), "all redacted", "all redacted")
    add_check(checks, "credential_pattern_count_3_or_more", credential_pattern_count >= 3, credential_pattern_count, ">= 3")
    add_check(checks, "credential_output_has_no_values", not credential_secret_hits, ";".join(credential_secret_hits), "no secret values in output")
    add_check(checks, "runner_audit_exists", RUNNER_AUDIT.exists(), RUNNER_AUDIT, "exists")
    add_check(checks, "runner_audit_rows_5", len(runner_rows) == 5, len(runner_rows), 5)
    add_check(checks, "runner_not_executed", all(not truthy(row.get("executed")) for row in runner_rows), "all false", "all false")
    add_check(checks, "runner_all_not_allowed", all(not truthy(row.get("allowed")) for row in runner_rows), "all false", "all false")
    add_check(checks, "runner_output_has_no_values", not runner_secret_hits, ";".join(runner_secret_hits), "no secret values in output")
    add_check(checks, "all_gates_open", all(row.get("gate_status") == "open" for row in plan_rows), "all open", "all open")
    add_check(checks, "all_ready_to_live_trade_false", all(not truthy(row.get("ready_to_live_trade")) for row in plan_rows), "all false", "all false")
    add_check(checks, "stop_flag_absent", not STOP_FLAG.exists(), STOP_FLAG, "absent")

    blocker_failures = [row for row in checks if row["status"] == "fail" and row["severity"] == "blocker"]
    review_pass = not blocker_failures
    review_decision = {
        "decision_time": datetime.now().isoformat(timespec="seconds"),
        "check_id": "stage_state_live_gate_auto_safe_evidence_review",
        "status": "pass_auto_safe_evidence_live_blocked" if review_pass else "fail",
        "review_completed": review_pass,
        "auto_items_total": len(plan_rows),
        "auto_items_collected": len(collected),
        "auto_items_pending": len(pending),
        "credential_pattern_file_count": credential_pattern_count,
        "runner_executed": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "recommended_next_action": "manual_evidence_prerequisite_plan_or_continue_sim_only_monitoring",
    }

    write_csv(
        OUT_DIR / "auto_safe_evidence_review_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(OUT_DIR / "auto_safe_evidence_review_decision.csv", [review_decision], list(review_decision.keys()))
    write_json(OUT_DIR / "auto_safe_evidence_review_decision.json", review_decision)
    (OUT_DIR / "auto_safe_evidence_review.md").write_text(build_report(review_decision, checks), encoding="utf-8-sig")

    print(json.dumps(review_decision, ensure_ascii=False, indent=2))
    return 0 if review_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
