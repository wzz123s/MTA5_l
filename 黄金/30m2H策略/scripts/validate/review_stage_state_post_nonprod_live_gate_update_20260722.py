from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_post_nonprod_live_gate_update_20260722"

FINAL_GATE_CSV = (
    VALIDATION_DIR
    / "stage_state_final_live_gate_review_20260721"
    / "final_live_gate_review.csv"
)
REHEARSAL_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_nonprod_mt5_rehearsal_execution_20260721"
    / "nonprod_mt5_rehearsal_decision.json"
)
REHEARSAL_METRICS_CSV = (
    VALIDATION_DIR
    / "stage_state_nonprod_mt5_rehearsal_execution_20260721"
    / "nonprod_mt5_rehearsal_lifecycle_metrics.csv"
)
REHEARSAL_CHECKS_CSV = (
    VALIDATION_DIR
    / "stage_state_nonprod_mt5_rehearsal_execution_20260721"
    / "nonprod_mt5_rehearsal_checks.csv"
)
REHEARSAL_LEDGER = (
    VALIDATION_DIR
    / "stage_state_nonprod_mt5_rehearsal_execution_20260721"
    / "30m2H_strategy_trade_ledger_nonprod_rehearsal.csv"
)
REHEARSAL_DEALS = (
    VALIDATION_DIR
    / "stage_state_nonprod_mt5_rehearsal_execution_20260721"
    / "30m2H_strategy_deal_history_nonprod_rehearsal.csv"
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


def boolish(value: object) -> bool:
    return str(value).strip().lower() == "true"


def metric(metrics: List[Dict[str, str]], name: str) -> str:
    for row in metrics:
        if row.get("metric") == name:
            return row.get("value", "")
    return ""


def check(
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


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviewed_at = datetime.now().isoformat(timespec="seconds")

    final_rows = read_rows(FINAL_GATE_CSV)
    rehearsal = read_json(REHEARSAL_DECISION_JSON)
    metrics = read_rows(REHEARSAL_METRICS_CSV)
    checks_source = read_rows(REHEARSAL_CHECKS_CSV)

    source_blockers = [
        row for row in checks_source if row.get("severity") == "blocker" and row.get("status") != "pass"
    ]
    nonprod_order_lifecycle_passed = (
        rehearsal.get("status") == "nonprod_mt5_rehearsal_passed"
        and rehearsal.get("nonprod_rehearsal_passed") is True
        and not source_blockers
        and int(str(rehearsal.get("trade_ledger_rows", "0"))) > 0
        and int(str(rehearsal.get("deal_history_rows", "0"))) > 0
        and int(str(rehearsal.get("sl_rows", "0"))) > 0
        and int(str(rehearsal.get("expert_exit_rows", "0"))) > 0
        and REHEARSAL_LEDGER.exists()
        and REHEARSAL_DEALS.exists()
    )

    updated_rows: List[Dict[str, object]] = []
    for row in final_rows:
        gap_id = row["gap_id"]
        updated = {
            "review_time": reviewed_at,
            "gap_id": gap_id,
            "priority": row.get("priority", ""),
            "category": row.get("category", ""),
            "severity": row.get("severity", ""),
            "gate_item": row.get("gate_item", ""),
            "previous_closure_status": row.get("closure_status", ""),
            "post_nonprod_status": "blocked",
            "evidence_delta": "unchanged",
            "remaining_blocker": row.get("blocked_reason", ""),
            "ready_to_live_trade": False,
        }
        if gap_id == "LIVE-GAP-010":
            updated["evidence_delta"] = (
                "MT5 Strategy Tester order lifecycle passed: "
                f"final_balance={rehearsal.get('final_balance')}, "
                f"ledger_rows={rehearsal.get('trade_ledger_rows')}, "
                f"deal_history_rows={rehearsal.get('deal_history_rows')}, "
                f"SL={rehearsal.get('sl_rows')}, EXPERT={rehearsal.get('expert_exit_rows')}, "
                f"lots={rehearsal.get('min_lot')}->{rehearsal.get('max_lot')}"
            )
            updated["post_nonprod_status"] = "partially_satisfied_order_lifecycle_passed"
            updated["remaining_blocker"] = (
                "alerts and emergency handling evidence are still missing; original gate requires "
                "rehearsal_alert_log plus emergency behavior validation"
            )
        elif gap_id == "LIVE-GAP-007":
            updated["evidence_delta"] = (
                "nonprod order lifecycle produced SL and EXPERT exits, but no separate emergency "
                "disable/remove-EA rehearsal report exists"
            )
            updated["remaining_blocker"] = "emergency stop and rollback rehearsal still missing"
        elif gap_id == "LIVE-GAP-008":
            updated["evidence_delta"] = (
                "tester logs/ledger exist, but no watched alert channel or reconciliation checklist execution evidence exists"
            )
            updated["remaining_blocker"] = "monitoring and reconciliation evidence still missing"
        elif gap_id == "LIVE-GAP-006":
            updated["evidence_delta"] = (
                "demo run used strategy risk and lots, but real live numeric limits are not defined"
            )
            updated["remaining_blocker"] = (
                "live numeric limits missing: max daily loss, max drawdown, max orders, max spread, margin guard"
            )
        elif gap_id == "LIVE-GAP-009":
            updated["evidence_delta"] = (
                "demo account parameters and broker symbol spec are available, but real live account snapshot is absent"
            )
            updated["remaining_blocker"] = "real live account/leverage/balance snapshot still missing"
        updated_rows.append(updated)

    fully_closed = sum(1 for row in updated_rows if row["post_nonprod_status"] == "closed")
    partial = sum(1 for row in updated_rows if str(row["post_nonprod_status"]).startswith("partially_satisfied"))
    blocked = len(updated_rows) - fully_closed

    checks = [
        check("final_gate_input_count_10", len(final_rows) == 10, len(final_rows), 10),
        check("nonprod_rehearsal_passed", bool(nonprod_order_lifecycle_passed), rehearsal.get("status"), "nonprod_mt5_rehearsal_passed"),
        check("ledger_and_deal_files_exist", REHEARSAL_LEDGER.exists() and REHEARSAL_DEALS.exists(), f"ledger={REHEARSAL_LEDGER.exists()} deals={REHEARSAL_DEALS.exists()}", "both exist"),
        check("order_lifecycle_has_in_out", metric(metrics, "deal_entry_in_rows") == "15" and metric(metrics, "deal_entry_out_rows") == "15", f"IN={metric(metrics, 'deal_entry_in_rows')} OUT={metric(metrics, 'deal_entry_out_rows')}", "15/15"),
        check("sl_and_expert_exit_present", metric(metrics, "sl_rows") == "10" and metric(metrics, "expert_exit_rows") == "5", f"SL={metric(metrics, 'sl_rows')} EXPERT={metric(metrics, 'expert_exit_rows')}", "10/5"),
        check("no_live_gate_closed_by_partial_rehearsal", fully_closed == 0, fully_closed, 0),
        check("live_gap_010_partial_not_closed", partial == 1, partial, 1),
        check("ready_to_live_trade_false", True, False, False),
    ]
    failures = [row for row in checks if row["severity"] == "blocker" and not boolish(row["pass"])]

    remaining_actions = [
        {
            "sequence": 1,
            "gap_id": "LIVE-GAP-006",
            "action": "define_live_numeric_risk_limits",
            "required_output": "live_risk_policy.json with max_daily_loss, max_drawdown, max_orders, max_spread_points, margin_guard_pct",
            "can_codex_auto_complete": False,
            "ready_to_live_trade": False,
        },
        {
            "sequence": 2,
            "gap_id": "LIVE-GAP-007",
            "action": "execute_nonprod_emergency_stop_rehearsal",
            "required_output": "emergency_rehearsal_report.csv showing disable auto trading/remove EA/rollback behavior",
            "can_codex_auto_complete": False,
            "ready_to_live_trade": False,
        },
        {
            "sequence": 3,
            "gap_id": "LIVE-GAP-008",
            "action": "define_and_rehearse_monitoring_reconciliation",
            "required_output": "live_monitoring_policy.json, reconciliation_checklist.csv, rehearsal_alert_log.csv",
            "can_codex_auto_complete": False,
            "ready_to_live_trade": False,
        },
        {
            "sequence": 4,
            "gap_id": "LIVE-GAP-001/002/003/004/005/009",
            "action": "collect_real_live_approval_and_live_account_package",
            "required_output": "signed live approval, deployment proof, sim-mode transition approval, credential policy, runner decision, live account snapshot",
            "can_codex_auto_complete": False,
            "ready_to_live_trade": False,
        },
        {
            "sequence": 5,
            "gap_id": "ALL",
            "action": "rerun_final_live_gate_review",
            "required_output": "final_live_gate_review status closed only if every prior gate has real evidence",
            "can_codex_auto_complete": True,
            "ready_to_live_trade": False,
        },
    ]

    decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_post_nonprod_live_gate_update",
        "status": "post_nonprod_gate_update_live_still_blocked" if not failures else "post_nonprod_gate_update_invalid",
        "gate_count": len(updated_rows),
        "closed_gate_count": fully_closed,
        "partially_satisfied_gate_count": partial,
        "blocked_gate_count": blocked,
        "nonprod_order_lifecycle_passed": nonprod_order_lifecycle_passed,
        "final_balance": rehearsal.get("final_balance", ""),
        "profit": rehearsal.get("profit", ""),
        "trade_ledger_rows": rehearsal.get("trade_ledger_rows", ""),
        "deal_history_rows": rehearsal.get("deal_history_rows", ""),
        "ready_to_live_trade": False,
        "blocker_failure_count": len(failures),
        "recommended_next_action": "define_live_numeric_risk_limits_then_emergency_monitoring_rehearsals",
    }

    write_csv(
        OUT_DIR / "post_nonprod_live_gate_update.csv",
        updated_rows,
        [
            "review_time",
            "gap_id",
            "priority",
            "category",
            "severity",
            "gate_item",
            "previous_closure_status",
            "post_nonprod_status",
            "evidence_delta",
            "remaining_blocker",
            "ready_to_live_trade",
        ],
    )
    write_csv(
        OUT_DIR / "post_nonprod_remaining_live_actions.csv",
        remaining_actions,
        ["sequence", "gap_id", "action", "required_output", "can_codex_auto_complete", "ready_to_live_trade"],
    )
    write_csv(
        OUT_DIR / "post_nonprod_live_gate_update_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(OUT_DIR / "post_nonprod_live_gate_update_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "post_nonprod_live_gate_update_decision.json", decision)

    lines = [
        "# Post Non-production Live Gate Update",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- gate_count: `{decision['gate_count']}`",
        f"- closed_gate_count: `{decision['closed_gate_count']}`",
        f"- partially_satisfied_gate_count: `{decision['partially_satisfied_gate_count']}`",
        f"- blocked_gate_count: `{decision['blocked_gate_count']}`",
        f"- nonprod_order_lifecycle_passed: `{decision['nonprod_order_lifecycle_passed']}`",
        f"- final_balance: `{decision['final_balance']}`",
        f"- profit: `{decision['profit']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Interpretation",
        "",
        "- MT5 Strategy Tester order lifecycle evidence is now real non-production evidence.",
        "- `LIVE-GAP-010` moves from not-executed to partially satisfied.",
        "- No live gate is fully closed by this partial evidence alone.",
        "- Live remains blocked until numeric risk limits, emergency rehearsal, monitoring/reconciliation, and real live approvals exist.",
        "",
        "## Gate Delta",
        "",
    ]
    for row in updated_rows:
        lines.append(f"- `{row['gap_id']}` `{row['post_nonprod_status']}`: {row['remaining_blocker']}")
    lines.extend(["", "## Remaining Actions", ""])
    for row in remaining_actions:
        lines.append(f"- `{row['sequence']}` `{row['gap_id']}` {row['action']}: {row['required_output']}")
    lines.extend(["", "## Checks", ""])
    for row in checks:
        lines.append(f"- `{row['check_id']}`: `{row['pass']}` - actual `{row['actual']}`, expected `{row['expected']}`")
    lines.append("")
    (OUT_DIR / "post_nonprod_live_gate_update.md").write_text("\n".join(lines), encoding="utf-8-sig")

    for key, value in decision.items():
        print(f"{key}={value}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
