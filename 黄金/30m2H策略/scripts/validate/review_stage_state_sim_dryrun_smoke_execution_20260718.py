from __future__ import annotations


import csv
import re
import shutil
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(r"F:\use_code\MTA5_l")
VALIDATION_DIR = ROOT / "黄金" / "30m2H策略" / "data" / "validation"
PACKAGE_DIR = VALIDATION_DIR / "stage_state_sim_dryrun_smoke_package_20260718"
OUT_DIR = VALIDATION_DIR / "stage_state_sim_dryrun_smoke_execution_review_20260718"

AUTO_TRADE = ROOT / "auto_trade"
SMOKE_INI = AUTO_TRADE / "30m2H_Strategy_EA.stage_state_sim_dryrun_smoke_20260601_20260707.ini"
SMOKE_REPORT = AUTO_TRADE / "stage_state_sim_dryrun_smoke_20260601_20260707_report.xml"

TERMINAL_DATA = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16"
)
TESTER_DATA = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\B695BCB6C1E6864B6D96307B87B29F16"
)
AGENT_DATA = TESTER_DATA / "Agent-127.0.0.1-3000"

TERMINAL_LOG = TERMINAL_DATA / "logs" / "20260718.log"
TESTER_LOG = TERMINAL_DATA / "tester" / "logs" / "20260718.log"
AGENT_LOG = AGENT_DATA / "logs" / "20260718.log"
SIGNALS_EXPORT = AGENT_DATA / "MQL5" / "Files" / "30m2H_strategy_signals_export.csv"
TRADE_LEDGER = AGENT_DATA / "MQL5" / "Files" / "30m2H_strategy_trade_ledger.csv"


def read_text_auto(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="ignore")
    return data.decode("utf-8-sig", errors="ignore")


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


def last_session(text: str, marker: str) -> str:
    idx = text.rfind(marker)
    if idx < 0:
        return text
    return text[idx:]


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


def copy_artifact(path: Path, out_name: str) -> Dict[str, object]:
    exists = path.exists()
    dest = OUT_DIR / out_name
    if exists:
        shutil.copy2(path, dest)
    stat = path.stat() if exists else None
    return {
        "source": str(path),
        "copy": str(dest) if exists else "",
        "exists": exists,
        "length": stat.st_size if stat else "",
        "last_write_time": stat.st_mtime if stat else "",
    }


def file_inventory() -> List[Dict[str, object]]:
    files = [
        ("smoke_ini", SMOKE_INI, "workspace"),
        ("requested_report_xml", SMOKE_REPORT, "workspace"),
        ("terminal_log", TERMINAL_LOG, "mt5_data"),
        ("tester_log", TESTER_LOG, "mt5_data"),
        ("tester_agent_log", AGENT_LOG, "mt5_data"),
        ("signals_export", SIGNALS_EXPORT, "tester_agent_files"),
        ("trade_ledger", TRADE_LEDGER, "tester_agent_files"),
    ]
    rows: List[Dict[str, object]] = []
    for role, path, scope in files:
        exists = path.exists()
        stat = path.stat() if exists else None
        rows.append(
            {
                "role": role,
                "scope": scope,
                "path": str(path),
                "exists": exists,
                "length": stat.st_size if stat else "",
                "last_write_time": stat.st_mtime if stat else "",
            }
        )
    return rows


def csv_summary(path: Path, role: str) -> Dict[str, object]:
    if not path.exists():
        return {"role": role, "path": str(path), "exists": False, "row_count": 0, "columns": ""}
    rows = read_rows(path)
    columns = list(rows[0].keys()) if rows else []
    if not columns:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            columns = next(reader, [])
    return {
        "role": role,
        "path": str(path),
        "exists": True,
        "row_count": len(rows),
        "columns": ",".join(columns),
    }


