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
STARTUP_DIR = VALIDATION_DIR / "stage_state_sim_only_startup_attach_gate_20260719"
EXECUTION_GATE_DIR = VALIDATION_DIR / "stage_state_sim_continuous_runner_execution_gate_20260720"
FINITE_DIR = VALIDATION_DIR / "stage_state_sim_continuous_runner_finite_trial_20260720"
OBSERVATION_DIR = VALIDATION_DIR / "stage_state_sim_continuous_runner_observation_window_20260720"
OUT_DIR = VALIDATION_DIR / "stage_state_sim_only_post_observation_readiness_gate_20260720"

CONFIG_PATH = SIM_ONLY_DIR / "sim_continuous_runner_config_20260720.json"
CHART_DECISION = SIM_ONLY_DIR / "sim_only_chart_trial_decision.json"
CHART_CHECKS = SIM_ONLY_DIR / "sim_only_chart_trial_checks.csv"
STARTUP_DECISION = STARTUP_DIR / "sim_only_startup_attach_decision.json"
STARTUP_CHECKS = STARTUP_DIR / "sim_only_startup_attach_checks.csv"
FORWARD_DECISION = SIM_ONLY_DIR / "forward_review_20260720_config_01" / "sim_continuous_runner_monitor_decision.json"
FORWARD_CHECKS = SIM_ONLY_DIR / "forward_review_20260720_config_01" / "sim_continuous_runner_monitor_checks.csv"
EXECUTION_DECISION = EXECUTION_GATE_DIR / "sim_continuous_runner_execution_gate_decision.json"
EXECUTION_CHECKS = EXECUTION_GATE_DIR / "sim_continuous_runner_execution_gate_checks.csv"
FINITE_DECISION = FINITE_DIR / "finite_runner_trial_decision.json"
FINITE_CHECKS = FINITE_DIR / "finite_runner_trial_checks.csv"
OBSERVATION_DECISION = OBSERVATION_DIR / "finite_runner_trial_decision.json"
OBSERVATION_CHECKS = OBSERVATION_DIR / "finite_runner_trial_checks.csv"
OBSERVATION_CYCLES = OBSERVATION_DIR / "finite_runner_trial_cycles.csv"
TERMINAL_EXE = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")


def read_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


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
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


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


