from __future__ import annotations


import csv
import json
import re
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
AUTO_TRADE = ROOT / "auto_trade"
OUT_DIR = VALIDATION_DIR / "stage_state_nonprod_mt5_rehearsal_execution_20260721"

PACKAGE_DECISION = (
    VALIDATION_DIR
    / "stage_state_nonprod_mt5_rehearsal_package_20260721"
    / "nonprod_mt5_rehearsal_package_decision.json"
)
DEMO_DECISION = (
    VALIDATION_DIR
    / "stage_state_demo_manual_confirmation_package_20260721"
    / "demo_manual_confirmation_decision.json"
)

INI = AUTO_TRADE / "30m2H_Strategy_EA.nonprod_demo_rehearsal_20260601_20260707_20260721.ini"
REPORT_XML = AUTO_TRADE / "nonprod_demo_rehearsal_20260601_20260707_20260721_report.xml"
TERMINAL_LOG = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\logs\20260721.log"
)
TESTER_LOG = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\tester\logs\20260721.log"
)
AGENT_LOG = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\B695BCB6C1E6864B6D96307B87B29F16\Agent-127.0.0.1-3000\logs\20260721.log"
)
AGENT_FILES = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\B695BCB6C1E6864B6D96307B87B29F16\Agent-127.0.0.1-3000\MQL5\Files"
)
SIGNALS_EXPORT = AGENT_FILES / "30m2H_strategy_signals_export.csv"
TRADE_LEDGER = AGENT_FILES / "30m2H_strategy_trade_ledger.csv"
DEAL_HISTORY = AGENT_FILES / "30m2H_strategy_deal_history.csv"


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def decode_bytes(data: bytes) -> str:
    for encoding in ("utf-16", "utf-16-le", "utf-8-sig", "utf-8"):
        try:
            text = data.decode(encoding)
        except UnicodeError:
            continue
        if "\x00" not in text[:200]:
            return text
    return data.decode("utf-8", errors="ignore")


def read_text_auto(path: Path) -> str:
    return decode_bytes(path.read_bytes())


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


def boolish(value: object) -> bool:
    return str(value).strip().lower() == "true"


def safe_float(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def redact(text: str) -> str:
    text = re.sub(r"'\d{5,}'", "'ACCOUNT_REDACTED'", text)
    text = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "IP_REDACTED", text)
    return text


def last_session(text: str) -> str:
    marker = str(INI)
    idx = text.rfind(marker)
    return text[idx:] if idx >= 0 else text


def copy_redacted_log(source: Path, name: str) -> Dict[str, object]:
    exists = source.exists()
    dest = OUT_DIR / name
    if exists:
        dest.write_text(redact(read_text_auto(source)), encoding="utf-8-sig")
    stat = source.stat() if exists else None
    return {
        "role": name,
        "source": str(source),
        "copy": str(dest) if exists else "",
        "exists": exists,
        "length": stat.st_size if stat else "",
        "last_write_time": stat.st_mtime if stat else "",
        "redacted": exists,
    }


def copy_csv(source: Path, name: str) -> Dict[str, object]:
    exists = source.exists()
    dest = OUT_DIR / name
    if exists:
        shutil.copy2(source, dest)
    stat = source.stat() if exists else None
    return {
        "role": name,
        "source": str(source),
        "copy": str(dest) if exists else "",
        "exists": exists,
        "length": stat.st_size if stat else "",
        "last_write_time": stat.st_mtime if stat else "",
        "redacted": False,
    }


def csv_summary(path: Path, role: str) -> Dict[str, object]:
    if not path.exists():
        return {"role": role, "exists": False, "row_count": 0, "columns": ""}
    rows = read_rows(path)
    columns = list(rows[0].keys()) if rows else []
    return {"role": role, "exists": True, "row_count": len(rows), "columns": ",".join(columns)}


