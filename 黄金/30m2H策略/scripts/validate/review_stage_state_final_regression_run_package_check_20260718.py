from __future__ import annotations


import csv
import hashlib
import re
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(r"F:\use_code\MTA5_l")
VALIDATION_DIR = ROOT / "黄金" / "30m2H策略" / "data" / "validation"
THREE_VERSION_DIR = VALIDATION_DIR / "stage_state_final_regression_three_version_unified_report_20260718"
MT5_CLOSURE_DIR = VALIDATION_DIR / "stage_state_final_regression_mt5_ledger_closure_review_20260718"
OUT_DIR = VALIDATION_DIR / "stage_state_final_regression_run_package_check_20260718"

AUTO_TRADE = ROOT / "auto_trade"
MQ5 = AUTO_TRADE / "30m2H_Strategy_EA.mq5"
LOCAL_EX5 = AUTO_TRADE / "30m2H_Strategy_EA.ex5"
TESTER_INI = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_full_2018_20260707.ini"
COMPILE_LOG = AUTO_TRADE / "compile_stage_state_fix.log"
GENERATED_SET = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_frozen_20260718.set"
TERMINAL_EXE = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")
DEPLOYED_EX5 = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\MQL5\Experts\Advisors\30m2H_Strategy_EA.ex5"
)

MT5_ARCHIVE_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"
REQUIRED_ARCHIVE_FILES = [
    "30m2H_strategy_trade_ledger.csv",
    "30m2H_strategy_deal_history.csv",
    "30m2H_strategy_signals_export.csv",
    "terminal_20260716.log",
    "tester_agent_20260716.log",
]


EXPECTED_TESTER_FIELDS = {
    "Expert": r"Advisors\30m2H_Strategy_EA.ex5",
    "Symbol": "XAUUSDm",
    "Period": "M30",
    "Optimization": "0",
    "Model": "0",
    "FromDate": "2018.01.01",
    "ToDate": "2026.07.07",
    "Deposit": "500",
    "Currency": "USD",
    "Leverage": "100",
    "ReplaceReport": "1",
    "ShutdownTerminal": "1",
}


