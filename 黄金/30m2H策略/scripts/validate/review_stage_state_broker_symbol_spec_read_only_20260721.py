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
COLLECT_DIR = VALIDATION_DIR / "stage_state_broker_symbol_spec_read_only_20260721"
OUT_DIR = VALIDATION_DIR / "stage_state_broker_symbol_spec_read_only_review_20260721"

SPEC_CSV = COLLECT_DIR / "broker_symbol_spec.csv"
DECISION_JSON = COLLECT_DIR / "broker_symbol_spec_read_only_decision.json"
SYMBOL = "XAUUSDm"
APPROVAL_PHRASE = "USER_APPROVES_READ_ONLY_MT5_SYMBOL_SPEC_QUERY_NO_ORDERS"


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
    chunks: List[str] = []
    for path in COLLECT_DIR.glob("broker_symbol_spec*"):
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".csv"}:
            chunks.append(path.read_text(encoding="utf-8-sig", errors="ignore"))
    return "\n".join(chunks)


def present(row: Dict[str, str], fields: List[str]) -> bool:
    return all(str(row.get(field, "")).strip() != "" for field in fields)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    decision = read_json(DECISION_JSON)
    spec_rows = read_rows(SPEC_CSV)
    first = spec_rows[0] if spec_rows else {}
    required_fields = ["symbol", "contract_size", "min_lot", "lot_step", "margin_initial", "digits", "spread_policy"]
    action_flags_false = (
        decision.get("orders_placed") is False
        and decision.get("runner_executed") is False
        and decision.get("live_set_switched") is False
        and all(not boolish(row.get("orders_placed")) for row in spec_rows)
        and all(not boolish(row.get("runner_executed")) for row in spec_rows)
        and all(not boolish(row.get("live_set_switched")) for row in spec_rows)
    )
    process_not_spawned = decision.get("terminal_spawned") is False and all(not boolish(row.get("terminal_spawned")) for row in spec_rows)
    checks = [
        check("decision_status_collected", decision.get("status") == "broker_symbol_spec_collected_read_only_live_blocked", str(decision.get("status"))),
        check("row_count_is_1", len(spec_rows) == 1 and decision.get("broker_symbol_spec_rows") == 1, f"rows={len(spec_rows)}"),
        check("symbol_is_expected", first.get("symbol") == SYMBOL and decision.get("symbol") == SYMBOL, f"symbol={first.get('symbol')}"),
        check("required_fields_present", present(first, required_fields), f"required={required_fields}"),
        check("approval_phrase_present", first.get("approval_phrase") == APPROVAL_PHRASE and decision.get("approval_phrase") == APPROVAL_PHRASE, "approval phrase"),
        check("read_only_collection_mode", first.get("collection_mode") == "read_only_symbol_info", first.get("collection_mode", "")),
        check("mt5_initialized_only_for_read", decision.get("mt5_initialized") is True and boolish(first.get("mt5_initialized")), "mt5 initialized flag"),
        check("terminal_process_not_spawned", process_not_spawned, f"before={decision.get('terminal_process_count_before')} after={decision.get('terminal_process_count_after')}"),
        check("no_runner_order_live_set_actions", action_flags_false, "action flags"),
        check("no_secret_assignments_in_outputs", not has_secret_assignment(output_text()), "secret assignment scan"),
        check("gate_status_open", first.get("gate_status") == "open" and decision.get("gate_status") == "open", "gate status"),
        check("ready_to_live_trade_false", not boolish(first.get("ready_to_live_trade")) and decision.get("ready_to_live_trade") is False, "ready flags"),
    ]
    failures = [row for row in checks if not row["passed"]]
    review_decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_broker_symbol_spec_read_only_review",
        "status": "pass_broker_symbol_spec_read_only_live_blocked" if not failures else "fail_broker_symbol_spec_read_only_review",
        "review_completed": True,
        "symbol": SYMBOL,
        "broker_symbol_spec_rows": len(spec_rows),
        "terminal_spawned": False,
        "orders_placed": False,
        "runner_executed": False,
        "live_set_switched": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(failures),
        "recommended_next_action": "update_closeout_remaining_pending_auto_items",
    }
    write_csv(OUT_DIR / "broker_symbol_spec_read_only_review_checks.csv", checks, ["check_id", "passed", "severity", "detail"])
    write_csv(OUT_DIR / "broker_symbol_spec_read_only_review_decision.csv", [review_decision], list(review_decision.keys()))
    write_json(OUT_DIR / "broker_symbol_spec_read_only_review_decision.json", review_decision)
    lines = [
        "# Broker Symbol Spec Read-only Review",
        "",
        "## Decision",
        "",
        f"- status: `{review_decision['status']}`",
        f"- symbol: `{review_decision['symbol']}`",
        f"- broker_symbol_spec_rows: `{review_decision['broker_symbol_spec_rows']}`",
        f"- blocker_failure_count: `{review_decision['blocker_failure_count']}`",
        f"- ready_to_live_trade: `{review_decision['ready_to_live_trade']}`",
        "",
        "## Checks",
        "",
    ]
    for row in checks:
        lines.append(f"- `{row['check_id']}`: `{row['passed']}` - {row['detail']}")
    lines.append("")
    (OUT_DIR / "broker_symbol_spec_read_only_review.md").write_text("\n".join(lines), encoding="utf-8-sig")
    for key, value in review_decision.items():
        print(f"{key}={value}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
