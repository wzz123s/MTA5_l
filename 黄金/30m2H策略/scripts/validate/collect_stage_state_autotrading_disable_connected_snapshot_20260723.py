from __future__ import annotations


import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_autotrading_disable_connected_snapshot_20260723"

TERMINAL_PATH = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")
EMERGENCY_STOP_FLAG = ROOT / "auto_trade" / "EMERGENCY_STOP.flag"
RUNNER_STOP_FLAG = ROOT / "auto_trade" / "RUNNER_STOP.flag"


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def terminal_process_snapshot() -> List[Dict[str, object]]:
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-Process terminal64 -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,Path,StartTime | ConvertTo-Json -Compress",
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
            "start_time": row.get("StartTime", ""),
        }
        for row in parsed
    ]


def check(check_id: str, passed: bool, actual: object, expected: object, note: str = "") -> Dict[str, object]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "pass": passed,
        "actual": actual,
        "expected": expected,
        "severity": "blocker",
        "note": note,
    }


def main() -> int:
    import MetaTrader5 as mt5

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now().isoformat(timespec="seconds")
    processes_before = terminal_process_snapshot()

    initialized = mt5.initialize(path=str(TERMINAL_PATH))
    if not initialized:
        decision = {
            "decision_time": collected_at,
            "check_id": "stage_state_autotrading_disable_connected_snapshot",
            "status": "mt5_initialize_failed",
            "mt5_last_error": str(mt5.last_error()),
            "orders_placed": False,
            "runner_executed": False,
            "ready_to_live_trade": False,
        }
        write_json(OUT_DIR / "autotrading_disable_connected_snapshot_decision.json", decision)
        return 1

    try:
        terminal = mt5.terminal_info()
        terminal_dict = terminal._asdict() if terminal else {}
        trade_allowed = bool(terminal_dict.get("trade_allowed")) if "trade_allowed" in terminal_dict else None
        connected = bool(terminal_dict.get("connected")) if "connected" in terminal_dict else None
        tradeapi_disabled = terminal_dict.get("tradeapi_disabled", "")
        processes_after = terminal_process_snapshot()

        terminal_row = {
            "snapshot_type": "connected_session_terminal_info",
            "terminal_path": str(TERMINAL_PATH),
            "build": terminal_dict.get("build", ""),
            "connected": connected,
            "trade_allowed": trade_allowed,
            "tradeapi_disabled": tradeapi_disabled,
            "process_count_before": len(processes_before),
            "process_count_after": len(processes_after),
            "collected_at": collected_at,
            "ready_to_live_trade": False,
        }
        flag_row = {
            "emergency_stop_flag_exists": EMERGENCY_STOP_FLAG.exists(),
            "runner_stop_flag_exists": RUNNER_STOP_FLAG.exists(),
            "emergency_stop_flag": str(EMERGENCY_STOP_FLAG),
            "runner_stop_flag": str(RUNNER_STOP_FLAG),
            "collected_at": collected_at,
            "ready_to_live_trade": False,
        }
        checks = [
            check("mt5_initialized", True, True, True),
            check("terminal_connected", connected is True, connected, True),
            check("terminal_trade_allowed_false", trade_allowed is False, trade_allowed, False),
            check("emergency_stop_flag_exists", EMERGENCY_STOP_FLAG.exists(), EMERGENCY_STOP_FLAG.exists(), True),
            check("runner_stop_flag_exists", RUNNER_STOP_FLAG.exists(), RUNNER_STOP_FLAG.exists(), True),
            check("orders_placed", True, False, False, "snapshot is read-only and does not call order_send"),
            check("runner_executed", True, False, False, "auto_trade runner is not invoked"),
        ]
        blocker_failures = [row for row in checks if row["severity"] == "blocker" and not row["pass"]]
        connected_confirmed = not blocker_failures
        decision = {
            "decision_time": collected_at,
            "check_id": "stage_state_autotrading_disable_connected_snapshot",
            "status": (
                "connected_session_autotrading_disabled_confirmed"
                if connected_confirmed
                else "connected_session_autotrading_disabled_not_confirmed"
            ),
            "terminal_connected": connected,
            "terminal_trade_allowed": trade_allowed,
            "terminal_tradeapi_disabled": tradeapi_disabled,
            "emergency_stop_flag_exists": EMERGENCY_STOP_FLAG.exists(),
            "runner_stop_flag_exists": RUNNER_STOP_FLAG.exists(),
            "connected_session_autotrading_disable_confirmed": connected_confirmed,
            "manual_ui_screenshot_supplied": False,
            "orders_placed": False,
            "runner_executed": False,
            "blocker_failure_count": len(blocker_failures),
            "ready_to_live_trade": False,
        }

        write_csv(
            OUT_DIR / "autotrading_disable_terminal_snapshot.csv",
            [terminal_row],
            list(terminal_row.keys()),
        )
        write_csv(OUT_DIR / "autotrading_disable_stop_flags.csv", [flag_row], list(flag_row.keys()))
        write_csv(OUT_DIR / "autotrading_disable_connected_checks.csv", checks, list(checks[0].keys()))
        write_csv(
            OUT_DIR / "autotrading_disable_connected_snapshot_decision.csv",
            [decision],
            list(decision.keys()),
        )
        write_json(OUT_DIR / "autotrading_disable_connected_snapshot_decision.json", decision)

        report = f"""# AutoTrading Disable Connected-Session Snapshot

Generated: {collected_at}

## Decision

- Status: `{decision["status"]}`
- Terminal connected: `{connected}`
- Terminal trade_allowed: `{trade_allowed}`
- Emergency stop flag exists: `{EMERGENCY_STOP_FLAG.exists()}`
- Runner stop flag exists: `{RUNNER_STOP_FLAG.exists()}`
- Orders placed: `false`
- Runner executed: `false`
- Ready to live trade: `false`

## Summary

This is a read-only connected-session snapshot. It verifies the terminal-side trading permission and stop flags without placing orders or invoking the Python runner.
"""
        (OUT_DIR / "autotrading_disable_connected_snapshot_review.md").write_text(
            report,
            encoding="utf-8-sig",
        )
        return 0 if connected_confirmed else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