def check(
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


def redacted_logs_have_unredacted_account() -> bool:
    pattern = re.compile(r"'\d{5,}'")
    for path in OUT_DIR.glob("*_redacted.log"):
        text = path.read_text(encoding="utf-8-sig", errors="ignore")
        if pattern.search(text):
            return True
    return False


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now().isoformat(timespec="seconds")
    package = read_json(PACKAGE_DECISION)
    demo = read_json(DEMO_DECISION)

    terminal_text = read_text_auto(TERMINAL_LOG) if TERMINAL_LOG.exists() else ""
    tester_text = read_text_auto(TESTER_LOG) if TESTER_LOG.exists() else ""
    agent_text = read_text_auto(AGENT_LOG) if AGENT_LOG.exists() else ""
    terminal_session = last_session(terminal_text)
    tester_agent_session = f"{tester_text}\n{agent_text}"

    signals = read_rows(SIGNALS_EXPORT) if SIGNALS_EXPORT.exists() else []
    ledger = read_rows(TRADE_LEDGER) if TRADE_LEDGER.exists() else []
    deals = read_rows(DEAL_HISTORY) if DEAL_HISTORY.exists() else []

    lots = [safe_float(row.get("lots", "")) for row in ledger if row.get("lots", "")]
    net_profit = sum(safe_float(row.get("net_profit", "")) for row in ledger)
    exit_counts = Counter(row.get("local_exit_reason", "") for row in ledger)
    stage_counts = Counter(row.get("stage", "") for row in ledger)
    deal_reason_counts = Counter(row.get("deal_reason", "") for row in ledger)
    deal_entry_counts = Counter(row.get("deal_entry", "") for row in deals)

    final_balance_match = re.search(r"final balance\s+([0-9]+\.[0-9]{2})\s+USD", tester_agent_session)
    final_balance = final_balance_match.group(1) if final_balance_match else ""

    artifacts = [
        copy_redacted_log(TERMINAL_LOG, "terminal_20260721_nonprod_rehearsal_redacted.log"),
        copy_redacted_log(TESTER_LOG, "tester_20260721_nonprod_rehearsal_redacted.log"),
        copy_redacted_log(AGENT_LOG, "tester_agent_20260721_nonprod_rehearsal_redacted.log"),
        copy_csv(SIGNALS_EXPORT, "30m2H_strategy_signals_export_nonprod_rehearsal.csv"),
        copy_csv(TRADE_LEDGER, "30m2H_strategy_trade_ledger_nonprod_rehearsal.csv"),
        copy_csv(DEAL_HISTORY, "30m2H_strategy_deal_history_nonprod_rehearsal.csv"),
    ]
    if REPORT_XML.exists():
        artifacts.append(copy_csv(REPORT_XML, "nonprod_demo_rehearsal_report.xml"))

    summaries = [
        csv_summary(SIGNALS_EXPORT, "signals_export"),
        csv_summary(TRADE_LEDGER, "trade_ledger"),
        csv_summary(DEAL_HISTORY, "deal_history"),
    ]
    lifecycle_rows: List[Dict[str, object]] = [
        {"metric": "final_balance", "value": final_balance, "note": ""},
        {"metric": "initial_deposit", "value": package.get("deposit", ""), "note": ""},
        {"metric": "net_profit_sum_from_ledger", "value": round(net_profit, 2), "note": ""},
        {"metric": "signal_rows", "value": len(signals), "note": ""},
        {"metric": "trade_ledger_rows", "value": len(ledger), "note": ""},
        {"metric": "deal_history_rows", "value": len(deals), "note": ""},
        {"metric": "min_lot", "value": min(lots) if lots else "", "note": ""},
        {"metric": "max_lot", "value": max(lots) if lots else "", "note": ""},
        {"metric": "sl_rows", "value": deal_reason_counts.get("SL", 0), "note": ""},
        {"metric": "expert_exit_rows", "value": deal_reason_counts.get("EXPERT", 0), "note": ""},
        {"metric": "deal_entry_in_rows", "value": deal_entry_counts.get("IN", 0), "note": ""},
        {"metric": "deal_entry_out_rows", "value": deal_entry_counts.get("OUT", 0), "note": ""},
    ]
    for key, value in sorted(exit_counts.items()):
        lifecycle_rows.append({"metric": f"local_exit_reason_{key or 'blank'}", "value": value, "note": ""})
    for key, value in sorted(stage_counts.items()):
        lifecycle_rows.append({"metric": f"stage_{key or 'blank'}", "value": value, "note": ""})
    for key, value in sorted(deal_reason_counts.items()):
        lifecycle_rows.append({"metric": f"deal_reason_{key or 'blank'}", "value": value, "note": ""})

    checks = [
        check("package_ready", package.get("ready_to_execute_nonprod_rehearsal") is True, package.get("ready_to_execute_nonprod_rehearsal"), True),
        check("demo_ready_not_live", demo.get("ready_to_nonprod_rehearsal") is True and demo.get("ready_to_live_trade") is False, f"nonprod={demo.get('ready_to_nonprod_rehearsal')} live={demo.get('ready_to_live_trade')}", "nonprod true, live false"),
        check("terminal_loaded_expected_ini", str(INI) in terminal_session, "seen" if str(INI) in terminal_session else "not found", "seen"),
        check("terminal_tester_started", "automatical testing started" in terminal_session, "seen" if "automatical testing started" in terminal_session else "not found", "seen"),
        check("terminal_tester_finished_success", 'last test passed with result "successfully finished"' in terminal_session, "seen" if 'last test passed with result "successfully finished"' in terminal_session else "not found", "seen"),
        check("terminal_shutdown_code_0", "exit with code 0" in terminal_session and "shutdown with 0" in terminal_session, "seen" if "exit with code 0" in terminal_session and "shutdown with 0" in terminal_session else "not found", "seen"),
        check("agent_test_passed", "Test passed in" in tester_agent_session, "seen" if "Test passed in" in tester_agent_session else "not found", "seen"),
        check("final_balance_2043_70", final_balance == "2043.70", final_balance, "2043.70"),
        check("signals_export_rows_1180", len(signals) == 1180, len(signals), 1180),
        check("trade_ledger_has_rows", len(ledger) > 0, len(ledger), "> 0"),
        check("deal_history_has_rows", len(deals) > 0, len(deals), "> 0"),
        check("deal_history_has_in_and_out", deal_entry_counts.get("IN", 0) > 0 and deal_entry_counts.get("OUT", 0) > 0, f"IN={deal_entry_counts.get('IN', 0)} OUT={deal_entry_counts.get('OUT', 0)}", "IN>0 and OUT>0"),
        check("sl_and_expert_exits_present", deal_reason_counts.get("SL", 0) > 0 and deal_reason_counts.get("EXPERT", 0) > 0, f"SL={deal_reason_counts.get('SL', 0)} EXPERT={deal_reason_counts.get('EXPERT', 0)}", "SL>0 and EXPERT>0"),
        check("stages_1_2_3_present", all(stage_counts.get(str(i), 0) > 0 for i in (1, 2, 3)), f"stage_counts={dict(stage_counts)}", "1/2/3 present"),
        check("lots_within_strategy_cap", bool(lots) and min(lots) >= 0.01 and max(lots) <= 10.0, f"min={min(lots) if lots else ''} max={max(lots) if lots else ''}", "0.01 <= lots <= 10.0"),
        check("net_profit_matches_balance_delta", round(net_profit, 2) == round(safe_float(final_balance) - safe_float(str(package.get("deposit", "0"))), 2), round(net_profit, 2), round(safe_float(final_balance) - safe_float(str(package.get("deposit", "0"))), 2)),
        check("no_python_runner_invocation", "auto_trader.py" not in terminal_session + tester_agent_session, "not found", "not found"),
        check("report_xml_optional", REPORT_XML.exists(), str(REPORT_XML) if REPORT_XML.exists() else "missing", "exists", "warning", "MT5 tester logs and CSV exports are authoritative for this run if XML is absent."),
    ]

    unredacted = redacted_logs_have_unredacted_account()
    checks.append(check("redacted_logs_no_full_account", not unredacted, unredacted, False))
    blocker_failures = [row for row in checks if row["severity"] == "blocker" and not row["pass"]]
    warning_failures = [row for row in checks if row["severity"] == "warning" and not row["pass"]]

    decision = {
        "decision_time": collected_at,
        "check_id": "stage_state_nonprod_mt5_rehearsal_execution",
        "status": "nonprod_mt5_rehearsal_passed" if not blocker_failures else "nonprod_mt5_rehearsal_failed",
        "nonprod_rehearsal_passed": not blocker_failures,
        "final_balance": final_balance,
        "initial_deposit": package.get("deposit", ""),
        "profit": round(net_profit, 2),
        "signal_rows": len(signals),
        "trade_ledger_rows": len(ledger),
        "deal_history_rows": len(deals),
        "sl_rows": deal_reason_counts.get("SL", 0),
        "expert_exit_rows": deal_reason_counts.get("EXPERT", 0),
        "min_lot": min(lots) if lots else "",
        "max_lot": max(lots) if lots else "",
        "runner_executed": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "warning_count": len(warning_failures),
        "recommended_next_action": "update_live_gate_with_nonprod_rehearsal_evidence_then_keep_live_blocked_pending_real_live_risk_limits",
    }

    write_csv(OUT_DIR / "nonprod_mt5_rehearsal_artifacts.csv", artifacts, ["role", "source", "copy", "exists", "length", "last_write_time", "redacted"])
    write_csv(OUT_DIR / "nonprod_mt5_rehearsal_csv_summary.csv", summaries, ["role", "exists", "row_count", "columns"])
    write_csv(OUT_DIR / "nonprod_mt5_rehearsal_lifecycle_metrics.csv", lifecycle_rows, ["metric", "value", "note"])
    write_csv(OUT_DIR / "nonprod_mt5_rehearsal_checks.csv", checks, ["check_id", "status", "pass", "actual", "expected", "severity", "note"])
    write_csv(OUT_DIR / "nonprod_mt5_rehearsal_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "nonprod_mt5_rehearsal_decision.json", decision)

    report_lines = [
        "# Non-production MT5 Rehearsal Execution Review",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- nonprod_rehearsal_passed: `{decision['nonprod_rehearsal_passed']}`",
        f"- initial_deposit: `{decision['initial_deposit']}`",
        f"- final_balance: `{decision['final_balance']}`",
        f"- profit: `{decision['profit']}`",
        f"- signal_rows: `{decision['signal_rows']}`",
        f"- trade_ledger_rows: `{decision['trade_ledger_rows']}`",
        f"- deal_history_rows: `{decision['deal_history_rows']}`",
        f"- sl_rows: `{decision['sl_rows']}`",
        f"- expert_exit_rows: `{decision['expert_exit_rows']}`",
        f"- min_lot: `{decision['min_lot']}`",
        f"- max_lot: `{decision['max_lot']}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Boundary",
        "",
        "- MT5 Strategy Tester executed the EA in a non-production rehearsal window.",
        "- Logs were copied in redacted form.",
        "- The Python runner was not executed.",
        "- This does not approve real-money live trading.",
        "",
        "## Lifecycle Metrics",
        "",
    ]
    for row in lifecycle_rows:
        report_lines.append(f"- `{row['metric']}`: `{row['value']}`")
    report_lines.extend(["", "## Checks", ""])
    for row in checks:
        report_lines.append(f"- `{row['check_id']}`: `{row['pass']}` - actual `{row['actual']}`, expected `{row['expected']}`")
    report_lines.append("")
    (OUT_DIR / "nonprod_mt5_rehearsal_execution_review.md").write_text("\n".join(report_lines), encoding="utf-8-sig")

    for key, value in decision.items():
        print(f"{key}={value}")
    return 1 if blocker_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
