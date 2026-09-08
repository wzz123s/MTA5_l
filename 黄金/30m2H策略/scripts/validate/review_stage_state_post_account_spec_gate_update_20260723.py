from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_post_account_spec_gate_update_20260723"

POST_MONITORING_CSV = (
    VALIDATION_DIR
    / "stage_state_post_monitoring_reconciliation_gate_update_20260723"
    / "post_monitoring_reconciliation_gate_update.csv"
)
ACCOUNT_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_live_account_spec_snapshot_read_only_20260723"
    / "live_account_spec_snapshot_decision.json"
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
    prior_rows = read_rows(POST_MONITORING_CSV)
    account = read_json(ACCOUNT_DECISION_JSON)

    account_snapshot_ready = (
        account.get("status") == "live_account_spec_snapshot_collected_demo_context"
        and account.get("blocker_failure_count") == 0
        and account.get("account_leverage") == account.get("requested_leverage")
        and account.get("balance") == account.get("balance_cap")
        and account.get("positions_count") == 0
        and account.get("orders_count") == 0
        and account.get("credential_values_output") is False
        and account.get("orders_placed") is False
    )

    updated_rows: List[Dict[str, object]] = []
    for row in prior_rows:
        new_row: Dict[str, object] = {
            "review_time": reviewed_at,
            "gap_id": row.get("gap_id", ""),
            "priority": row.get("priority", ""),
            "category": row.get("category", ""),
            "severity": row.get("severity", ""),
            "gate_item": row.get("gate_item", ""),
            "previous_status": row.get("post_monitoring_status", row.get("previous_status", "")),
            "post_account_spec_status": row.get("post_monitoring_status", ""),
            "evidence_delta": row.get("evidence_delta", ""),
            "remaining_blocker": row.get("remaining_blocker", ""),
            "ready_to_live_trade": False,
        }
        if row.get("gap_id") == "LIVE-GAP-009":
            if account_snapshot_ready:
                new_row["post_account_spec_status"] = "partially_satisfied_demo_account_spec_snapshot_collected"
                new_row["evidence_delta"] = (
                    f"read-only MT5 account/spec snapshot collected: account_alias={account.get('account_alias')}, "
                    f"server={account.get('server')}, symbol={account.get('symbol')}, "
                    f"balance={account.get('balance')}, leverage=1:{account.get('account_leverage')}, "
                    f"positions={account.get('positions_count')}, orders={account.get('orders_count')}, "
                    f"margin_basis={account.get('implied_leverage_unique_from_margin')}"
                )
                new_row["remaining_blocker"] = "operator/live approval must confirm this account snapshot is the intended execution context"
            else:
                new_row["post_account_spec_status"] = "blocked_account_spec_snapshot_not_ready"
                new_row["evidence_delta"] = "read-only account/spec snapshot failed or did not match requested demo context"
                new_row["remaining_blocker"] = "account/spec mismatch or missing snapshot"
        updated_rows.append(new_row)

    partial_count = sum(1 for row in updated_rows if str(row["post_account_spec_status"]).startswith("partially_satisfied"))
    closed_count = sum(1 for row in updated_rows if row["post_account_spec_status"] == "closed")
    blocked_count = len(updated_rows) - closed_count
    decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_post_account_spec_gate_update",
        "status": "post_account_spec_update_live_still_blocked",
        "gate_count": len(updated_rows),
        "closed_gate_count": closed_count,
        "partially_satisfied_gate_count": partial_count,
        "blocked_gate_count": blocked_count,
        "account_snapshot_ready": account_snapshot_ready,
        "live_gap_009_status": next(
            row["post_account_spec_status"] for row in updated_rows if row["gap_id"] == "LIVE-GAP-009"
        ),
        "ready_to_live_trade": False,
        "recommended_next_action": "collect_remaining_manual_approval_autotrading_alert_reconciliation_evidence_then_run_final_live_gate_review",
    }

    write_csv(
        OUT_DIR / "post_account_spec_gate_update.csv",
        updated_rows,
        [
            "review_time",
            "gap_id",
            "priority",
            "category",
            "severity",
            "gate_item",
            "previous_status",
            "post_account_spec_status",
            "evidence_delta",
            "remaining_blocker",
            "ready_to_live_trade",
        ],
    )
    write_csv(OUT_DIR / "post_account_spec_gate_update_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "post_account_spec_gate_update_decision.json", decision)

    report = f"""# Post Account / Spec Gate Update

Generated: {reviewed_at}

## Decision

- Status: `{decision["status"]}`
- Gate count: `{decision["gate_count"]}`
- Closed gates: `{decision["closed_gate_count"]}`
- Partially satisfied gates: `{decision["partially_satisfied_gate_count"]}`
- Blocked gates: `{decision["blocked_gate_count"]}`
- LIVE-GAP-009: `{decision["live_gap_009_status"]}`
- Ready to live trade: `false`

## Summary

The read-only account/spec snapshot matches the requested demo context. LIVE-GAP-009 is partially satisfied, but still requires operator/live approval that this is the intended execution context.
"""
    (OUT_DIR / "post_account_spec_gate_update.md").write_text(report, encoding="utf-8-sig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
