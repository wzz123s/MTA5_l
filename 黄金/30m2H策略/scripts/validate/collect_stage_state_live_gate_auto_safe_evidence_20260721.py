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
OUT_DIR = VALIDATION_DIR / "stage_state_live_gate_auto_safe_evidence_20260721"

FILL_PLAN = FILL_PLAN_DIR / "live_gate_evidence_fill_plan.csv"
AUTO_TRADE = ROOT / "auto_trade"
AUTO_TRADER = AUTO_TRADE / "auto_trader.py"
VERIFY_CONNECTION = AUTO_TRADE / "verify_connection.py"
SIGNAL_VALIDATOR = AUTO_TRADE / "signal_validator.py"
ENV_EXAMPLE = AUTO_TRADE / ".env.example"
MAIN_EA = AUTO_TRADE / "30m2H_Strategy_EA.mq5"
SIM_ONLY_EA = AUTO_TRADE / "30m2H_Strategy_EA_SIM_ONLY.mq5"


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="ignore")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def credential_patterns(text: str) -> Dict[str, bool]:
    return {
        "hardcoded_account_pattern": bool(re.search(r"['\"]account['\"]\s*:\s*\d+", text, re.IGNORECASE)),
        "hardcoded_password_pattern": bool(re.search(r"['\"]password['\"]\s*:\s*['\"][^'\"]+['\"]", text, re.IGNORECASE)),
        "mt5_login_pattern": bool(re.search(r"\blogin\s*=\s*CONFIG\[['\"]account['\"]\]", text, re.IGNORECASE)),
        "api_token_pattern": bool(re.search(r"(?i)\b(api[_-]?key|token|secret)\b\s*[:=]\s*['\"]?(?!TEMPLATE|PENDING|false|true|none|null)[A-Za-z0-9_\-]{16,}", text)),
    }


