from __future__ import annotations


import csv
import json
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
AUTO_TRADE = ROOT / "auto_trade"
OUT_DIR = VALIDATION_DIR / "stage_state_live_monitoring_reconciliation_package_20260723"

POST_EMERGENCY_DECISION = (
    VALIDATION_DIR
    / "stage_state_post_emergency_stop_gate_update_20260723"
    / "post_emergency_stop_gate_update_decision.json"
)
GUARD_REHEARSAL_DECISION = (
    VALIDATION_DIR
    / "stage_state_live_risk_guard_rehearsal_execution_20260722"
    / "live_risk_guard_rehearsal_decision.json"
)
GUARD_REHEARSAL_DIR = VALIDATION_DIR / "stage_state_live_risk_guard_rehearsal_execution_20260722"
SIGNALS_EXPORT = GUARD_REHEARSAL_DIR / "30m2H_strategy_signals_export_live_risk_guard_rehearsal.csv"
TRADE_LEDGER = GUARD_REHEARSAL_DIR / "30m2H_strategy_trade_ledger_live_risk_guard_rehearsal.csv"
DEAL_HISTORY = GUARD_REHEARSAL_DIR / "30m2H_strategy_deal_history_live_risk_guard_rehearsal.csv"
RUNNER_STOP_FLAG = AUTO_TRADE / "RUNNER_STOP.flag"
EMERGENCY_STOP_FLAG = AUTO_TRADE / "EMERGENCY_STOP.flag"


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def safe_float(value: object) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


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

    post_emergency = read_json(POST_EMERGENCY_DECISION)
    guard = read_json(GUARD_REHEARSAL_DECISION)
    signals = read_rows(SIGNALS_EXPORT) if SIGNALS_EXPORT.exists() else []
    ledger = read_rows(TRADE_LEDGER) if TRADE_LEDGER.exists() else []
    deals = read_rows(DEAL_HISTORY) if DEAL_HISTORY.exists() else []
    processes = terminal_process_snapshot()

    deal_entry_counts = Counter(row.get("deal_entry", "") for row in deals)
    deal_reason_counts = Counter(row.get("deal_reason", "") for row in ledger)
    stage_counts = Counter(row.get("stage", "") for row in ledger)
    lots = [safe_float(row.get("lots", "")) for row in ledger if row.get("lots", "")]
    net_profit = round(sum(safe_float(row.get("net_profit", "")) for row in ledger), 2)
    final_balance = safe_float(guard.get("final_balance", "0"))
    initial_deposit = safe_float(guard.get("initial_deposit", "0"))
    balance_delta = round(final_balance - initial_deposit, 2)

    alert_log = OUT_DIR / "live_monitoring_alert_test_log.jsonl"
    alert_event = {
        "event_time": generated_at,
        "event_type": "LIVE_GAP_008_TEST_ALERT",
        "severity": "test",
        "channel": "local_file_only",
        "watched_by_operator": False,
        "message": "Monitoring alert write-path test. This is not a live trading alert approval.",
        "ready_to_live_trade": False,
    }
    alert_log.write_text(json.dumps(alert_event, ensure_ascii=False) + "\n", encoding="utf-8-sig")

    policy = {
        "gap_id": "LIVE-GAP-008",
        "policy_status": "local_policy_and_probe_ready_watched_channel_pending",
        "scope": "MT5_EA_ONLY_XAUUSDm_monitoring_reconciliation",
        "generated_at": generated_at,
        "ready_to_live_trade": False,
        "alert_channels": {
            "local_file": str(alert_log),
            "terminal_journal": "MT5 Journal/Experts logs",
            "external_watched_channel": "manual_pending",
        },
        "watched_alert_channel_confirmed": False,
        "checks": {
            "terminal_process": {
                "frequency_sec": 60,
                "source": "Get-Process terminal64",
                "fail_closed_action": "create EMERGENCY_STOP.flag and RUNNER_STOP.flag; notify operator",
            },
            "ea_log_errors": {
                "frequency_sec": 60,
                "source": "MT5 Experts/Journal logs",
                "fail_closed_action": "stop new entries and review logs before resume",
            },
            "signal_export_freshness": {
                "frequency_sec": 300,
                "source": "30m2H_strategy_signals_export.csv",
                "fail_closed_action": "alert if stale during scheduled trading window",
            },
            "trade_ledger_reconciliation": {
                "frequency_sec": 300,
                "source": "30m2H_strategy_trade_ledger.csv and deal history",
                "fail_closed_action": "block resume until ledger/deal mismatch is explained",
            },
            "position_order_snapshot": {
                "frequency_sec": 60,
                "source": "MT5 positions/orders read-only snapshot",
                "fail_closed_action": "operator review if unexpected position/order exists",
            },
            "margin_level": {
                "frequency_sec": 60,
                "threshold_pct": 500,
                "fail_closed_action": "block new entries and escalate",
            },
        },
    }

    reconciliation_rows = [
        {
            "check_id": "signal_export_rows",
            "source_a": str(SIGNALS_EXPORT),
            "source_b": "expected guard rehearsal",
            "actual": len(signals),
            "expected": guard.get("signal_rows", ""),
            "status": "pass" if len(signals) == int(guard.get("signal_rows", 0)) else "fail",
            "fail_closed_action": "investigate missing signal export rows before resume",
        },
        {
            "check_id": "trade_ledger_rows",
            "source_a": str(TRADE_LEDGER),
            "source_b": "expected guard rehearsal",
            "actual": len(ledger),
            "expected": guard.get("trade_ledger_rows", ""),
            "status": "pass" if len(ledger) == int(guard.get("trade_ledger_rows", 0)) else "fail",
            "fail_closed_action": "investigate ledger row mismatch before resume",
        },
        {
            "check_id": "deal_history_rows",
            "source_a": str(DEAL_HISTORY),
            "source_b": "expected guard rehearsal",
            "actual": len(deals),
            "expected": guard.get("deal_history_rows", ""),
            "status": "pass" if len(deals) == int(guard.get("deal_history_rows", 0)) else "fail",
            "fail_closed_action": "investigate deal history row mismatch before resume",
        },
        {
            "check_id": "deal_in_out_balance",
            "source_a": str(DEAL_HISTORY),
            "source_b": "IN/OUT counts",
            "actual": f"IN={deal_entry_counts.get('IN', 0)} OUT={deal_entry_counts.get('OUT', 0)}",
            "expected": "IN=15 OUT=15",
            "status": "pass" if deal_entry_counts.get("IN", 0) == 15 and deal_entry_counts.get("OUT", 0) == 15 else "fail",
            "fail_closed_action": "investigate unmatched order lifecycle before resume",
        },
        {
            "check_id": "net_profit_balance_delta",
            "source_a": str(TRADE_LEDGER),
            "source_b": str(GUARD_REHEARSAL_DECISION),
            "actual": net_profit,
            "expected": balance_delta,
            "status": "pass" if net_profit == balance_delta else "fail",
            "fail_closed_action": "block resume until PnL reconciliation is explained",
        },
        {
            "check_id": "stage_rows_present",
            "source_a": str(TRADE_LEDGER),
            "source_b": "stage counts",
            "actual": dict(stage_counts),
            "expected": "stage 1/2/3 present",
            "status": "pass" if all(stage_counts.get(str(i), 0) > 0 for i in (1, 2, 3)) else "fail",
            "fail_closed_action": "investigate missing split-stage lifecycle before resume",
        },
    ]

    checklist = [
        {
            "check_id": "MON-001",
            "frequency": "60s",
            "source_a": "MT5 terminal process",
            "source_b": "operator schedule",
            "owner": "user",
            "fail_closed_action": "if unexpected stopped or unexpected running, write alert and keep stop flags",
        },
        {
            "check_id": "MON-002",
            "frequency": "60s",
            "source_a": "MT5 account positions/orders",
            "source_b": "EA ledger",
            "owner": "user",
            "fail_closed_action": "if mismatch, block resume and collect snapshot",
        },
        {
            "check_id": "MON-003",
            "frequency": "300s",
            "source_a": "signals export",
            "source_b": "expected market window",
            "owner": "user",
            "fail_closed_action": "if stale, alert and do not enable new entries",
        },
        {
            "check_id": "MON-004",
            "frequency": "300s",
            "source_a": "trade ledger",
            "source_b": "deal history",
            "owner": "user",
            "fail_closed_action": "if ledger mismatch, stop and reconcile",
        },
        {
            "check_id": "MON-005",
            "frequency": "60s",
            "source_a": "margin level",
            "source_b": "risk policy",
            "owner": "user",
            "fail_closed_action": "if margin level < 500%, block new entries",
        },
        {
            "check_id": "MON-006",
            "frequency": "live window start",
            "source_a": "alert channel",
            "source_b": "operator confirmation",
            "owner": "user",
            "fail_closed_action": "if not watched, do not start live",
        },
    ]

    reconciliation_pass = all(row["status"] == "pass" for row in reconciliation_rows)
    policy_path = OUT_DIR / "live_monitoring_policy.json"
    checklist_path = OUT_DIR / "reconciliation_checklist.csv"
    write_json(policy_path, policy)
    write_csv(checklist_path, checklist, ["check_id", "frequency", "source_a", "source_b", "owner", "fail_closed_action"])
    write_csv(
        OUT_DIR / "reconciliation_probe.csv",
        reconciliation_rows,
        ["check_id", "source_a", "source_b", "actual", "expected", "status", "fail_closed_action"],
    )

    checks = [
        check("post_emergency_gate_still_not_live", post_emergency.get("ready_to_live_trade") is False, post_emergency.get("ready_to_live_trade"), False),
        check("monitoring_policy_created", policy_path.exists(), str(policy_path), "exists"),
        check("reconciliation_checklist_created", checklist_path.exists(), str(checklist_path), "exists"),
        check("local_alert_test_log_created", alert_log.exists(), str(alert_log), "exists"),
        check("guard_rehearsal_ledger_reconciles", reconciliation_pass, "pass" if reconciliation_pass else "fail", "pass"),
        check("emergency_stop_flag_present", EMERGENCY_STOP_FLAG.exists(), str(EMERGENCY_STOP_FLAG), "exists"),
        check("runner_stop_flag_present", RUNNER_STOP_FLAG.exists(), str(RUNNER_STOP_FLAG), "exists"),
        check("terminal_process_snapshot_collected", True, len(processes), "collected"),
        check("watched_alert_channel_confirmed", False, "missing", "operator watched alert channel evidence", "blocker", "Local alert write-path is not enough for live operation."),
        check("live_reconciliation_operator_confirmed", False, "missing", "operator signed/confirmed reconciliation owner", "blocker", "Policy/checklist exists, but live operator confirmation is still absent."),
    ]

    blocker_failures = [row for row in checks if row["severity"] == "blocker" and not row["pass"]]
    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_live_monitoring_reconciliation_package",
        "status": "live_monitoring_policy_and_local_reconciliation_probe_ready_manual_watch_pending",
        "monitoring_policy_ready": True,
        "local_alert_write_path_tested": True,
        "reconciliation_probe_passed": reconciliation_pass,
        "watched_alert_channel_confirmed": False,
        "operator_reconciliation_confirmed": False,
        "terminal64_process_count": len(processes),
        "live_gap_008_closed": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "recommended_next_action": "collect_watched_alert_channel_and_operator_reconciliation_confirmation",
    }

    process_rows = processes if processes else [{"id": "", "process_name": "", "path": "", "state": "no_terminal64_process_seen"}]
    write_csv(OUT_DIR / "monitoring_terminal_process_snapshot.csv", process_rows, ["id", "process_name", "path", "state"])
    write_csv(OUT_DIR / "monitoring_reconciliation_checks.csv", checks, ["check_id", "status", "pass", "actual", "expected", "severity", "note"])
    write_csv(OUT_DIR / "monitoring_reconciliation_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "monitoring_reconciliation_decision.json", decision)

    report = f"""# LIVE-GAP-008 Monitoring / Alerts / Reconciliation Package

Generated: {generated_at}

## Decision

- Status: `{decision["status"]}`
- Monitoring policy ready: `true`
- Local alert write path tested: `true`
- Reconciliation probe passed: `{reconciliation_pass}`
- Watched alert channel confirmed: `false`
- Operator reconciliation confirmed: `false`
- LIVE-GAP-008 closed: `false`
- Ready to live trade: `false`

## Evidence

- Monitoring policy: `{policy_path}`
- Reconciliation checklist: `{checklist_path}`
- Alert test log: `{alert_log}`
- Reconciliation probe: `{OUT_DIR / "reconciliation_probe.csv"}`

## Remaining Blockers

- Operator must confirm a watched alert channel for the live window.
- Operator must confirm the reconciliation owner/process.
"""
    (OUT_DIR / "monitoring_reconciliation_summary.md").write_text(report, encoding="utf-8-sig")
    return 1 if blocker_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