def failed_non_pending(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [row for row in rows if row.get("status") != "pass" and row.get("severity") != "pending"]


def failed_all(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [row for row in rows if row.get("status") != "pass"]


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


def existing_path(value: object) -> bool:
    text = str(value or "").strip()
    return bool(text) and Path(text).exists()


def build_report(decision: Dict[str, object], checks: List[Dict[str, object]]) -> str:
    failed = [row for row in checks if row["status"] != "pass"]
    lines = [
        "# SIM_ONLY Post Observation Readiness Gate",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- ready_to_continue_sim_only_monitoring: `{decision['ready_to_continue_sim_only_monitoring']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        f"- blocker_failure_count: `{decision['blocker_failure_count']}`",
        f"- observation_cycles_completed: `{decision['observation_cycles_completed']}`",
        f"- observation_signal_rows_first: `{decision['observation_signal_rows_first']}`",
        f"- observation_signal_rows_last: `{decision['observation_signal_rows_last']}`",
        f"- observation_trade_ledger_rows_last: `{decision['observation_trade_ledger_rows_last']}`",
        f"- positions_count: `{decision['positions_count']}`",
        f"- orders_count: `{decision['orders_count']}`",
        "",
        "## Allowed Next Action",
        "",
        "- Continue bounded SIM_ONLY monitoring with the finite runner and the 20260720 SIM_ONLY config.",
        "- Keep `ready_to_live_trade` false.",
        "- Keep `auto_trade/auto_trader.py` blocked.",
        "- Keep `InpSimMode=true`.",
        "",
        "## Stop Method",
        "",
        "- Create `auto_trade/RUNNER_STOP.flag` before the next cycle to stop a bounded runner cleanly.",
        "- If ledger rows become non-zero, positions/orders become non-zero, or a live marker appears, fail closed.",
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
    chart = read_json(CHART_DECISION)
    startup = read_json(STARTUP_DECISION)
    forward = read_json(FORWARD_DECISION)
    execution = read_json(EXECUTION_DECISION)
    finite = read_json(FINITE_DECISION)
    observation = read_json(OBSERVATION_DECISION)
    cycles = read_rows(OBSERVATION_CYCLES)
    counts = mt5_counts()

    chart_checks = read_rows(CHART_CHECKS)
    startup_checks = read_rows(STARTUP_CHECKS)
    forward_checks = read_rows(FORWARD_CHECKS)
    execution_checks = read_rows(EXECUTION_CHECKS)
    finite_checks = read_rows(FINITE_CHECKS)
    observation_checks = read_rows(OBSERVATION_CHECKS)

    checks: List[Dict[str, object]] = []
    add_check(checks, "config_exists", CONFIG_PATH.exists(), CONFIG_PATH, "exists")
    add_check(checks, "config_live_trade_disabled", config.get("live_trade_enabled") is False, config.get("live_trade_enabled"), False)
    add_check(checks, "config_sim_only_lock", config.get("sim_only_lock") is True, config.get("sim_only_lock"), True)
    add_check(checks, "config_execution_not_auto_opened", config.get("execution_enabled") is False, config.get("execution_enabled"), False)
    add_check(checks, "config_auto_trader_blocked", "auto_trade/auto_trader.py" in (config.get("do_not_run") or []), config.get("do_not_run"), "contains auto_trade/auto_trader.py")
    add_check(checks, "sim_only_ex5_exists", existing_path(dict(config.get("ea", {}) or {}).get("local_ex5")), dict(config.get("ea", {}) or {}).get("local_ex5"), "exists")
    add_check(checks, "sim_only_set_exists", existing_path(dict(config.get("ea", {}) or {}).get("parameter_set")), dict(config.get("ea", {}) or {}).get("parameter_set"), "exists")
    add_check(checks, "kill_switch_absent", not Path(r"F:\use_code\MTA5_l\auto_trade\RUNNER_STOP.flag").exists(), "absent", "absent")

    add_check(checks, "chart_package_pass", chart.get("status") == "pass", chart.get("status"), "pass")
    add_check(checks, "chart_checks_pass", not failed_non_pending(chart_checks), len(failed_non_pending(chart_checks)), 0)
    add_check(checks, "chart_live_trade_closed", chart.get("ready_to_live_trade") is False, chart.get("ready_to_live_trade"), False)

    add_check(checks, "startup_attach_accepted_status", startup.get("status") == "pass_attach_pending_market_data", startup.get("status"), "pass_attach_pending_market_data")
    add_check(checks, "startup_terminal_attached", truthy(startup.get("terminal_running_and_attached")), startup.get("terminal_running_and_attached"), True)
    add_check(checks, "startup_no_non_pending_failures", not failed_non_pending(startup_checks), len(failed_non_pending(startup_checks)), 0)
    add_check(checks, "startup_pending_resolved_by_forward_review", bool(failed_all(startup_checks)) and forward.get("status") == "pass", f"startup_pending={len(failed_all(startup_checks))}, forward={forward.get('status')}", "pending resolved by forward pass")

    add_check(checks, "forward_review_pass", forward.get("status") == "pass" and truthy(forward.get("pass")), forward.get("status"), "pass")
    add_check(checks, "forward_checks_pass", not failed_non_pending(forward_checks), len(failed_non_pending(forward_checks)), 0)
    add_check(checks, "forward_live_trade_closed", forward.get("ready_to_live_trade") is False, forward.get("ready_to_live_trade"), False)
    add_check(checks, "forward_signal_rows_positive", int_value(forward.get("signal_csv_rows")) > 0, forward.get("signal_csv_rows"), "> 0")
    add_check(checks, "forward_trade_ledger_zero", int_value(forward.get("trade_ledger_rows")) == 0, forward.get("trade_ledger_rows"), 0)

    add_check(checks, "execution_gate_pass", execution.get("status") == "pass", execution.get("status"), "pass")
    add_check(checks, "execution_checks_pass", not failed_non_pending(execution_checks), len(failed_non_pending(execution_checks)), 0)
    add_check(checks, "execution_ready_sim_only", execution.get("ready_to_sim_continuous_runner_execution") is True, execution.get("ready_to_sim_continuous_runner_execution"), True)
    add_check(checks, "execution_live_trade_closed", execution.get("ready_to_live_trade") is False, execution.get("ready_to_live_trade"), False)

    add_check(checks, "finite_trial_pass", finite.get("status") == "pass", finite.get("status"), "pass")
    add_check(checks, "finite_checks_pass", not failed_non_pending(finite_checks), len(failed_non_pending(finite_checks)), 0)
    add_check(checks, "finite_live_trade_closed", finite.get("ready_to_live_trade") is False, finite.get("ready_to_live_trade"), False)
    add_check(checks, "finite_positions_zero", int_value(finite.get("last_positions_count"), -1) == 0, finite.get("last_positions_count"), 0)
    add_check(checks, "finite_orders_zero", int_value(finite.get("last_orders_count"), -1) == 0, finite.get("last_orders_count"), 0)

    add_check(checks, "observation_pass", observation.get("status") == "pass", observation.get("status"), "pass")
    add_check(checks, "observation_checks_pass", not failed_non_pending(observation_checks), len(failed_non_pending(observation_checks)), 0)
    add_check(checks, "observation_live_trade_closed", observation.get("ready_to_live_trade") is False, observation.get("ready_to_live_trade"), False)
    add_check(checks, "observation_cycles_12", int_value(observation.get("cycles_completed")) == 12, observation.get("cycles_completed"), 12)
    add_check(checks, "observation_no_failed_cycles", int_value(observation.get("failed_cycles_count")) == 0, observation.get("failed_cycles_count"), 0)
    add_check(checks, "observation_last_ledger_zero", int_value(observation.get("last_trade_ledger_rows"), -1) == 0, observation.get("last_trade_ledger_rows"), 0)
    add_check(checks, "observation_last_positions_zero", int_value(observation.get("last_positions_count"), -1) == 0, observation.get("last_positions_count"), 0)
    add_check(checks, "observation_last_orders_zero", int_value(observation.get("last_orders_count"), -1) == 0, observation.get("last_orders_count"), 0)

    all_cycle_pass = bool(cycles) and all(row.get("status") == "pass" and row.get("monitor_status") == "pass" for row in cycles)
    all_cycle_blockers_zero = bool(cycles) and all(int_value(row.get("monitor_blocker_failure_count")) == 0 for row in cycles)
    all_cycle_ledger_zero = bool(cycles) and all(int_value(row.get("trade_ledger_rows"), -1) == 0 for row in cycles)
    all_cycle_positions_zero = bool(cycles) and all(int_value(row.get("positions_count"), -1) == 0 for row in cycles)
    all_cycle_orders_zero = bool(cycles) and all(int_value(row.get("orders_count"), -1) == 0 for row in cycles)
    first_signal_rows = int_value(cycles[0].get("signal_csv_rows")) if cycles else 0
    last_signal_rows = int_value(cycles[-1].get("signal_csv_rows")) if cycles else 0
    add_check(checks, "observation_cycle_rows_12", len(cycles) == 12, len(cycles), 12)
    add_check(checks, "observation_all_cycles_pass", all_cycle_pass, all_cycle_pass, True)
    add_check(checks, "observation_all_cycle_blockers_zero", all_cycle_blockers_zero, all_cycle_blockers_zero, True)
    add_check(checks, "observation_all_cycle_ledger_zero", all_cycle_ledger_zero, all_cycle_ledger_zero, True)
    add_check(checks, "observation_all_cycle_positions_zero", all_cycle_positions_zero, all_cycle_positions_zero, True)
    add_check(checks, "observation_all_cycle_orders_zero", all_cycle_orders_zero, all_cycle_orders_zero, True)
    add_check(checks, "observation_signal_rows_non_decreasing", last_signal_rows >= first_signal_rows > 0, f"{first_signal_rows}->{last_signal_rows}", "non-decreasing and > 0")

    add_check(checks, "mt5_counts_available", truthy(counts.get("ok")), counts.get("error") or counts.get("ok"), True)
    add_check(checks, "mt5_positions_zero_now", counts.get("positions_count") == 0, counts.get("positions_count"), 0)
    add_check(checks, "mt5_orders_zero_now", counts.get("orders_count") == 0, counts.get("orders_count"), 0)

    blocker_failures = [row for row in checks if row["status"] == "fail" and row["severity"] == "blocker"]
    gate_pass = not blocker_failures
    decision = {
        "decision_time": datetime.now().isoformat(timespec="seconds"),
        "check_id": "stage_state_sim_only_post_observation_readiness_gate",
        "status": "pass" if gate_pass else "fail",
        "ready_to_continue_sim_only_monitoring": gate_pass,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "observation_cycles_completed": observation.get("cycles_completed", ""),
        "observation_signal_rows_first": first_signal_rows,
        "observation_signal_rows_last": last_signal_rows,
        "observation_trade_ledger_rows_last": observation.get("last_trade_ledger_rows", ""),
        "positions_count": counts.get("positions_count", ""),
        "orders_count": counts.get("orders_count", ""),
        "config_path": str(CONFIG_PATH),
        "observation_decision": str(OBSERVATION_DECISION),
        "continue_sim_only_command": "python 黄金/30m2H策略\\scripts\\validate\\sim_continuous_runner_finite_trial_20260720.py --config 黄金/30m2H策略\\data\\validation\\stage_state_sim_only_chart_trial_package_20260719\\sim_continuous_runner_config_20260720.json --out-dir 黄金/30m2H策略\\data\\validation\\stage_state_sim_continuous_runner_next_window --cycles 12 --interval-sec 300",
        "stop_flag_file": str(ROOT / "auto_trade" / "RUNNER_STOP.flag"),
    }

    write_csv(
        OUT_DIR / "sim_only_post_observation_readiness_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(OUT_DIR / "sim_only_post_observation_readiness_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "sim_only_post_observation_readiness_decision.json", decision)
    (OUT_DIR / "sim_only_post_observation_readiness_gate.md").write_text(build_report(decision, checks), encoding="utf-8-sig")

    print(json.dumps(decision, ensure_ascii=False, indent=2))
    return 0 if gate_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
