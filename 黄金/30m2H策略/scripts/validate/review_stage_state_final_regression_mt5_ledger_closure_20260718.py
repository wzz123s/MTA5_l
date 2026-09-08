from __future__ import annotations


import csv
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


ROOT = Path(r"F:\use_code\MTA5_l")
VALIDATION_DIR = ROOT / "黄金" / "30m2H策略" / "data" / "validation"
MT5_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
MAPPED_REVIEW_DIR = VALIDATION_DIR / "stage_state_final_regression_mapped_alignment_summary_review_20260718"
OUT_DIR = VALIDATION_DIR / "stage_state_final_regression_mt5_ledger_closure_review_20260718"


TRADE_LEDGER = MT5_DIR / "30m2H_strategy_trade_ledger.csv"
DEAL_HISTORY = MT5_DIR / "30m2H_strategy_deal_history.csv"
SIGNALS_EXPORT = MT5_DIR / "30m2H_strategy_signals_export.csv"
TERMINAL_LOG = MT5_DIR / "terminal_20260716.log"
TESTER_LOG = MT5_DIR / "tester_agent_20260716.log"
UNIQUE_SIGNALS = DYNAMIC_DIR / "mt5_ledger_unique_signals.csv"


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def fnum(value: object) -> float:
    try:
        return float(str(value).strip())
    except Exception:
        return 0.0


