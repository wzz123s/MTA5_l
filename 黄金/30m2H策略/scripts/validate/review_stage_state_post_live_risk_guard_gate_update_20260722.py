from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_post_live_risk_guard_gate_update_20260722"

POST_NONPROD_CSV = (
    VALIDATION_DIR
    / "stage_state_post_nonprod_live_gate_update_20260722"
    / "post_nonprod_live_gate_update.csv"
)
GUARD_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_live_risk_guard_rehearsal_execution_20260722"
    / "live_risk_guard_rehearsal_decision.json"
)
LEVERAGE_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_live_leverage_margin_basis_read_only_20260722"
    / "live_leverage_margin_basis_decision.json"
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
    prior_rows = read_rows(POST_NONPROD_CSV)
    guard = read_json(GUARD_DECISION_JSON)
    leverage = read_json(LEVERAGE_DECISION_JSON)

    guard_passed = (
        guard.get("status") == "live_risk_guard_rehearsal_passed"
        and guard.get("guard_rehearsal_code_path_passed") is True
        and guard.get("nonprod_rehearsal_passed_exact_environment") is True
        and guard.get("blocker_failure_count") == 0
        and guard.get("ready_to_live_trade") is False
    )
    leverage_confirmed = (
        leverage.get("matches_requested_leverage") is True
        and leverage.get("account_leverage") == leverage.get("requested_leverage")
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
            "previous_status": row.get("post_nonprod_status", row.get("previous_closure_status", "")),
            "post_live_risk_guard_status": row.get("post_nonprod_status", ""),
            "evidence_delta": row.get("evidence_delta", ""),
            "remaining_blocker": row.get("remaining_blocker", ""),
            "ready_to_live_trade": False,
        }
        if row.get("gap_id") == "LIVE-GAP-006":
            if guard_passed and leverage_confirmed:
                new_row["post_live_risk_guard_status"] = "partially_satisfied_guard_code_and_nonprod_rehearsal_passed"
                new_row["evidence_delta"] = (
                    "EA live risk guards compiled and guard-enabled nonprod rehearsal passed: "
                    f"final_balance={guard.get('final_balance')}, profit={guard.get('profit')}, "
                    f"ledger_rows={guard.get('trade_ledger_rows')}, deal_history_rows={guard.get('deal_history_rows')}, "
                    f"effective_leverage=1:{guard.get('requested_leverage')}, "
                    f"OrderCalcMargin markers={guard.get('margin_order_calc_count')}, "
                    f"lots={guard.get('min_lot')}->{guard.get('max_lot')}"
                )
                new_row["remaining_blocker"] = (
                    "final live risk policy approval and broader live approval package are still missing; "
                    "alerts/emergency/monitoring gates remain separate blockers"
                )
            else:
                new_row["post_live_risk_guard_status"] = "blocked_guard_rehearsal_or_leverage_basis_not_confirmed"
                new_row["evidence_delta"] = "guard rehearsal evidence was attempted but did not satisfy exact environment checks"
                new_row["remaining_blocker"] = "guard rehearsal or leverage basis failed"
        updated_rows.append(new_row)

    partial_count = sum(1 for row in updated_rows if str(row["post_live_risk_guard_status"]).startswith("partially_satisfied"))
    closed_count = sum(1 for row in updated_rows if row["post_live_risk_guard_status"] == "closed")
    blocked_count = len(updated_rows) - closed_count
    decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_post_live_risk_guard_gate_update",
        "status": "post_live_risk_guard_update_live_still_blocked",
        "gate_count": len(updated_rows),
        "closed_gate_count": closed_count,
        "partially_satisfied_gate_count": partial_count,
        "blocked_gate_count": blocked_count,
        "guard_rehearsal_passed": guard_passed,
        "leverage_basis_confirmed": leverage_confirmed,
        "live_gap_006_status": next(
            row["post_live_risk_guard_status"] for row in updated_rows if row["gap_id"] == "LIVE-GAP-006"
        ),
        "ready_to_live_trade": False,
        "recommended_next_action": "complete_emergency_monitoring_alerts_and_final_live_approval_gates",
    }

    write_csv(
        OUT_DIR / "post_live_risk_guard_gate_update.csv",
        updated_rows,
        [
            "review_time",
            "gap_id",
            "priority",
            "category",
            "severity",
            "gate_item",
            "previous_status",
            "post_live_risk_guard_status",
            "evidence_delta",
            "remaining_blocker",
            "ready_to_live_trade",
        ],
    )
    write_csv(OUT_DIR / "post_live_risk_guard_gate_update_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "post_live_risk_guard_gate_update_decision.json", decision)

    report_lines = [
        "# Post Live Risk Guard Gate Update",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- gate_count: `{decision['gate_count']}`",
        f"- closed_gate_count: `{decision['closed_gate_count']}`",
        f"- partially_satisfied_gate_count: `{decision['partially_satisfied_gate_count']}`",
        f"- blocked_gate_count: `{decision['blocked_gate_count']}`",
        f"- guard_rehearsal_passed: `{decision['guard_rehearsal_passed']}`",
        f"- leverage_basis_confirmed: `{decision['leverage_basis_confirmed']}`",
        f"- LIVE-GAP-006: `{decision['live_gap_006_status']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Summary",
        "",
        "- LIVE-GAP-006 now has EA guard implementation plus guard-enabled MT5 non-production rehearsal evidence.",
        "- It is still not treated as live approval because approval, emergency, alerting, monitoring, and final gate review remain open.",
        "",
    ]
    (OUT_DIR / "post_live_risk_guard_gate_update.md").write_text("\n".join(report_lines), encoding="utf-8-sig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
