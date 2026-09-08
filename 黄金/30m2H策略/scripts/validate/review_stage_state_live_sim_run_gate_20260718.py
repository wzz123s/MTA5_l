from __future__ import annotations


import csv
import re
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(r"F:\use_code\MTA5_l")
VALIDATION_DIR = ROOT / "黄金" / "30m2H策略" / "data" / "validation"
RUN_PACKAGE_DIR = VALIDATION_DIR / "stage_state_final_regression_run_package_check_20260718"
OUT_DIR = VALIDATION_DIR / "stage_state_live_sim_run_gate_20260718"

AUTO_TRADE = ROOT / "auto_trade"
FROZEN_SET = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_frozen_20260718.set"
SIM_SET = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_sim_dryrun_20260718.set"
TESTER_INI = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_full_2018_20260707.ini"
LOCAL_EX5 = AUTO_TRADE / "30m2H_Strategy_EA.ex5"
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


def parse_set(path: Path) -> Tuple[Dict[str, str], List[str]]:
    values: Dict[str, str] = {}
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    for line in lines:
        text = line.strip()
        if not text or text.startswith(";") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        values[key.strip()] = value.strip().split("||", 1)[0]
    return values, lines


def write_sim_set(lines: List[str]) -> None:
    out_lines: List[str] = []
    replaced = False
    for line in lines:
        if line.startswith("; Date:"):
            out_lines.append("; Date: 2026-07-18")
            continue
        if line.startswith("; Use the .ini"):
            out_lines.append("; Sim dry-run snapshot: InpSimMode=true, no order placement expected.")
            continue
        if line.startswith("InpSimMode="):
            out_lines.append("InpSimMode=true||false||0||true||N")
            replaced = True
            continue
        out_lines.append(line)
    if not replaced:
        out_lines.append("InpSimMode=true||false||0||true||N")
    text = "\n".join(out_lines) + "\n"
    SIM_SET.write_text(text, encoding="utf-8-sig")
    (OUT_DIR / SIM_SET.name).write_text(text, encoding="utf-8-sig")


def file_contains_hardcoded_credential(path: Path) -> bool:
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    password_pattern = re.compile(r"['\"]password['\"]\s*:\s*['\"][^'\"]+['\"]")
    account_pattern = re.compile(r"['\"]account['\"]\s*:\s*\d+")
    login_pattern = re.compile(r"\blogin\s*=\s*CONFIG\[['\"]account['\"]\]")
    return bool(password_pattern.search(text) and account_pattern.search(text) and login_pattern.search(text))


def python_runner_strategy_stale(path: Path) -> bool:
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
    scope: str,
    passed: bool,
    actual: object,
    expected: object,
    severity: str,
    note: str = "",
) -> None:
    rows.append(
        {
            "check_id": check_id,
            "scope": scope,
            "status": "pass" if passed else "fail",
            "pass": passed,
            "actual": actual,
            "expected": expected,
            "severity": severity,
            "note": note,
        }
    )


