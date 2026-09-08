from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_post_autotrading_disable_gate_update_20260723"

POST_ACCOUNT_SPEC_CSV = (
    VALIDATION_DIR
    / "stage_state_post_account_spec_gate_update_20260723"
    / "post_account_spec_gate_update.csv"
)
AUTOTRADING_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_autotrading_disable_connected_snapshot_20260723"
    / "autotrading_disable_connected_snapshot_decision.json"
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
    prior_rows = read_rows(POST_ACCOUNT_SPEC_CSV)
    autotrading = read_json(AUTOTRADING_DECISION_JSON)

    connected_confirmed = autotrading.get("connected_session_autotrading_disable_confirmed") is True
    trade_allowed = autotrading.get("terminal_trade_allowed")
    stop_flags_ready = (
        autotrading.get("emergency_stop_flag_exists") is True
        and autotrading.get("runner_stop_flag_exists") is True
    )

    updated_rows: List[Dict[str, object]] = []
    for row in prior_rows:
        status = row.get("post_account_spec_status", "")
        evidence_delta = row.get("evidence_delta", "")
        remaining_blocker = row.get("remaining_blocker", "")
        if row.get("gap_id") == "LIVE-GAP-007":
            if connected_confirmed and stop_flags_ready:
                status = "partially_satisfied_runbook_stop_flags_and_connected_autotrading_disabled"
                evidence_delta = (
                    "emergency runbook and stop flags ready; connected-session terminal_info.trade_allowed=False verified"
                )
                remaining_blocker = (
                    "final live approval, alert/monitoring evidence, and any operator-required GUI screenshot remain separate blockers"
                )
            else:
                status = "partially_satisfied_runbook_and_stop_flags_ready_manual_ui_pending"
                evidence_delta = (
                    "emergency runbook and stop flags ready; connected-session AutoTrading disabled evidence not confirmed"
                )
                remaining_blocker = "manual MT5 Algo Trading / AutoTrading disable evidence is still missing"

        new_row: Dict[str, object] = {
            "review_time": reviewed_at,
            "gap_id": row.get("gap_id", ""),
            "priority": row.get("priority", ""),
            "category": row.get("category", ""),
            "severity": row.get("severity", ""),
            "gate_item": row.get("gate_item", ""),
            "previous_status": row.get("post_account_spec_status", row.get("previous_status", "")),
            "post_autotrading_disable_status": status,
            "evidence_delta": evidence_delta,
            "remaining_blocker": remaining_blocker,
            "ready_to_live_trade": False,
        }
        updated_rows.append(new_row)

    partial_count = sum(
        1 for row in updated_rows if str(row["post_autotrading_disable_status"]).startswith("partially_satisfied")
    )
    closed_count = sum(1 for row in updated_rows if row["post_autotrading_disable_status"] == "closed")
    blocked_count = len(updated_rows) - closed_count
    live_gap_007_status = next(
        row["post_autotrading_disable_status"] for row in updated_rows if row["gap_id"] == "LIVE-GAP-007"
    )
    decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_post_autotrading_disable_gate_update",
        "status": "post_autotrading_disable_update_live_still_blocked",
        "gate_count": len(updated_rows),
        "closed_gate_count": closed_count,
        "partially_satisfied_gate_count": partial_count,
        "blocked_gate_count": blocked_count,
        "connected_session_autotrading_disable_confirmed": connected_confirmed,
        "terminal_trade_allowed": trade_allowed,
        "stop_flags_ready": stop_flags_ready,
        "live_gap_007_status": live_gap_007_status,
        "ready_to_live_trade": False,
        "recommended_next_action": "collect_watched_alert_operator_reconciliation_and_live_approval_package_then_run_final_live_gate_review",
    }

    write_csv(
        OUT_DIR / "post_autotrading_disable_gate_update.csv",
        updated_rows,
        [
            "review_time",
            "gap_id",
            "priority",
            "category",
            "severity",
            "gate_item",
            "previous_status",
            "post_autotrading_disable_status",
            "evidence_delta",
            "remaining_blocker",
            "ready_to_live_trade",
        ],
    )
    write_csv(
        OUT_DIR / "post_autotrading_disable_gate_update_decision.csv",
        [decision],
        list(decision.keys()),
    )
    write_json(OUT_DIR / "post_autotrading_disable_gate_update_decision.json", decision)

    report = f"""# Post AutoTrading Disable Gate Update

Generated: {reviewed_at}

## Decision

- Status: `{decision["status"]}`
- Gate count: `{decision["gate_count"]}`
- Closed gates: `{decision["closed_gate_count"]}`
- Partially satisfied gates: `{decision["partially_satisfied_gate_count"]}`
- Blocked gates: `{decision["blocked_gate_count"]}`
- Connected-session AutoTrading disabled confirmed: `{connected_confirmed}`
- Terminal trade_allowed: `{trade_allowed}`
- LIVE-GAP-007: `{live_gap_007_status}`
- Ready to live trade: `false`

## Summary

LIVE-GAP-007 now has read-only connected-session evidence that terminal-side trading is disabled and stop flags remain present. Live trading is still blocked because broader live approval, watched alert, reconciliation, and any operator-required GUI screenshot evidence remain outside this automated check.
"""
    (OUT_DIR / "post_autotrading_disable_gate_update.md").write_text(report, encoding="utf-8-sig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
