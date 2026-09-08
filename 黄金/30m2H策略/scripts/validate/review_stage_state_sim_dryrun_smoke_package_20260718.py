from __future__ import annotations


import csv
import re
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(r"F:\use_code\MTA5_l")
VALIDATION_DIR = ROOT / "黄金" / "30m2H策略" / "data" / "validation"
RUN_PACKAGE_DIR = VALIDATION_DIR / "stage_state_final_regression_run_package_check_20260718"
LIVE_SIM_DIR = VALIDATION_DIR / "stage_state_live_sim_run_gate_20260718"
OUT_DIR = VALIDATION_DIR / "stage_state_sim_dryrun_smoke_package_20260718"

AUTO_TRADE = ROOT / "auto_trade"
BASE_TESTER_INI = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_full_2018_20260707.ini"
SIM_SET = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_sim_dryrun_20260718.set"
SMOKE_TESTER_INI = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_sim_dryrun_smoke_20260601_20260707.ini"
SMOKE_REPORT = AUTO_TRADE / "stage_state_sim_dryrun_smoke_20260601_20260707_report.xml"
LOCAL_EX5 = AUTO_TRADE / "30m2H_Strategy_EA.ex5"
MQ5 = AUTO_TRADE / "30m2H_Strategy_EA.mq5"
TERMINAL_EXE = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")


EXPECTED_TESTER_FIELDS = {
    "Expert": r"Advisors\30m2H_Strategy_EA.ex5",
    "Symbol": "XAUUSDm",
    "Period": "M30",
    "Optimization": "0",
    "Model": "0",
    "FromDate": "2026.06.01",
    "ToDate": "2026.07.07",
    "Deposit": "500",
    "Currency": "USD",
    "Leverage": "100",
    "Visual": "0",
    "ReplaceReport": "1",
    "ShutdownTerminal": "1",
}

EXPECTED_INPUT_FIELDS = {
    "InpSymbol": "XAUUSDm",
    "InpRiskPct": "3.0",
    "InpUseDynamicLots": "true",
    "InpMaxPos": "3",
    "InpUseLayer1": "true",
    "InpUseLayer3": "true",
    "InpUseM15EarlyEntry": "true",
    "InpEnableM15Slot2": "false",
    "InpUseM15RescueTag": "true",
    "InpVerboseDecisionDiag": "true",
    "InpExportCSV": "true",
    "InpExportTradeLedger": "true",
    "InpExportStagePriceDiag": "false",
    "InpExportM15EntryDiag": "false",
    "InpSimMode": "true",
}


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


def current_value(value: str) -> str:
    return value.split("||", 1)[0].strip()


def parse_ini(path: Path) -> Tuple[Dict[str, str], Dict[str, str], List[str]]:
    tester: Dict[str, str] = {}
    inputs: Dict[str, str] = {}
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    section = ""
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if section == "Tester":
            tester[key] = current_value(value)
        elif section == "TesterInputs":
            inputs[key] = current_value(value)
    return tester, inputs, lines


