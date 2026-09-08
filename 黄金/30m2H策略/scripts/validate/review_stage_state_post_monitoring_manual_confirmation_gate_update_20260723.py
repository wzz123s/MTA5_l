from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_post_monitoring_manual_confirmation_gate_update_20260723"

POST_AUTOTRADING_CSV = (
    VALIDATION_DIR
    / "stage_state_post_autotrading_disable_gate_update_20260723"
    / "post_autotrading_disable_gate_update.csv"
)
CONFIRMATION_PACKAGE_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_live_monitoring_manual_confirmation_package_20260723"
    / "monitoring_manual_confirmation_package_decision.json"
)
CONFIRMATION_TEMPLATE_JSON = (
    VALIDATION_DIR
    / "stage_state_live_monitoring_manual_confirmation_package_20260723"
    / "watched_alert_operator_confirmation_template.json"
)


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


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviewed_at = datetime.now().isoformat(timespec="seconds")
    prior_rows = read_rows(POST_AUTOTRADING_CSV)
    package = read_json(CONFIRMATION_PACKAGE_DECISION_JSON)
    template = read_json(CONFIRMATION_TEMPLATE_JSON)

    watched_confirmed = template.get("watched_alert_channel_confirmed") is True
    reconciliation_confirmed = template.get("operator_reconciliation_confirmed") is True
    package_ready = package.get("status") == "manual_monitoring_confirmation_package_ready_not_confirmed"
    local_probe_ready = (
        package.get("monitoring_policy_ready") is True
        and package.get("local_alert_write_path_tested") is True
        and package.get("reconciliation_probe_passed") is True
    )

    updated_rows: List[Dict[str, object]] = []
    for row in prior_rows:
        status = row.get("post_autotrading_disable_status", "")
        evidence_delta = row.get("evidence_delta", "")
        remaining_blocker = row.get("remaining_blocker", "")
        if row.get("gap_id") == "LIVE-GAP-008":
            if watched_confirmed and reconciliation_confirmed and local_probe_ready:
                status = "partially_satisfied_policy_probe_and_manual_operator_confirmation_collected"
                evidence_delta = (
                    "monitoring policy, local alert probe, reconciliation probe, watched channel, and operator confirmation collected"
                )
                remaining_blocker = "final live approval package and broader live gates remain open"
            elif package_ready and local_probe_ready:
                status = "partially_satisfied_policy_probe_and_manual_confirmation_package_ready"
                evidence_delta = "monitoring policy, local alert probe, reconciliation probe, and manual confirmation package are ready"
                remaining_blocker = "watched alert channel and operator reconciliation confirmation are still not signed/confirmed"
            else:
                status = "blocked_monitoring_confirmation_package_not_ready"
                evidence_delta = "monitoring manual confirmation package failed"
                remaining_blocker = "manual confirmation package must be regenerated and reviewed"

        updated_rows.append(
            {
                "review_time": reviewed_at,
                "gap_id": row.get("gap_id", ""),
                "priority": row.get("priority", ""),
                "category": row.get("category", ""),
                "severity": row.get("severity", ""),
                "gate_item": row.get("gate_item", ""),
                "previous_status": row.get("post_autotrading_disable_status", row.get("previous_status", "")),
                "post_monitoring_manual_confirmation_status": status,
                "evidence_delta": evidence_delta,
                "remaining_blocker": remaining_blocker,
                "ready_to_live_trade": False,
            }
        )

    partial_count = sum(
        1
        for row in updated_rows
        if str(row["post_monitoring_manual_confirmation_status"]).startswith("partially_satisfied")
    )
    closed_count = sum(1 for row in updated_rows if row["post_monitoring_manual_confirmation_status"] == "closed")
    blocked_count = len(updated_rows) - closed_count
    live_gap_008_status = next(
        row["post_monitoring_manual_confirmation_status"] for row in updated_rows if row["gap_id"] == "LIVE-GAP-008"
    )
    decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_post_monitoring_manual_confirmation_gate_update",
        "status": "post_monitoring_manual_confirmation_update_live_still_blocked",
        "gate_count": len(updated_rows),
        "closed_gate_count": closed_count,
        "partially_satisfied_gate_count": partial_count,
        "blocked_gate_count": blocked_count,
        "manual_confirmation_package_ready": package_ready,
        "local_probe_ready": local_probe_ready,
        "watched_alert_channel_confirmed": watched_confirmed,
        "operator_reconciliation_confirmed": reconciliation_confirmed,
        "live_gap_008_status": live_gap_008_status,
        "ready_to_live_trade": False,
        "recommended_next_action": "collect_human_signed_monitoring_confirmation_or_continue_final_approval_package_preparation",
    }

    write_csv(
        OUT_DIR / "post_monitoring_manual_confirmation_gate_update.csv",
        updated_rows,
        [
            "review_time",
            "gap_id",
            "priority",
            "category",
            "severity",
            "gate_item",
            "previous_status",
            "post_monitoring_manual_confirmation_status",
            "evidence_delta",
            "remaining_blocker",
            "ready_to_live_trade",
        ],
    )
    write_csv(
        OUT_DIR / "post_monitoring_manual_confirmation_gate_update_decision.csv",
        [decision],
        list(decision.keys()),
    )
    write_json(OUT_DIR / "post_monitoring_manual_confirmation_gate_update_decision.json", decision)

    report = f"""# Post Monitoring Manual Confirmation Gate Update

Generated: {reviewed_at}

## Decision

- Status: `{decision["status"]}`
- Gate count: `{decision["gate_count"]}`
- Closed gates: `{decision["closed_gate_count"]}`
- Partially satisfied gates: `{decision["partially_satisfied_gate_count"]}`
- Blocked gates: `{decision["blocked_gate_count"]}`
- LIVE-GAP-008: `{live_gap_008_status}`
- Watched alert channel confirmed: `{watched_confirmed}`
- Operator reconciliation confirmed: `{reconciliation_confirmed}`
- Ready to live trade: `false`

## Summary

The manual confirmation package for LIVE-GAP-008 is ready. The gate is not closed until a human/operator confirmation record marks both watched alert channel and reconciliation ownership as confirmed.
"""
    (OUT_DIR / "post_monitoring_manual_confirmation_gate_update.md").write_text(report, encoding="utf-8-sig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
