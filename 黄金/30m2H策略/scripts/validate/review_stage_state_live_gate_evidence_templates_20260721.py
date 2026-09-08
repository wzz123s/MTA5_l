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
TEMPLATE_DIR = VALIDATION_DIR / "stage_state_live_gate_evidence_templates_20260721"
OUT_DIR = VALIDATION_DIR / "stage_state_live_gate_evidence_templates_review_20260721"

INDEX = TEMPLATE_DIR / "live_gate_evidence_index.csv"
SCHEMA = TEMPLATE_DIR / "live_gate_evidence_schema.csv"
GEN_DECISION = TEMPLATE_DIR / "live_gate_evidence_templates_decision.json"
CHECKLIST_DECISION = VALIDATION_DIR / "stage_state_live_trade_gate_checklist_draft_20260720" / "live_trade_gate_checklist_draft_decision.json"
DRAFT_REVIEW_DECISION = VALIDATION_DIR / "stage_state_live_trade_gate_draft_review_20260720" / "live_trade_gate_draft_review_decision.json"
STOP_FLAG = ROOT / "auto_trade" / "RUNNER_STOP.flag"

EXPECTED_GAPS = {
    "LIVE-GAP-001",
    "LIVE-GAP-002",
    "LIVE-GAP-003",
    "LIVE-GAP-004",
    "LIVE-GAP-005",
    "LIVE-GAP-006",
    "LIVE-GAP-007",
    "LIVE-GAP-008",
    "LIVE-GAP-009",
    "LIVE-GAP-010",
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


def file_text(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="ignore")
    return data.decode("utf-8-sig", errors="ignore")


def suspicious_secret_hits(path: Path) -> List[str]:
    text = file_text(path)
    hits: List[str] = []
    patterns = {
        "password_assignment": re.compile(r"(?i)\bpassword\b\s*[:=]\s*['\"]?(?!TEMPLATE_PLACEHOLDER|PENDING|false|true|none|null)[^'\"\s,}]+"),
        "account_number": re.compile(r"(?i)\b(account|login)\b\s*[:=]\s*['\"]?\d{5,}"),
        "api_key": re.compile(r"(?i)\b(api[_-]?key|token|secret)\b\s*[:=]\s*['\"]?(?!TEMPLATE_PLACEHOLDER|PENDING|false|true|none|null)[A-Za-z0-9_\-]{16,}"),
    }
    for label, pattern in patterns.items():
        if pattern.search(text):
            hits.append(label)
    return hits


def build_report(decision: Dict[str, object], checks: List[Dict[str, object]]) -> str:
    failed = [row for row in checks if row["status"] != "pass"]
    lines = [
        "# Live Gate Evidence Templates Review",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- review_completed: `{decision['review_completed']}`",
        f"- gate_count: `{decision['gate_count']}`",
        f"- evidence_template_count: `{decision['evidence_template_count']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        f"- open_gate_count: `{decision['open_gate_count']}`",
        f"- blocker_failure_count: `{decision['blocker_failure_count']}`",
        f"- suspicious_secret_hit_count: `{decision['suspicious_secret_hit_count']}`",
        "",
        "## Boundary",
        "",
        "- Templates remain open and template-only.",
        "- This review does not close any gate.",
        "- This review does not enable live trading.",
        "- This review does not change `InpSimMode`.",
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
    index_rows = read_rows(INDEX)
    schema_rows = read_rows(SCHEMA)
    gen_decision = read_json(GEN_DECISION)
    checklist_decision = read_json(CHECKLIST_DECISION)
    draft_review_decision = read_json(DRAFT_REVIEW_DECISION)

    gap_ids = {row.get("gap_id", "") for row in index_rows}
    open_rows = [row for row in index_rows if row.get("gate_status") == "open"]
    template_only_rows = [row for row in index_rows if row.get("template_status") == "template_only"]
    files_missing: List[str] = []
    secret_hits: List[str] = []
    for row in index_rows:
        path = TEMPLATE_DIR / row.get("relative_path", "")
        if not path.exists():
            files_missing.append(str(path))
            continue
        hits = suspicious_secret_hits(path)
        if hits:
            secret_hits.append(f"{path.name}:{';'.join(hits)}")

    checks: List[Dict[str, object]] = []
    add_check(checks, "index_exists", INDEX.exists(), INDEX, "exists")
    add_check(checks, "schema_exists", SCHEMA.exists(), SCHEMA, "exists")
    add_check(checks, "generation_status_templates_generated", gen_decision.get("status") == "templates_generated", gen_decision.get("status"), "templates_generated")
    add_check(checks, "checklist_draft_complete", checklist_decision.get("status") == "draft_complete", checklist_decision.get("status"), "draft_complete")
    add_check(checks, "draft_review_live_blocked", draft_review_decision.get("status") == "draft_review_pass_live_blocked", draft_review_decision.get("status"), "draft_review_pass_live_blocked")
    add_check(checks, "expected_gap_ids_present", gap_ids == EXPECTED_GAPS, ";".join(sorted(gap_ids)), ";".join(sorted(EXPECTED_GAPS)))
    add_check(checks, "gate_count_10", len(gap_ids) == 10, len(gap_ids), 10)
    add_check(checks, "evidence_template_count_22", len(index_rows) == 22, len(index_rows), 22)
    add_check(checks, "schema_rows_match_index", len(schema_rows) == len(index_rows), len(schema_rows), len(index_rows))
    add_check(checks, "all_templates_exist", not files_missing, ";".join(files_missing), "no missing files")
    add_check(checks, "all_templates_template_only", len(template_only_rows) == len(index_rows), len(template_only_rows), len(index_rows))
    add_check(checks, "all_gates_open", len(open_rows) == len(index_rows), len(open_rows), len(index_rows))
    add_check(checks, "no_suspicious_secret_hits", not secret_hits, ";".join(secret_hits), "no suspicious secret hits")
    add_check(checks, "stop_flag_absent", not STOP_FLAG.exists(), STOP_FLAG, "absent")
    add_check(checks, "ready_to_live_trade_false", gen_decision.get("ready_to_live_trade") is False, gen_decision.get("ready_to_live_trade"), False)

    blocker_failures = [row for row in checks if row["status"] == "fail" and row["severity"] == "blocker"]
    review_pass = not blocker_failures
    decision = {
        "decision_time": datetime.now().isoformat(timespec="seconds"),
        "check_id": "stage_state_live_gate_evidence_templates_review",
        "status": "pass_templates_open_live_blocked" if review_pass else "fail",
        "review_completed": review_pass,
        "gate_count": len(gap_ids),
        "evidence_template_count": len(index_rows),
        "open_gate_count": len(open_rows),
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "suspicious_secret_hit_count": len(secret_hits),
        "index_path": str(INDEX),
        "recommended_next_action": "fill_evidence_values_only_after_manual_approval_plan",
    }

    write_csv(
        OUT_DIR / "live_gate_evidence_templates_review_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(OUT_DIR / "live_gate_evidence_templates_review_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "live_gate_evidence_templates_review_decision.json", decision)
    (OUT_DIR / "live_gate_evidence_templates_review.md").write_text(build_report(decision, checks), encoding="utf-8-sig")

    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0 if review_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
