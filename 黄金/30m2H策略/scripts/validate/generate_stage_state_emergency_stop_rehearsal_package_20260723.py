from __future__ import annotations


import csv
import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
AUTO_TRADE = ROOT / "auto_trade"
OUT_DIR = VALIDATION_DIR / "stage_state_emergency_stop_rehearsal_package_20260723"

DEMO_EMERGENCY_POLICY = (
    VALIDATION_DIR
    / "stage_state_demo_manual_confirmation_package_20260721"
    / "evidence"
    / "LIVE-GAP-007"
    / "demo_emergency_stop_policy.md"
)
GUARD_REHEARSAL_DECISION = (
    VALIDATION_DIR
    / "stage_state_live_risk_guard_rehearsal_execution_20260722"
    / "live_risk_guard_rehearsal_decision.json"
)
POST_RISK_GATE_DECISION = (
    VALIDATION_DIR
    / "stage_state_post_live_risk_guard_gate_update_20260722"
    / "post_live_risk_guard_gate_update_decision.json"
)
SIM_RUNNER_GATE_DECISION = (
    VALIDATION_DIR
    / "stage_state_sim_continuous_runner_execution_gate_20260720"
    / "sim_continuous_runner_execution_gate_decision.json"
)

RUNNER_STOP_FLAG = AUTO_TRADE / "RUNNER_STOP.flag"
EMERGENCY_STOP_FLAG = AUTO_TRADE / "EMERGENCY_STOP.flag"


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


