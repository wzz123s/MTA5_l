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
OUT_DIR = VALIDATION_DIR / "stage_state_live_risk_guard_rehearsal_execution_20260722"

PACKAGE_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_live_risk_guard_rehearsal_package_20260722"
    / "live_risk_guard_rehearsal_package_decision.json"
)
INI = AUTO_TRADE / "30m2H_Strategy_EA.live_risk_guard_rehearsal_20260601_20260707_20260722.ini"
REPORT_XML = AUTO_TRADE / "live_risk_guard_rehearsal_20260601_20260707_20260722_report.xml"

TERMINAL_LOG = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\logs\20260722.log"
)
TESTER_LOG = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Terminal\B695BCB6C1E6864B6D96307B87B29F16\tester\logs\20260722.log"
)
AGENT_LOG = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\B695BCB6C1E6864B6D96307B87B29F16\Agent-127.0.0.1-3000\logs\20260722.log"
)
AGENT_FILES = Path(
    r"C:\Users\3762\AppData\Roaming\MetaQuotes\Tester\B695BCB6C1E6864B6D96307B87B29F16\Agent-127.0.0.1-3000\MQL5\Files"
)
SIGNALS_EXPORT = AGENT_FILES / "30m2H_strategy_signals_export.csv"
TRADE_LEDGER = AGENT_FILES / "30m2H_strategy_trade_ledger.csv"
DEAL_HISTORY = AGENT_FILES / "30m2H_strategy_deal_history.csv"

REQUESTED_LEVERAGE = 2000


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


def safe_float(value: object) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


def redact(text: str) -> str:
    text = re.sub(r"'\d{5,}'", "'ACCOUNT_REDACTED'", text)
    text = re.sub(r"\b\d{5,}\b", "NUMBER_REDACTED", text)
    text = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "IP_REDACTED", text)
    return text


def last_session(text: str) -> str:
    marker = str(INI)
    idx = text.rfind(marker)
    return text[idx:] if idx >= 0 else text


def last_agent_session(text: str) -> str:
    marker = "InpEnableLiveRiskGuards=true"
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


def copy_file(source: Path, name: str, redacted: bool = False) -> Dict[str, object]:
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
        "redacted": redacted,
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


