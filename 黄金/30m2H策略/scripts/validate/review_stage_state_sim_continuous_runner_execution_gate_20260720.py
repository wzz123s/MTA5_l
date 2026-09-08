from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
SIM_ONLY_DIR = VALIDATION_DIR / "stage_state_sim_only_chart_trial_package_20260719"
OUT_DIR = VALIDATION_DIR / "stage_state_sim_continuous_runner_execution_gate_20260720"

CONFIG_PATH = SIM_ONLY_DIR / "sim_continuous_runner_config_20260720.json"
FORWARD_DECISION = SIM_ONLY_DIR / "forward_review_20260720_config_01" / "sim_continuous_runner_monitor_decision.json"
FORWARD_CHECKS = SIM_ONLY_DIR / "forward_review_20260720_config_01" / "sim_continuous_runner_monitor_checks.csv"
MONITOR_DECISION = SIM_ONLY_DIR / "monitor_probe_20260720_config_01" / "sim_continuous_runner_monitor_decision.json"
MONITOR_CHECKS = SIM_ONLY_DIR / "monitor_probe_20260720_config_01" / "sim_continuous_runner_monitor_checks.csv"
STARTUP_ATTACH_DECISION = VALIDATION_DIR / "stage_state_sim_only_startup_attach_gate_20260719" / "sim_only_startup_attach_decision.json"
TERMINAL_EXE = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def mt5_counts() -> Dict[str, object]:
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception as exc:
        return {"ok": False, "positions_count": "", "orders_count": "", "error": f"import failed: {exc}"}
    ok = mt5.initialize(path=str(TERMINAL_EXE))
    if not ok:
        return {"ok": False, "positions_count": "", "orders_count": "", "error": str(mt5.last_error())}
    try:
        positions = mt5.positions_get() or []
        orders = mt5.orders_get() or []
        return {"ok": True, "positions_count": len(positions), "orders_count": len(orders), "error": ""}
    finally:
        mt5.shutdown()


def add_check(
    checks: List[Dict[str, object]],
    check_id: str,
    passed: bool,
    actual: object,
    expected: object,
    severity: str = "blocker",
    note: str = "",
) -> None:
    checks.append(
        {
            "check_id": check_id,
            "status": "pass" if passed else "fail",
            "pass": passed,
            "actual": actual,
            "expected": expected,
            "severity": severity,
            "note": note,
        }
    )


def all_checks_pass(rows: List[Dict[str, str]]) -> bool:
    return bool(rows) and all(row.get("status") == "pass" for row in rows)


