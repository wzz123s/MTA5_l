from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_post_emergency_stop_gate_update_20260723"

POST_RISK_GATE_CSV = (
    VALIDATION_DIR
    / "stage_state_post_live_risk_guard_gate_update_20260722"
    / "post_live_risk_guard_gate_update.csv"
)
EMERGENCY_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_emergency_stop_rehearsal_package_20260723"
    / "emergency_rehearsal_decision.json"
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
    prior_rows = read_rows(POST_RISK_GATE_CSV)
    emergency = read_json(EMERGENCY_DECISION_JSON)

    automated_ready = emergency.get("emergency_automated_controls_ready") is True
    manual_confirmed = emergency.get("manual_autotrading_disable_confirmed") is True

    updated_rows: List[Dict[str, object]] = []
    for row in prior_rows:
        new_row: Dict[str, object] = {
            "review_time": reviewed_at,
            "gap_id": row.get("gap_id", ""),
            "priority": row.get("priority", ""),
            "category": row.get("category", ""),
            "severity": row.get("severity", ""),
            "gate_item": row.get("gate_item", ""),
            "previous_status": row.get("post_live_risk_guard_status", row.get("previous_status", "")),
            "post_emergency_status": row.get("post_live_risk_guard_status", ""),
            "evidence_delta": row.get("evidence_delta", ""),
            "remaining_blocker": row.get("remaining_blocker", ""),
            "ready_to_live_trade": False,
        }
        if row.get("gap_id") == "LIVE-GAP-007":
            if automated_ready and manual_confirmed:
                new_row["post_emergency_status"] = "partially_satisfied_emergency_rehearsal_evidence_collected"
                new_row["evidence_delta"] = "emergency runbook, stop flags, terminal snapshot, and manual AutoTrading disable evidence collected"
                new_row["remaining_blocker"] = "final live approval and broader alert/monitoring gates remain open"
            elif automated_ready:
                new_row["post_emergency_status"] = "partially_satisfied_runbook_and_stop_flags_ready_manual_ui_pending"
                new_row["evidence_delta"] = (
                    "emergency runbook created; EMERGENCY_STOP.flag and RUNNER_STOP.flag created; "
                    f"terminal64_process_count={emergency.get('terminal64_process_count')}"
                )
                new_row["remaining_blocker"] = "manual MT5 Algo Trading / AutoTrading disable evidence is still missing"
            else:
                new_row["post_emergency_status"] = "blocked_emergency_controls_not_ready"
                new_row["evidence_delta"] = "emergency stop package failed"
                new_row["remaining_blocker"] = "emergency controls not ready"
        updated_rows.append(new_row)

    partial_count = sum(1 for row in updated_rows if str(row["post_emergency_status"]).startswith("partially_satisfied"))
    closed_count = sum(1 for row in updated_rows if row["post_emergency_status"] == "closed")
    blocked_count = len(updated_rows) - closed_count
    decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_post_emergency_stop_gate_update",
        "status": "post_emergency_stop_update_live_still_blocked",
        "gate_count": len(updated_rows),
        "closed_gate_count": closed_count,
        "partially_satisfied_gate_count": partial_count,
        "blocked_gate_count": blocked_count,
        "emergency_automated_controls_ready": automated_ready,
        "manual_autotrading_disable_confirmed": manual_confirmed,
        "live_gap_007_status": next(
            row["post_emergency_status"] for row in updated_rows if row["gap_id"] == "LIVE-GAP-007"
        ),
        "ready_to_live_trade": False,
        "recommended_next_action": "collect_manual_autotrading_disable_evidence_then_complete_monitoring_alerts_gate",
    }

    write_csv(
        OUT_DIR / "post_emergency_stop_gate_update.csv",
        updated_rows,
        [
            "review_time",
            "gap_id",
            "priority",
            "category",
            "severity",
            "gate_item",
            "previous_status",
            "post_emergency_status",
            "evidence_delta",
            "remaining_blocker",
            "ready_to_live_trade",
        ],
    )
    write_csv(OUT_DIR / "post_emergency_stop_gate_update_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "post_emergency_stop_gate_update_decision.json", decision)

    report = f"""# Post Emergency Stop Gate Update

Generated: {reviewed_at}

## Decision

- Status: `{decision["status"]}`
- Gate count: `{decision["gate_count"]}`
- Closed gates: `{decision["closed_gate_count"]}`
- Partially satisfied gates: `{decision["partially_satisfied_gate_count"]}`
- Blocked gates: `{decision["blocked_gate_count"]}`
- LIVE-GAP-007: `{decision["live_gap_007_status"]}`
- Ready to live trade: `false`

## Summary

Emergency runbook and stop flags are ready. Manual MT5 Algo Trading / AutoTrading disable evidence is still required, so LIVE-GAP-007 remains only partially satisfied.
"""
    (OUT_DIR / "post_emergency_stop_gate_update.md").write_text(report, encoding="utf-8-sig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