def truthy(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def normalize_anchor(value: str) -> str:
    text = value.strip()
    for fmt in ("%Y.%m.%d %H:%M", "%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    return text


def count_csv_data_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return max(sum(1 for _line in f) - 1, 0)


def read_log_text(path: Path) -> str:
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="ignore")
    return data.decode("utf-8-sig", errors="ignore")


def add_check(
    checks: List[Dict[str, object]],
    check_id: str,
    actual: object,
    expected: object,
    tolerance: float,
    note: str = "",
) -> None:
    actual_num = fnum(actual)
    expected_num = fnum(expected)
    if isinstance(actual, bool) or isinstance(expected, bool):
        passed = bool(actual) == bool(expected)
        diff: object = ""
    elif isinstance(actual, str) or isinstance(expected, str):
        passed = str(actual) == str(expected)
        diff = ""
    else:
        diff = round(actual_num - expected_num, 10)
        passed = abs(actual_num - expected_num) <= tolerance
    checks.append(
        {
            "check_id": check_id,
            "actual": actual,
            "expected": expected,
            "diff": diff,
            "tolerance": tolerance,
            "pass": passed,
            "note": note,
        }
    )


def parse_tester_log() -> Dict[str, object]:
    final_balance = ""
    final_balance_line_count = 0
    csv_export_closed = False
    for line in read_log_text(TESTER_LOG).splitlines():
        if "final balance" in line.lower():
            match = re.search(r"final balance\s+([0-9.]+)\s+USD", line, flags=re.I)
            if match:
                final_balance = float(match.group(1))
                final_balance_line_count += 1
        if "CSV export closed" in line:
            csv_export_closed = True
    return {
        "tester_final_balance": final_balance,
        "tester_final_balance_line_count": final_balance_line_count,
        "tester_csv_export_closed": csv_export_closed,
    }


def parse_terminal_log() -> Dict[str, object]:
    text = read_log_text(TERMINAL_LOG)
    return {
        "terminal_test_successfully_finished": 'last test passed with result "successfully finished"' in text,
        "terminal_exit_code_0": "exit with code 0" in text,
        "terminal_stopped_0": "stopped with 0" in text,
        "terminal_shutdown_0": "shutdown with 0" in text,
    }


def build_trade_group_summary(trade_rows: List[Dict[str, str]]) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    groups: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in trade_rows:
        groups[normalize_anchor(row.get("signal_anchor_time", ""))].append(row)

    summary_rows: List[Dict[str, object]] = []
    anomaly_rows: List[Dict[str, object]] = []
    for anchor, rows in sorted(groups.items()):
        stages = sorted({int(fnum(row.get("stage"))) for row in rows})
        net_profit = round(sum(fnum(row.get("net_profit")) for row in rows), 6)
        has_deinit = any("deinit" in " ".join(row.values()).lower() for row in rows)
        stage_complete = len(rows) == 3 and stages == [1, 2, 3]
        summary = {
            "signal_anchor_time": anchor,
            "stage_rows": len(rows),
            "stage_list": ",".join(str(stage) for stage in stages),
            "net_profit": net_profit,
            "has_deinit_text": has_deinit,
            "stage_complete": stage_complete,
        }
        summary_rows.append(summary)
        if not stage_complete or has_deinit:
            anomaly_rows.append(summary)
    return summary_rows, anomaly_rows


def build_deal_position_anomalies(deal_rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    groups: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in deal_rows:
        position_id = row.get("position_id", "")
        if position_id:
            groups[position_id].append(row)

    anomalies: List[Dict[str, object]] = []
    for position_id, rows in sorted(groups.items(), key=lambda item: int(fnum(item[0]))):
        in_rows = [row for row in rows if row.get("deal_entry") == "IN"]
        out_rows = [row for row in rows if row.get("deal_entry") == "OUT"]
        in_volume = sum(fnum(row.get("volume")) for row in in_rows)
        out_volume = sum(fnum(row.get("volume")) for row in out_rows)
        ok = len(in_rows) == 1 and len(out_rows) == 1 and abs(in_volume - out_volume) <= 1e-9
        if not ok:
            anomalies.append(
                {
                    "position_id": position_id,
                    "in_rows": len(in_rows),
                    "out_rows": len(out_rows),
                    "in_volume": round(in_volume, 6),
                    "out_volume": round(out_volume, 6),
                    "volume_diff": round(in_volume - out_volume, 10),
                    "position_closed": ok,
                }
            )
    return anomalies


def build_ticket_mismatch_rows(
    trade_rows: List[Dict[str, str]],
    deal_rows: List[Dict[str, str]],
) -> List[Dict[str, object]]:
    out_deals = {row.get("deal_ticket", ""): row for row in deal_rows if row.get("deal_entry") == "OUT"}
    mismatches: List[Dict[str, object]] = []
    for row in trade_rows:
        ticket = row.get("deal_ticket", "")
        deal = out_deals.get(ticket)
        if not deal:
            mismatches.append(
                {
                    "deal_ticket": ticket,
                    "signal_anchor_time": row.get("signal_anchor_time", ""),
                    "stage": row.get("stage", ""),
                    "ledger_net_profit": row.get("net_profit", ""),
                    "deal_net_profit": "",
                    "diff": "",
                    "reason": "missing_out_deal_ticket",
                }
            )
            continue
        diff = fnum(row.get("net_profit")) - fnum(deal.get("net_profit"))
        if abs(diff) > 1e-9:
            mismatches.append(
                {
                    "deal_ticket": ticket,
                    "signal_anchor_time": row.get("signal_anchor_time", ""),
                    "stage": row.get("stage", ""),
                    "ledger_net_profit": row.get("net_profit", ""),
                    "deal_net_profit": deal.get("net_profit", ""),
                    "diff": round(diff, 10),
                    "reason": "net_profit_mismatch",
                }
            )
    return mismatches


def build_unique_signal_mismatches(
    stage_group_rows: List[Dict[str, object]],
    unique_rows: List[Dict[str, str]],
) -> List[Dict[str, object]]:
    stage_by_anchor = {row["signal_anchor_time"]: row for row in stage_group_rows}
    unique_by_anchor = {normalize_anchor(row.get("signal_anchor_time", "")): row for row in unique_rows}
    keys = sorted(set(stage_by_anchor) | set(unique_by_anchor))
    mismatches: List[Dict[str, object]] = []
    for key in keys:
        stage = stage_by_anchor.get(key)
        unique = unique_by_anchor.get(key)
        if not stage or not unique:
            mismatches.append(
                {
                    "signal_anchor_time": key,
                    "stage_group_net_profit": stage.get("net_profit", "") if stage else "",
                    "unique_net_profit": unique.get("net_profit", "") if unique else "",
                    "stage_rows": stage.get("stage_rows", "") if stage else "",
                    "unique_stage_rows": unique.get("stage_rows", "") if unique else "",
                    "diff": "",
                    "reason": "missing_stage_or_unique_anchor",
                }
            )
            continue
        diff = fnum(stage.get("net_profit")) - fnum(unique.get("net_profit"))
        stage_rows_diff = int(fnum(stage.get("stage_rows"))) - int(fnum(unique.get("stage_rows")))
        if abs(diff) > 1e-6 or stage_rows_diff != 0:
            mismatches.append(
                {
                    "signal_anchor_time": key,
                    "stage_group_net_profit": stage.get("net_profit", ""),
                    "unique_net_profit": unique.get("net_profit", ""),
                    "stage_rows": stage.get("stage_rows", ""),
                    "unique_stage_rows": unique.get("stage_rows", ""),
                    "diff": round(diff, 10),
                    "reason": "net_profit_or_stage_rows_mismatch",
                }
            )
    return mismatches


def latest_checklist_rows() -> List[Dict[str, str]]:
    prior = MAPPED_REVIEW_DIR / "final_regression_checklist_status_after_mapped_alignment.csv"
    return read_rows(prior)


def write_audit_md(
    decision: Dict[str, object],
    summary: Dict[str, object],
    checks: List[Dict[str, object]],
) -> None:
    failed_checks = [row for row in checks if not truthy(row.get("pass"))]
    lines: List[str] = []
    lines.append("# Final Regression: MT5 Full Stage-state Ledger Closure Review")
    lines.append("")
    lines.append(f"- Decision date: {decision['decision_date']}")
    lines.append(f"- Check id: `{decision['check_id']}`")
    lines.append(f"- Status: `{decision['status']}`")
    lines.append(f"- Pass: `{decision['pass']}`")
    lines.append(f"- Reason: `{decision['reason']}`")
    lines.append("")
    lines.append("## Closure Snapshot")
    lines.append("")
    lines.append("| metric | value |")
    lines.append("|---|---:|")
    for key in [
        "trade_ledger_stage_rows",
        "trade_ledger_unique_signals",
        "deal_history_rows",
        "deal_history_in_rows",
        "deal_history_out_rows",
        "trade_ledger_net_profit",
        "deal_history_out_net_profit",
        "unique_signals_net_profit",
        "initial_balance",
        "computed_final_balance",
        "unique_final_balance",
        "tester_final_balance",
        "deinit_rows",
    ]:
        lines.append(f"| `{key}` | {summary.get(key, '')} |")
    lines.append("")
    lines.append("## Check Result")
    lines.append("")
    lines.append(f"- Failed checks: `{len(failed_checks)}`")
    lines.append(f"- Stage group anomalies: `{summary['stage_group_anomaly_count']}`")
    lines.append(f"- Position closure anomalies: `{summary['position_closure_anomaly_count']}`")
    lines.append(f"- Ticket profit mismatches: `{summary['ticket_profit_mismatch_count']}`")
    lines.append(f"- Unique signal mismatches: `{summary['unique_signal_mismatch_count']}`")
    lines.append("")
    lines.append("## Boundary")
    lines.append("")
    lines.append("This review validates ledger/accounting closure only. It does not rerun the tester and does not modify EA or Python strategy logic.")
    lines.append("")
    (OUT_DIR / "mt5_ledger_closure_review.md").write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    trade_rows = read_rows(TRADE_LEDGER)
    deal_rows = read_rows(DEAL_HISTORY)
    unique_rows = read_rows(UNIQUE_SIGNALS)

    stage_group_rows, stage_group_anomalies = build_trade_group_summary(trade_rows)
    position_anomalies = build_deal_position_anomalies(deal_rows)
    ticket_mismatches = build_ticket_mismatch_rows(trade_rows, deal_rows)
    unique_mismatches = build_unique_signal_mismatches(stage_group_rows, unique_rows)

    in_deals = [row for row in deal_rows if row.get("deal_entry") == "IN"]
    out_deals = [row for row in deal_rows if row.get("deal_entry") == "OUT"]
    deinit_rows = [
        row for row in trade_rows if "deinit" in " ".join(row.values()).lower()
    ]

    trade_net = round(sum(fnum(row.get("net_profit")) for row in trade_rows), 6)
    deal_out_net = round(sum(fnum(row.get("net_profit")) for row in out_deals), 6)
    unique_net = round(sum(fnum(row.get("net_profit")) for row in unique_rows), 6)
    initial_balance = fnum(unique_rows[0].get("balance_before")) if unique_rows else 0.0
    unique_final_balance = fnum(unique_rows[-1].get("balance_after")) if unique_rows else 0.0
    computed_final_balance = round(initial_balance + trade_net, 6)
    tester = parse_tester_log()
    terminal = parse_terminal_log()
    signal_export_rows = count_csv_data_rows(SIGNALS_EXPORT)

    summary = {
        "trade_ledger_stage_rows": len(trade_rows),
        "trade_ledger_unique_signals": len(stage_group_rows),
        "deal_history_rows": len(deal_rows),
        "deal_history_in_rows": len(in_deals),
        "deal_history_out_rows": len(out_deals),
        "unique_signal_rows": len(unique_rows),
        "signals_export_rows": signal_export_rows,
        "trade_ledger_net_profit": trade_net,
        "deal_history_out_net_profit": deal_out_net,
        "unique_signals_net_profit": unique_net,
        "initial_balance": initial_balance,
        "computed_final_balance": computed_final_balance,
        "unique_final_balance": unique_final_balance,
        "tester_final_balance": tester["tester_final_balance"],
        "deinit_rows": len(deinit_rows),
        "stage_group_anomaly_count": len(stage_group_anomalies),
        "position_closure_anomaly_count": len(position_anomalies),
        "ticket_profit_mismatch_count": len(ticket_mismatches),
        "unique_signal_mismatch_count": len(unique_mismatches),
        "tester_final_balance_line_count": tester["tester_final_balance_line_count"],
        "tester_csv_export_closed": tester["tester_csv_export_closed"],
        **terminal,
    }

    checks: List[Dict[str, object]] = []
    add_check(checks, "stage_rows_equal_unique_signals_times_3", len(trade_rows), len(stage_group_rows) * 3, 0)
    add_check(checks, "stage_group_anomaly_count_zero", len(stage_group_anomalies), 0, 0)
    add_check(checks, "deal_out_rows_equal_trade_stage_rows", len(out_deals), len(trade_rows), 0)
    add_check(checks, "deal_in_rows_equal_trade_stage_rows", len(in_deals), len(trade_rows), 0)
    add_check(checks, "deal_history_rows_equal_in_plus_out", len(deal_rows), len(in_deals) + len(out_deals), 0)
    add_check(checks, "position_closure_anomaly_count_zero", len(position_anomalies), 0, 0)
    add_check(checks, "ticket_profit_mismatch_count_zero", len(ticket_mismatches), 0, 0)
    add_check(checks, "unique_signal_mismatch_count_zero", len(unique_mismatches), 0, 0)
    add_check(checks, "trade_net_equals_deal_out_net", trade_net, deal_out_net, 1e-6)
    add_check(checks, "trade_net_equals_unique_net", trade_net, unique_net, 1e-6)
    add_check(checks, "computed_final_equals_unique_final", computed_final_balance, unique_final_balance, 1e-6)
    add_check(checks, "tester_final_equals_unique_final", tester["tester_final_balance"], unique_final_balance, 1e-2)
    add_check(checks, "deinit_rows_zero", len(deinit_rows), 0, 0)
    add_check(checks, "terminal_test_successfully_finished", terminal["terminal_test_successfully_finished"], True, 0)
    add_check(checks, "terminal_exit_code_0", terminal["terminal_exit_code_0"], True, 0)
    add_check(checks, "terminal_stopped_0", terminal["terminal_stopped_0"], True, 0)
    add_check(checks, "terminal_shutdown_0", terminal["terminal_shutdown_0"], True, 0)
    add_check(checks, "tester_csv_export_closed", tester["tester_csv_export_closed"], True, 0)
    add_check(
        checks,
        "tester_final_balance_line_count_nonzero",
        tester["tester_final_balance_line_count"] >= 1,
        True,
        0,
        "terminal archive may contain multiple tester sessions; the parsed last final balance is checked separately",
    )
    add_check(checks, "signals_export_nonempty", signal_export_rows > 0, True, 0)

    failed_checks = [row for row in checks if not truthy(row.get("pass"))]
    passed = not failed_checks
    decision = {
        "decision_date": date.today().isoformat(),
        "check_id": "mt5_full_stage_state_ledger_closure_review",
        "status": "pass" if passed else "fail",
        "pass": passed,
        "failed_check_count": len(failed_checks),
        "stage_group_anomaly_count": len(stage_group_anomalies),
        "position_closure_anomaly_count": len(position_anomalies),
        "ticket_profit_mismatch_count": len(ticket_mismatches),
        "unique_signal_mismatch_count": len(unique_mismatches),
        "reason": "mt5_deal_history_trade_ledger_unique_signals_and_tester_final_balance_close"
        if passed
        else "mt5_ledger_closure_check_failed",
        "next_check": "three_version_unified_report_refresh" if passed else "fix_mt5_ledger_closure_inputs",
        "no_ea_or_python_logic_changes_in_this_step": True,
    }

    write_csv(
        OUT_DIR / "mt5_ledger_closure_summary.csv",
        [summary],
        list(summary.keys()),
    )
    write_csv(
        OUT_DIR / "mt5_ledger_closure_checks.csv",
        checks,
        ["check_id", "actual", "expected", "diff", "tolerance", "pass", "note"],
    )
    write_csv(
        OUT_DIR / "mt5_trade_stage_group_summary.csv",
        stage_group_rows,
        ["signal_anchor_time", "stage_rows", "stage_list", "net_profit", "has_deinit_text", "stage_complete"],
    )
    write_csv(
        OUT_DIR / "mt5_trade_stage_group_anomalies.csv",
        stage_group_anomalies,
        ["signal_anchor_time", "stage_rows", "stage_list", "net_profit", "has_deinit_text", "stage_complete"],
    )
    write_csv(
        OUT_DIR / "mt5_deal_position_closure_anomalies.csv",
        position_anomalies,
        ["position_id", "in_rows", "out_rows", "in_volume", "out_volume", "volume_diff", "position_closed"],
    )
    write_csv(
        OUT_DIR / "mt5_ticket_profit_mismatches.csv",
        ticket_mismatches,
        ["deal_ticket", "signal_anchor_time", "stage", "ledger_net_profit", "deal_net_profit", "diff", "reason"],
    )
    write_csv(
        OUT_DIR / "mt5_unique_signal_closure_mismatches.csv",
        unique_mismatches,
        [
            "signal_anchor_time",
            "stage_group_net_profit",
            "unique_net_profit",
            "stage_rows",
            "unique_stage_rows",
            "diff",
            "reason",
        ],
    )
    write_csv(
        OUT_DIR / "mt5_ledger_closure_review_decision.csv",
        [decision],
        [
            "decision_date",
            "check_id",
            "status",
            "pass",
            "failed_check_count",
            "stage_group_anomaly_count",
            "position_closure_anomaly_count",
            "ticket_profit_mismatch_count",
            "unique_signal_mismatch_count",
            "reason",
            "next_check",
            "no_ea_or_python_logic_changes_in_this_step",
        ],
    )

    checklist_rows: List[Dict[str, object]] = []
    for row in latest_checklist_rows():
        if row.get("check_id") == "mt5_full_stage_state_ledger_closure_review":
            row["status"] = decision["status"]
            row["evidence"] = str((OUT_DIR / "mt5_ledger_closure_review_decision.csv").relative_to(ROOT))
        elif "evidence" not in row:
            row["evidence"] = ""
        checklist_rows.append(row)
    write_csv(
        OUT_DIR / "final_regression_checklist_status_after_mt5_ledger_closure.csv",
        checklist_rows,
        ["order", "check_id", "description", "status", "evidence"],
    )

    readme = "\n".join(
        [
            "# stage_state_final_regression_mt5_ledger_closure_review_20260718",
            "",
            "Final regression check 3: MT5 full stage-state ledger closure review.",
            "",
            "- `mt5_ledger_closure_review_decision.csv`: check decision.",
            "- `mt5_ledger_closure_summary.csv`: closure metric snapshot.",
            "- `mt5_ledger_closure_checks.csv`: individual pass/fail checks.",
            "- `mt5_trade_stage_group_summary.csv`: stage rows grouped by signal anchor.",
            "- `mt5_trade_stage_group_anomalies.csv`: incomplete/deinit signal groups.",
            "- `mt5_deal_position_closure_anomalies.csv`: position IN/OUT closure anomalies.",
            "- `mt5_ticket_profit_mismatches.csv`: ledger deal-ticket profit mismatches.",
            "- `mt5_unique_signal_closure_mismatches.csv`: stage group versus unique signal mismatches.",
            "- `final_regression_checklist_status_after_mt5_ledger_closure.csv`: checklist progress after this check.",
            "- `mt5_ledger_closure_review.md`: human-readable review.",
            "",
        ]
    )
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8-sig")
    write_audit_md(decision, summary, checks)

    print(f"wrote {OUT_DIR}")
    print(f"status={decision['status']}")
    print(f"failed_check_count={len(failed_checks)}")
    print(f"trade_ledger_net_profit={trade_net}")
    print(f"tester_final_balance={tester['tester_final_balance']}")


if __name__ == "__main__":
    main()
