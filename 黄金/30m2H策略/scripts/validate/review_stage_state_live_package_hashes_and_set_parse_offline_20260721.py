from __future__ import annotations


import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
COLLECT_DIR = VALIDATION_DIR / "stage_state_live_package_hashes_and_set_parse_offline_20260721"
OUT_DIR = VALIDATION_DIR / "stage_state_live_package_hashes_and_set_parse_offline_review_20260721"

HASH_CSV = COLLECT_DIR / "live_package_hashes.csv"
PARSED_SET_JSON = COLLECT_DIR / "parsed_live_set_template.json"
DECISION_JSON = COLLECT_DIR / "live_package_hashes_and_set_parse_offline_decision.json"
HASH_APPROVAL = "USER_APPROVES_HASHING_REVIEWED_LIVE_PACKAGE_MANIFEST_ONLY"
SET_APPROVAL = "USER_APPROVES_OFFLINE_PARSE_REVIEWED_SET_TEMPLATE_ONLY"


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


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check(check_id: str, passed: bool, detail: str, severity: str = "critical") -> Dict[str, object]:
    return {"check_id": check_id, "passed": passed, "severity": severity, "detail": detail}


def workspace_path(relative_path: str) -> Path:
    return ROOT / relative_path


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    hash_rows = read_rows(HASH_CSV)
    parsed_set = read_json(PARSED_SET_JSON)
    decision = read_json(DECISION_JSON)
    hash_mismatches = []
    for row in hash_rows:
        path = workspace_path(row["path"])
        if not path.exists() or sha256(path) != row["sha256"]:
            hash_mismatches.append(row["path"])
    no_actions = (
        decision.get("mt5_accessed") is False
        and decision.get("runner_executed") is False
        and decision.get("orders_placed") is False
        and decision.get("live_set_switched") is False
        and all(not boolish(row.get("mt5_accessed")) for row in hash_rows)
        and all(not boolish(row.get("runner_executed")) for row in hash_rows)
        and all(not boolish(row.get("orders_placed")) for row in hash_rows)
        and all(not boolish(row.get("live_set_switched")) for row in hash_rows)
        and parsed_set.get("mt5_accessed") is False
        and parsed_set.get("runner_executed") is False
        and parsed_set.get("orders_placed") is False
        and parsed_set.get("live_set_switched") is False
    )
    checks = [
        check("decision_status_collected", decision.get("status") == "live_package_hashes_and_set_parse_collected_offline_live_blocked", str(decision.get("status"))),
        check("hash_rows_are_2", len(hash_rows) == 2 and decision.get("hash_rows") == 2, f"rows={len(hash_rows)}"),
        check("hashes_match_files", not hash_mismatches, f"mismatches={hash_mismatches}"),
        check("hash_approval_present", all(row.get("approval_phrase") == HASH_APPROVAL for row in hash_rows), "hash approval phrase"),
        check("parsed_set_required_fields_present", all(str(parsed_set.get(field, "")).strip() for field in ["set_path", "InpSimMode", "InpExportCSV", "InpExportTradeLedger"]), "parsed set fields"),
        check("set_approval_present", parsed_set.get("approval_phrase") == SET_APPROVAL, "set approval phrase"),
        check("set_parse_is_offline", parsed_set.get("collection_mode") == "offline_set_text_parse", str(parsed_set.get("collection_mode"))),
        check("inp_sim_mode_false_captured", parsed_set.get("InpSimMode") == "false" and decision.get("InpSimMode") == "false", f"InpSimMode={parsed_set.get('InpSimMode')}"),
        check("export_flags_true", parsed_set.get("InpExportCSV") == "true" and parsed_set.get("InpExportTradeLedger") == "true", "export flags"),
        check("no_mt5_runner_order_live_set_actions", no_actions, "action flags"),
        check("ready_to_live_trade_false", parsed_set.get("ready_to_live_trade") is False and decision.get("ready_to_live_trade") is False, "ready flags"),
    ]
    failures = [row for row in checks if not row["passed"]]
    review_decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_live_package_hashes_and_set_parse_offline_review",
        "status": "pass_live_package_hashes_and_set_parse_offline_live_blocked" if not failures else "fail_live_package_hashes_and_set_parse_offline_review",
        "review_completed": True,
        "hash_rows": len(hash_rows),
        "set_parse_collected": True,
        "InpSimMode": parsed_set.get("InpSimMode", ""),
        "ready_to_live_trade": False,
        "blocker_failure_count": len(failures),
        "recommended_next_action": "update_final_closeout_after_all_pending_auto_collected" if not failures else "fix_offline_hash_or_set_parse",
    }
    write_csv(OUT_DIR / "live_package_hashes_and_set_parse_offline_review_checks.csv", checks, ["check_id", "passed", "severity", "detail"])
    write_csv(OUT_DIR / "live_package_hashes_and_set_parse_offline_review_decision.csv", [review_decision], list(review_decision.keys()))
    write_json(OUT_DIR / "live_package_hashes_and_set_parse_offline_review_decision.json", review_decision)
    lines = [
        "# Live Package Hashes And Set Parse Offline Review",
        "",
        "## Decision",
        "",
        f"- status: `{review_decision['status']}`",
        f"- hash_rows: `{review_decision['hash_rows']}`",
        f"- InpSimMode: `{review_decision['InpSimMode']}`",
        f"- blocker_failure_count: `{review_decision['blocker_failure_count']}`",
        f"- ready_to_live_trade: `{review_decision['ready_to_live_trade']}`",
        "",
        "## Checks",
        "",
    ]
    for row in checks:
        lines.append(f"- `{row['check_id']}`: `{row['passed']}` - {row['detail']}")
    lines.append("")
    (OUT_DIR / "live_package_hashes_and_set_parse_offline_review.md").write_text("\n".join(lines), encoding="utf-8-sig")
    for key, value in review_decision.items():
        print(f"{key}={value}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
