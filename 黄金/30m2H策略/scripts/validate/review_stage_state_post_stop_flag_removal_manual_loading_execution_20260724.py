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
OUT_DIR = VALIDATION_DIR / "stage_state_post_stop_flag_removal_manual_loading_execution_20260724"

APPROVAL_TEMPLATE_JSON = (
    VALIDATION_DIR
    / "stage_state_stop_flag_removal_manual_loading_approval_request_20260723"
    / "stop_flag_removal_manual_loading_approval_template.json"
)
LOADING_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_exact_mt5_ea_live_loading_package_20260723"
    / "exact_mt5_ea_live_loading_decision.json"
)
LOADING_MANIFEST_JSON = (
    VALIDATION_DIR
    / "stage_state_exact_mt5_ea_live_loading_package_20260723"
    / "exact_mt5_ea_live_loading_manifest.json"
)
EMERGENCY_STOP_FLAG = ROOT / "auto_trade" / "EMERGENCY_STOP.flag"
RUNNER_STOP_FLAG = ROOT / "auto_trade" / "RUNNER_STOP.flag"
TERMINAL_PATH = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")
SYMBOL = "XAUUSDm"


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


def check_row(
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
    import MetaTrader5 as mt5

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reviewed_at = datetime.now().isoformat(timespec="seconds")

    approval = read_json(APPROVAL_TEMPLATE_JSON)
    loading = read_json(LOADING_DECISION_JSON)
    manifest = read_json(LOADING_MANIFEST_JSON)
    approval_items = approval.get("approval_items", {})
    if not isinstance(approval_items, dict):
        approval_items = {}

    approval_required = len(approval_items)
    approval_signed = sum(1 for value in approval_items.values() if value is True)
    all_approved = approval_required > 0 and approval_signed == approval_required
    stop_flags_removed = not EMERGENCY_STOP_FLAG.exists() and not RUNNER_STOP_FLAG.exists()
    processes = terminal_process_snapshot()

    terminal_connected = False
    terminal_trade_allowed = None
    positions_count = ""
    orders_count = ""
    mt5_initialized = mt5.initialize(path=str(TERMINAL_PATH))
    if mt5_initialized:
        try:
            terminal = mt5.terminal_info()
            terminal_dict = terminal._asdict() if terminal else {}
            terminal_connected = bool(terminal_dict.get("connected"))
            terminal_trade_allowed = bool(terminal_dict.get("trade_allowed")) if "trade_allowed" in terminal_dict else None
            positions = mt5.positions_get(symbol=SYMBOL)
            orders = mt5.orders_get(symbol=SYMBOL)
            positions_count = len(positions) if positions is not None else ""
            orders_count = len(orders) if orders is not None else ""
        finally:
            mt5.shutdown()

    loading_package_ready = loading.get("status") == "exact_live_loading_package_ready_fail_closed"
    checks = [
        check_row("approval_items_all_signed", all_approved, approval_signed, approval_required),
        check_row("loading_package_ready", loading_package_ready, loading.get("status"), "exact_live_loading_package_ready_fail_closed"),
        check_row("stop_flags_removed", stop_flags_removed, stop_flags_removed, True),
        check_row("orders_placed_by_this_step", True, False, False, "blocker", "This review does not place orders."),
        check_row("runner_executed_by_this_step", True, False, False, "blocker", "This review does not run Python runner."),
        check_row("ea_loaded_evidence_collected", False, False, True, "manual_pending", "EA load must be verified by MT5 GUI/Experts evidence after manual loading."),
        check_row("ready_to_live_trade_false", True, False, False, "blocker", "Stop flag removal is not proof that EA is loaded and trading-ready."),
    ]
    blocker_failures = [row for row in checks if row["severity"] == "blocker" and not row["pass"]]
    manual_pending = [row for row in checks if row["severity"] == "manual_pending" and not row["pass"]]

    execution_rows = [
        {
            "event_time": reviewed_at,
            "event": "operator_approval_applied",
            "status": "approved" if all_approved else "blocked",
            "detail": f"approval_items_signed={approval_signed}/{approval_required}",
            "ready_to_live_trade": False,
        },
        {
            "event_time": reviewed_at,
            "event": "stop_flags_removed",
            "status": "completed" if stop_flags_removed else "blocked",
            "detail": f"EMERGENCY_STOP.flag exists={EMERGENCY_STOP_FLAG.exists()}; RUNNER_STOP.flag exists={RUNNER_STOP_FLAG.exists()}",
            "ready_to_live_trade": False,
        },
        {
            "event_time": reviewed_at,
            "event": "manual_ea_loading",
            "status": "pending_manual_evidence",
            "detail": "Load EA in MT5 GUI on XAUUSDm/M30 using approved set snapshot; collect post-load evidence.",
            "ready_to_live_trade": False,
        },
    ]

    terminal_row = {
        "snapshot_time": reviewed_at,
        "mt5_initialized": mt5_initialized,
        "terminal_connected": terminal_connected,
        "terminal_trade_allowed": terminal_trade_allowed,
        "terminal64_process_count": len(processes),
        "positions_count": positions_count,
        "orders_count": orders_count,
        "orders_placed": False,
        "runner_executed": False,
        "ea_loaded": False,
        "ready_to_live_trade": False,
    }

    decision = {
        "decision_time": reviewed_at,
        "check_id": "stage_state_post_stop_flag_removal_manual_loading_execution",
        "status": (
            "stop_flags_removed_manual_ea_loading_pending"
            if not blocker_failures and manual_pending
            else "post_stop_flag_removal_execution_blocked"
        ),
        "approval_items_signed": approval_signed,
        "approval_items_required": approval_required,
        "loading_package_ready": loading_package_ready,
        "stop_flags_removed": stop_flags_removed,
        "manual_ea_loading_pending": True,
        "terminal64_process_count": len(processes),
        "terminal_trade_allowed": terminal_trade_allowed,
        "positions_count": positions_count,
        "orders_count": orders_count,
        "orders_placed": False,
        "runner_executed": False,
        "ea_loaded": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "manual_pending_count": len(manual_pending),
        "recommended_next_action": "manually_load_ea_in_mt5_gui_then_collect_post_load_evidence",
    }

    write_csv(
        OUT_DIR / "post_stop_flag_removal_execution_events.csv",
        execution_rows,
        ["event_time", "event", "status", "detail", "ready_to_live_trade"],
    )
    write_csv(
        OUT_DIR / "post_stop_flag_removal_terminal_snapshot.csv",
        [terminal_row],
        list(terminal_row.keys()),
    )
    write_csv(OUT_DIR / "post_stop_flag_removal_checks.csv", checks, list(checks[0].keys()))
    write_csv(OUT_DIR / "post_stop_flag_removal_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "post_stop_flag_removal_decision.json", decision)

    report = f"""# Post Stop Flag Removal Execution Review

Generated: {reviewed_at}

## Decision

- Status: `{decision["status"]}`
- Approval items: `{approval_signed} / {approval_required}`
- Loading package ready: `{loading_package_ready}`
- Stop flags removed: `{stop_flags_removed}`
- Manual EA loading pending: `true`
- Terminal trade_allowed: `{terminal_trade_allowed}`
- Positions / orders: `{positions_count} / {orders_count}`
- Orders placed by this step: `false`
- Python runner executed: `false`
- EA loaded evidence: `false`
- Ready to live trade: `false`

## Manual Loading Target

- Terminal: `{TERMINAL_PATH}`
- EA EX5: `{manifest.get("ea_ex5")}`
- Set snapshot: `{manifest.get("live_loading_set_snapshot")}`
- Symbol/timeframe: `{manifest.get("symbol")} / {manifest.get("timeframe")}`

## Boundary

Stop flags were removed after explicit approval. The EA is not marked loaded until MT5 GUI/Experts evidence is collected.
"""
    (OUT_DIR / "post_stop_flag_removal_execution_review.md").write_text(report, encoding="utf-8-sig")
    return 0 if not blocker_failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
