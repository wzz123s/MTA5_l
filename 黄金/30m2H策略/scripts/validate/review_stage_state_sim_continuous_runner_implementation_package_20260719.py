from __future__ import annotations


import csv
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(r"F:\use_code\MTA5_l")
VALIDATION_DIR = ROOT / "黄金" / "30m2H策略" / "data" / "validation"
DESIGN_DIR = VALIDATION_DIR / "stage_state_sim_continuous_runner_design_package_20260718"
SMOKE_EXECUTION_DIR = VALIDATION_DIR / "stage_state_sim_dryrun_smoke_execution_review_20260718"
OUT_DIR = VALIDATION_DIR / "stage_state_sim_continuous_runner_implementation_package_20260719"

AUTO_TRADE = ROOT / "auto_trade"
MONITOR_SCRIPT = ROOT / "黄金" / "30m2H策略" / "scripts" / "validate" / "sim_continuous_runner_monitor_20260719.py"
CONFIG_PATH = OUT_DIR / "sim_continuous_runner_config_20260719.json"
PREFLIGHT_OUT_DIR = OUT_DIR / "monitor_preflight"
TERMINAL_DATA = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"
)

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


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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


def build_safe_config() -> Dict[str, object]:
    template = read_json(DESIGN_DIR / "sim_continuous_runner_config_template.json")
    config: Dict[str, object] = dict(template)
    config["package"] = "stage_state_sim_continuous_runner_implementation_20260719"
    config["mode"] = "SIM_ONLY_IMPLEMENTATION_PREFLIGHT"
    config["execution_enabled"] = False
    config["live_trade_enabled"] = False
    config["sim_only_lock"] = True
    config["manual_chart_trial_required"] = True
    config["forward_dryrun_review_required"] = True
    config["credential_policy"] = {
        "runner_uses_python_auto_trader": False,
        "runner_uses_hardcoded_python_credentials": False,
        "blocked_source_files": [
            "auto_trade/auto_trader.py",
            "auto_trade/verify_connection.py",
            "auto_trade/signal_validator.py",
        ],
    }
    config["monitor_script"] = str(MONITOR_SCRIPT)

    monitoring = dict(config.get("monitoring", {}) or {})
    monitoring["heartbeat_file"] = str(OUT_DIR / "sim_continuous_runner_heartbeat.json")
    monitoring["alert_file"] = str(OUT_DIR / "sim_continuous_runner_alerts.jsonl")
    monitoring["preflight_allow_stale_archive"] = True
    monitoring["signal_csv_candidates"] = [
        str(TERMINAL_DATA / "MQL5" / "Files" / "30m2H_strategy_signals_export.csv"),
        str(SMOKE_EXECUTION_DIR / "30m2H_strategy_signals_export_smoke.csv")
    ]
    monitoring["trade_ledger_candidates"] = [
        str(TERMINAL_DATA / "MQL5" / "Files" / "30m2H_strategy_trade_ledger.csv"),
        str(SMOKE_EXECUTION_DIR / "30m2H_strategy_trade_ledger_smoke.csv")
    ]
    monitoring["log_candidates"] = [
        str(TERMINAL_DATA / "logs" / "20260719.log"),
        str(SMOKE_EXECUTION_DIR / "terminal_20260718_smoke.log"),
        str(SMOKE_EXECUTION_DIR / "tester_20260718_smoke.log"),
        str(SMOKE_EXECUTION_DIR / "tester_agent_20260718_smoke.log"),
    ]
    config["monitoring"] = monitoring
    return config


