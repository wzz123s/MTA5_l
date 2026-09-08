from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_post_monitoring_reconciliation_gate_update_20260723"

POST_EMERGENCY_CSV = (
    VALIDATION_DIR
    / "stage_state_post_emergency_stop_gate_update_20260723"
    / "post_emergency_stop_gate_update.csv"
)
MONITORING_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_live_monitoring_reconciliation_package_20260723"
    / "monitoring_reconciliation_decision.json"
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
    prior_rows = read_rows(POST_EMERGENCY_CSV)
    monitoring = read_json(MONITORING_DECISION_JSON)

    local_monitoring_ready = (
        monitoring.get("monitoring_policy_ready") is True
        and monitoring.get("local_alert_write_path_tested") is True
        and monitoring.get("reconciliation_probe_passed") is True
    )
    watched_confirmed = monitoring.get("watched_alert_channel_confirmed") is True
    operator_recon_confirmed = monitoring.get("operator_reconciliation_confirmed") is True

    updated_rows: List[Dict[str, object]] = []
    for row in prior_rows:
        new_row: Dict[str, object] = {
            "review_time": reviewed_at,
            "gap_id": row.get("gap_id", ""),
            "priority": row.get("priority", ""),
            "category": row.get("category", ""),
            "severity": row.get("severity", ""),
            "gate_item": row.get("gate_item", ""),
            "previous_status": row.get("post_emergency_status", row.get("previous_status", "")),
            "post_monitoring_status": row.get("post_emergency_status", ""),
            "evidence_delta": row.get("evidence_delta", ""),
            "remaining_blocker": row.get("remaining_blocker", ""),
            "ready_to_live_trade": False,
        }
        if row.get("gap_id") == "LIVE-GAP-008":
            if local_monitoring_ready and watched_confirmed and operator_recon_confirmed:
                new_row["post_monitoring_status"] = "partially_satisfied_monitoring_and_operator_confirmation_collected"
                new_row["evidence_delta"] = "monitoring policy, local alert test, reconciliation probe, watched channel, and operator confirmation collected"
                new_row["remaining_blocker"] = "final live approval and broader live package gates remain open"
            elif local_monitoring_ready:
                new_row["post_monitoring_status"] = "partially_satisfied_policy_alert_probe_and_reconciliation_ready_manual_watch_pending"
                new_row["evidence_delta"] = (
                    "monitoring policy created; local alert write-path tested; "
                    f"reconciliation probe passed; terminal64_process_count={monitoring.get('terminal64_process_count')}"
                )
                new_row["remaining_blocker"] = "watched alert channel evidence and operator reconciliation confirmation are still missing"
            else:
                new_row["post_monitoring_status"] = "blocked_monitoring_or_reconciliation_probe_failed"
                new_row["evidence_delta"] = "monitoring/reconciliation package failed"
                new_row["remaining_blocker"] = "monitoring policy or reconciliation probe not ready"
        updated_rows.append(new_row)

    partial_count = sum(1 for row in updated_rows if str(row["post_monitoring_status"]).startswith("partially_satisfied"))
    closed_count = sum(1 for row in updated_rows if row["post_monitoring_status"] == "closed")
    blocked_count = len(updated_rows) - closed_count
    decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_post_monitoring_reconciliation_gate_update",
        "status": "post_monitoring_reconciliation_update_live_still_blocked",
        "gate_count": len(updated_rows),
        "closed_gate_count": closed_count,
        "partially_satisfied_gate_count": partial_count,
        "blocked_gate_count": blocked_count,
        "local_monitoring_ready": local_monitoring_ready,
        "watched_alert_channel_confirmed": watched_confirmed,
        "operator_reconciliation_confirmed": operator_recon_confirmed,
        "live_gap_008_status": next(
            row["post_monitoring_status"] for row in updated_rows if row["gap_id"] == "LIVE-GAP-008"
        ),
        "ready_to_live_trade": False,
        "recommended_next_action": "collect_watched_alert_and_operator_reconciliation_confirmation_then_run_final_live_gate_review",
    }

    write_csv(
        OUT_DIR / "post_monitoring_reconciliation_gate_update.csv",
        updated_rows,
        [
            "review_time",
            "gap_id",
            "priority",
            "category",
            "severity",
            "gate_item",
            "previous_status",
            "post_monitoring_status",
            "evidence_delta",
            "remaining_blocker",
            "ready_to_live_trade",
        ],
    )
    write_csv(OUT_DIR / "post_monitoring_reconciliation_gate_update_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "post_monitoring_reconciliation_gate_update_decision.json", decision)

    report = f"""# Post Monitoring / Reconciliation Gate Update

Generated: {reviewed_at}

## Decision

- Status: `{decision["status"]}`
- Gate count: `{decision["gate_count"]}`
- Closed gates: `{decision["closed_gate_count"]}`
- Partially satisfied gates: `{decision["partially_satisfied_gate_count"]}`
- Blocked gates: `{decision["blocked_gate_count"]}`
- LIVE-GAP-008: `{decision["live_gap_008_status"]}`
- Ready to live trade: `false`

## Summary

Monitoring policy, local alert write-path, and reconciliation probe are ready. A watched alert channel and operator reconciliation confirmation are still required, so LIVE-GAP-008 remains only partially satisfied.
"""
    (OUT_DIR / "post_monitoring_reconciliation_gate_update.md").write_text(report, encoding="utf-8-sig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