def write_md(decision: Dict[str, object], summary_rows: List[Dict[str, object]], checks: List[Dict[str, object]]) -> None:
    sim_failures = [row for row in checks if row["scope"] == "sim" and not truthy(row["pass"]) and row["severity"] == "blocker"]
    live_failures = [row for row in checks if row["scope"] == "live" and not truthy(row["pass"]) and row["severity"] == "blocker"]
    lines: List[str] = []
    lines.append("# Live / Sim Run Gate")
    lines.append("")
    lines.append(f"- Decision date: {decision['decision_date']}")
    lines.append(f"- Status: `{decision['status']}`")
    lines.append(f"- Ready to sim dry-run: `{decision['ready_to_sim_dry_run']}`")
    lines.append(f"- Ready to live trade: `{decision['ready_to_live_trade']}`")
    lines.append(f"- Sim blocker count: `{len(sim_failures)}`")
    lines.append(f"- Live blocker count: `{len(live_failures)}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| key | value |")
    lines.append("|---|---|")
    for row in summary_rows:
        lines.append(f"| `{row['key']}` | {row['value']} |")
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append("- The frozen MT5 tester package is ready for replay.")
    lines.append("- A signal-only sim dry-run parameter set has been generated with `InpSimMode=true`.")
    lines.append("- Live trading is not approved in this gate. Live needs separate credential handling, risk limits, monitoring, and operational controls.")
    lines.append("- Existing Python `auto_trader.py` is not the current frozen EA strategy runner and must not be treated as the production runner.")
    lines.append("")
    lines.append("## Dry-run Use")
    lines.append("")
    lines.append(f"- Use `{SIM_SET}` for manual MT5 chart/UI signal-only dry run.")
    lines.append("- Use the existing frozen tester `.ini` only for full Strategy Tester replay.")
    lines.append("")
    (OUT_DIR / "live_sim_run_gate.md").write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    run_package_decision = read_rows(RUN_PACKAGE_DIR / "run_package_check_decision.csv")[0]
    checklist_rows = read_rows(RUN_PACKAGE_DIR / "final_regression_checklist_status_after_run_package.csv")
    frozen_values, frozen_lines = parse_set(FROZEN_SET)
    write_sim_set(frozen_lines)
    sim_values, _ = parse_set(SIM_SET)

    hardcoded_files = [
        str(path.relative_to(ROOT))
        for path in [AUTO_TRADER, VERIFY_CONNECTION, SIGNAL_VALIDATOR]
        if path.exists() and file_contains_hardcoded_credential(path)
    ]
    stale_python_runner = python_runner_strategy_stale(AUTO_TRADER)

    checks: List[Dict[str, object]] = []
    add_check(checks, "final_regression_5_of_5_pass", "sim", all(row.get("status") == "pass" for row in checklist_rows), "all pass", "all pass", "blocker")
    add_check(checks, "run_package_ready_to_frozen_tester_run", "sim", truthy(run_package_decision.get("ready_to_frozen_tester_run")), run_package_decision.get("ready_to_frozen_tester_run"), "True", "blocker")
    add_check(checks, "frozen_set_exists", "sim", FROZEN_SET.exists(), str(FROZEN_SET), "exists", "blocker")
    add_check(checks, "sim_set_exists", "sim", SIM_SET.exists(), str(SIM_SET), "exists", "blocker")
    add_check(checks, "sim_set_has_sim_mode_true", "sim", sim_values.get("InpSimMode") == "true", sim_values.get("InpSimMode", ""), "true", "blocker")
    add_check(checks, "sim_set_keeps_export_csv", "sim", sim_values.get("InpExportCSV") == "true", sim_values.get("InpExportCSV", ""), "true", "blocker")
    add_check(checks, "sim_set_keeps_export_trade_ledger", "sim", sim_values.get("InpExportTradeLedger") == "true", sim_values.get("InpExportTradeLedger", ""), "true", "blocker")
    add_check(checks, "local_ex5_exists", "sim", LOCAL_EX5.exists(), str(LOCAL_EX5), "exists", "blocker")
    add_check(checks, "tester_ini_exists", "sim", TESTER_INI.exists(), str(TESTER_INI), "exists", "blocker")

    add_check(checks, "hardcoded_credentials_externalized", "live", len(hardcoded_files) == 0, ";".join(hardcoded_files), "no hardcoded credentials", "blocker", "Do not expose account credentials in source files.")
    add_check(checks, "python_auto_trader_matches_frozen_ea_strategy", "live", not stale_python_runner, "stale_or_incomplete_python_runner", "current frozen EA strategy runner", "blocker")
    add_check(checks, "live_specific_risk_limits_defined", "live", False, "missing live-specific max loss/session/kill switch config", "defined", "blocker")
    add_check(checks, "live_monitoring_and_restart_plan_defined", "live", False, "missing monitor/restart/alert plan", "defined", "blocker")
    add_check(checks, "live_trade_manual_approval_done", "live", False, "not requested/approved", "approved", "blocker")

    sim_blockers = [row for row in checks if row["scope"] == "sim" and not truthy(row["pass"]) and row["severity"] == "blocker"]
    live_blockers = [row for row in checks if row["scope"] == "live" and not truthy(row["pass"]) and row["severity"] == "blocker"]
    ready_to_sim = len(sim_blockers) == 0

    summary_rows = [
        {"key": "frozen_set", "value": str(FROZEN_SET)},
        {"key": "sim_dryrun_set", "value": str(SIM_SET)},
        {"key": "tester_ini", "value": str(TESTER_INI)},
        {"key": "local_ex5", "value": str(LOCAL_EX5)},
        {"key": "frozen_expected_trades", "value": "82"},
        {"key": "frozen_expected_final_balance", "value": "1649.84"},
        {"key": "sim_mode", "value": sim_values.get("InpSimMode", "")},
        {"key": "export_csv", "value": sim_values.get("InpExportCSV", "")},
        {"key": "export_trade_ledger", "value": sim_values.get("InpExportTradeLedger", "")},
        {"key": "hardcoded_credential_file_count", "value": len(hardcoded_files)},
        {"key": "python_auto_trader_current_runner", "value": not stale_python_runner},
    ]

    decision = {
        "decision_date": date.today().isoformat(),
        "check_id": "stage_state_live_sim_run_gate",
        "status": "pass" if ready_to_sim else "fail",
        "pass": ready_to_sim,
        "ready_to_sim_dry_run": ready_to_sim,
        "ready_to_live_trade": False,
        "sim_blocker_count": len(sim_blockers),
        "live_blocker_count": len(live_blockers),
        "reason": "sim_dryrun_set_ready_live_trade_not_approved" if ready_to_sim else "sim_dryrun_has_blockers",
        "next_action": "manual_mt5_sim_dry_run_or_define_live_trade_controls",
        "no_ea_or_python_strategy_logic_changes_in_this_step": True,
    }

    write_csv(
        OUT_DIR / "live_sim_run_gate_decision.csv",
        [decision],
        [
            "decision_date",
            "check_id",
            "status",
            "pass",
            "ready_to_sim_dry_run",
            "ready_to_live_trade",
            "sim_blocker_count",
            "live_blocker_count",
            "reason",
            "next_action",
            "no_ea_or_python_strategy_logic_changes_in_this_step",
        ],
    )
    write_csv(OUT_DIR / "live_sim_run_gate_summary.csv", summary_rows, ["key", "value"])
    write_csv(
        OUT_DIR / "live_sim_run_gate_checks.csv",
        checks,
        ["check_id", "scope", "status", "pass", "actual", "expected", "severity", "note"],
    )

    checklist = [
        {"order": 1, "item": "Final regression 5/5 pass", "scope": "sim", "status": "pass" if all(row.get("status") == "pass" for row in checklist_rows) else "fail"},
        {"order": 2, "item": "Frozen tester run package ready", "scope": "sim", "status": "pass" if truthy(run_package_decision.get("ready_to_frozen_tester_run")) else "fail"},
        {"order": 3, "item": "Sim dry-run set generated with InpSimMode=true", "scope": "sim", "status": "pass" if sim_values.get("InpSimMode") == "true" else "fail"},
        {"order": 4, "item": "Live credentials externalized", "scope": "live", "status": "blocked"},
        {"order": 5, "item": "Live risk/monitoring controls defined", "scope": "live", "status": "blocked"},
        {"order": 6, "item": "Manual live approval", "scope": "live", "status": "blocked"},
    ]
    write_csv(OUT_DIR / "live_sim_run_gate_checklist.csv", checklist, ["order", "item", "scope", "status"])

    dryrun_lines = [
        "# MT5 Sim Dry-run Notes",
        "",
        f"- Load EA: `{LOCAL_EX5}`",
        f"- Load parameter set: `{SIM_SET}`",
        "- Confirm `InpSimMode=true` before attaching/running.",
        "- This dry run is for signal/log validation only; it is not live trading approval.",
        "- Frozen tester replay remains available through the existing `.ini` run command from the run-package check.",
        "",
    ]
    (OUT_DIR / "sim_dryrun_notes.md").write_text("\n".join(dryrun_lines), encoding="utf-8-sig")
    write_md(decision, summary_rows, checks)

    print(f"wrote {OUT_DIR}")
    print(f"status={decision['status']}")
    print(f"ready_to_sim_dry_run={decision['ready_to_sim_dry_run']}")
    print(f"ready_to_live_trade={decision['ready_to_live_trade']}")
    print(f"live_blocker_count={decision['live_blocker_count']}")


if __name__ == "__main__":
    main()