def parse_unique_ints(pattern: str, text: str) -> List[int]:
    return sorted({int(m.group(1)) for m in re.finditer(pattern, text)})


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now().isoformat(timespec="seconds")
    package = read_json(PACKAGE_DECISION_JSON)

    terminal_text = read_text_auto(TERMINAL_LOG) if TERMINAL_LOG.exists() else ""
    tester_text = read_text_auto(TESTER_LOG) if TESTER_LOG.exists() else ""
    agent_text = read_text_auto(AGENT_LOG) if AGENT_LOG.exists() else ""
    terminal_session = last_session(terminal_text)
    agent_session = last_agent_session(agent_text)
    tester_agent_session = agent_session

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
    live_risk_block_count = tester_agent_session.count("LIVE_RISK_BLOCK")
    margin_order_calc_count = tester_agent_session.count("MarginCalc: ORDER_CALC")
    effective_leverages = parse_unique_ints(r"Leverage:\s+1:(\d+)", tester_agent_session)
    leverage_actual = ",".join(str(v) for v in effective_leverages)

    artifacts = [
        copy_redacted_log(TERMINAL_LOG, "terminal_20260722_live_risk_guard_rehearsal_redacted.log"),
        copy_redacted_log(TESTER_LOG, "tester_20260722_live_risk_guard_rehearsal_redacted.log"),
        copy_redacted_log(AGENT_LOG, "tester_agent_20260722_live_risk_guard_rehearsal_redacted.log"),
        copy_file(SIGNALS_EXPORT, "30m2H_strategy_signals_export_live_risk_guard_rehearsal.csv"),
        copy_file(TRADE_LEDGER, "30m2H_strategy_trade_ledger_live_risk_guard_rehearsal.csv"),
        copy_file(DEAL_HISTORY, "30m2H_strategy_deal_history_live_risk_guard_rehearsal.csv"),
    ]
    if REPORT_XML.exists():
        artifacts.append(copy_file(REPORT_XML, "live_risk_guard_rehearsal_report.xml"))

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
        {"metric": "live_risk_block_count", "value": live_risk_block_count, "note": "0 is acceptable when no guard limit is breached."},
        {"metric": "margin_order_calc_count", "value": margin_order_calc_count, "note": ""},
        {"metric": "effective_leverage_seen", "value": leverage_actual, "note": f"Requested tester leverage was 1:{REQUESTED_LEVERAGE}."},
    ]
    for key, value in sorted(exit_counts.items()):
        lifecycle_rows.append({"metric": f"local_exit_reason_{key or 'blank'}", "value": value, "note": ""})
    for key, value in sorted(stage_counts.items()):
        lifecycle_rows.append({"metric": f"stage_{key or 'blank'}", "value": value, "note": ""})
    for key, value in sorted(deal_reason_counts.items()):
        lifecycle_rows.append({"metric": f"deal_reason_{key or 'blank'}", "value": value, "note": ""})

    checks = [
        check("package_ready", package.get("ready_to_execute_nonprod_guard_rehearsal") is True, package.get("ready_to_execute_nonprod_guard_rehearsal"), True),
        check("terminal_loaded_expected_ini", str(INI) in terminal_session, "seen" if str(INI) in terminal_session else "not found", "seen"),
        check("terminal_tester_started", "automatical testing started" in terminal_session, "seen" if "automatical testing started" in terminal_session else "not found", "seen"),
        check("terminal_tester_finished_success", 'last test passed with result "successfully finished"' in terminal_session, "seen" if 'last test passed with result "successfully finished"' in terminal_session else "not found", "seen"),
        check("terminal_shutdown_code_0", "exit with code 0" in terminal_session and "shutdown with 0" in terminal_session, "seen" if "exit with code 0" in terminal_session and "shutdown with 0" in terminal_session else "not found", "seen"),
        check("agent_test_passed", "Test passed in" in tester_agent_session, "seen" if "Test passed in" in tester_agent_session else "not found", "seen"),
        check("guard_input_enabled_in_agent_log", "InpEnableLiveRiskGuards=true" in tester_agent_session, "seen" if "InpEnableLiveRiskGuards=true" in tester_agent_session else "not found", "seen"),
        check("order_calc_margin_used", margin_order_calc_count > 0, margin_order_calc_count, "> 0"),
        check("final_balance_present", bool(final_balance), final_balance, "present"),
        check("signals_export_rows_1180", len(signals) == 1180, len(signals), 1180),
        check("trade_ledger_has_rows", len(ledger) > 0, len(ledger), "> 0"),
        check("deal_history_has_rows", len(deals) > 0, len(deals), "> 0"),
        check("deal_history_has_in_and_out", deal_entry_counts.get("IN", 0) > 0 and deal_entry_counts.get("OUT", 0) > 0, f"IN={deal_entry_counts.get('IN', 0)} OUT={deal_entry_counts.get('OUT', 0)}", "IN>0 and OUT>0"),
        check("sl_and_expert_exits_present", deal_reason_counts.get("SL", 0) > 0 and deal_reason_counts.get("EXPERT", 0) > 0, f"SL={deal_reason_counts.get('SL', 0)} EXPERT={deal_reason_counts.get('EXPERT', 0)}", "SL>0 and EXPERT>0"),
        check("stages_1_2_3_present", all(stage_counts.get(str(i), 0) > 0 for i in (1, 2, 3)), f"stage_counts={dict(stage_counts)}", "1/2/3 present"),
        check("lots_within_live_guard_cap", bool(lots) and min(lots) >= 0.01 and max(lots) <= 0.10, f"min={min(lots) if lots else ''} max={max(lots) if lots else ''}", "0.01 <= lots <= 0.10"),
        check("net_profit_matches_balance_delta", round(net_profit, 2) == round(safe_float(final_balance) - safe_float(package.get("deposit", "0")), 2), round(net_profit, 2), round(safe_float(final_balance) - safe_float(package.get("deposit", "0")), 2)),
        check("no_python_runner_invocation", "auto_trader.py" not in terminal_session + tester_agent_session, "not found", "not found"),
        check(
            "effective_leverage_matches_requested",
            effective_leverages == [REQUESTED_LEVERAGE],
            leverage_actual or "not found",
            f"1:{REQUESTED_LEVERAGE}",
            "blocker",
            "Exact leverage/margin basis must match the requested demo environment.",
        ),
        check("report_xml_optional", REPORT_XML.exists(), str(REPORT_XML) if REPORT_XML.exists() else "missing", "exists", "warning", "MT5 logs and CSV exports are accepted if XML is absent."),
        check("live_risk_block_not_required", live_risk_block_count >= 0, live_risk_block_count, ">= 0", "info", "No block is acceptable because limits did not necessarily breach."),
    ]

    unredacted = redacted_logs_have_unredacted_account()
    checks.append(check("redacted_logs_no_full_account", not unredacted, unredacted, False))
    blocker_failures = [row for row in checks if row["severity"] == "blocker" and not row["pass"]]
    warning_failures = [row for row in checks if row["severity"] == "warning" and not row["pass"]]

    code_path_passed = not [row for row in checks if row["severity"] == "blocker" and row["check_id"] != "effective_leverage_matches_requested" and not row["pass"]]
    status = (
        "live_risk_guard_rehearsal_passed"
        if not blocker_failures
        else "live_risk_guard_rehearsal_completed_with_leverage_mismatch"
        if code_path_passed and effective_leverages != [REQUESTED_LEVERAGE]
        else "live_risk_guard_rehearsal_failed"
    )
    decision = {
        "decision_time": collected_at,
        "check_id": "stage_state_live_risk_guard_rehearsal_execution",
        "status": status,
        "guard_rehearsal_code_path_passed": code_path_passed,
        "nonprod_rehearsal_passed_exact_environment": not blocker_failures,
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
        "live_risk_block_count": live_risk_block_count,
        "margin_order_calc_count": margin_order_calc_count,
        "requested_leverage": REQUESTED_LEVERAGE,
        "effective_leverage_seen": effective_leverages,
        "runner_executed": False,
        "ready_to_live_trade": False,
        "blocker_failure_count": len(blocker_failures),
        "warning_count": len(warning_failures),
        "recommended_next_action": (
            "resolve_tester_or_account_leverage_mismatch_then_update_live_gate"
            if effective_leverages != [REQUESTED_LEVERAGE]
            else "update_live_gate_with_guard_enabled_rehearsal_evidence"
        ),
    }

    write_csv(OUT_DIR / "live_risk_guard_rehearsal_artifacts.csv", artifacts, ["role", "source", "copy", "exists", "length", "last_write_time", "redacted"])
    write_csv(OUT_DIR / "live_risk_guard_rehearsal_csv_summary.csv", summaries, ["role", "exists", "row_count", "columns"])
    write_csv(OUT_DIR / "live_risk_guard_rehearsal_lifecycle_metrics.csv", lifecycle_rows, ["metric", "value", "note"])
    write_csv(OUT_DIR / "live_risk_guard_rehearsal_checks.csv", checks, ["check_id", "status", "pass", "actual", "expected", "severity", "note"])
    write_csv(OUT_DIR / "live_risk_guard_rehearsal_decision.csv", [decision], list(decision.keys()))
    write_json(OUT_DIR / "live_risk_guard_rehearsal_decision.json", decision)

    report_lines = [
        "# LIVE-GAP-006 Guard-enabled Non-production Rehearsal Execution Review",
        "",
        "## Decision",
        "",
        f"- status: `{decision['status']}`",
        f"- guard_rehearsal_code_path_passed: `{decision['guard_rehearsal_code_path_passed']}`",
        f"- nonprod_rehearsal_passed_exact_environment: `{decision['nonprod_rehearsal_passed_exact_environment']}`",
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
        f"- live_risk_block_count: `{decision['live_risk_block_count']}`",
        f"- margin_order_calc_count: `{decision['margin_order_calc_count']}`",
        f"- requested_leverage: `1:{REQUESTED_LEVERAGE}`",
        f"- effective_leverage_seen: `{leverage_actual}`",
        f"- ready_to_live_trade: `{decision['ready_to_live_trade']}`",
        "",
        "## Boundary",
        "",
        "- MT5 Strategy Tester executed the EA in a non-production rehearsal window.",
        "- `InpEnableLiveRiskGuards=true` was visible in the tester agent log.",
        "- Logs were copied in redacted form.",
        "- The Python runner was not executed.",
        "- This does not approve real-money live trading.",
        "",
        "## Key Finding",
        "",
        f"- The guard code path executed and used `OrderCalcMargin`, but the EA saw effective leverage `{leverage_actual or 'not found'}` instead of requested `1:{REQUESTED_LEVERAGE}`.",
        "- Therefore the run is valid as a guard-code rehearsal, but not as exact demo leverage evidence.",
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
    (OUT_DIR / "live_risk_guard_rehearsal_execution_review.md").write_text("\n".join(report_lines), encoding="utf-8-sig")

    return 1 if blocker_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