def config_has_secret_literal(config_path: Path) -> bool:
    text = config_path.read_text(encoding="utf-8-sig", errors="ignore")
    password_pattern = re.compile(r"password\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE)
    account_pattern = re.compile(r"account\s*[:=]\s*\d{4,}", re.IGNORECASE)
    return bool(password_pattern.search(text) or account_pattern.search(text))


def run_preflight() -> Dict[str, object]:
    result = subprocess.run(
        [
            sys.executable,
            str(MONITOR_SCRIPT),
            "--config",
            str(CONFIG_PATH),
            "--out-dir",
            str(PREFLIGHT_OUT_DIR),
            "--mode",
            "preflight",
        ],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        timeout=60,
    )
    (OUT_DIR / "sim_continuous_runner_monitor_preflight_stdout.txt").write_text(
        result.stdout + result.stderr,
        encoding="utf-8-sig",
    )
    decision_path = PREFLIGHT_OUT_DIR / "sim_continuous_runner_monitor_decision.json"
    decision = read_json(decision_path) if decision_path.exists() else {}
    decision["process_returncode"] = result.returncode
    return decision


def manual_trial_rows() -> List[Dict[str, object]]:
    return [
        {
            "step_id": "open_chart",
            "status": "pending",
            "action": "Open MT5 and select XAUUSDm M30 chart.",
            "acceptance": "Chart symbol/period equals XAUUSDm/M30.",
        },
        {
            "step_id": "attach_ea",
            "status": "pending",
            "action": "Attach Advisors\\30m2H_Strategy_EA.ex5.",
            "acceptance": "EA init log appears without initialization error.",
        },
        {
            "step_id": "load_sim_set",
            "status": "pending",
            "action": "Load auto_trade/30m2H_Strategy_EA.stage_state_sim_dryrun_20260718.set.",
            "acceptance": "InpSimMode=true, InpExportCSV=true, InpExportTradeLedger=true.",
        },
        {
            "step_id": "observe_sim_marker",
            "status": "pending",
            "action": "Observe Experts/Journal log.",
            "acceptance": "SIMULATION mode marker is present.",
        },
        {
            "step_id": "run_monitor",
            "status": "pending",
            "action": "Run monitor in forward-review mode after at least one new M30 bar.",
            "acceptance": "Monitor status pass, ready_to_live_trade remains false.",
        },
    ]


def write_commands_md() -> None:
    preflight = (
        f'python "{MONITOR_SCRIPT}" --config "{CONFIG_PATH}" '
        f'--out-dir "{PREFLIGHT_OUT_DIR}" --mode preflight'
    )
    forward = (
        f'python "{MONITOR_SCRIPT}" --config "{CONFIG_PATH}" '
        f'--out-dir "{OUT_DIR / "monitor_forward_review"}" --mode forward-review'
    )
    lines = [
        "# Sim Continuous Runner Monitor Commands",
        "",
        "Preflight command:",
        "",
        "```powershell",
        preflight,
        "```",
        "",
        "Forward-review command after manual MT5 chart trial:",
        "",
        "```powershell",
        forward,
        "```",
        "",
        "Execution boundary:",
        "",
        "- These commands do not run `auto_trade/auto_trader.py`.",
        "- The config has `live_trade_enabled=false` and `sim_only_lock=true`.",
        "- Forward-review does not approve live trading.",
    ]
    (OUT_DIR / "sim_continuous_runner_monitor_commands.md").write_text("\n".join(lines), encoding="utf-8-sig")


def write_gate_md(decision: Dict[str, object]) -> None:
    lines = [
        "# Sim Continuous Runner Implementation Package",
        "",
        f"- Decision date: {decision['decision_date']}",
        f"- Status: `{decision['status']}`",
        f"- Ready to manual chart trial: `{decision['ready_to_manual_chart_trial']}`",
        f"- Ready to sim continuous runner execution: `{decision['ready_to_sim_continuous_runner_execution']}`",
        f"- Ready to live trade: `{decision['ready_to_live_trade']}`",
        f"- Blocker failure count: `{decision['blocker_failure_count']}`",
        "",
        "## What Exists Now",
        "",
        "- A no-secret sim-only runner config.",
        "- A reusable preflight/monitor script.",
        "- A monitor preflight run with decision CSV/JSON.",
        "- A manual chart trial checklist.",
        "",
        "## Still Closed",
        "",
        "- Continuous execution is not opened.",
        "- Live trading is not opened.",
        "- `auto_trade/auto_trader.py` remains blocked from this path.",
        "",
        "## Next Gate",
        "",
        "- Manual MT5 chart trial with `InpSimMode=true`.",
        "- Then run monitor in `forward-review` mode after at least one new M30 bar.",
    ]
    (OUT_DIR / "sim_continuous_runner_implementation_package.md").write_text("\n".join(lines), encoding="utf-8-sig")
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PREFLIGHT_OUT_DIR.mkdir(parents=True, exist_ok=True)

    design = first_row(DESIGN_DIR / "sim_continuous_runner_design_decision.csv")
    hardcoded_files = [
        str(path.relative_to(ROOT))
        for path in [AUTO_TRADER, VERIFY_CONNECTION, SIGNAL_VALIDATOR]
        if file_contains_hardcoded_credential(path)
    ]

    config = build_safe_config()
    write_json(CONFIG_PATH, config)
    preflight_decision = run_preflight()

    checks: List[Dict[str, object]] = []
    add_check(checks, "design_package_ready", truthy(design.get("ready_to_sim_continuous_runner_implementation")), design.get("ready_to_sim_continuous_runner_implementation", "missing"), "True")
    add_check(checks, "design_execution_not_open", not truthy(design.get("ready_to_sim_continuous_runner_execution")), design.get("ready_to_sim_continuous_runner_execution", "missing"), "False")
    add_check(checks, "config_exists", CONFIG_PATH.exists(), str(CONFIG_PATH), "exists")
    add_check(checks, "config_live_trade_false", config.get("live_trade_enabled") is False, config.get("live_trade_enabled"), "False")
    add_check(checks, "config_execution_false", config.get("execution_enabled") is False, config.get("execution_enabled"), "False")
    add_check(checks, "config_sim_only_lock_true", config.get("sim_only_lock") is True, config.get("sim_only_lock"), "True")
    add_check(checks, "config_blocks_auto_trader", "auto_trade/auto_trader.py" in (config.get("do_not_run") or []), config.get("do_not_run"), "contains auto_trade/auto_trader.py")
    add_check(checks, "config_has_no_secret_literal", not config_has_secret_literal(CONFIG_PATH), "no secret literal detected", "no account/password literal")
    add_check(checks, "monitor_script_exists", MONITOR_SCRIPT.exists(), str(MONITOR_SCRIPT), "exists")
    add_check(checks, "monitor_preflight_returncode", preflight_decision.get("process_returncode") == 0, preflight_decision.get("process_returncode", "missing"), "0")
    add_check(checks, "monitor_preflight_passed", truthy(preflight_decision.get("pass")), preflight_decision.get("pass", "missing"), "True")
    add_check(checks, "monitor_execution_still_closed", not truthy(preflight_decision.get("ready_to_sim_continuous_runner_execution")), preflight_decision.get("ready_to_sim_continuous_runner_execution", "missing"), "False")
    add_check(checks, "monitor_live_still_closed", not truthy(preflight_decision.get("ready_to_live_trade")), preflight_decision.get("ready_to_live_trade", "missing"), "False")
    add_check(checks, "credential_risk_files_identified", len(hardcoded_files) == 3, len(hardcoded_files), "3", "warning", "Files are blocked from runner path; values are not output.")

    blocker_failures = [row for row in checks if row["severity"] == "blocker" and row["status"] == "fail"]
    warning_failures = [row for row in checks if row["severity"] == "warning" and row["status"] == "fail"]
    passed = len(blocker_failures) == 0
    decision = {
        "decision_date": date.today().isoformat(),
        "check_id": "stage_state_sim_continuous_runner_implementation_package",
        "status": "pass" if passed else "fail",
        "pass": passed,
        "ready_to_manual_chart_trial": passed,
        "ready_to_sim_continuous_runner_execution": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "warning_count": len(warning_failures),
        "monitor_preflight_status": preflight_decision.get("status", ""),
        "hardcoded_credential_file_count": len(hardcoded_files),
        "reason": "sim_continuous_runner_implementation_package_ready_for_manual_chart_trial" if passed else "sim_continuous_runner_implementation_package_has_blockers",
        "next_action": "manual_mt5_chart_trial_then_forward_review_monitor",
        "no_ea_or_python_strategy_logic_changes_in_this_step": True,
    }

    write_commands_md()
    write_gate_md(decision)
    write_csv(OUT_DIR / "sim_continuous_runner_implementation_decision.csv", [decision], list(decision.keys()))
    write_csv(
        OUT_DIR / "sim_continuous_runner_implementation_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(
        OUT_DIR / "sim_continuous_runner_manual_chart_trial_checklist.csv",
        manual_trial_rows(),
        ["step_id", "status", "action", "acceptance"],
    )
    write_csv(
        OUT_DIR / "sim_continuous_runner_credential_isolation_status.csv",
        [{"file": item, "runner_dependency": False, "status": "blocked_from_runner_path"} for item in hardcoded_files],
        ["file", "runner_dependency", "status"],
    )

    print(f"status={decision['status']}")
    print(f"ready_to_manual_chart_trial={decision['ready_to_manual_chart_trial']}")
    print(f"ready_to_sim_continuous_runner_execution={decision['ready_to_sim_continuous_runner_execution']}")
    print(f"ready_to_live_trade={decision['ready_to_live_trade']}")
    print(f"blocker_failure_count={decision['blocker_failure_count']}")
    print(f"warning_count={decision['warning_count']}")
    print(f"monitor_preflight_status={decision['monitor_preflight_status']}")
    print(f"output_dir={OUT_DIR}")


if __name__ == "__main__":
    main()
