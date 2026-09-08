from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_final_live_approval_package_draft_20260723"

LATEST_GATE_CSV = (
    VALIDATION_DIR
    / "stage_state_post_monitoring_manual_confirmation_gate_update_20260723"
    / "post_monitoring_manual_confirmation_gate_update.csv"
)
LATEST_GATE_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_post_monitoring_manual_confirmation_gate_update_20260723"
    / "post_monitoring_manual_confirmation_gate_update_decision.json"
)
ACCOUNT_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_live_account_spec_snapshot_read_only_20260723"
    / "live_account_spec_snapshot_decision.json"
)
MONITORING_TEMPLATE_JSON = (
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


def approval_template(gates: List[Dict[str, str]], account: Dict[str, object], monitoring: Dict[str, object]) -> Dict[str, object]:
    gate_status = {
        row["gap_id"]: row["post_monitoring_manual_confirmation_status"]
        for row in gates
        if row.get("gap_id")
    }
    return {
        "source": "final_live_operator_approval_template_not_signed",
        "account_alias": account.get("account_alias", "MT5_ACCOUNT_REDACTED"),
        "server": account.get("server", ""),
        "symbol": account.get("symbol", "XAUUSDm"),
        "balance_cap": account.get("balance_cap", 2000.0),
        "leverage": account.get("account_leverage", 2000),
        "ready_to_live_trade": False,
        "operator_alias": "manual_pending",
        "approval_items": {
            "LIVE-GAP-001_live_trading_approval": False,
            "LIVE-GAP-002_live_package_manifest_release_approval": False,
            "LIVE-GAP-003_InpSimMode_false_loading_approval": False,
            "LIVE-GAP-004_secret_externalization_approval": False,
            "LIVE-GAP-005_MT5_EA_only_order_path_approval": False,
            "LIVE-GAP-006_live_risk_policy_approval": False,
            "LIVE-GAP-008_watched_alert_channel_confirmed": monitoring.get("watched_alert_channel_confirmed") is True,
            "LIVE-GAP-008_operator_reconciliation_confirmed": monitoring.get("operator_reconciliation_confirmed") is True,
            "LIVE-GAP-009_account_spec_intended_context_confirmed": False,
            "LIVE-GAP-010_nonprod_rehearsal_alert_emergency_acceptance": False,
        },
        "current_gate_status": gate_status,
        "do_not_include": [
            "full account number",
            "password",
            "investor password",
            "api token",
            "secret key",
        ],
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().isoformat(timespec="seconds")
    gates = read_rows(LATEST_GATE_CSV)
    latest_decision = read_json(LATEST_GATE_DECISION_JSON)
    account = read_json(ACCOUNT_DECISION_JSON)
    monitoring_template = read_json(MONITORING_TEMPLATE_JSON)

    status_field = "post_monitoring_manual_confirmation_status"
    gate_snapshot: List[Dict[str, object]] = []
    for row in gates:
        gate_snapshot.append(
            {
                "generated_at": generated_at,
                "gap_id": row.get("gap_id", ""),
                "priority": row.get("priority", ""),
                "category": row.get("category", ""),
                "severity": row.get("severity", ""),
                "gate_item": row.get("gate_item", ""),
                "current_status": row.get(status_field, ""),
                "evidence_delta": row.get("evidence_delta", ""),
                "remaining_blocker": row.get("remaining_blocker", ""),
                "ready_to_live_trade": False,
            }
        )

    signoffs = [
        {
            "signoff_id": "SIGN-001",
            "gap_id": "LIVE-GAP-001",
            "required_action": "explicitly approve demo/live execution scope",
            "minimum_evidence": "operator approval record with account alias, symbol, balance cap, leverage, and execution mode",
            "current_status": "missing",
            "blocks_live": True,
        },
        {
            "signoff_id": "SIGN-002",
            "gap_id": "LIVE-GAP-002",
            "required_action": "approve exact EA package and deployment manifest",
            "minimum_evidence": "EX5/MQ5 path, compile log, set file/inputs, manifest, and release timestamp",
            "current_status": "missing",
            "blocks_live": True,
        },
        {
            "signoff_id": "SIGN-003",
            "gap_id": "LIVE-GAP-003",
            "required_action": "approve InpSimMode=false loading",
            "minimum_evidence": "operator confirms live set transition from SIM_ONLY to execution mode",
            "current_status": "missing",
            "blocks_live": True,
        },
        {
            "signoff_id": "SIGN-004",
            "gap_id": "LIVE-GAP-004",
            "required_action": "approve credential externalization",
            "minimum_evidence": "no credentials in repo outputs; any required login handled outside tracked files",
            "current_status": "missing",
            "blocks_live": True,
        },
        {
            "signoff_id": "SIGN-005",
            "gap_id": "LIVE-GAP-005",
            "required_action": "approve MT5 EA-only production order path",
            "minimum_evidence": "operator confirms no Python runner order placement and no external order source",
            "current_status": "missing",
            "blocks_live": True,
        },
        {
            "signoff_id": "SIGN-006",
            "gap_id": "LIVE-GAP-006",
            "required_action": "approve live numeric risk policy",
            "minimum_evidence": "operator accepts risk guard limits, max lot behavior, balance cap, and fail-closed rules",
            "current_status": "technical_rehearsal_passed_approval_missing",
            "blocks_live": True,
        },
        {
            "signoff_id": "SIGN-007",
            "gap_id": "LIVE-GAP-008",
            "required_action": "sign watched alert and reconciliation confirmation",
            "minimum_evidence": "watched alert channel confirmed and operator reconciliation confirmed",
            "current_status": "confirmation_package_ready_not_signed",
            "blocks_live": True,
        },
        {
            "signoff_id": "SIGN-008",
            "gap_id": "LIVE-GAP-009",
            "required_action": "confirm account/spec snapshot is intended execution context",
            "minimum_evidence": "operator confirms account alias, server, symbol, balance cap, leverage, and no unexpected exposure",
            "current_status": "snapshot_collected_approval_missing",
            "blocks_live": True,
        },
        {
            "signoff_id": "SIGN-009",
            "gap_id": "LIVE-GAP-010",
            "required_action": "accept non-production rehearsal alert/emergency evidence",
            "minimum_evidence": "operator accepts guard rehearsal, alert handling, emergency stop behavior, and ledger/deal reconciliation",
            "current_status": "order_lifecycle_passed_alert_emergency_acceptance_missing",
            "blocks_live": True,
        },
    ]

    remaining_steps = [
        {
            "step_no": 1,
            "step": "complete final operator approval template",
            "expected_output": "final_live_operator_approval_template.json updated outside secrets with required approval booleans true where genuinely approved",
            "can_be_automated": False,
        },
        {
            "step_no": 2,
            "step": "rerun final gate review from signed approval evidence",
            "expected_output": "final live gate decision remains false until every P0/P1 gate is closed",
            "can_be_automated": True,
        },
        {
            "step_no": 3,
            "step": "only after final gate passes, prepare live loading package",
            "expected_output": "exact EX5/set/manifest and MT5 EA-only launch checklist",
            "can_be_automated": True,
        },
        {
            "step_no": 4,
            "step": "only after explicit live approval, remove stop flags and load EA",
            "expected_output": "MT5 EA loaded with approved inputs and monitored alerts",
            "can_be_automated": False,
        },
    ]

    approval = approval_template(gates, account, monitoring_template)
    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_final_live_approval_package_draft",
        "status": "final_live_approval_package_draft_ready_not_signed",
        "gate_count": latest_decision.get("gate_count", len(gates)),
        "closed_gate_count": latest_decision.get("closed_gate_count", 0),
        "partially_satisfied_gate_count": latest_decision.get("partially_satisfied_gate_count", 0),
        "blocked_gate_count": latest_decision.get("blocked_gate_count", len(gates)),
        "required_signoff_count": len(signoffs),
        "signed_signoff_count": 0,
        "remaining_minimum_steps": len(remaining_steps),
        "ready_to_live_trade": False,
        "recommended_next_action": "operator_completes_non_secret_final_approval_template_then_run_final_live_gate_review",
    }

    write_csv(
        OUT_DIR / "final_live_gate_status_snapshot.csv",
        gate_snapshot,
        [
            "generated_at",
            "gap_id",
            "priority",
            "category",
            "severity",
            "gate_item",
            "current_status",
            "evidence_delta",
            "remaining_blocker",
            "ready_to_live_trade",
        ],
    )
    write_csv(
        OUT_DIR / "final_live_signoff_requirements.csv",
        signoffs,
        ["signoff_id", "gap_id", "required_action", "minimum_evidence", "current_status", "blocks_live"],
    )
    write_csv(
        OUT_DIR / "final_live_remaining_steps.csv",
        remaining_steps,
        ["step_no", "step", "expected_output", "can_be_automated"],
    )
    write_json(OUT_DIR / "final_live_operator_approval_template.json", approval)
    write_csv(OUT_DIR / "final_live_approval_package_draft_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "final_live_approval_package_draft_decision.json", decision)

    report = f"""# Final Live Approval Package Draft

Generated: {generated_at}

## Decision

- Status: `{decision["status"]}`
- Closed gates: `{decision["closed_gate_count"]}`
- Partially satisfied gates: `{decision["partially_satisfied_gate_count"]}`
- Blocked gates: `{decision["blocked_gate_count"]}`
- Required signoffs: `{decision["required_signoff_count"]}`
- Signed signoffs: `0`
- Ready to live trade: `false`

## Execution Context Snapshot

- Account alias: `{account.get("account_alias", "MT5_ACCOUNT_REDACTED")}`
- Server: `{account.get("server", "")}`
- Symbol: `{account.get("symbol", "XAUUSDm")}`
- Balance cap: `{account.get("balance_cap", 2000.0)}`
- Leverage: `1:{account.get("account_leverage", 2000)}`
- Positions / orders: `{account.get("positions_count", "")} / {account.get("orders_count", "")}`

## What Is Technically Prepared

- EA risk guards compiled and non-production guard rehearsal passed.
- Emergency stop flags exist and connected-session `terminal_info.trade_allowed=False` is verified.
- Monitoring policy, local alert write path, and ledger/deal reconciliation probe are ready.
- Account/spec read-only snapshot matches the requested demo context.

## What Still Blocks Running

The remaining blockers are not more backtest bugs. They are live-operation approvals:

1. Live/demo execution approval record.
2. Exact package/deployment manifest and compile/release approval.
3. `InpSimMode=false` loading approval.
4. Credential externalization approval.
5. MT5 EA-only production order path approval.
6. Live risk policy approval.
7. Watched alert channel and operator reconciliation confirmation.
8. Account/spec intended-context confirmation.
9. Non-production alert/emergency acceptance.

## Shortest Path From Here

1. Complete `final_live_operator_approval_template.json` with non-secret approvals only.
2. Rerun the final live gate review from signed evidence.
3. If every gate closes, prepare the exact MT5 EA loading package.
4. Only after explicit approval, remove stop flags and load the EA.

Stop flags remain in place. This package does not enable trading.
"""
    (OUT_DIR / "final_live_approval_package_draft.md").write_text(report, encoding="utf-8-sig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