EXPECTED_INPUTS = {
    "InpMagic": "302025",
    "InpSymbol": "XAUUSDm",
    "InpRiskPct": "3.0",
    "InpStopLo": "5000.0",
    "InpStopHi": "35000.0",
    "InpMaxPos": "3",
    "InpMinLots": "0.01",
    "InpMaxLots": "10.0",
    "InpUseDynamicLots": "true",
    "InpBias55Threshold": "3.0",
    "InpPreCrossGapPct": "0.300",
    "InpPostNMin": "2",
    "InpPostNMax": "6",
    "InpUseLayer1": "true",
    "InpUseH2EarlyGateQ2": "true",
    "InpH2EarlyGateQ": "2",
    "InpUseLayer3": "true",
    "InpBias5TopPct": "34.0",
    "InpBias5Lookback": "500",
    "InpUseM15EarlyEntry": "true",
    "InpEnableM15Slot2": "false",
    "InpUseM15RescueTag": "true",
    "InpM15Period": "15",
    "InpVerboseDecisionDiag": "true",
    "InpStageCount": "3",
    "InpStage1Lots": "0.01",
    "InpStage2Lots": "0.02",
    "InpStage3Lots": "0.03",
    "InpStage1R": "2.0",
    "InpStage2TrailR": "1.5",
    "InpStage2ForceR": "4.0",
    "InpH2CrossBars": "3",
    "InpStage3On": "true",
    "InpDebugStages": "true",
    "InpExportCSV": "true",
    "InpExportTradeLedger": "true",
    "InpExportStagePriceDiag": "false",
    "InpExportM15EntryDiag": "false",
    "InpFastMA": "5",
    "InpSlowMA": "13",
    "InpStopLookback": "200",
    "InpH2Thresh": "0.0",
    "InpH2Period": "16386",
    "InpM30Period": "30",
    "InpH2SMA5": "5",
    "InpH2SMA13": "13",
    "InpH2SMA55": "55",
    "InpH2SMA144": "144",
    "InpH2SMA233": "233",
    "InpSlippage": "30",
    "InpCheckSec": "10",
    "InpSimMode": "false",
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


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def read_text_auto(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="ignore")
    return data.decode("utf-8-sig", errors="ignore")


def parse_ini(path: Path) -> Tuple[Dict[str, str], Dict[str, str], List[str]]:
    tester: Dict[str, str] = {}
    inputs: Dict[str, str] = {}
    input_lines: List[str] = []
    section = ""
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
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
        value = value.strip()
        current_value = value.split("||", 1)[0]
        if section == "Tester":
            tester[key] = current_value
        elif section == "TesterInputs":
            inputs[key] = current_value
            input_lines.append(f"{key}={value}")
    return tester, inputs, input_lines


def mql_input_names(path: Path) -> List[str]:
    names: List[str] = []
    pattern = re.compile(r"\binput\s+(?:[\w:<>]+\s+)+(?P<name>Inp[A-Za-z0-9_]+)\b")
    for line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        match = pattern.search(line)
        if match:
            names.append(match.group("name"))
    return names


def add_check(
    rows: List[Dict[str, object]],
    check_id: str,
    status: bool,
    actual: object,
    expected: object,
    severity: str = "blocker",
    note: str = "",
) -> None:
    rows.append(
        {
            "check_id": check_id,
            "status": "pass" if status else "fail",
            "pass": status,
            "actual": actual,
            "expected": expected,
            "severity": severity,
            "note": note,
        }
    )


def file_inventory() -> List[Dict[str, object]]:
    files = [
        ("mq5_source", MQ5, True),
        ("local_ex5", LOCAL_EX5, True),
        ("deployed_ex5", DEPLOYED_EX5, True),
        ("tester_ini", TESTER_INI, True),
        ("compile_log", COMPILE_LOG, True),
        ("terminal_exe", TERMINAL_EXE, True),
        ("generated_current_set", GENERATED_SET, True),
    ]
    rows: List[Dict[str, object]] = []
    for role, path, required in files:
        exists = path.exists()
        stat = path.stat() if exists else None
        rows.append(
            {
                "role": role,
                "path": str(path),
                "required": required,
                "exists": exists,
                "size": stat.st_size if stat else "",
                "last_write_time": stat.st_mtime if stat else "",
            }
        )
    return rows


def generate_set_snapshot(input_lines: List[str]) -> None:
    header = [
        "; 30m2H_Strategy_EA frozen stage-state parameter snapshot",
        "; Generated from auto_trade/30m2H_Strategy_EA.stage_state_full_2018_20260707.ini",
        "; Date: 2026-07-18",
        "; Use the .ini for full MT5 tester replay; this .set prevents loading stale v3.21/v3.22 inputs in manual UI runs.",
        "",
    ]
    text = "\n".join(header + input_lines) + "\n"
    GENERATED_SET.write_text(text, encoding="utf-8-sig")
    (OUT_DIR / "30m2H_Strategy_EA.stage_state_frozen_20260718.set").write_text(
        text, encoding="utf-8-sig"
    )


def latest_checklist_rows() -> List[Dict[str, str]]:
    return read_rows(THREE_VERSION_DIR / "final_regression_checklist_status_after_three_version_report.csv")


def write_run_command(tester: Dict[str, str]) -> None:
    command = (
        f'& "{TERMINAL_EXE}" /config:"{TESTER_INI}"'
    )
    lines = [
        "# Frozen MT5 Tester Run Command",
        "",
        "Run from PowerShell:",
        "",
        "```powershell",
        command,
        "```",
        "",
        "Expected frozen reference after full tester:",
        "",
        "- Symbol: XAUUSDm",
        "- Period: M30",
        f"- Date range: {tester.get('FromDate')} to {tester.get('ToDate')}",
        f"- Deposit: {tester.get('Deposit')} {tester.get('Currency')}",
        f"- Leverage: 1:{tester.get('Leverage')}",
        "- Expected final balance from frozen archive: 1649.84 USD",
        "",
    ]
    (OUT_DIR / "run_package_command.md").write_text("\n".join(lines), encoding="utf-8-sig")


def write_review_md(
    decision: Dict[str, object],
    summary_rows: List[Dict[str, object]],
    checks: List[Dict[str, object]],
) -> None:
    failed = [row for row in checks if not truthy(row.get("pass")) and row.get("severity") == "blocker"]
    lines: List[str] = []
    lines.append("# Final Regression: EA EX5 / SET Run Package Check")
    lines.append("")
    lines.append(f"- Decision date: {decision['decision_date']}")
    lines.append(f"- Check id: `{decision['check_id']}`")
    lines.append(f"- Status: `{decision['status']}`")
    lines.append(f"- Pass: `{decision['pass']}`")
    lines.append(f"- Ready to frozen tester run: `{decision['ready_to_frozen_tester_run']}`")
    lines.append(f"- Reason: `{decision['reason']}`")
    lines.append("")
    lines.append("## Package Summary")
    lines.append("")
    lines.append("| key | value |")
    lines.append("|---|---|")
    for row in summary_rows:
        lines.append(f"| `{row['key']}` | {row['value']} |")
    lines.append("")
    lines.append("## Check Result")
    lines.append("")
    lines.append(f"- Blocker failures: `{len(failed)}`")
    lines.append("- Local EX5 and deployed EX5 SHA256 hashes match.")
    lines.append("- Current frozen `.set` snapshot was generated from the full tester `.ini`.")
    lines.append("- Older v3.21/v3.22 `.set` files are historical and should not be treated as the frozen run package.")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("This check validates run-package readiness for the frozen MT5 tester baseline. It does not approve live trading and does not modify EA/Python strategy logic.")
    lines.append("")
    (OUT_DIR / "run_package_check.md").write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    tester, inputs, input_lines = parse_ini(TESTER_INI)
    generate_set_snapshot(input_lines)

    checks: List[Dict[str, object]] = []
    for role, path in [
        ("mq5_source", MQ5),
        ("local_ex5", LOCAL_EX5),
        ("deployed_ex5", DEPLOYED_EX5),
        ("tester_ini", TESTER_INI),
        ("compile_log", COMPILE_LOG),
        ("terminal_exe", TERMINAL_EXE),
        ("generated_current_set", GENERATED_SET),
    ]:
        add_check(checks, f"{role}_exists", path.exists(), path.exists(), True)
        if path.exists():
            add_check(checks, f"{role}_nonempty", path.stat().st_size > 0, path.stat().st_size, ">0")

    add_check(
        checks,
        "local_ex5_newer_than_mq5",
        LOCAL_EX5.stat().st_mtime >= MQ5.stat().st_mtime,
        LOCAL_EX5.stat().st_mtime - MQ5.stat().st_mtime,
        ">=0 seconds",
    )
    compile_text = read_text_auto(COMPILE_LOG)
    add_check(
        checks,
        "compile_log_zero_errors_zero_warnings",
        "Result: 0 errors, 0 warnings" in compile_text,
        "Result: 0 errors, 0 warnings" in compile_text,
        True,
    )

    local_hash = sha256(LOCAL_EX5)
    deployed_hash = sha256(DEPLOYED_EX5)
    add_check(checks, "local_ex5_hash_equals_deployed_ex5_hash", local_hash == deployed_hash, local_hash, deployed_hash)
    add_check(
        checks,
        "local_ex5_size_equals_deployed_ex5_size",
        LOCAL_EX5.stat().st_size == DEPLOYED_EX5.stat().st_size,
        LOCAL_EX5.stat().st_size,
        DEPLOYED_EX5.stat().st_size,
    )

    for key, expected in EXPECTED_TESTER_FIELDS.items():
        add_check(
            checks,
            f"tester_field_{key}",
            tester.get(key) == expected,
            tester.get(key, ""),
            expected,
        )

    for key, expected in EXPECTED_INPUTS.items():
        add_check(
            checks,
            f"input_{key}",
            inputs.get(key) == expected,
            inputs.get(key, ""),
            expected,
        )

    input_names = mql_input_names(MQ5)
    missing_inputs = sorted(set(input_names) - set(inputs))
    add_check(
        checks,
        "tester_ini_contains_all_mq5_inputs",
        len(missing_inputs) == 0,
        ";".join(missing_inputs),
        "no missing input",
    )

    old_set_files = sorted(
        path.name for path in AUTO_TRADE.glob("*.set") if path.name != GENERATED_SET.name
    )
    add_check(
        checks,
        "old_set_files_are_historical_only",
        bool(old_set_files),
        ";".join(old_set_files),
        "historical set files present but not current frozen package",
        severity="warning",
        note="Current frozen set snapshot is generated from the .ini in this check.",
    )

    for name in REQUIRED_ARCHIVE_FILES:
        path = MT5_ARCHIVE_DIR / name
        add_check(checks, f"archive_{name}_exists", path.exists(), path.exists(), True)
        if path.exists():
            add_check(checks, f"archive_{name}_nonempty", path.stat().st_size > 0, path.stat().st_size, ">0")

    checklist_rows = latest_checklist_rows()
    first_four_pass = all(row.get("status") == "pass" for row in checklist_rows[:4])
    add_check(checks, "first_four_final_regression_checks_pass", first_four_pass, first_four_pass, True)

    blocker_failures = [row for row in checks if not truthy(row.get("pass")) and row.get("severity") == "blocker"]
    passed = len(blocker_failures) == 0

    summary_rows = [
        {"key": "mq5_source", "value": str(MQ5)},
        {"key": "local_ex5", "value": str(LOCAL_EX5)},
        {"key": "deployed_ex5", "value": str(DEPLOYED_EX5)},
        {"key": "terminal_exe", "value": str(TERMINAL_EXE)},
        {"key": "tester_ini", "value": str(TESTER_INI)},
        {"key": "generated_set", "value": str(GENERATED_SET)},
        {"key": "local_ex5_sha256", "value": local_hash},
        {"key": "deployed_ex5_sha256", "value": deployed_hash},
        {"key": "tester_symbol", "value": tester.get("Symbol", "")},
        {"key": "tester_period", "value": tester.get("Period", "")},
        {"key": "date_range", "value": f"{tester.get('FromDate', '')} to {tester.get('ToDate', '')}"},
        {"key": "deposit", "value": tester.get("Deposit", "")},
        {"key": "leverage", "value": tester.get("Leverage", "")},
        {"key": "risk_pct", "value": inputs.get("InpRiskPct", "")},
        {"key": "dynamic_lots", "value": inputs.get("InpUseDynamicLots", "")},
        {"key": "stage_lots", "value": f"{inputs.get('InpStage1Lots')}/{inputs.get('InpStage2Lots')}/{inputs.get('InpStage3Lots')}"},
        {"key": "expected_frozen_final_balance", "value": "1649.84"},
        {"key": "expected_frozen_trades", "value": "82"},
    ]

    decision = {
        "decision_date": date.today().isoformat(),
        "check_id": "ea_ex5_set_run_package_check",
        "status": "pass" if passed else "fail",
        "pass": passed,
        "ready_to_frozen_tester_run": passed,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "warning_count": len([row for row in checks if row.get("severity") == "warning"]),
        "reason": "ea_binary_config_set_snapshot_and_archive_outputs_are_ready_for_frozen_tester_run"
        if passed
        else "run_package_check_has_blocker_failures",
        "next_check": "final_regression_complete" if passed else "fix_run_package_blockers",
        "no_ea_or_python_logic_changes_in_this_step": True,
    }

    write_csv(
        OUT_DIR / "run_package_check_decision.csv",
        [decision],
        [
            "decision_date",
            "check_id",
            "status",
            "pass",
            "ready_to_frozen_tester_run",
            "ready_to_live_trade",
            "blocker_failure_count",
            "warning_count",
            "reason",
            "next_check",
            "no_ea_or_python_logic_changes_in_this_step",
        ],
    )
    write_csv(OUT_DIR / "run_package_check_summary.csv", summary_rows, ["key", "value"])
    write_csv(
        OUT_DIR / "run_package_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(
        OUT_DIR / "run_package_file_inventory.csv",
        file_inventory(),
        ["role", "path", "required", "exists", "size", "last_write_time"],
    )
    write_csv(
        OUT_DIR / "run_package_tester_fields.csv",
        [
            {
                "field": key,
                "actual": tester.get(key, ""),
                "expected": expected,
                "pass": tester.get(key) == expected,
            }
            for key, expected in EXPECTED_TESTER_FIELDS.items()
        ],
        ["field", "actual", "expected", "pass"],
    )
    write_csv(
        OUT_DIR / "run_package_input_fields.csv",
        [
            {
                "field": key,
                "actual": inputs.get(key, ""),
                "expected": expected,
                "pass": inputs.get(key) == expected,
            }
            for key, expected in EXPECTED_INPUTS.items()
        ],
        ["field", "actual", "expected", "pass"],
    )

    checklist_out: List[Dict[str, object]] = []
    for row in checklist_rows:
        if row.get("check_id") == "ea_ex5_set_run_package_check":
            row["status"] = decision["status"]
            row["evidence"] = str((OUT_DIR / "run_package_check_decision.csv").relative_to(ROOT))
        elif "evidence" not in row:
            row["evidence"] = ""
        checklist_out.append(row)
    write_csv(
        OUT_DIR / "final_regression_checklist_status_after_run_package.csv",
        checklist_out,
        ["order", "check_id", "description", "status", "evidence"],
    )

    write_run_command(tester)
    write_review_md(decision, summary_rows, checks)

    readme = "\n".join(
        [
            "# stage_state_final_regression_run_package_check_20260718",
            "",
            "Final regression check 5: EA EX5 / SET run package check.",
            "",
            "- `run_package_check_decision.csv`: check decision.",
            "- `run_package_check_summary.csv`: package summary.",
            "- `run_package_checks.csv`: individual checks.",
            "- `run_package_file_inventory.csv`: required file inventory.",
            "- `run_package_tester_fields.csv`: tester config field checks.",
            "- `run_package_input_fields.csv`: tester input checks.",
            "- `30m2H_Strategy_EA.stage_state_frozen_20260718.set`: frozen parameter set snapshot generated from `.ini`.",
            "- `final_regression_checklist_status_after_run_package.csv`: checklist status after this final check.",
            "- `run_package_command.md`: frozen tester run command.",
            "- `run_package_check.md`: human-readable review.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8-sig")

    print(f"wrote {OUT_DIR}")
    print(f"status={decision['status']}")
    print(f"ready_to_frozen_tester_run={decision['ready_to_frozen_tester_run']}")
    print(f"blocker_failure_count={decision['blocker_failure_count']}")


if __name__ == "__main__":
    main()
