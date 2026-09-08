from __future__ import annotations


import csv
import json
import re
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(r"F:\use_code\MTA5_l")
VALIDATION_DIR = ROOT / "黄金" / "30m2H策略" / "data" / "validation"
POST_SMOKE_DIR = VALIDATION_DIR / "stage_state_post_smoke_decision_gate_20260718"
SMOKE_EXECUTION_DIR = VALIDATION_DIR / "stage_state_sim_dryrun_smoke_execution_review_20260718"
OUT_DIR = VALIDATION_DIR / "stage_state_sim_continuous_runner_design_package_20260718"

AUTO_TRADE = ROOT / "auto_trade"
TERMINAL_EXE = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")
LOCAL_EX5 = AUTO_TRADE / "30m2H_Strategy_EA.ex5"
SIM_SET = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_sim_dryrun_20260718.set"
SMOKE_INI = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_sim_dryrun_smoke_20260601_20260707.ini"
AUTO_TRADER = AUTO_TRADE / "auto_trader.py"
VERIFY_CONNECTION = AUTO_TRADE / "verify_connection.py"
SIGNAL_VALIDATOR = AUTO_TRADE / "signal_validator.py"


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def first_row(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    rows = read_rows(path)
    return rows[0] if rows else {}


def current_value(value: str) -> str:
    return value.split("||", 1)[0].strip()


def parse_set(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = current_value(value)
    return values


def file_contains_hardcoded_credential(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    password_pattern = re.compile(r"['\"]password['\"]\s*:\s*['\"][^'\"]+['\"]")
    account_pattern = re.compile(r"['\"]account['\"]\s*:\s*\d+")
    login_pattern = re.compile(r"\blogin\s*=\s*CONFIG\[['\"]account['\"]\]")
    return bool(password_pattern.search(text) and account_pattern.search(text) and login_pattern.search(text))


def python_runner_strategy_stale(path: Path) -> bool:
    if not path.exists():
        return True
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    required_current_markers = [
        "InpUseLayer3",
        "InpUseM15EarlyEntry",
        "InpEnableM15Slot2",
        "InpExportTradeLedger",
        "stage_state",
    ]
    return not all(marker in text for marker in required_current_markers)


def add_check(
    rows: List[Dict[str, object]],
    check_id: str,
    passed: bool,
    actual: object,
    expected: object,
    severity: str = "blocker",
    note: str = "",
) -> None:
    rows.append(
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


def scope_rows() -> List[Dict[str, object]]:
    return [
        {
            "area": "runtime",
            "decision": "MT5 terminal plus deployed EX5 on XAUUSDm M30 chart",
            "allowed": True,
            "blocked": False,
            "note": "Signal-only continuous forward dry-run; not a Python trading bot.",
        },
        {
            "area": "mode_lock",
            "decision": "InpSimMode must remain true",
            "allowed": True,
            "blocked": False,
            "note": "Any config with InpSimMode=false belongs to a separate live approval gate.",
        },
        {
            "area": "python_auto_trader",
            "decision": "Do not use auto_trade/auto_trader.py as runner",
            "allowed": False,
            "blocked": True,
            "note": "It is stale for the frozen EA and contains credential risk.",
        },
        {
            "area": "live_trade",
            "decision": "Live trading remains closed",
            "allowed": False,
            "blocked": True,
            "note": "No real order placement, no InpSimMode=false, no live runner.",
        },
    ]


def risk_control_rows() -> List[Dict[str, object]]:
    return [
        {
            "control_id": "sim_only_lock",
            "default": "true",
            "failure_action": "stop_runner_and_alert",
            "acceptance": "Every runner config and EA input snapshot has InpSimMode=true.",
        },
        {
            "control_id": "allowed_symbol_period",
            "default": "XAUUSDm/M30",
            "failure_action": "stop_runner_and_alert",
            "acceptance": "Runner refuses any symbol/period outside XAUUSDm/M30.",
        },
        {
            "control_id": "max_real_positions_allowed",
            "default": "0",
            "failure_action": "stop_runner_and_alert",
            "acceptance": "Monitor reports failure if real positions/orders are detected.",
        },
        {
            "control_id": "kill_switch_file",
            "default": "auto_trade/RUNNER_STOP.flag",
            "failure_action": "stop_runner",
            "acceptance": "Creating the flag stops or blocks the runner before next cycle.",
        },
        {
            "control_id": "signal_csv_max_age_minutes",
            "default": "90",
            "failure_action": "alert",
            "acceptance": "When market is expected open, signal export freshness is monitored.",
        },
        {
            "control_id": "daily_loss_limit",
            "default": "0_real_money_loss_allowed",
            "failure_action": "stop_runner_and_alert",
            "acceptance": "Any real-money loss in sim-only mode is treated as critical.",
        },
    ]


def monitoring_rows() -> List[Dict[str, object]]:
    return [
        {
            "monitor_id": "terminal_process",
            "source": "Get-Process terminal64",
            "pass_condition": "terminal64 exists during scheduled forward dry-run window",
            "failure_action": "alert_or_restart_after_manual_approval",
        },
        {
            "monitor_id": "mode_banner",
            "source": "terminal/experts log",
            "pass_condition": "latest EA init contains SIMULATION or InpSimMode=true evidence",
            "failure_action": "stop_runner_and_alert",
        },
        {
            "monitor_id": "signal_export_freshness",
            "source": "30m2H_strategy_signals_export.csv",
            "pass_condition": "file exists and LastWriteTime is within configured threshold when market is open",
            "failure_action": "alert",
        },
        {
            "monitor_id": "trade_ledger_no_real_rows",
            "source": "30m2H_strategy_trade_ledger.csv",
            "pass_condition": "0 data rows while InpSimMode=true",
            "failure_action": "stop_runner_and_alert",
        },
        {
            "monitor_id": "critical_log_errors",
            "source": "terminal/tester/experts logs",
            "pass_condition": "no initialization failure, no invalid symbol/period, no live order send",
            "failure_action": "stop_runner_and_alert",
        },
        {
            "monitor_id": "heartbeat_file",
            "source": "validation/runner heartbeat json",
            "pass_condition": "heartbeat updated every monitor cycle",
            "failure_action": "alert",
        },
    ]


def forward_dryrun_test_rows() -> List[Dict[str, object]]:
    return [
        {
            "test_id": "preflight_config_lock",
            "data": "sim dry-run set/config template",
            "method": "parse config and set",
            "acceptance": "InpSimMode=true, live_trade_enabled=false, allowed_symbol=XAUUSDm, allowed_period=M30.",
        },
        {
            "test_id": "manual_chart_attach_smoke",
            "data": "MT5 chart XAUUSDm M30 with frozen EX5",
            "method": "attach EA using sim dry-run set and watch init log",
            "acceptance": "EA initializes in SIMULATION mode without strategy init errors.",
        },
        {
            "test_id": "signal_export_forward_update",
            "data": "live-market M30/M15 ticks during forward window",
            "method": "monitor CSV LastWriteTime and row count",
            "acceptance": "signal CSV updates when new bars arrive; no stale-output alert.",
        },
        {
            "test_id": "no_real_order_artifacts",
            "data": "trade ledger and MT5 positions/orders",
            "method": "check ledger rows and optional terminal account view",
            "acceptance": "trade ledger has 0 real data rows and terminal has no new real orders/positions.",
        },
        {
            "test_id": "stop_flag_behavior",
            "data": "RUNNER_STOP.flag",
            "method": "create stop flag before next monitor cycle",
            "acceptance": "runner refuses to continue or reports stopped state.",
        },
        {
            "test_id": "post_run_review",
            "data": "logs, CSV, heartbeat, monitor report",
            "method": "run validation review script",
            "acceptance": "forward dry-run decision status is pass and ready_to_live_trade remains false.",
        },
    ]


def implementation_tasks() -> List[Dict[str, object]]:
    return [
        {
            "step_id": "safe_config_file",
            "status": "pending",
            "deliverable": "Create an actual sim-only runner config from the template without secrets.",
            "acceptance": "Config validates and contains live_trade_enabled=false plus InpSimMode=true.",
        },
        {
            "step_id": "monitor_script",
            "status": "pending",
            "deliverable": "Implement monitor/preflight script that checks terminal, logs, CSV freshness, ledger rows, and stop flag.",
            "acceptance": "Script emits decision CSV/JSON and fails closed on unsafe conditions.",
        },
        {
            "step_id": "manual_runbook_trial",
            "status": "pending",
            "deliverable": "Use the runbook to attach EA to XAUUSDm M30 in MT5 with sim dry-run set.",
            "acceptance": "SIMULATION mode is visible in log and no live order is sent.",
        },
        {
            "step_id": "forward_dryrun_review",
            "status": "pending",
            "deliverable": "Run a short forward dry-run review after at least one new M30 bar.",
            "acceptance": "CSV updates, ledger stays header-only, monitor status pass.",
        },
    ]


def config_template() -> Dict[str, object]:
    return {
        "schema_version": 1,
        "package": "stage_state_sim_continuous_runner_design_20260718",
        "mode": "SIM_ONLY_DESIGN_TEMPLATE",
        "live_trade_enabled": False,
        "sim_only_lock": True,
        "do_not_run": ["auto_trade/auto_trader.py"],
        "terminal": {
            "path": str(TERMINAL_EXE),
            "launch_requires_manual_approval": True,
            "window_style": "hidden_or_manual",
        },
        "ea": {
            "expert": "Advisors\\30m2H_Strategy_EA.ex5",
            "local_ex5": str(LOCAL_EX5),
            "parameter_set": str(SIM_SET),
            "required_inputs": {
                "InpSymbol": "XAUUSDm",
                "InpRiskPct": "3.0",
                "InpUseDynamicLots": "true",
                "InpExportCSV": "true",
                "InpExportTradeLedger": "true",
                "InpSimMode": "true",
            },
        },
        "chart": {"symbol": "XAUUSDm", "period": "M30"},
        "secrets": {
            "store_credentials_in_this_config": False,
            "source": "existing MT5 terminal session/profile or external secret store only",
        },
        "risk_controls": {
            "max_real_positions_allowed": 0,
            "max_real_orders_allowed": 0,
            "daily_real_money_loss_allowed": 0,
            "kill_switch_file": str(AUTO_TRADE / "RUNNER_STOP.flag"),
            "allowed_symbol": "XAUUSDm",
            "allowed_period": "M30",
        },
        "monitoring": {
            "heartbeat_file": str(OUT_DIR / "sim_continuous_runner_heartbeat.json"),
            "signal_csv_max_age_minutes": 90,
            "ledger_data_rows_expected": 0,
            "alert_file": str(OUT_DIR / "sim_continuous_runner_alerts.jsonl"),
        },
    }


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def write_md(decision: Dict[str, object]) -> None:
    lines = [
        "# Sim Continuous Runner Design Package",
        "",
        f"- Decision date: {decision['decision_date']}",
        f"- Status: `{decision['status']}`",
        f"- Ready to implementation package: `{decision['ready_to_sim_continuous_runner_implementation']}`",
        f"- Ready to execution: `{decision['ready_to_sim_continuous_runner_execution']}`",
        f"- Ready to live trade: `{decision['ready_to_live_trade']}`",
        f"- Blocker failure count: `{decision['blocker_failure_count']}`",
        "",
        "## Boundary",
        "",
        "- This package designs a local MT5 signal-only forward dry-run runner.",
        "- It does not start continuous running.",
        "- It does not approve live trading.",
        "- It does not use `auto_trade/auto_trader.py`.",
        "- `InpSimMode=true` is a hard requirement.",
        "",
        "## Package Files",
        "",
        "- `sim_continuous_runner_config_template.json`",
        "- `sim_continuous_runner_scope.csv`",
        "- `sim_continuous_runner_risk_controls.csv`",
        "- `sim_continuous_runner_monitoring_spec.csv`",
        "- `sim_continuous_runner_forward_dryrun_test_plan.csv`",
        "- `sim_continuous_runner_implementation_tasks.csv`",
        "- `sim_continuous_runner_runbook.md`",
        "",
        "## Next Gate",
        "",
        "- Build the implementation package: safe config file, monitor/preflight script, manual MT5 chart runbook trial, and forward dry-run review.",
        "- Execution remains blocked until that implementation gate passes.",
    ]
    (OUT_DIR / "sim_continuous_runner_design_package.md").write_text("\n".join(lines), encoding="utf-8-sig")
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8-sig")


def write_runbook() -> None:
    lines = [
        "# Sim Continuous Runner Runbook",
        "",
        "## Start Preconditions",
        "",
        "- Use `XAUUSDm` / `M30` only.",
        "- Load `auto_trade/30m2H_Strategy_EA.stage_state_sim_dryrun_20260718.set`.",
        "- Confirm `InpSimMode=true` before enabling the EA.",
        "- Do not run `auto_trade/auto_trader.py`.",
        "- Keep live trading approval closed.",
        "",
        "## Manual Forward Dry-run Flow",
        "",
        "1. Open MT5 terminal with the account already configured in MT5.",
        "2. Open an `XAUUSDm` `M30` chart.",
        "3. Attach `Advisors\\30m2H_Strategy_EA.ex5`.",
        "4. Load the sim dry-run set and verify `InpSimMode=true`.",
        "5. Watch the Experts/Journal log for `SIMULATION` mode.",
        "6. Let at least one new M30 bar close.",
        "7. Check signal CSV freshness and confirm trade ledger remains header-only.",
        "8. Run the future forward dry-run review script before opening any execution gate.",
        "",
        "## Stop Flow",
        "",
        "1. Disable Algo Trading or remove the EA from the chart.",
        "2. Create `auto_trade/RUNNER_STOP.flag` once monitor implementation exists.",
        "3. Save/copy no credentials into project files.",
    ]
    (OUT_DIR / "sim_continuous_runner_runbook.md").write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    post_smoke = first_row(POST_SMOKE_DIR / "post_smoke_decision_gate_decision.csv")
    smoke_execution = first_row(SMOKE_EXECUTION_DIR / "sim_dryrun_smoke_execution_decision.csv")
    sim_values = parse_set(SIM_SET)

    hardcoded_files = [
        str(path.relative_to(ROOT))
        for path in [AUTO_TRADER, VERIFY_CONNECTION, SIGNAL_VALIDATOR]
        if file_contains_hardcoded_credential(path)
    ]
    stale_auto_trader = python_runner_strategy_stale(AUTO_TRADER)

    checks: List[Dict[str, object]] = []
    add_check(checks, "post_smoke_design_gate_ready", truthy(post_smoke.get("ready_to_sim_continuous_runner_design")), post_smoke.get("ready_to_sim_continuous_runner_design", "missing"), "True")
    add_check(checks, "post_smoke_execution_not_open", not truthy(post_smoke.get("ready_to_sim_continuous_runner_execution")), post_smoke.get("ready_to_sim_continuous_runner_execution", "missing"), "False")
    add_check(checks, "post_smoke_live_not_open", not truthy(post_smoke.get("ready_to_live_trade")), post_smoke.get("ready_to_live_trade", "missing"), "False")
    add_check(checks, "smoke_execution_passed", truthy(smoke_execution.get("smoke_execution_passed")), smoke_execution.get("smoke_execution_passed", "missing"), "True")
    add_check(checks, "terminal_exe_exists", TERMINAL_EXE.exists(), str(TERMINAL_EXE), "exists")
    add_check(checks, "local_ex5_exists", LOCAL_EX5.exists(), str(LOCAL_EX5), "exists")
    add_check(checks, "sim_set_exists", SIM_SET.exists(), str(SIM_SET), "exists")
    add_check(checks, "sim_set_inp_sim_mode_true", sim_values.get("InpSimMode") == "true", sim_values.get("InpSimMode", ""), "true")
    add_check(checks, "sim_set_export_csv_true", sim_values.get("InpExportCSV") == "true", sim_values.get("InpExportCSV", ""), "true")
    add_check(checks, "sim_set_export_trade_ledger_true", sim_values.get("InpExportTradeLedger") == "true", sim_values.get("InpExportTradeLedger", ""), "true")
    add_check(checks, "smoke_ini_exists_for_reference", SMOKE_INI.exists(), str(SMOKE_INI), "exists", "warning")
    add_check(checks, "hardcoded_credentials_are_known_blocker", len(hardcoded_files) > 0, len(hardcoded_files), "> 0", "warning", "Design package keeps runner independent from these files until isolation is implemented.")
    add_check(checks, "auto_trader_is_not_current_runner", stale_auto_trader, "stale_or_incomplete" if stale_auto_trader else "current", "stale_or_incomplete", "warning", "This is expected; design explicitly blocks this runner path.")
    add_check(checks, "live_trade_remains_closed", True, "closed_by_design", "closed")
    add_check(checks, "continuous_execution_remains_closed", True, "closed_by_design", "closed")

    blocker_failures = [row for row in checks if row["severity"] == "blocker" and row["status"] == "fail"]
    warning_failures = [row for row in checks if row["severity"] == "warning" and row["status"] == "fail"]
    ready = len(blocker_failures) == 0

    decision = {
        "decision_date": date.today().isoformat(),
        "check_id": "stage_state_sim_continuous_runner_design_package",
        "status": "pass" if ready else "fail",
        "pass": ready,
        "ready_to_sim_continuous_runner_design": ready,
        "ready_to_sim_continuous_runner_implementation": ready,
        "ready_to_sim_continuous_runner_execution": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "warning_count": len(warning_failures),
        "hardcoded_credential_file_count": len(hardcoded_files),
        "reason": "sim_continuous_runner_design_package_ready" if ready else "sim_continuous_runner_design_package_has_blockers",
        "next_action": "build_sim_continuous_runner_implementation_package" if ready else "fix_design_package_blockers",
        "no_ea_or_python_strategy_logic_changes_in_this_step": True,
    }

    write_json(OUT_DIR / "sim_continuous_runner_config_template.json", config_template())
    write_md(decision)
    write_runbook()
    write_csv(OUT_DIR / "sim_continuous_runner_design_decision.csv", [decision], list(decision.keys()))
    write_csv(
        OUT_DIR / "sim_continuous_runner_design_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(
        OUT_DIR / "sim_continuous_runner_scope.csv",
        scope_rows(),
        ["area", "decision", "allowed", "blocked", "note"],
    )
    write_csv(
        OUT_DIR / "sim_continuous_runner_risk_controls.csv",
        risk_control_rows(),
        ["control_id", "default", "failure_action", "acceptance"],
    )
    write_csv(
        OUT_DIR / "sim_continuous_runner_monitoring_spec.csv",
        monitoring_rows(),
        ["monitor_id", "source", "pass_condition", "failure_action"],
    )
    write_csv(
        OUT_DIR / "sim_continuous_runner_forward_dryrun_test_plan.csv",
        forward_dryrun_test_rows(),
        ["test_id", "data", "method", "acceptance"],
    )
    write_csv(
        OUT_DIR / "sim_continuous_runner_implementation_tasks.csv",
        implementation_tasks(),
        ["step_id", "status", "deliverable", "acceptance"],
    )
    write_csv(
        OUT_DIR / "sim_continuous_runner_credential_findings.csv",
        [{"file": item, "issue": "hardcoded_credential_pattern_detected", "action": "isolate_before_runner_execution"} for item in hardcoded_files],
        ["file", "issue", "action"],
    )

    print(f"status={decision['status']}")
    print(f"ready_to_sim_continuous_runner_implementation={decision['ready_to_sim_continuous_runner_implementation']}")
    print(f"ready_to_sim_continuous_runner_execution={decision['ready_to_sim_continuous_runner_execution']}")
    print(f"ready_to_live_trade={decision['ready_to_live_trade']}")
    print(f"blocker_failure_count={decision['blocker_failure_count']}")
    print(f"warning_count={decision['warning_count']}")
    print(f"hardcoded_credential_file_count={decision['hardcoded_credential_file_count']}")
    print(f"output_dir={OUT_DIR}")


if __name__ == "__main__":
    main()