def sha256(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def create_flag(path: Path, generated_at: str, reason: str) -> Dict[str, object]:
    content = "\n".join(
        [
            f"created_at={generated_at}",
            "scope=nonprod_emergency_stop_rehearsal",
            f"reason={reason}",
            "ready_to_live_trade=false",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8-sig")
    return {
        "flag_path": str(path),
        "exists": path.exists(),
        "sha256": sha256(path),
        "created_at": generated_at,
        "reason": reason,
    }


def terminal_process_snapshot() -> List[Dict[str, object]]:
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-Process terminal64 -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,Path | ConvertTo-Json -Compress",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    raw = result.stdout.strip()
    if not raw:
        return []
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        parsed = [parsed]
    return [
        {
            "id": row.get("Id", ""),
            "process_name": row.get("ProcessName", ""),
            "path": row.get("Path", ""),
        }
        for row in parsed
    ]


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
    generated_at = datetime.now().isoformat(timespec="seconds")

    guard = read_json(GUARD_REHEARSAL_DECISION)
    post_risk_gate = read_json(POST_RISK_GATE_DECISION)
    sim_runner_gate = read_json(SIM_RUNNER_GATE_DECISION) if SIM_RUNNER_GATE_DECISION.exists() else {}

    flag_rows = [
        create_flag(EMERGENCY_STOP_FLAG, generated_at, "manual_or_operator_emergency_stop"),
        create_flag(RUNNER_STOP_FLAG, generated_at, "block_python_runner_and_fail_closed"),
    ]
    processes = terminal_process_snapshot()
    process_rows = processes if processes else [{"id": "", "process_name": "", "path": "", "state": "no_terminal64_process_seen"}]

    runbook = f"""# LIVE-GAP-007 Emergency Stop And Rollback Runbook

Generated: {generated_at}

## Scope

This runbook is for the MT5 EA-only path on `XAUUSDm`. It is a non-production rehearsal artifact and does not approve real-money live trading.

## Immediate Stop Order

1. Create or confirm `auto_trade/EMERGENCY_STOP.flag`.
2. Create or confirm `auto_trade/RUNNER_STOP.flag`.
3. In MT5, turn off Algo Trading / AutoTrading.
4. Remove the EA from any `XAUUSDm` chart or close the terminal if this is a tester/demo rehearsal.
5. Confirm positions and orders. If positions exist, follow strategy-defined close rules unless a separate emergency manual-close approval is recorded.
6. Freeze deployments: do not replace `.ex5` or `.set` until a post-incident review is complete.

## Verification

- Check no unauthorized Python runner is active.
- Check MT5 terminal state and process state.
- Check positions, orders, ledger, and deal history.
- Save journal/expert logs, screenshots if a GUI action was performed, and the final gate decision.

## Rollback

- Keep the last reviewed EX5/set package.
- Keep both stop flags in place until a deliberate resume decision removes them.
- Require a final live gate review before any real-money operation.
"""
    (OUT_DIR / "emergency_runbook.md").write_text(runbook, encoding="utf-8-sig")

    evidence_requirements = [
        {
            "evidence_id": "ER-001",
            "evidence": "emergency_runbook.md",
            "status": "created",
            "remaining_gap": "",
        },
        {
            "evidence_id": "ER-002",
            "evidence": "EMERGENCY_STOP.flag",
            "status": "created",
            "remaining_gap": "",
        },
        {
            "evidence_id": "ER-003",
            "evidence": "RUNNER_STOP.flag",
            "status": "created",
            "remaining_gap": "",
        },
        {
            "evidence_id": "ER-004",
            "evidence": "MT5 Algo Trading / AutoTrading disabled evidence",
            "status": "manual_pending",
            "remaining_gap": "requires operator screenshot/log or connected-session evidence",
        },
        {
            "evidence_id": "ER-005",
            "evidence": "positions/orders snapshot after emergency action",
            "status": "pending",
            "remaining_gap": "requires read-only account snapshot immediately after a manual UI rehearsal",
        },
        {
            "evidence_id": "ER-006",
            "evidence": "rollback/re-enable approval",
            "status": "not_started",
            "remaining_gap": "required before removing stop flags for live use",
        },
    ]

    checks = [
        check("demo_emergency_policy_exists", DEMO_EMERGENCY_POLICY.exists(), str(DEMO_EMERGENCY_POLICY), "exists"),
        check("guard_rehearsal_passed", guard.get("status") == "live_risk_guard_rehearsal_passed", guard.get("status"), "live_risk_guard_rehearsal_passed"),
        check("post_risk_gate_still_not_live", post_risk_gate.get("ready_to_live_trade") is False, post_risk_gate.get("ready_to_live_trade"), False),
        check("emergency_stop_flag_created", EMERGENCY_STOP_FLAG.exists(), str(EMERGENCY_STOP_FLAG), "exists"),
        check("runner_stop_flag_created", RUNNER_STOP_FLAG.exists(), str(RUNNER_STOP_FLAG), "exists"),
        check("sim_runner_gate_had_zero_positions_orders", sim_runner_gate.get("positions_count") == 0 and sim_runner_gate.get("orders_count") == 0, f"positions={sim_runner_gate.get('positions_count')} orders={sim_runner_gate.get('orders_count')}", "positions=0 orders=0", "warning", "Older SIM_ONLY gate evidence; not a substitute for a fresh GUI emergency snapshot."),
        check("terminal64_process_snapshot_collected", True, len(processes), "collected"),
        check("manual_autotrading_disable_evidence", False, "missing", "operator screenshot/log", "blocker", "Cannot be auto-generated without a real MT5 GUI action."),
    ]

    blocker_failures = [row for row in checks if row["severity"] == "blocker" and not row["pass"]]
    warning_failures = [row for row in checks if row["severity"] == "warning" and not row["pass"]]

    report_rows = [
        {
            "rehearsal_id": "LIVE-GAP-007-20260723",
            "environment": "nonprod_rehearsal",
            "action": "create_emergency_stop_and_runner_stop_flags",
            "status": "passed",
            "evidence_path": f"{EMERGENCY_STOP_FLAG}; {RUNNER_STOP_FLAG}",
            "reviewed_at": generated_at,
        },
        {
            "rehearsal_id": "LIVE-GAP-007-20260723",
            "environment": "nonprod_rehearsal",
            "action": "terminal_process_snapshot",
            "status": "collected",
            "evidence_path": str(OUT_DIR / "emergency_terminal_process_snapshot.csv"),
            "reviewed_at": generated_at,
        },
        {
            "rehearsal_id": "LIVE-GAP-007-20260723",
            "environment": "manual_mt5_gui",
            "action": "disable_algo_trading_autotrading",
            "status": "pending_manual_evidence",
            "evidence_path": "operator screenshot or journal/expert log required",
            "reviewed_at": generated_at,
        },
    ]

    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_emergency_stop_rehearsal_package",
        "status": "emergency_stop_runbook_and_flags_ready_manual_ui_rehearsal_pending",
        "emergency_automated_controls_ready": True,
        "manual_autotrading_disable_confirmed": False,
        "terminal64_process_count": len(processes),
        "live_gap_007_closed": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "warning_count": len(warning_failures),
        "recommended_next_action": "perform_manual_mt5_autotrading_disable_rehearsal_and_collect_screenshot_or_log",
    }

    write_csv(OUT_DIR / "emergency_stop_flags.csv", flag_rows, ["flag_path", "exists", "sha256", "created_at", "reason"])
    write_csv(OUT_DIR / "emergency_terminal_process_snapshot.csv", process_rows, ["id", "process_name", "path", "state"])
    write_csv(OUT_DIR / "emergency_evidence_requirements.csv", evidence_requirements, ["evidence_id", "evidence", "status", "remaining_gap"])
    write_csv(OUT_DIR / "emergency_rehearsal_report.csv", report_rows, ["rehearsal_id", "environment", "action", "status", "evidence_path", "reviewed_at"])
    write_csv(OUT_DIR / "emergency_rehearsal_checks.csv", checks, ["check_id", "status", "pass", "actual", "expected", "severity", "note"])
    write_csv(OUT_DIR / "emergency_rehearsal_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "emergency_rehearsal_decision.json", decision)

    summary = f"""# LIVE-GAP-007 Emergency Stop Rehearsal Package

Generated: {generated_at}

## Decision

- Status: `{decision["status"]}`
- Emergency automated controls ready: `true`
- Manual AutoTrading disable confirmed: `false`
- LIVE-GAP-007 closed: `false`
- Ready to live trade: `false`

## What Is Ready

- Emergency runbook created.
- `EMERGENCY_STOP.flag` created.
- `RUNNER_STOP.flag` created.
- Terminal process snapshot collected.

## Remaining Blocker

Manual MT5 GUI evidence is still required: the operator must disable Algo Trading / AutoTrading and provide a screenshot or journal/expert log.
"""
    (OUT_DIR / "emergency_rehearsal_summary.md").write_text(summary, encoding="utf-8-sig")
    return 1 if blocker_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