def build_report(decision: Dict[str, object], checks: List[Dict[str, object]]) -> str:
    failed = [row for row in checks if row["status"] != "pass"]
    lines = [
        "# SIM Continuous Runner Execution Gate",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- ready_to_sim_continuous_runner_execution: `{decision['ready_to_sim_continuous_runner_execution']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        f"- blocker_failure_count: `{decision['blocker_failure_count']}`",
        f"- forward_review_status: `{decision['forward_review_status']}`",
        f"- monitor_probe_status: `{decision['monitor_probe_status']}`",
        f"- signal_csv_rows: `{decision['signal_csv_rows']}`",
        f"- trade_ledger_rows: `{decision['trade_ledger_rows']}`",
        f"- positions_count: `{decision['positions_count']}`",
        f"- orders_count: `{decision['orders_count']}`",
        "",
        "## Boundary",
        "",
        "- This opens the SIM_ONLY continuous monitoring/execution gate only.",
        "- `ready_to_live_trade` remains false.",
        "- `auto_trade/auto_trader.py` remains blocked.",
        "- The active EA is `30m2H_Strategy_EA_SIM_ONLY.ex5` with `InpSimMode=true`.",
        "- Trade ledger is expected to stay at 0 data rows in SIM_ONLY mode.",
        "",
        "## Failed Checks",
        "",
    ]
    if not failed:
        lines.append("- None.")
    else:
        for row in failed:
            lines.append(f"- `{row['check_id']}`: {row['actual']} (expected {row['expected']})")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    config = read_json(CONFIG_PATH)
    forward = read_json(FORWARD_DECISION)
    monitor = read_json(MONITOR_DECISION)
    startup = read_json(STARTUP_ATTACH_DECISION)
    forward_checks = read_rows(FORWARD_CHECKS)
    monitor_checks = read_rows(MONITOR_CHECKS)
    counts = mt5_counts()

    checks: List[Dict[str, object]] = []
    add_check(checks, "config_exists", CONFIG_PATH.exists(), CONFIG_PATH, "exists")
    add_check(checks, "config_live_trade_disabled", config.get("live_trade_enabled") is False, config.get("live_trade_enabled"), False)
    add_check(checks, "config_sim_only_lock", config.get("sim_only_lock") is True, config.get("sim_only_lock"), True)
    add_check(checks, "config_execution_not_auto_opened", config.get("execution_enabled") is False, config.get("execution_enabled"), False)
    add_check(checks, "config_blocks_auto_trader", "auto_trade/auto_trader.py" in (config.get("do_not_run") or []), config.get("do_not_run"), "contains auto_trade/auto_trader.py")
    add_check(checks, "config_uses_sim_only_ex5", "SIM_ONLY" in str(config.get("ea", {}).get("expert", "")), config.get("ea", {}).get("expert", ""), "SIM_ONLY expert")
    add_check(checks, "startup_attach_ready", truthy(startup.get("terminal_running_and_attached")), startup.get("terminal_running_and_attached"), True)
    add_check(checks, "forward_review_pass", forward.get("status") == "pass" and truthy(forward.get("pass")), forward.get("status"), "pass")
    add_check(checks, "forward_review_checks_pass", all_checks_pass(forward_checks), "pass" if all_checks_pass(forward_checks) else "fail", "all pass")
    add_check(checks, "monitor_probe_pass", monitor.get("status") == "pass" and truthy(monitor.get("pass")), monitor.get("status"), "pass")
    add_check(checks, "monitor_probe_checks_pass", all_checks_pass(monitor_checks), "pass" if all_checks_pass(monitor_checks) else "fail", "all pass")
    add_check(checks, "forward_live_trade_closed", forward.get("ready_to_live_trade") is False, forward.get("ready_to_live_trade"), False)
    add_check(checks, "monitor_live_trade_closed", monitor.get("ready_to_live_trade") is False, monitor.get("ready_to_live_trade"), False)
    add_check(checks, "signal_csv_has_runtime_rows", int(forward.get("signal_csv_rows") or 0) > 0, forward.get("signal_csv_rows"), "> 0")
    add_check(checks, "trade_ledger_has_no_rows", int(forward.get("trade_ledger_rows") or 0) == 0, forward.get("trade_ledger_rows"), 0)
    add_check(checks, "mt5_counts_available", truthy(counts.get("ok")), counts.get("error") or counts.get("ok"), True)
    add_check(checks, "mt5_positions_zero", counts.get("positions_count") == 0, counts.get("positions_count"), 0)
    add_check(checks, "mt5_orders_zero", counts.get("orders_count") == 0, counts.get("orders_count"), 0)

    blocker_failures = [row for row in checks if row["status"] == "fail" and row["severity"] == "blocker"]
    gate_pass = not blocker_failures
    decision = {
        "decision_time": datetime.now().isoformat(timespec="seconds"),
        "check_id": "stage_state_sim_continuous_runner_execution_gate",
        "status": "pass" if gate_pass else "fail",
        "ready_to_sim_continuous_runner_execution": gate_pass,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "forward_review_status": forward.get("status", ""),
        "monitor_probe_status": monitor.get("status", ""),
        "signal_csv_rows": forward.get("signal_csv_rows", 0),
        "trade_ledger_rows": forward.get("trade_ledger_rows", 0),
        "positions_count": counts.get("positions_count", ""),
        "orders_count": counts.get("orders_count", ""),
        "config_path": str(CONFIG_PATH),
        "forward_review_decision": str(FORWARD_DECISION),
        "monitor_probe_decision": str(MONITOR_DECISION),
    }

    write_csv(
        OUT_DIR / "sim_continuous_runner_execution_gate_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(
        OUT_DIR / "sim_continuous_runner_execution_gate_decision.csv",
        [decision],
        [
            "decision_time",
            "check_id",
            "status",
            "ready_to_sim_continuous_runner_execution",
            "ready_to_live_trade",
            "blocker_failure_count",
            "forward_review_status",
            "monitor_probe_status",
            "signal_csv_rows",
            "trade_ledger_rows",
            "positions_count",
            "orders_count",
            "config_path",
            "forward_review_decision",
            "monitor_probe_decision",
        ],
    )
    write_json(OUT_DIR / "sim_continuous_runner_execution_gate_decision.json", decision)
    (OUT_DIR / "sim_continuous_runner_execution_gate.md").write_text(build_report(decision, checks), encoding="utf-8-sig")

    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
