from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_live_monitoring_manual_confirmation_package_20260723"

POLICY_JSON = (
    VALIDATION_DIR
    / "stage_state_live_monitoring_reconciliation_package_20260723"
    / "live_monitoring_policy.json"
)
MONITORING_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_live_monitoring_reconciliation_package_20260723"
    / "monitoring_reconciliation_decision.json"
)
ACCOUNT_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_live_account_spec_snapshot_read_only_20260723"
    / "live_account_spec_snapshot_decision.json"
)
AUTOTRADING_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_autotrading_disable_connected_snapshot_20260723"
    / "autotrading_disable_connected_snapshot_decision.json"
)


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
    generated_at = datetime.now().isoformat(timespec="seconds")

    policy = read_json(POLICY_JSON)
    monitoring = read_json(MONITORING_DECISION_JSON)
    account = read_json(ACCOUNT_DECISION_JSON)
    autotrading = read_json(AUTOTRADING_DECISION_JSON)

    alert_channels = policy.get("alert_channels", {}) if isinstance(policy.get("alert_channels"), dict) else {}
    checks = policy.get("checks", {}) if isinstance(policy.get("checks"), dict) else {}
    account_alias = account.get("account_alias", "MT5_ACCOUNT_REDACTED")
    server = account.get("server", "")
    symbol = account.get("symbol", "XAUUSDm")

    confirmation_template = {
        "generated_at": generated_at,
        "source": "manual_confirmation_template_not_signed",
        "account_alias": account_alias,
        "server": server,
        "symbol": symbol,
        "watched_alert_channel_confirmed": False,
        "operator_reconciliation_confirmed": False,
        "operator_alias": "manual_pending",
        "watched_alert_channels": {
            "local_file": alert_channels.get("local_file", ""),
            "terminal_journal": alert_channels.get("terminal_journal", ""),
            "external_watched_channel": alert_channels.get("external_watched_channel", "manual_pending"),
        },
        "watch_frequency_sec": checks.get("terminal_process", {}).get("frequency_sec", 60)
        if isinstance(checks.get("terminal_process"), dict)
        else 60,
        "reconciliation_frequency_sec": checks.get("trade_ledger_reconciliation", {}).get("frequency_sec", 300)
        if isinstance(checks.get("trade_ledger_reconciliation"), dict)
        else 300,
        "mismatch_action": "create/keep EMERGENCY_STOP.flag and RUNNER_STOP.flag; stop new entries; review before resume",
        "stop_action": "close MT5 Algo Trading / AutoTrading and keep stop flags until gate is rerun",
        "ready_to_live_trade": False,
        "credential_values_output": False,
    }

    requirements = [
        {
            "requirement_id": "WATCH-001",
            "requirement": "confirm watched alert channel",
            "minimum_evidence": "operator confirms local alert file and MT5 Journal/Experts are actively watched during run window, or supplies an external watched channel",
            "current_status": "pending_human_confirmation",
            "ready_to_live_trade": False,
        },
        {
            "requirement_id": "WATCH-002",
            "requirement": "confirm operator alias",
            "minimum_evidence": "non-secret operator alias or role responsible for monitoring",
            "current_status": "pending_human_confirmation",
            "ready_to_live_trade": False,
        },
        {
            "requirement_id": "RECON-001",
            "requirement": "confirm reconciliation cadence",
            "minimum_evidence": "operator confirms reconciliation every 300 seconds or after each deal, using signal export, trade ledger, and deal history",
            "current_status": "pending_human_confirmation",
            "ready_to_live_trade": False,
        },
        {
            "requirement_id": "RECON-002",
            "requirement": "confirm mismatch handling",
            "minimum_evidence": "operator confirms mismatch keeps stop flags and blocks resume until explained",
            "current_status": "pending_human_confirmation",
            "ready_to_live_trade": False,
        },
    ]

    decision = {
        "decision_time": generated_at,
        "check_id": "stage_state_live_monitoring_manual_confirmation_package",
        "status": "manual_monitoring_confirmation_package_ready_not_confirmed",
        "monitoring_policy_ready": monitoring.get("monitoring_policy_ready") is True,
        "local_alert_write_path_tested": monitoring.get("local_alert_write_path_tested") is True,
        "reconciliation_probe_passed": monitoring.get("reconciliation_probe_passed") is True,
        "terminal_trade_allowed": autotrading.get("terminal_trade_allowed"),
        "stop_flags_ready": (
            autotrading.get("emergency_stop_flag_exists") is True
            and autotrading.get("runner_stop_flag_exists") is True
        ),
        "watched_alert_channel_confirmed": False,
        "operator_reconciliation_confirmed": False,
        "manual_confirmation_file": str(OUT_DIR / "watched_alert_operator_confirmation_template.json"),
        "ready_to_live_trade": False,
        "recommended_next_action": "human_operator_confirms_template_then_rerun_post_monitoring_confirmation_gate_update",
    }

    write_json(OUT_DIR / "watched_alert_operator_confirmation_template.json", confirmation_template)
    write_csv(
        OUT_DIR / "monitoring_manual_confirmation_requirements.csv",
        requirements,
        ["requirement_id", "requirement", "minimum_evidence", "current_status", "ready_to_live_trade"],
    )
    write_csv(
        OUT_DIR / "monitoring_manual_confirmation_package_decision.csv",
        [decision],
        list(decision.keys()),
    )
    write_json(OUT_DIR / "monitoring_manual_confirmation_package_decision.json", decision)

    report = f"""# LIVE-GAP-008 Manual Monitoring Confirmation Package

Generated: {generated_at}

## Current Automated Evidence

- Monitoring policy ready: `{decision["monitoring_policy_ready"]}`
- Local alert write path tested: `{decision["local_alert_write_path_tested"]}`
- Reconciliation probe passed: `{decision["reconciliation_probe_passed"]}`
- Terminal trade_allowed: `{decision["terminal_trade_allowed"]}`
- Stop flags ready: `{decision["stop_flags_ready"]}`
- Ready to live trade: `false`

## Required Human Confirmation

1. Confirm the watched alert channel.
2. Confirm the operator alias/role watching alerts.
3. Confirm reconciliation cadence and data sources.
4. Confirm mismatch handling keeps the system stopped until review.

## Confirmation Template

Use `watched_alert_operator_confirmation_template.json` as the non-secret approval record. Do not write full account numbers, passwords, investor passwords, or API tokens.
"""
    (OUT_DIR / "monitoring_manual_confirmation_package.md").write_text(report, encoding="utf-8-sig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
