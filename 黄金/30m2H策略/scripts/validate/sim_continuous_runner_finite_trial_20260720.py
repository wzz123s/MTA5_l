from __future__ import annotations


import argparse
import copy
import csv
import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from sim_continuous_runner_monitor_20260719 import path_from, read_json, run_monitor


DEFAULT_TERMINAL = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def int_value(value: object, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def terminal_path_from(config: Dict[str, object]) -> Path:
    terminal = dict(config.get("terminal", {}) or {})
    path = path_from(terminal.get("path"))
    return path or DEFAULT_TERMINAL


def kill_switch_from(config: Dict[str, object]) -> Optional[Path]:
    risk = dict(config.get("risk_controls", {}) or {})
    return path_from(risk.get("kill_switch_file"))


def mt5_counts(terminal_path: Path) -> Dict[str, object]:
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception as exc:
        return {"ok": False, "positions_count": "", "orders_count": "", "error": f"import failed: {exc}"}

    ok = mt5.initialize(path=str(terminal_path))
    if not ok:
        return {"ok": False, "positions_count": "", "orders_count": "", "error": str(mt5.last_error())}
    try:
        positions = mt5.positions_get() or []
        orders = mt5.orders_get() or []
        return {"ok": True, "positions_count": len(positions), "orders_count": len(orders), "error": ""}
    finally:
        mt5.shutdown()


def effective_monitor_config(config: Dict[str, object], out_dir: Path) -> Dict[str, object]:
    effective = copy.deepcopy(config)
    monitoring = dict(effective.get("monitoring", {}) or {})
    monitoring["heartbeat_file"] = str(out_dir / "finite_runner_heartbeat.json")
    monitoring["alert_file"] = str(out_dir / "finite_runner_alerts.jsonl")
    effective["monitoring"] = monitoring
    return effective


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


def reset_generated_outputs(out_dir: Path) -> None:
    for name in [
        "finite_runner_alerts.jsonl",
        "finite_runner_heartbeat.json",
        "finite_runner_trial.md",
        "finite_runner_trial_checks.csv",
        "finite_runner_trial_cycles.csv",
        "finite_runner_trial_decision.csv",
        "finite_runner_trial_decision.json",
        "finite_runner_effective_config.json",
    ]:
        path = out_dir / name
        if path.exists() and path.parent == out_dir:
            path.unlink()
    for child in out_dir.glob("cycle_*"):
        if child.parent == out_dir and child.is_dir():
            shutil.rmtree(child)


def build_report(decision: Dict[str, object], checks: List[Dict[str, object]], cycles: List[Dict[str, object]]) -> str:
    failed = [row for row in checks if row["status"] != "pass"]
    lines = [
        "# SIM Continuous Runner Finite Trial",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- ready_to_sim_continuous_runner_execution: `{decision['ready_to_sim_continuous_runner_execution']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        f"- cycles_requested: `{decision['cycles_requested']}`",
        f"- cycles_completed: `{decision['cycles_completed']}`",
        f"- failed_cycles_count: `{decision['failed_cycles_count']}`",
        f"- blocker_failure_count: `{decision['blocker_failure_count']}`",
        f"- last_signal_csv_rows: `{decision['last_signal_csv_rows']}`",
        f"- last_trade_ledger_rows: `{decision['last_trade_ledger_rows']}`",
        f"- last_positions_count: `{decision['last_positions_count']}`",
        f"- last_orders_count: `{decision['last_orders_count']}`",
        "",
        "## Boundary",
        "",
        "- This is a bounded SIM_ONLY continuous monitor trial.",
        "- It does not launch MT5, does not call `auto_trade/auto_trader.py`, and does not enable live trading.",
        "- `ready_to_live_trade` remains false.",
        "- The kill switch is `auto_trade/RUNNER_STOP.flag`; if present, the trial stops before the next cycle.",
        "",
        "## Cycle Summary",
        "",
    ]
    if not cycles:
        lines.append("- No monitor cycle completed.")
    else:
        for row in cycles:
            lines.append(
                "- cycle `{cycle}`: status `{status}`, monitor `{monitor_status}`, signal rows `{signal_csv_rows}`, "
                "ledger rows `{trade_ledger_rows}`, positions `{positions_count}`, orders `{orders_count}`".format(**row)
            )
    lines.extend(["", "## Failed Checks", ""])
    if not failed:
        lines.append("- None.")
    else:
        for row in failed:
            lines.append(f"- `{row['check_id']}`: {row['actual']} (expected {row['expected']})")
    lines.append("")
    return "\n".join(lines)


def cycle_passed(row: Dict[str, object]) -> bool:
    return (
        row.get("status") == "pass"
        and row.get("monitor_status") == "pass"
        and int_value(row.get("monitor_blocker_failure_count")) == 0
        and row.get("ready_to_live_trade") is False
        and int_value(row.get("trade_ledger_rows")) == 0
        and truthy(row.get("mt5_ok"))
        and int_value(row.get("positions_count"), -1) == 0
        and int_value(row.get("orders_count"), -1) == 0
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--interval-sec", type=float, default=20.0)
    args = parser.parse_args()

    config_path = Path(args.config).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    reset_generated_outputs(out_dir)

    config = read_json(config_path)
    terminal_path = terminal_path_from(config)
    kill_switch = kill_switch_from(config)
    effective_config = effective_monitor_config(config, out_dir)
    write_json(out_dir / "finite_runner_effective_config.json", effective_config)

    cycles: List[Dict[str, object]] = []
    stopped_by_kill_switch = False

    for index in range(1, args.cycles + 1):
        if kill_switch and kill_switch.exists():
            stopped_by_kill_switch = True
            break

        cycle_dir = out_dir / f"cycle_{index:03d}"
        start_time = datetime.now().isoformat(timespec="seconds")
        decision = run_monitor(effective_config, cycle_dir, "monitor")
        counts = mt5_counts(terminal_path)
        end_time = datetime.now().isoformat(timespec="seconds")

        row: Dict[str, object] = {
            "cycle": index,
            "start_time": start_time,
            "end_time": end_time,
            "status": "pass",
            "monitor_status": decision.get("status", ""),
            "monitor_blocker_failure_count": decision.get("blocker_failure_count", ""),
            "monitor_warning_count": decision.get("warning_count", ""),
            "terminal_running": decision.get("terminal_running", ""),
            "signal_csv_rows": decision.get("signal_csv_rows", ""),
            "trade_ledger_rows": decision.get("trade_ledger_rows", ""),
            "ready_to_live_trade": decision.get("ready_to_live_trade"),
            "mt5_ok": counts.get("ok"),
            "positions_count": counts.get("positions_count", ""),
            "orders_count": counts.get("orders_count", ""),
            "mt5_error": counts.get("error", ""),
            "cycle_out_dir": str(cycle_dir),
        }
        row["status"] = "pass" if cycle_passed(row) else "fail"
        cycles.append(row)

        if row["status"] != "pass":
            break
        if index < args.cycles and args.interval_sec > 0:
            time.sleep(args.interval_sec)

    failed_cycles = [row for row in cycles if row.get("status") != "pass"]
    last = cycles[-1] if cycles else {}
    checks: List[Dict[str, object]] = []
    add_check(checks, "config_exists", config_path.exists(), config_path, "exists")
    add_check(checks, "sim_only_lock_enabled", config.get("sim_only_lock") is True, config.get("sim_only_lock"), True)
    add_check(checks, "live_trade_disabled", config.get("live_trade_enabled") is False, config.get("live_trade_enabled"), False)
    add_check(checks, "execution_not_auto_opened", config.get("execution_enabled") is False, config.get("execution_enabled"), False)
    add_check(checks, "auto_trader_blocked", "auto_trade/auto_trader.py" in (config.get("do_not_run") or []), config.get("do_not_run"), "contains auto_trade/auto_trader.py")
    add_check(checks, "terminal_path_exists", terminal_path.exists(), terminal_path, "exists")
    add_check(checks, "kill_switch_absent_at_finish", not bool(kill_switch and kill_switch.exists()), kill_switch or "", "absent")
    add_check(checks, "not_stopped_by_kill_switch", not stopped_by_kill_switch, stopped_by_kill_switch, False)
    add_check(checks, "cycles_completed", len(cycles) == args.cycles, len(cycles), args.cycles)
    add_check(checks, "all_monitor_cycles_pass", not failed_cycles and len(cycles) == args.cycles, len(failed_cycles), 0)
    add_check(checks, "all_monitor_blockers_zero", all(int_value(row.get("monitor_blocker_failure_count")) == 0 for row in cycles), "all zero", "all zero")
    add_check(checks, "all_monitor_live_trade_closed", all(row.get("ready_to_live_trade") is False for row in cycles), "all false", "all false")
    add_check(checks, "all_trade_ledger_rows_zero", all(int_value(row.get("trade_ledger_rows")) == 0 for row in cycles), "all zero", "all zero")
    add_check(checks, "all_mt5_counts_available", all(truthy(row.get("mt5_ok")) for row in cycles), "all available", "all available")
    add_check(checks, "all_mt5_positions_zero", all(int_value(row.get("positions_count"), -1) == 0 for row in cycles), "all zero", "all zero")
    add_check(checks, "all_mt5_orders_zero", all(int_value(row.get("orders_count"), -1) == 0 for row in cycles), "all zero", "all zero")

    blocker_failures = [row for row in checks if row["status"] == "fail" and row["severity"] == "blocker"]
    status = "stopped_by_kill_switch" if stopped_by_kill_switch else ("pass" if not blocker_failures else "fail")
    decision = {
        "decision_time": datetime.now().isoformat(timespec="seconds"),
        "check_id": "stage_state_sim_continuous_runner_finite_trial",
        "status": status,
        "pass": status == "pass",
        "ready_to_sim_continuous_runner_execution": status == "pass",
        "ready_to_live_trade": False,
        "cycles_requested": args.cycles,
        "cycles_completed": len(cycles),
        "interval_sec": args.interval_sec,
        "failed_cycles_count": len(failed_cycles),
        "blocker_failure_count": len(blocker_failures),
        "stopped_by_kill_switch": stopped_by_kill_switch,
        "last_signal_csv_rows": last.get("signal_csv_rows", ""),
        "last_trade_ledger_rows": last.get("trade_ledger_rows", ""),
        "last_positions_count": last.get("positions_count", ""),
        "last_orders_count": last.get("orders_count", ""),
        "config_path": str(config_path),
        "out_dir": str(out_dir),
        "kill_switch_file": str(kill_switch or ""),
    }

    write_csv(
        out_dir / "finite_runner_trial_cycles.csv",
        cycles,
        [
            "cycle",
            "start_time",
            "end_time",
            "status",
            "monitor_status",
            "monitor_blocker_failure_count",
            "monitor_warning_count",
            "terminal_running",
            "signal_csv_rows",
            "trade_ledger_rows",
            "ready_to_live_trade",
            "mt5_ok",
            "positions_count",
            "orders_count",
            "mt5_error",
            "cycle_out_dir",
        ],
    )
    write_csv(
        out_dir / "finite_runner_trial_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(out_dir / "finite_runner_trial_decision.csv", [decision], list(decision.keys()))
    write_json(out_dir / "finite_runner_trial_decision.json", decision)
    (out_dir / "finite_runner_trial.md").write_text(build_report(decision, checks, cycles), encoding="utf-8-sig")

    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
