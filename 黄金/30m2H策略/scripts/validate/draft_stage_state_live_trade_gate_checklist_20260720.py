from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
GAP_DIR = VALIDATION_DIR / "stage_state_live_trade_readiness_gap_audit_20260720"
OUT_DIR = VALIDATION_DIR / "stage_state_live_trade_gate_checklist_draft_20260720"

GAP_CHECKLIST = GAP_DIR / "live_trade_readiness_gap_checklist.csv"


GATE_DEFINITIONS: Dict[str, Dict[str, str]] = {
    "LIVE-GAP-001": {
        "priority": "P0",
        "gate_item": "Live trading approval record",
        "closure_condition": "A signed and dated approval record exists and explicitly names account, symbol, max risk, allowed runner, and rollback owner.",
        "evidence_required": "live_trade_approval_record.md with approval_id, approver, date, account alias, symbol, max risk, and scope.",
        "script_check": "Verify approval file exists, required fields are non-empty, and approval_scope is live-trade-gate-only.",
        "manual_confirmation": "Human approver must confirm this is not inherited from SIM_ONLY readiness.",
        "fail_closed_action": "Keep ready_to_live_trade=false and keep InpSimMode=true.",
    },
    "LIVE-GAP-002": {
        "priority": "P0",
        "gate_item": "Independent live package audit",
        "closure_condition": "Live EX5, live set, startup config, deployment path, and SHA256 hashes are reviewed independently from SIM_ONLY artifacts.",
        "evidence_required": "live_package_manifest.json, live_package_hashes.csv, compile log, deployed path proof.",
        "script_check": "Verify live artifact paths exist, hashes match, compile log has 0 errors/warnings, and package is not SIM_ONLY.",
        "manual_confirmation": "Reviewer confirms the live package is intentionally separate from SIM_ONLY package.",
        "fail_closed_action": "Use only SIM_ONLY package; do not attach a live package.",
    },
    "LIVE-GAP-003": {
        "priority": "P0",
        "gate_item": "InpSimMode=false gate",
        "closure_condition": "A dedicated gate explicitly authorizes changing InpSimMode from true to false after all live package and risk gates pass.",
        "evidence_required": "sim_mode_transition_approval.md and parsed live set showing InpSimMode=false.",
        "script_check": "Verify all prior gate statuses pass before accepting InpSimMode=false.",
        "manual_confirmation": "Approver types exact phrase: APPROVE_INPSIMMODE_FALSE.",
        "fail_closed_action": "Abort live gate and continue with InpSimMode=true.",
    },
    "LIVE-GAP-004": {
        "priority": "P0",
        "gate_item": "Credential externalization",
        "closure_condition": "No source file contains live account/password values; live credentials are loaded from approved external secret storage.",
        "evidence_required": "secret_policy.md, .env.example without real values, credential_scan_report.csv.",
        "script_check": "Scan blocked source files for hardcoded account/password patterns and verify no real credential values are stored in repository files.",
        "manual_confirmation": "Operator confirms the live terminal/session does not expose credentials in logs or generated reports.",
        "fail_closed_action": "Do not run Python runner or any live startup using source-stored credentials.",
    },
    "LIVE-GAP-005": {
        "priority": "P0",
        "gate_item": "Approved production runner path",
        "closure_condition": "The live execution path is declared as EA-only or audited runner-only, with one source of orders and no stale Python runner.",
        "evidence_required": "production_runner_decision.md and runner_source_audit.csv.",
        "script_check": "Verify auto_trade/auto_trader.py remains blocked unless separately audited and approved.",
        "manual_confirmation": "Reviewer confirms exactly one live order path is enabled.",
        "fail_closed_action": "Keep auto_trade/auto_trader.py blocked and keep live trading disabled.",
    },
    "LIVE-GAP-006": {
        "priority": "P0",
        "gate_item": "Live risk policy",
        "closure_condition": "Live max daily loss, max drawdown, max orders, max spread, margin guard, lot caps, and balance cap are defined.",
        "evidence_required": "live_risk_policy.json with numeric limits and fail-closed thresholds.",
        "script_check": "Parse policy and verify every numeric limit is present, positive, and stricter than broad account defaults.",
        "manual_confirmation": "Operator confirms policy matches the intended account size and leverage.",
        "fail_closed_action": "Reject live start if any risk value is missing, zero where not allowed, or too broad.",
    },
    "LIVE-GAP-007": {
        "priority": "P0",
        "gate_item": "Emergency stop and rollback",
        "closure_condition": "Emergency disable and emergency close-position procedure is documented and tested outside real-money mode.",
        "evidence_required": "emergency_runbook.md and emergency_rehearsal_report.csv.",
        "script_check": "Verify runbook and rehearsal report exist, and rehearsal status is pass.",
        "manual_confirmation": "Operator confirms who can stop the system and how positions are handled.",
        "fail_closed_action": "Reject live start; RUNNER_STOP.flag alone is insufficient for real positions.",
    },
    "LIVE-GAP-008": {
        "priority": "P1",
        "gate_item": "Live monitoring, alerts, and reconciliation",
        "closure_condition": "Alerts and reconciliation are defined for order, position, P/L, margin, disconnect, stale tick, and ledger mismatch.",
        "evidence_required": "live_monitoring_policy.json and reconciliation_checklist.csv.",
        "script_check": "Verify every alert type has channel, threshold, owner, and fail-closed action.",
        "manual_confirmation": "Operator confirms alert channel is watched during live window.",
        "fail_closed_action": "Do not start live without watched alerts.",
    },
    "LIVE-GAP-009": {
        "priority": "P1",
        "gate_item": "Broker/account/spec confirmation",
        "closure_condition": "Allowed account, leverage, symbol spec, contract size, margin, min lot, step lot, spread policy, and balance cap are recorded.",
        "evidence_required": "live_account_spec_snapshot.json and broker_symbol_spec.csv.",
        "script_check": "Verify account/spec files exist and symbol is XAUUSDm with expected lot and margin fields.",
        "manual_confirmation": "Operator confirms this is the intended account and not a different terminal profile.",
        "fail_closed_action": "Reject live gate if account/spec is stale or missing.",
    },
    "LIVE-GAP-010": {
        "priority": "P1",
        "gate_item": "Non-production order-placement rehearsal",
        "closure_condition": "A demo or tester order-placement rehearsal validates open/close, SL/TP, ledger, alerts, and emergency handling.",
        "evidence_required": "nonprod_order_rehearsal_report.md, rehearsal_ledger.csv, rehearsal_alert_log.csv.",
        "script_check": "Verify rehearsal report status is pass and all expected order lifecycle events are present.",
        "manual_confirmation": "Reviewer confirms rehearsal did not use real money.",
        "fail_closed_action": "Do not enable real-money order placement.",
    },
}


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


