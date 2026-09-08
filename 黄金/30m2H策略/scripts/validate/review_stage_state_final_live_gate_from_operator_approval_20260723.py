from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_final_live_gate_review_from_operator_approval_20260723"

APPROVAL_TEMPLATE_JSON = (
    VALIDATION_DIR
    / "stage_state_final_live_approval_package_draft_20260723"
    / "final_live_operator_approval_template.json"
)
GATE_STATUS_CSV = (
    VALIDATION_DIR
    / "stage_state_post_monitoring_manual_confirmation_gate_update_20260723"
    / "post_monitoring_manual_confirmation_gate_update.csv"
)
SIGNOFF_REQUIREMENTS_CSV = (
    VALIDATION_DIR
    / "stage_state_final_live_approval_package_draft_20260723"
    / "final_live_signoff_requirements.csv"
)
EMERGENCY_STOP_FLAG = ROOT / "auto_trade" / "EMERGENCY_STOP.flag"
RUNNER_STOP_FLAG = ROOT / "auto_trade" / "RUNNER_STOP.flag"


GATE_APPROVAL_KEYS = {
    "LIVE-GAP-001": ["LIVE-GAP-001_live_trading_approval"],
    "LIVE-GAP-002": ["LIVE-GAP-002_live_package_manifest_release_approval"],
    "LIVE-GAP-003": ["LIVE-GAP-003_InpSimMode_false_loading_approval"],
    "LIVE-GAP-004": ["LIVE-GAP-004_secret_externalization_approval"],
    "LIVE-GAP-005": ["LIVE-GAP-005_MT5_EA_only_order_path_approval"],
    "LIVE-GAP-006": ["LIVE-GAP-006_live_risk_policy_approval"],
    "LIVE-GAP-007": [
        "LIVE-GAP-001_live_trading_approval",
        "LIVE-GAP-008_watched_alert_channel_confirmed",
        "LIVE-GAP-008_operator_reconciliation_confirmed",
        "LIVE-GAP-010_nonprod_rehearsal_alert_emergency_acceptance",
    ],
    "LIVE-GAP-008": [
        "LIVE-GAP-008_watched_alert_channel_confirmed",
        "LIVE-GAP-008_operator_reconciliation_confirmed",
    ],
    "LIVE-GAP-009": ["LIVE-GAP-009_account_spec_intended_context_confirmed"],
    "LIVE-GAP-010": [
        "LIVE-GAP-008_watched_alert_channel_confirmed",
        "LIVE-GAP-008_operator_reconciliation_confirmed",
        "LIVE-GAP-010_nonprod_rehearsal_alert_emergency_acceptance",
    ],
}

APPROVAL_ONLY_GATES = {
    "LIVE-GAP-001",
    "LIVE-GAP-002",
    "LIVE-GAP-003",
    "LIVE-GAP-004",
    "LIVE-GAP-005",
}


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
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def check_row(
    check_id: str,
    passed: bool,
    actual: object,
    expected: object,
    severity: str = "blocker",
    note: str = "",
) -> Dict[str, object]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "pass": passed,
        "actual": actual,
        "expected": expected,
        "severity": severity,
        "note": note,
    }


def all_keys_true(approval_items: Dict[str, object], keys: List[str]) -> bool:
    return all(boolish(approval_items.get(key)) for key in keys)