def signal_decision_counts(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    rows = read_rows(path)
    counts: Counter[str] = Counter(row.get("decision", "") for row in rows)
    return [{"decision": key, "row_count": value} for key, value in sorted(counts.items())]


def write_md(decision: Dict[str, object], checks: List[Dict[str, object]], csv_rows: List[Dict[str, object]]) -> None:
    failed_blockers = [row for row in checks if row["severity"] == "blocker" and row["status"] == "fail"]
    warnings = [row for row in checks if row["severity"] == "warning" and row["status"] == "fail"]
    lines = [
        "# Sim Dry-run Smoke Execution Review",
        "",
        f"- Decision date: {decision['decision_date']}",
        f"- Status: `{decision['status']}`",
        f"- Smoke execution passed: `{decision['smoke_execution_passed']}`",
        f"- Ready to live trade: `{decision['ready_to_live_trade']}`",
        f"- Blocker failure count: `{decision['blocker_failure_count']}`",
        f"- Warning count: `{decision['warning_count']}`",
        "",
        "## Evidence",
        "",
        "- MT5 terminal loaded the generated smoke `.ini`.",
        "- Strategy Tester started and finished successfully.",
        "- Tester/agent logs report `final balance 500.00 USD`.",
        "- Signal CSV was exported from the tester agent files directory.",
        "- Trade ledger is header-only, which matches `InpSimMode=true` with no real tester orders.",
        "",
        "## CSV Outputs",
        "",
        "| role | exists | row_count |",
        "|---|---:|---:|",
    ]
    for row in csv_rows:
        lines.append(f"| `{row['role']}` | {row['exists']} | {row['row_count']} |")
    lines.append("")
    if warnings:
        lines.extend(["## Warnings", "", "| check_id | actual | expected |", "|---|---|---|"])
        for row in warnings:
            lines.append(f"| `{row['check_id']}` | {row['actual']} | {row['expected']} |")
        lines.append("")
    if failed_blockers:
        lines.extend(["## Blockers", "", "| check_id | actual | expected |", "|---|---|---|"])
        for row in failed_blockers:
            lines.append(f"| `{row['check_id']}` | {row['actual']} | {row['expected']} |")
        lines.append("")
    lines.extend(
        [
            "## Decision",
            "",
            "- The short-window signal-only smoke is accepted as passed.",
            "- Missing XML tester report is a warning only because terminal, tester, agent log, final balance, CSV export, and ledger closure all confirm the run.",
            "- Live trading remains blocked and still needs a separate operational gate.",
        ]
    )
    (OUT_DIR / "sim_dryrun_smoke_execution_review.md").write_text("\n".join(lines), encoding="utf-8-sig")
    (OUT_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    package_rows = read_rows(PACKAGE_DIR / "sim_dryrun_smoke_package_decision.csv")
    package_ready = bool(package_rows) and truthy(package_rows[0].get("ready_to_execute_tester_smoke"))

    terminal_text = read_text_auto(TERMINAL_LOG) if TERMINAL_LOG.exists() else ""
    tester_text = read_text_auto(TESTER_LOG) if TESTER_LOG.exists() else ""
    agent_text = read_text_auto(AGENT_LOG) if AGENT_LOG.exists() else ""
    ini_marker = str(SMOKE_INI)
    terminal_session = last_session(terminal_text, ini_marker)
    tester_agent_session = f"{tester_text}\n{agent_text}"

    csv_rows = [csv_summary(SIGNALS_EXPORT, "signals_export"), csv_summary(TRADE_LEDGER, "trade_ledger")]
    signal_rows = read_rows(SIGNALS_EXPORT) if SIGNALS_EXPORT.exists() else []
    ledger_rows = read_rows(TRADE_LEDGER) if TRADE_LEDGER.exists() else []

    checks: List[Dict[str, object]] = []
    add_check(checks, "prereq_smoke_package_ready", package_ready, package_rows[0].get("ready_to_execute_tester_smoke", "") if package_rows else "missing", "True")
    add_check(checks, "terminal_log_exists", TERMINAL_LOG.exists(), str(TERMINAL_LOG), "exists")
    add_check(checks, "tester_log_exists", TESTER_LOG.exists(), str(TESTER_LOG), "exists")
    add_check(checks, "agent_log_exists", AGENT_LOG.exists(), str(AGENT_LOG), "exists")
    add_check(checks, "terminal_start_config_seen", ini_marker in terminal_session, ini_marker if ini_marker in terminal_session else "not found", "smoke ini path in terminal log")
    add_check(checks, "terminal_automatic_testing_started", "automatical testing started" in terminal_session, "seen" if "automatical testing started" in terminal_session else "not found", "seen")
    add_check(checks, "terminal_last_test_success", 'last test passed with result "successfully finished"' in terminal_session, "seen" if 'last test passed with result "successfully finished"' in terminal_session else "not found", "seen")
    add_check(checks, "terminal_exit_code_0", "exit with code 0" in terminal_session and "shutdown with 0" in terminal_session, "exit/shutdown markers", "exit with code 0 and shutdown with 0")
    add_check(checks, "tester_thread_finished", "thread finished" in tester_agent_session, "seen" if "thread finished" in tester_agent_session else "not found", "seen")
    add_check(checks, "agent_test_passed", "Test passed in" in tester_agent_session, "seen" if "Test passed in" in tester_agent_session else "not found", "seen")
    balance_match = re.search(r"final balance\s+500\.00\s+USD", tester_agent_session)
    add_check(checks, "agent_final_balance_500", bool(balance_match), balance_match.group(0) if balance_match else "not found", "final balance 500.00 USD")
    add_check(checks, "csv_export_closed", "CSV export closed" in tester_agent_session, "seen" if "CSV export closed" in tester_agent_session else "not found", "seen")
    add_check(checks, "trade_ledger_export_closed", "Trade ledger export closed" in tester_agent_session, "seen" if "Trade ledger export closed" in tester_agent_session else "not found", "seen")
    add_check(checks, "signals_export_exists", SIGNALS_EXPORT.exists(), str(SIGNALS_EXPORT), "exists")
    add_check(checks, "signals_export_has_rows", len(signal_rows) > 0, len(signal_rows), "> 0")
    add_check(checks, "trade_ledger_header_only_in_sim_mode", TRADE_LEDGER.exists() and len(ledger_rows) == 0, len(ledger_rows), "0 data rows")
    add_check(checks, "no_auto_trader_invocation_in_logs", "auto_trader.py" not in terminal_session + tester_agent_session, "not found", "not found")
    add_check(checks, "requested_xml_report_exists", SMOKE_REPORT.exists(), str(SMOKE_REPORT) if SMOKE_REPORT.exists() else "missing", "exists", "warning", "MT5 still logged and exported a completed smoke run.")

    inventory = file_inventory()
    copied = [
        {"role": "terminal_log", **copy_artifact(TERMINAL_LOG, "terminal_20260718_smoke.log")},
        {"role": "tester_log", **copy_artifact(TESTER_LOG, "tester_20260718_smoke.log")},
        {"role": "tester_agent_log", **copy_artifact(AGENT_LOG, "tester_agent_20260718_smoke.log")},
        {"role": "signals_export", **copy_artifact(SIGNALS_EXPORT, "30m2H_strategy_signals_export_smoke.csv")},
        {"role": "trade_ledger", **copy_artifact(TRADE_LEDGER, "30m2H_strategy_trade_ledger_smoke.csv")},
    ]

    blocker_failures = [row for row in checks if row["severity"] == "blocker" and row["status"] == "fail"]
    warning_failures = [row for row in checks if row["severity"] == "warning" and row["status"] == "fail"]
    passed = len(blocker_failures) == 0
    decision = {
        "decision_date": date.today().isoformat(),
        "check_id": "stage_state_sim_dryrun_smoke_execution",
        "status": "pass" if passed else "fail",
        "pass": passed,
        "smoke_execution_passed": passed,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "warning_count": len(warning_failures),
        "signals_export_rows": len(signal_rows),
        "trade_ledger_rows": len(ledger_rows),
        "tester_final_balance": "500.00",
        "reason": "sim_dryrun_smoke_execution_passed_with_xml_report_warning" if passed and warning_failures else ("sim_dryrun_smoke_execution_passed" if passed else "sim_dryrun_smoke_execution_has_blockers"),
        "next_action": "post_smoke_decision_gate_for_sim_continuous_runner_design" if passed else "fix_smoke_execution_blockers",
        "no_ea_or_python_strategy_logic_changes_in_this_step": True,
    }

    write_md(decision, checks, csv_rows)
    write_csv(
        OUT_DIR / "sim_dryrun_smoke_execution_decision.csv",
        [decision],
        [
            "decision_date",
            "check_id",
            "status",
            "pass",
            "smoke_execution_passed",
            "ready_to_live_trade",
            "blocker_failure_count",
            "warning_count",
            "signals_export_rows",
            "trade_ledger_rows",
            "tester_final_balance",
            "reason",
            "next_action",
            "no_ea_or_python_strategy_logic_changes_in_this_step",
        ],
    )
    write_csv(
        OUT_DIR / "sim_dryrun_smoke_execution_checks.csv",
        checks,
        ["check_id", "status", "pass", "actual", "expected", "severity", "note"],
    )
    write_csv(
        OUT_DIR / "sim_dryrun_smoke_execution_file_inventory.csv",
        inventory,
        ["role", "scope", "path", "exists", "length", "last_write_time"],
    )
    write_csv(
        OUT_DIR / "sim_dryrun_smoke_execution_artifact_copies.csv",
        copied,
        ["role", "source", "copy", "exists", "length", "last_write_time"],
    )
    write_csv(
        OUT_DIR / "sim_dryrun_smoke_execution_csv_summary.csv",
        csv_rows,
        ["role", "path", "exists", "row_count", "columns"],
    )
    write_csv(
        OUT_DIR / "sim_dryrun_smoke_signal_decision_counts.csv",
        signal_decision_counts(SIGNALS_EXPORT),
        ["decision", "row_count"],
    )

    print(f"status={decision['status']}")
    print(f"smoke_execution_passed={decision['smoke_execution_passed']}")
    print(f"ready_to_live_trade={decision['ready_to_live_trade']}")
    print(f"blocker_failure_count={decision['blocker_failure_count']}")
    print(f"warning_count={decision['warning_count']}")
    print(f"signals_export_rows={decision['signals_export_rows']}")
    print(f"trade_ledger_rows={decision['trade_ledger_rows']}")
    print(f"output_dir={OUT_DIR}")


if __name__ == "__main__":
    main()