def build_rows(gaps: List[Dict[str, str]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for gap in gaps:
        gap_id = gap["gap_id"]
        details = GATE_DEFINITIONS.get(gap_id, {})
        rows.append(
            {
                "gap_id": gap_id,
                "priority": details.get("priority", "P2"),
                "category": gap.get("category", ""),
                "severity": gap.get("severity", ""),
                "gate_item": details.get("gate_item", gap.get("requirement", "")),
                "requirement": gap.get("requirement", ""),
                "current_state": gap.get("current_state", ""),
                "closure_condition": details.get("closure_condition", ""),
                "evidence_required": details.get("evidence_required", ""),
                "script_check": details.get("script_check", ""),
                "manual_confirmation": details.get("manual_confirmation", ""),
                "fail_closed_action": details.get("fail_closed_action", ""),
                "draft_status": "open",
            }
        )
    return rows


def build_manual_template(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    return [
        {
            "confirmation_id": f"CONF-{row['gap_id']}",
            "gap_id": row["gap_id"],
            "required_phrase_or_value": "PENDING_MANUAL_CONFIRMATION",
            "current_value": "",
            "confirmed_by": "",
            "confirmed_at": "",
            "notes": row["manual_confirmation"],
        }
        for row in rows
    ]


def build_report(decision: Dict[str, object], rows: List[Dict[str, object]]) -> str:
    lines = [
        "# Live Trade Gate Checklist Draft",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- checklist_item_count: `{decision['checklist_item_count']}`",
        f"- critical_item_count: `{decision['critical_item_count']}`",
        f"- major_item_count: `{decision['major_item_count']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Boundary",
        "",
        "- This is a checklist draft only.",
        "- It does not enable live trading.",
        "- It does not authorize `InpSimMode=false`.",
        "- It does not authorize `auto_trade/auto_trader.py`.",
        "",
        "## Checklist",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"### {row['gap_id']} - {row['gate_item']}",
                "",
                f"- priority: `{row['priority']}`",
                f"- severity: `{row['severity']}`",
                f"- closure condition: {row['closure_condition']}",
                f"- evidence required: {row['evidence_required']}",
                f"- script check: {row['script_check']}",
                f"- manual confirmation: {row['manual_confirmation']}",
                f"- fail closed: {row['fail_closed_action']}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gaps = read_rows(GAP_CHECKLIST)
    rows = build_rows(gaps)
    manual = build_manual_template(rows)

    critical_count = sum(1 for row in rows if row["severity"] == "critical")
    major_count = sum(1 for row in rows if row["severity"] == "major")
    missing_definitions = [row["gap_id"] for row in rows if not row.get("closure_condition")]
    decision = {
        "decision_time": datetime.now().isoformat(timespec="seconds"),
        "check_id": "stage_state_live_trade_gate_checklist_draft",
        "status": "draft_complete" if not missing_definitions and len(rows) == 10 else "draft_incomplete",
        "checklist_item_count": len(rows),
        "critical_item_count": critical_count,
        "major_item_count": major_count,
        "missing_definition_count": len(missing_definitions),
        "missing_definitions": ";".join(missing_definitions),
        "ready_to_live_trade": False,
        "recommended_next_action": "run_live_gate_draft_review_default_false",
    }

    write_csv(
        OUT_DIR / "live_trade_gate_checklist_draft.csv",
        rows,
        [
            "gap_id",
            "priority",
            "category",
            "severity",
            "gate_item",
            "requirement",
            "current_state",
            "closure_condition",
            "evidence_required",
            "script_check",
            "manual_confirmation",
            "fail_closed_action",
            "draft_status",
        ],
    )
    write_csv(
        OUT_DIR / "live_trade_gate_manual_confirmation_template.csv",
        manual,
        ["confirmation_id", "gap_id", "required_phrase_or_value", "current_value", "confirmed_by", "confirmed_at", "notes"],
    )
    write_json(OUT_DIR / "live_trade_gate_checklist_draft_decision.json", decision)
    write_csv(OUT_DIR / "live_trade_gate_checklist_draft_decision.csv", [decision], list(decision.keys()))
    (OUT_DIR / "live_trade_gate_checklist_draft.md").write_text(build_report(decision, rows), encoding="utf-8-sig")

    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0 if decision["status"] == "draft_complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