def collect_credential_scan(reviewed_at: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for path in [AUTO_TRADER, VERIFY_CONNECTION, SIGNAL_VALIDATOR, ENV_EXAMPLE]:
        text = read_text(path)
        patterns = credential_patterns(text)
        rows.append(
            {
                "path": rel(path),
                "scan_status": "scanned" if path.exists() else "missing",
                "hardcoded_account_pattern": patterns["hardcoded_account_pattern"],
                "hardcoded_password_pattern": patterns["hardcoded_password_pattern"],
                "mt5_login_pattern": patterns["mt5_login_pattern"],
                "api_token_pattern": patterns["api_token_pattern"],
                "values_redacted": True,
                "reviewed_at": reviewed_at,
            }
        )
    return rows


def marker_count(text: str, markers: List[str]) -> int:
    return sum(1 for marker in markers if marker in text)


def collect_runner_source_audit(reviewed_at: str) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    current_strategy_markers = [
        "InpUseLayer3",
        "InpUseM15EarlyEntry",
        "InpEnableM15Slot2",
        "InpExportTradeLedger",
        "InpSimMode",
        "stage_state",
    ]
    sources = [
        (AUTO_TRADER, False, "blocked_python_runner_not_approved_for_live"),
        (VERIFY_CONNECTION, False, "utility_contains_connection_logic_not_live_runner"),
        (SIGNAL_VALIDATOR, False, "utility_not_live_runner"),
        (MAIN_EA, False, "main_ea_exists_but_live_package_not_approved"),
        (SIM_ONLY_EA, False, "sim_only_ea_monitoring_only_not_live_runner"),
    ]
    for path, allowed, reason in sources:
        text = read_text(path)
        rows.append(
            {
                "runner_path": rel(path),
                "allowed": allowed,
                "reason": reason,
                "reviewed_by": "codex_static_audit",
                "reviewed_at": reviewed_at,
                "executed": False,
                "exists": path.exists(),
                "current_marker_count": marker_count(text, current_strategy_markers),
                "contains_order_send_marker": "OrderSend" in text or ".Buy(" in text or ".Sell(" in text,
            }
        )
    return rows


def build_auto_plan(fill_rows: List[Dict[str, str]], reviewed_at: str) -> List[Dict[str, object]]:
    out: List[Dict[str, object]] = []
    for row in fill_rows:
        if row.get("collection_method") != "auto":
            continue
        file_name = row["file_name"]
        if file_name == "credential_scan_report.csv":
            status = "collected"
            note = "Static scan collected with values redacted."
        elif file_name == "runner_source_audit.csv":
            status = "collected"
            note = "Static source audit collected; no runner executed."
        else:
            status = "pending_manual_prerequisite"
            note = "Skipped by auto-safe policy; requires live package/live set/broker-spec approval first."
        out.append(
            {
                "gap_id": row["gap_id"],
                "file_name": file_name,
                "collection_method": row["collection_method"],
                "auto_safe_status": status,
                "contains_secret_risk": row["contains_secret_risk"],
                "live_action_risk": row["live_action_risk"],
                "requires_user_approval": row["requires_user_approval"],
                "reviewed_at": reviewed_at,
                "note": note,
                "gate_status": "open",
                "ready_to_live_trade": False,
            }
        )
    return out


def build_report(decision: Dict[str, object], auto_plan: List[Dict[str, object]]) -> str:
    lines = [
        "# Live Gate Auto-safe Evidence Collection",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- auto_items_total: `{decision['auto_items_total']}`",
        f"- auto_items_collected: `{decision['auto_items_collected']}`",
        f"- auto_items_pending: `{decision['auto_items_pending']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        f"- credential_values_output: `{decision['credential_values_output']}`",
        f"- runner_executed: `{decision['runner_executed']}`",
        "",
        "## Boundary",
        "",
        "- Only credential scan and runner source audit were collected.",
        "- Credential values are not output.",
        "- Runner files are not executed.",
        "- Live package, live set parsing, and broker spec collection remain pending.",
        "",
        "## Auto Items",
        "",
    ]
    for row in auto_plan:
        lines.append(f"- `{row['file_name']}`: `{row['auto_safe_status']}` - {row['note']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    fill_rows = read_rows(FILL_PLAN)
    auto_plan = build_auto_plan(fill_rows, reviewed_at)
    credential_rows = collect_credential_scan(reviewed_at)
    runner_rows = collect_runner_source_audit(reviewed_at)

    collected_count = sum(1 for row in auto_plan if row["auto_safe_status"] == "collected")
    pending_count = sum(1 for row in auto_plan if row["auto_safe_status"] != "collected")
    credential_pattern_file_count = sum(
        1
        for row in credential_rows
        if row["hardcoded_account_pattern"] or row["hardcoded_password_pattern"] or row["mt5_login_pattern"] or row["api_token_pattern"]
    )
    blocked_runner_count = sum(1 for row in runner_rows if row["allowed"] is False)
    decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_live_gate_auto_safe_evidence",
        "status": "auto_safe_evidence_collected_live_blocked",
        "auto_items_total": len(auto_plan),
        "auto_items_collected": collected_count,
        "auto_items_pending": pending_count,
        "credential_scan_rows": len(credential_rows),
        "credential_pattern_file_count": credential_pattern_file_count,
        "runner_source_audit_rows": len(runner_rows),
        "blocked_runner_count": blocked_runner_count,
        "credential_values_output": False,
        "runner_executed": False,
        "gate_status": "open",
        "ready_to_live_trade": False,
        "recommended_next_action": "review_auto_safe_evidence_outputs",
    }

    write_csv(
        OUT_DIR / "auto_safe_evidence_collection_plan.csv",
        auto_plan,
        [
            "gap_id",
            "file_name",
            "collection_method",
            "auto_safe_status",
            "contains_secret_risk",
            "live_action_risk",
            "requires_user_approval",
            "reviewed_at",
            "note",
            "gate_status",
            "ready_to_live_trade",
        ],
    )
    write_csv(
        OUT_DIR / "credential_scan_report.csv",
        credential_rows,
        [
            "path",
            "scan_status",
            "hardcoded_account_pattern",
            "hardcoded_password_pattern",
            "mt5_login_pattern",
            "api_token_pattern",
            "values_redacted",
            "reviewed_at",
        ],
    )
    write_csv(
        OUT_DIR / "runner_source_audit.csv",
        runner_rows,
        [
            "runner_path",
            "allowed",
            "reason",
            "reviewed_by",
            "reviewed_at",
            "executed",
            "exists",
            "current_marker_count",
            "contains_order_send_marker",
        ],
    )
    write_json(OUT_DIR / "auto_safe_evidence_collection_decision.json", decision)
    write_csv(OUT_DIR / "auto_safe_evidence_collection_decision.csv", [decision], list(decision.keys()))
    (OUT_DIR / "auto_safe_evidence_collection.md").write_text(build_report(decision, auto_plan), encoding="utf-8-sig")

    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