def row_status(row: Dict[str, str]) -> str:
    for key in [
        "current_status",
        "post_monitoring_manual_confirmation_status",
        "post_autotrading_disable_status",
        "post_account_spec_status",
        "post_monitoring_reconciliation_status",
    ]:
        value = row.get(key, "")
        if value:
            return value
    return ""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviewed_at = datetime.now().isoformat(timespec="seconds")

    approval = read_json(APPROVAL_TEMPLATE_JSON)
    gate_rows = read_rows(GATE_STATUS_CSV)
    signoff_rows = read_rows(SIGNOFF_REQUIREMENTS_CSV)
    approval_items = approval.get("approval_items", {})
    if not isinstance(approval_items, dict):
        approval_items = {}

    operator_alias = str(approval.get("operator_alias", "")).strip()
    operator_alias_ready = bool(operator_alias and operator_alias != "manual_pending")
    signed_approval_keys = [key for key, value in approval_items.items() if boolish(value)]
    required_approval_keys = sorted({key for keys in GATE_APPROVAL_KEYS.values() for key in keys})

    gate_review_rows: List[Dict[str, object]] = []
    for row in gate_rows:
        gap_id = row.get("gap_id", "")
        required_keys = GATE_APPROVAL_KEYS.get(gap_id, [])
        approvals_passed = all_keys_true(approval_items, required_keys)
        prior_status = row_status(row)
        technical_ready = (
            gap_id in APPROVAL_ONLY_GATES
            or prior_status.startswith("partially_satisfied")
            or prior_status == "closed"
        )
        can_close = technical_ready and approvals_passed and operator_alias_ready
        if can_close:
            review_status = "closed_by_operator_approval_evidence"
            remaining_blocker = ""
        else:
            review_status = "blocked_pending_operator_approval_or_technical_evidence"
            missing_keys = [key for key in required_keys if not boolish(approval_items.get(key))]
            blockers = []
            if not technical_ready:
                blockers.append("technical evidence is not ready")
            if missing_keys:
                blockers.append("missing approval keys: " + ",".join(missing_keys))
            if not operator_alias_ready:
                blockers.append("operator_alias is manual_pending or empty")
            remaining_blocker = "; ".join(blockers)

        gate_review_rows.append(
            {
                "review_time": reviewed_at,
                "gap_id": gap_id,
                "priority": row.get("priority", ""),
                "category": row.get("category", ""),
                "severity": row.get("severity", ""),
                "gate_item": row.get("gate_item", ""),
                "prior_status": prior_status,
                "required_approval_keys": ",".join(required_keys),
                "approvals_passed": approvals_passed,
                "operator_alias_ready": operator_alias_ready,
                "final_gate_review_status": review_status,
                "remaining_blocker": remaining_blocker,
                "ready_to_live_trade": False,
            }
        )

    closed_count = sum(1 for row in gate_review_rows if row["final_gate_review_status"] == "closed_by_operator_approval_evidence")
    blocked_count = len(gate_review_rows) - closed_count
    all_gates_closed_by_approval = blocked_count == 0
    stop_flags_present = EMERGENCY_STOP_FLAG.exists() or RUNNER_STOP_FLAG.exists()
    ready_for_live_loading_package = all_gates_closed_by_approval
    ready_to_live_trade = False

    checks = [
        check_row(
            "operator_alias_ready",
            operator_alias_ready,
            operator_alias,
            "non-secret operator alias other than manual_pending",
        ),
        check_row(
            "all_required_approval_keys_true",
            all(boolish(approval_items.get(key)) for key in required_approval_keys),
            len(signed_approval_keys),
            len(required_approval_keys),
        ),
        check_row(
            "all_gates_closed_by_approval",
            all_gates_closed_by_approval,
            closed_count,
            len(gate_review_rows),
        ),
        check_row(
            "stop_flags_still_present_fail_closed",
            stop_flags_present,
            stop_flags_present,
            True,
            "info",
            "Stop flags staying present is expected before explicit live loading approval.",
        ),
        check_row(
            "ready_to_live_trade_false",
            ready_to_live_trade is False,
            ready_to_live_trade,
            False,
            "blocker",
            "This review never enables trading or removes stop flags.",
        ),
    ]

    blocker_failures = [row for row in checks if row["severity"] == "blocker" and not row["pass"]]
    decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_final_live_gate_review_from_operator_approval",
        "status": (
            "final_live_gate_approval_preconditions_satisfied_loading_package_pending"
            if ready_for_live_loading_package
            else "final_live_gate_blocked_operator_approval_missing"
        ),
        "gate_count": len(gate_review_rows),
        "closed_gate_count": closed_count,
        "blocked_gate_count": blocked_count,
        "required_signoff_count": len(signoff_rows),
        "required_approval_boolean_count": len(required_approval_keys),
        "signed_approval_boolean_count": len(signed_approval_keys),
        "operator_alias_ready": operator_alias_ready,
        "stop_flags_present": stop_flags_present,
        "ready_for_live_loading_package": ready_for_live_loading_package,
        "ready_to_live_trade": ready_to_live_trade,
        "blocker_failure_count": len(blocker_failures),
        "recommended_next_action": (
            "complete_non_secret_operator_approval_template_then_rerun_this_review"
            if not ready_for_live_loading_package
            else "prepare_exact_mt5_ea_live_loading_package_keep_stop_flags_until_explicit_approval"
        ),
    }

    write_csv(
        OUT_DIR / "final_live_gate_review_from_operator_approval.csv",
        gate_review_rows,
        [
            "review_time",
            "gap_id",
            "priority",
            "category",
            "severity",
            "gate_item",
            "prior_status",
            "required_approval_keys",
            "approvals_passed",
            "operator_alias_ready",
            "final_gate_review_status",
            "remaining_blocker",
            "ready_to_live_trade",
        ],
    )
    write_csv(OUT_DIR / "final_live_gate_review_checks.csv", checks, list(checks[0].keys()))
    write_csv(OUT_DIR / "final_live_gate_review_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "final_live_gate_review_decision.json", decision)

    report = f"""# Final Live Gate Review From Operator Approval

Generated: {reviewed_at}

## Decision

- Status: `{decision["status"]}`
- Closed gates: `{closed_count}`
- Blocked gates: `{blocked_count}`
- Required signoffs: `{decision["required_signoff_count"]}`
- Required approval booleans: `{decision["required_approval_boolean_count"]}`
- Signed approval booleans: `{decision["signed_approval_boolean_count"]}`
- Operator alias ready: `{operator_alias_ready}`
- Stop flags present: `{stop_flags_present}`
- Ready for live loading package: `{ready_for_live_loading_package}`
- Ready to live trade: `false`

## Summary

This review is intentionally conservative. It can only move the process toward a live loading package after all non-secret operator approvals are present. It never removes stop flags, never loads the EA, and never enables trading.
"""
    (OUT_DIR / "final_live_gate_review_from_operator_approval.md").write_text(report, encoding="utf-8-sig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