def parse_set(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith(";") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = current_value(value)
    return values


def replace_current_value(raw_value: str, new_current: str) -> str:
    if "||" not in raw_value:
        return new_current
    _, suffix = raw_value.split("||", 1)
    return f"{new_current}||{suffix}"


def mutate_ini_lines(lines: List[str]) -> List[str]:
    tester_updates = {**EXPECTED_TESTER_FIELDS, "Report": str(SMOKE_REPORT)}
    input_updates = {
        "InpSimMode": "true",
        "InpExportCSV": "true",
        "InpExportTradeLedger": "true",
        "InpExportStagePriceDiag": "false",
        "InpExportM15EntryDiag": "false",
    }
    out: List[str] = [
        "; 30m2H short-window Strategy Tester config for signal-only sim dry-run smoke",
        "; Generated from auto_trade/30m2H_Strategy_EA.stage_state_full_2018_20260707.ini",
        "; Window: 2026.06.01 to 2026.07.07",
        "; Safety: InpSimMode=true, no live approval, no auto_trader.py execution.",
    ]
    section = ""
    seen_tester: set[str] = set()
    seen_inputs: set[str] = set()
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith(";"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            if section == "Tester":
                for key, value in tester_updates.items():
                    if key not in seen_tester:
                        out.append(f"{key}={value}")
            elif section == "TesterInputs":
                for key, value in input_updates.items():
                    if key not in seen_inputs:
                        out.append(f"{key}={value}||false||0||true||N")
            section = stripped[1:-1]
            out.append("")
            out.append(stripped)
            continue
        if "=" not in raw:
            out.append(raw)
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip()
        if section == "Tester":
            if key in tester_updates:
                out.append(f"{key}={tester_updates[key]}")
                seen_tester.add(key)
            else:
                out.append(f"{key}={value}")
        elif section == "TesterInputs":
            if key in input_updates:
                out.append(f"{key}={replace_current_value(value, input_updates[key])}")
                seen_inputs.add(key)
            else:
                out.append(f"{key}={value}")
        else:
            out.append(f"{key}={value}")
    if section == "Tester":
        for key, value in tester_updates.items():
            if key not in seen_tester:
                out.append(f"{key}={value}")
    elif section == "TesterInputs":
        for key, value in input_updates.items():
            if key not in seen_inputs:
                out.append(f"{key}={value}||false||0||true||N")
    return out


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


def load_prereq_decision(path: Path, status_field: str) -> Tuple[bool, str]:
    if not path.exists():
        return False, "missing"
    rows = read_rows(path)
    if not rows:
        return False, "empty"
    value = rows[0].get(status_field, "")
    return truthy(value), value


def mql_sim_mode_has_guards(path: Path) -> bool:
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    input_marker = bool(re.search(r"\binput\s+bool\s+InpSimMode\b", text))
    order_guard = "if(InpSimMode)" in text and "no order placed" in text
    ledger_guard = "InpExportTradeLedger && !InpSimMode" in text or "!InpExportTradeLedger || InpSimMode" in text
    return input_marker and order_guard and ledger_guard


def write_run_command() -> None:
    command = f'& "{TERMINAL_EXE}" /config:"{SMOKE_TESTER_INI}"'
    lines = [
        "# Sim Dry-run Smoke Tester Command",
        "",
        "Run from PowerShell:",
        "",
        "```powershell",
        command,
        "```",
        "",
        "Safety posture:",
        "",
        "- `InpSimMode=true` is forced in the generated tester `.ini`.",
        "- Do not run `auto_trade/auto_trader.py` for this smoke.",
        "- Expected tester balance stays near the initial `$500` because sim mode does not place real tester orders.",
        "- Use the generated signal CSV/log output to verify the EA can initialize, scan, and export signals in the MT5 runtime.",
        "",
        "After the run, collect:",
        "",
        "- tester report: `auto_trade/stage_state_sim_dryrun_smoke_20260601_20260707_report.xml`",
        "- latest MT5 tester log",
        "- latest `30m2H_strategy_signals_export.csv` if exported",
    ]
    (OUT_DIR / "sim_dryrun_smoke_run_command.md").write_text("\n".join(lines), encoding="utf-8-sig")


def write_md(decision: Dict[str, object], checks: List[Dict[str, object]]) -> None:
    failed = [row for row in checks if row["status"] == "fail"]
    lines = [
        "# Sim Dry-run Smoke Package",
        "",
        f"- Decision date: {decision['decision_date']}",
        f"- Status: `{decision['status']}`",
        f"- Ready to execute tester smoke: `{decision['ready_to_execute_tester_smoke']}`",
        f"- Ready to live trade: `{decision['ready_to_live_trade']}`",
        f"- Blocker failure count: `{decision['blocker_failure_count']}`",
        "",
        "## Scope",
        "",
        "- Generates a short-window MT5 Strategy Tester `.ini` from the frozen full tester config.",
        "- Forces `InpSimMode=true`, `InpExportCSV=true`, and `InpExportTradeLedger=true`.",
        "- Keeps live trading blocked; this package is only for signal-only dry-run smoke.",
        "",
        "## Generated Files",
        "",
        f"- `{SMOKE_TESTER_INI}`",
        f"- `{OUT_DIR / SMOKE_TESTER_INI.name}`",
        f"- `{OUT_DIR / 'sim_dryrun_smoke_run_command.md'}`",
        f"- `{OUT_DIR / 'sim_dryrun_smoke_tester_fields.csv'}`",
        f"- `{OUT_DIR / 'sim_dryrun_smoke_input_fields.csv'}`",
        "",
        "## Expected Smoke Result",
        "",
        "- EA loads in Strategy Tester for `XAUUSDm` / `M30` / `2026.06.01` to `2026.07.07`.",
        "- Tester deposit/leverage remain `$500` and `1:100`.",
        "- Because `InpSimMode=true`, the run should not be treated as a profit regression; use it to validate initialization, signal scanning, CSV/log export, and absence of live-run escalation.",
        "",
    ]
    if failed:
        lines.extend(["## Failed Checks", "", "| check_id | actual | expected |", "|---|---|---|"])
        for row in failed:
            lines.append(f"| `{row['check_id']}` | {row['actual']} | {row['expected']} |")
        lines.append("")
    lines.extend(
        [
            "## Next Gate",
            "",
            "- Execute the generated tester command only if the external MT5 terminal launch is approved.",
            "- After execution, parse the report/log/export files before considering any live/sim continuous runner work.",
        ]
    )
    (OUT_DIR / "sim_dryrun_smoke_package.md").write_text("\n".join(lines), encoding="utf-8-sig")
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    checks: List[Dict[str, object]] = []
    for check_id, path in [
        ("base_tester_ini_exists", BASE_TESTER_INI),
        ("sim_dryrun_set_exists", SIM_SET),
        ("local_ex5_exists", LOCAL_EX5),
        ("mq5_source_exists", MQ5),
        ("terminal_exe_exists", TERMINAL_EXE),
    ]:
        add_check(checks, check_id, path.exists(), str(path), "exists")

    run_ready, run_actual = load_prereq_decision(
        RUN_PACKAGE_DIR / "run_package_check_decision.csv",
        "ready_to_frozen_tester_run",
    )
    live_sim_ready, live_sim_actual = load_prereq_decision(
        LIVE_SIM_DIR / "live_sim_run_gate_decision.csv",
        "ready_to_sim_dry_run",
    )
    add_check(checks, "prereq_frozen_run_package_ready", run_ready, run_actual, "True")
    add_check(checks, "prereq_live_sim_gate_ready", live_sim_ready, live_sim_actual, "True")

    if BASE_TESTER_INI.exists():
        _, _, base_lines = parse_ini(BASE_TESTER_INI)
        smoke_lines = mutate_ini_lines(base_lines)
        text = "\n".join(smoke_lines) + "\n"
        SMOKE_TESTER_INI.write_text(text, encoding="utf-8-sig")
        (OUT_DIR / SMOKE_TESTER_INI.name).write_text(text, encoding="utf-8-sig")

    generated_ini_exists = SMOKE_TESTER_INI.exists()
    add_check(checks, "smoke_tester_ini_generated", generated_ini_exists, str(SMOKE_TESTER_INI), "exists")

    tester_fields: List[Dict[str, object]] = []
    input_fields: List[Dict[str, object]] = []
    if generated_ini_exists:
        tester, inputs, _ = parse_ini(SMOKE_TESTER_INI)
        for key, expected in {**EXPECTED_TESTER_FIELDS, "Report": str(SMOKE_REPORT)}.items():
            actual = tester.get(key, "")
            passed = actual == expected
            tester_fields.append(
                {"field": key, "actual": actual, "expected": expected, "status": "pass" if passed else "fail"}
            )
            add_check(checks, f"tester_{key}", passed, actual, expected)
        for key, expected in EXPECTED_INPUT_FIELDS.items():
            actual = inputs.get(key, "")
            passed = actual == expected
            input_fields.append(
                {"field": key, "actual": actual, "expected": expected, "status": "pass" if passed else "fail"}
            )
            add_check(checks, f"input_{key}", passed, actual, expected)

    sim_set_values = parse_set(SIM_SET) if SIM_SET.exists() else {}
    add_check(checks, "set_inp_sim_mode_true", sim_set_values.get("InpSimMode") == "true", sim_set_values.get("InpSimMode", ""), "true")
    add_check(checks, "set_inp_export_csv_true", sim_set_values.get("InpExportCSV") == "true", sim_set_values.get("InpExportCSV", ""), "true")
    add_check(checks, "set_inp_export_trade_ledger_true", sim_set_values.get("InpExportTradeLedger") == "true", sim_set_values.get("InpExportTradeLedger", ""), "true")
    add_check(checks, "mq5_sim_mode_guard_markers_present", MQ5.exists() and mql_sim_mode_has_guards(MQ5), "InpSimMode/SIM markers", "present")

    blocker_failures = [row for row in checks if row["severity"] == "blocker" and row["status"] == "fail"]
    ready = len(blocker_failures) == 0
    decision = {
        "decision_date": date.today().isoformat(),
        "check_id": "stage_state_sim_dryrun_smoke_package",
        "status": "pass" if ready else "fail",
        "pass": ready,
        "ready_to_execute_tester_smoke": ready,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "smoke_from_date": "2026.06.01",
        "smoke_to_date": "2026.07.07",
        "tester_ini": str(SMOKE_TESTER_INI),
        "run_command_md": str(OUT_DIR / "sim_dryrun_smoke_run_command.md"),
        "reason": "sim_dryrun_smoke_tester_package_ready" if ready else "sim_dryrun_smoke_tester_package_has_blockers",
        "next_action": "run_mt5_strategy_tester_smoke_with_external_terminal_approval" if ready else "fix_failed_smoke_package_checks",
        "no_ea_or_python_strategy_logic_changes_in_this_step": True,
    }

    write_run_command()
    write_md(decision, checks)
    write_csv(
        OUT_DIR / "sim_dryrun_smoke_package_decision.csv",
        [decision],
        [
            "decision_date",
            "check_id",
            "status",
            "pass",
            "ready_to_execute_tester_smoke",
            "ready_to_live_trade",
            "blocker_failure_count",
            "smoke_from_date",
            "smoke_to_date",
            "tester_ini",
            "run_command_md",
            "reason",
            "next_action",
            "no_ea_or_python_strategy_logic_changes_in_this_step",
        ],
    )
    write_csv(
        OUT_DIR / "sim_dryrun_smoke_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(
        OUT_DIR / "sim_dryrun_smoke_tester_fields.csv",
        tester_fields,
        ["field", "actual", "expected", "status"],
    )
    write_csv(
        OUT_DIR / "sim_dryrun_smoke_input_fields.csv",
        input_fields,
        ["field", "actual", "expected", "status"],
    )

    print(f"status={decision['status']}")
    print(f"ready_to_execute_tester_smoke={decision['ready_to_execute_tester_smoke']}")
    print(f"ready_to_live_trade={decision['ready_to_live_trade']}")
    print(f"blocker_failure_count={decision['blocker_failure_count']}")
    print(f"tester_ini={SMOKE_TESTER_INI}")
    print(f"output_dir={OUT_DIR}")


if __name__ == "__main__":
    main()
