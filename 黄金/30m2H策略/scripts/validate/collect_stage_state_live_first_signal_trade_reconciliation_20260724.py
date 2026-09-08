from __future__ import annotations


import csv
import json
import re
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_live_first_signal_trade_reconciliation_20260724"

TERMINAL_PATH = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")
SYMBOL = "XAUUSDm"
EA_NAME = "30m2H_Strategy_EA"
PRIOR_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_live_monitor_first_tick_bar_evidence_20260724"
    / "live_monitor_first_tick_bar_decision.json"
)

SIGNALS_EXPORT_NAME = "30m2H_strategy_signals_export.csv"
TRADE_LEDGER_NAME = "30m2H_strategy_trade_ledger.csv"
STAGE_PRICE_DIAG_NAME = "30m2H_strategy_stage_price_diag.csv"
M15_ENTRY_DIAG_NAME = "30m2H_strategy_m15_entry_diag.csv"
EXPORT_NAMES = [
    SIGNALS_EXPORT_NAME,
    TRADE_LEDGER_NAME,
    STAGE_PRICE_DIAG_NAME,
    M15_ENTRY_DIAG_NAME,
]


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists() or path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: (v or "") for k, v in row.items()} for row in csv.DictReader(f)]


def read_text_any_encoding(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ["utf-8-sig", "utf-16", "utf-16-le", "gb18030"]:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8-sig", errors="replace").replace("\x00", "")


def redact(text: str) -> str:
    return re.sub(r"\b\d{6,}\b", "REDACTED_NUM", text)


def today_log_files(data_path: Path) -> List[Path]:
    stem = datetime.now().strftime("%Y%m%d")
    files: List[Path] = []
    for folder in [data_path / "MQL5" / "Logs", data_path / "Logs"]:
        path = folder / f"{stem}.log"
        if path.exists():
            files.append(path)
    return files


def scan_today_logs(data_path: Path) -> List[Dict[str, object]]:
    patterns = [
        ("new_m30_bar", "--- New M30 bar:"),
        ("status_line", "[STATUS]"),
        ("csv_row_written", "[CSV] row #"),
        ("skip_decision", "decision=SKIP"),
        ("buy_text", "BUY"),
        ("sell_text", "SELL"),
        ("live_risk_block", "[LIVE_RISK_BLOCK]"),
        ("trade_send", "OrderSend"),
        ("trade_result", "TRADE_RETCODE"),
        ("broker_reject", "reject"),
        ("failed", "failed"),
        ("error", "error"),
    ]
    rows: List[Dict[str, object]] = []
    for path in today_log_files(data_path):
        text = read_text_any_encoding(path)
        for line_no, line in enumerate(text.splitlines(), start=1):
            if EA_NAME not in line and "Experts" not in line:
                continue
            for hit_type, pattern in patterns:
                if pattern in line:
                    rows.append(
                        {
                            "log_file": str(path),
                            "log_mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                            "line_no": line_no,
                            "hit_type": hit_type,
                            "snippet": redact(line.strip())[:700],
                        }
                    )
    return rows


def safe_float(value: object) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


def is_accepted_signal(row: Dict[str, str]) -> bool:
    decision = row.get("decision", "").strip().upper()
    skip_reason = row.get("skip_reason", "").strip()
    if not decision or decision in {"SKIP", "NONE", "NO_SIGNAL"}:
        return False
    if skip_reason:
        return False
    return True


def summarize_signal_export(rows: List[Dict[str, str]]) -> Dict[str, object]:
    decisions = Counter((row.get("decision", "") or "EMPTY") for row in rows)
    skip_reasons = Counter((row.get("skip_reason", "") or "EMPTY") for row in rows)
    accepted = [row for row in rows if is_accepted_signal(row)]
    latest = rows[-1] if rows else {}
    first_accepted = accepted[0] if accepted else {}
    return {
        "row_count": len(rows),
        "accepted_signal_count": len(accepted),
        "skip_count": decisions.get("SKIP", 0),
        "decision_counts": json.dumps(dict(sorted(decisions.items())), ensure_ascii=False),
        "skip_reason_counts": json.dumps(dict(sorted(skip_reasons.items())), ensure_ascii=False),
        "latest_bar_time": latest.get("bar_time", ""),
        "latest_decision": latest.get("decision", ""),
        "latest_skip_reason": latest.get("skip_reason", ""),
        "first_accepted_bar_time": first_accepted.get("bar_time", ""),
        "first_accepted_decision": first_accepted.get("decision", ""),
        "first_accepted_stop_pts": first_accepted.get("stop_pts", ""),
    }


def summarize_trade_ledger(rows: List[Dict[str, str]]) -> Dict[str, object]:
    stages = Counter((row.get("stage", "") or "EMPTY") for row in rows)
    exit_reasons = Counter((row.get("local_exit_reason", "") or "EMPTY") for row in rows)
    open_like = [row for row in rows if row.get("open_time") and not row.get("exit_time")]
    latest = rows[-1] if rows else {}
    return {
        "row_count": len(rows),
        "open_like_row_count": len(open_like),
        "stage_counts": json.dumps(dict(sorted(stages.items())), ensure_ascii=False),
        "exit_reason_counts": json.dumps(dict(sorted(exit_reasons.items())), ensure_ascii=False),
        "net_profit_sum": round(sum(safe_float(row.get("net_profit", "")) for row in rows), 2),
        "latest_anchor_time": latest.get("signal_anchor_time", ""),
        "latest_trigger_tag": latest.get("trigger_tag", ""),
        "latest_dir": latest.get("dir", ""),
        "latest_ticket": latest.get("ticket", ""),
        "latest_position_id": latest.get("position_id", ""),
        "latest_open_time": latest.get("open_time", ""),
        "latest_exit_time": latest.get("exit_time", ""),
        "latest_net_profit": latest.get("net_profit", ""),
    }


def export_file_rows(data_path: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    export_dir = data_path / "MQL5" / "Files"
    for name in EXPORT_NAMES:
        path = export_dir / name
        exists = path.exists()
        rows.append(
            {
                "file_name": name,
                "path": str(path),
                "exists": exists,
                "length": path.stat().st_size if exists else "",
                "last_write_time": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
                if exists
                else "",
            }
        )
    return rows


def deal_to_row(deal: object) -> Dict[str, object]:
    fields = deal._asdict()
    return {
        "ticket": fields.get("ticket", ""),
        "order": fields.get("order", ""),
        "time": datetime.fromtimestamp(fields.get("time", 0)).isoformat(timespec="seconds")
        if fields.get("time")
        else "",
        "type": fields.get("type", ""),
        "entry": fields.get("entry", ""),
        "magic": fields.get("magic", ""),
        "position_id": fields.get("position_id", ""),
        "volume": fields.get("volume", ""),
        "price": fields.get("price", ""),
        "commission": fields.get("commission", ""),
        "swap": fields.get("swap", ""),
        "profit": fields.get("profit", ""),
        "fee": fields.get("fee", ""),
        "symbol": fields.get("symbol", ""),
        "comment": fields.get("comment", ""),
    }


def order_to_row(order: object) -> Dict[str, object]:
    fields = order._asdict()
    return {
        "ticket": fields.get("ticket", ""),
        "time_setup": datetime.fromtimestamp(fields.get("time_setup", 0)).isoformat(timespec="seconds")
        if fields.get("time_setup")
        else "",
        "type": fields.get("type", ""),
        "state": fields.get("state", ""),
        "magic": fields.get("magic", ""),
        "position_id": fields.get("position_id", ""),
        "volume_initial": fields.get("volume_initial", ""),
        "volume_current": fields.get("volume_current", ""),
        "price_open": fields.get("price_open", ""),
        "sl": fields.get("sl", ""),
        "tp": fields.get("tp", ""),
        "symbol": fields.get("symbol", ""),
        "comment": fields.get("comment", ""),
    }


def position_to_row(position: object) -> Dict[str, object]:
    fields = position._asdict()
    return {
        "ticket": fields.get("ticket", ""),
        "time": datetime.fromtimestamp(fields.get("time", 0)).isoformat(timespec="seconds")
        if fields.get("time")
        else "",
        "type": fields.get("type", ""),
        "magic": fields.get("magic", ""),
        "identifier": fields.get("identifier", ""),
        "volume": fields.get("volume", ""),
        "price_open": fields.get("price_open", ""),
        "sl": fields.get("sl", ""),
        "tp": fields.get("tp", ""),
        "price_current": fields.get("price_current", ""),
        "profit": fields.get("profit", ""),
        "swap": fields.get("swap", ""),
        "symbol": fields.get("symbol", ""),
        "comment": fields.get("comment", ""),
    }


def check_row(
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


def main() -> int:
    import MetaTrader5 as mt5

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now().isoformat(timespec="seconds")
    prior = read_json(PRIOR_DECISION_JSON)

    initialized = mt5.initialize(path=str(TERMINAL_PATH))
    if not initialized:
        decision = {
            "decision_time": collected_at,
            "check_id": "stage_state_live_first_signal_trade_reconciliation",
            "status": "mt5_initialize_failed",
            "mt5_last_error": str(mt5.last_error()),
            "ready_to_continue_monitoring": False,
            "ready_to_live_trade": False,
        }
        write_json(OUT_DIR / "live_first_signal_trade_reconciliation_decision.json", decision)
        return 1

    try:
        terminal = mt5.terminal_info()
        terminal_dict = terminal._asdict() if terminal else {}
        account = mt5.account_info()
        selected = mt5.symbol_select(SYMBOL, True)
        tick = mt5.symbol_info_tick(SYMBOL)
        positions_raw = mt5.positions_get(symbol=SYMBOL)
        orders_raw = mt5.orders_get(symbol=SYMBOL)
        day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        deals_raw = mt5.history_deals_get(day_start, datetime.now() + timedelta(minutes=1))
        orders_history_raw = mt5.history_orders_get(day_start, datetime.now() + timedelta(minutes=1))
        data_path = Path(terminal_dict.get("data_path", ""))

        login = str(getattr(account, "login", "") if account else "")
        account_alias = f"MT5_ACCOUNT_***{login[-3:]}" if len(login) >= 3 else "MT5_ACCOUNT_REDACTED"
        positions = [position_to_row(row) for row in positions_raw] if positions_raw is not None else []
        orders = [order_to_row(row) for row in orders_raw] if orders_raw is not None else []
        deals = [deal_to_row(row) for row in deals_raw if getattr(row, "symbol", "") == SYMBOL] if deals_raw else []
        orders_history = (
            [order_to_row(row) for row in orders_history_raw if getattr(row, "symbol", "") == SYMBOL]
            if orders_history_raw
            else []
        )

        export_dir = data_path / "MQL5" / "Files"
        signals_path = export_dir / SIGNALS_EXPORT_NAME
        ledger_path = export_dir / TRADE_LEDGER_NAME
        stage_price_path = export_dir / STAGE_PRICE_DIAG_NAME
        m15_diag_path = export_dir / M15_ENTRY_DIAG_NAME
        signals = read_csv_rows(signals_path)
        ledger = read_csv_rows(ledger_path)
        stage_price = read_csv_rows(stage_price_path)
        m15_diag = read_csv_rows(m15_diag_path)

        signal_summary = summarize_signal_export(signals)
        ledger_summary = summarize_trade_ledger(ledger)
        log_rows = scan_today_logs(data_path)
        hit_types = Counter(str(row["hit_type"]) for row in log_rows)
        accepted_signal_count = int(signal_summary["accepted_signal_count"])
        trade_evidence_count = len(ledger) + len(deals) + len(positions) + len(orders)
        no_trade_yet = accepted_signal_count == 0 and trade_evidence_count == 0
        first_trade_seen = len(ledger) > 0 or len(deals) > 0 or len(positions) > 0 or len(orders) > 0
        stage_diag_has_open_rows = len(stage_price) > 0

        terminal_row = {
            "snapshot_time": collected_at,
            "terminal_connected": terminal_dict.get("connected", ""),
            "terminal_trade_allowed": terminal_dict.get("trade_allowed", ""),
            "account_alias": account_alias,
            "server": getattr(account, "server", "") if account else "",
            "symbol_selected": selected,
            "tick_time": datetime.fromtimestamp(getattr(tick, "time", 0)).isoformat(timespec="seconds") if tick else "",
            "bid": getattr(tick, "bid", "") if tick else "",
            "ask": getattr(tick, "ask", "") if tick else "",
            "positions_count": len(positions),
            "orders_count": len(orders),
            "deal_history_count_today": len(deals),
            "order_history_count_today": len(orders_history),
            "orders_placed_by_collector": False,
            "runner_executed_by_collector": False,
        }

        terminal_ok = terminal_dict.get("connected") is True and terminal_dict.get("trade_allowed") is True
        export_rows = export_file_rows(data_path)
        exports_present = all(row["exists"] for row in export_rows)
        exports_nonempty = all(int(row["length"] or 0) > 0 for row in export_rows)
        skip_only_consistent = no_trade_yet and signal_summary["row_count"] > 0
        open_exposure_has_evidence = len(positions) == 0 or stage_diag_has_open_rows or len(ledger) > 0
        risk_block_count = hit_types.get("live_risk_block", 0)
        trade_log_count = hit_types.get("trade_send", 0) + hit_types.get("trade_result", 0)
        broker_issue_count = hit_types.get("broker_reject", 0) + hit_types.get("failed", 0) + hit_types.get("error", 0)

        if no_trade_yet:
            status = "live_first_signal_trade_waiting_no_accepted_signal_or_trade"
            first_signal_trade_gate_closed = False
        elif first_trade_seen and len(ledger) > 0 and (len(deals) > 0 or len(positions) > 0):
            status = "live_first_trade_reconciliation_evidence_available"
            first_signal_trade_gate_closed = True
        else:
            status = "live_first_signal_trade_partial_evidence_needs_followup"
            first_signal_trade_gate_closed = False

        checks = [
            check_row(
                "prior_first_tick_bar_ready",
                prior.get("ready_to_monitor_live") is True,
                prior.get("status"),
                "live_monitor_first_tick_bar_evidence_passed",
            ),
            check_row(
                "terminal_connected_and_autotrading",
                terminal_ok,
                f"{terminal_dict.get('connected')} / {terminal_dict.get('trade_allowed')}",
                "True / True",
            ),
            check_row("export_files_present", exports_present, len([r for r in export_rows if r["exists"]]), len(EXPORT_NAMES)),
            check_row("export_files_nonempty", exports_nonempty, len([r for r in export_rows if int(r["length"] or 0) > 0]), len(EXPORT_NAMES)),
            check_row("signal_export_has_rows", signal_summary["row_count"] > 0, signal_summary["row_count"], ">0"),
            check_row(
                "skip_only_no_trade_consistent",
                skip_only_consistent or first_trade_seen,
                f"accepted={accepted_signal_count}; trade_evidence={trade_evidence_count}",
                "accepted=0 and trade_evidence=0 OR first_trade_seen",
            ),
            check_row(
                "open_exposure_has_stage_or_ledger_evidence",
                open_exposure_has_evidence,
                f"positions={len(positions)}; stage_diag_rows={len(stage_price)}; ledger_rows={len(ledger)}",
                "if positions>0 then stage_diag_rows>0 or ledger_rows>0",
            ),
            check_row("live_risk_block_absent", risk_block_count == 0, risk_block_count, 0),
            check_row("broker_issue_absent", broker_issue_count == 0, broker_issue_count, 0, "warning"),
            check_row("orders_placed_by_collector", True, False, False),
            check_row("runner_executed_by_collector", True, False, False),
        ]
        blocker_failures = [row for row in checks if row["severity"] == "blocker" and not row["pass"]]
        warnings = [row for row in checks if row["severity"] == "warning" and not row["pass"]]
        ready_to_continue_monitoring = not blocker_failures

        signal_summary_row = {
            "snapshot_time": collected_at,
            **signal_summary,
        }
        ledger_summary_row = {
            "snapshot_time": collected_at,
            **ledger_summary,
        }
        decision = {
            "decision_time": collected_at,
            "check_id": "stage_state_live_first_signal_trade_reconciliation",
            "status": status if ready_to_continue_monitoring else "live_first_signal_trade_reconciliation_blocked",
            "terminal_connected": terminal_dict.get("connected"),
            "terminal_trade_allowed": terminal_dict.get("trade_allowed"),
            "account_alias": account_alias,
            "server": terminal_row["server"],
            "symbol": SYMBOL,
            "signal_export_rows": signal_summary["row_count"],
            "accepted_signal_count": accepted_signal_count,
            "latest_signal_bar_time": signal_summary["latest_bar_time"],
            "latest_signal_decision": signal_summary["latest_decision"],
            "latest_signal_skip_reason": signal_summary["latest_skip_reason"],
            "trade_ledger_rows": len(ledger),
            "stage_price_diag_rows": len(stage_price),
            "m15_entry_diag_rows": len(m15_diag),
            "positions_count": len(positions),
            "orders_count": len(orders),
            "deal_history_count_today": len(deals),
            "order_history_count_today": len(orders_history),
            "live_risk_block_count": risk_block_count,
            "trade_log_count": trade_log_count,
            "broker_issue_count": broker_issue_count,
            "first_signal_seen": accepted_signal_count > 0,
            "first_trade_seen": first_trade_seen,
            "first_signal_trade_gate_closed": first_signal_trade_gate_closed and ready_to_continue_monitoring,
            "ready_to_continue_monitoring": ready_to_continue_monitoring,
            "ready_to_live_trade": prior.get("ready_to_live_trade") is True and terminal_ok,
            "blocker_failure_count": len(blocker_failures),
            "warning_count": len(warnings),
            "orders_placed_by_collector": False,
            "runner_executed_by_collector": False,
            "recommended_next_action": "wait_for_first_accepted_signal_or_ea_trade_then_rerun_reconciliation",
        }

        write_csv(OUT_DIR / "live_first_signal_trade_terminal_snapshot.csv", [terminal_row], list(terminal_row.keys()))
        write_csv(OUT_DIR / "live_first_signal_trade_export_files.csv", export_rows, list(export_rows[0].keys()))
        write_csv(OUT_DIR / "live_first_signal_trade_signal_summary.csv", [signal_summary_row], list(signal_summary_row.keys()))
        write_csv(OUT_DIR / "live_first_signal_trade_ledger_summary.csv", [ledger_summary_row], list(ledger_summary_row.keys()))
        write_csv(
            OUT_DIR / "live_first_signal_trade_signal_latest_rows.csv",
            signals[-10:],
            signals[0].keys() if signals else ["bar_time", "decision", "skip_reason"],
        )
        write_csv(
            OUT_DIR / "live_first_signal_trade_trade_ledger_rows.csv",
            ledger,
            ledger[0].keys()
            if ledger
            else [
                "signal_anchor_time",
                "trigger_tag",
                "signal_src",
                "dir",
                "stage",
                "magic",
                "ticket",
                "position_id",
                "open_time",
                "exit_time",
                "net_profit",
            ],
        )
        write_csv(
            OUT_DIR / "live_first_signal_trade_stage_price_diag_latest_rows.csv",
            stage_price[-10:],
            stage_price[0].keys() if stage_price else ["time", "signal_anchor_time", "stage", "ticket", "position_id"],
        )
        write_csv(
            OUT_DIR / "live_first_signal_trade_m15_entry_diag_latest_rows.csv",
            m15_diag[-10:],
            m15_diag[0].keys() if m15_diag else ["time", "current_m30_bar", "result", "detail"],
        )
        write_csv(
            OUT_DIR / "live_first_signal_trade_deal_history_today.csv",
            deals,
            [
                "ticket",
                "order",
                "time",
                "type",
                "entry",
                "magic",
                "position_id",
                "volume",
                "price",
                "commission",
                "swap",
                "profit",
                "fee",
                "symbol",
                "comment",
            ],
        )
        write_csv(
            OUT_DIR / "live_first_signal_trade_order_history_today.csv",
            orders_history,
            [
                "ticket",
                "time_setup",
                "type",
                "state",
                "magic",
                "position_id",
                "volume_initial",
                "volume_current",
                "price_open",
                "sl",
                "tp",
                "symbol",
                "comment",
            ],
        )
        write_csv(
            OUT_DIR / "live_first_signal_trade_positions_current.csv",
            positions,
            [
                "ticket",
                "time",
                "type",
                "magic",
                "identifier",
                "volume",
                "price_open",
                "sl",
                "tp",
                "price_current",
                "profit",
                "swap",
                "symbol",
                "comment",
            ],
        )
        write_csv(
            OUT_DIR / "live_first_signal_trade_orders_current.csv",
            orders,
            [
                "ticket",
                "time_setup",
                "type",
                "state",
                "magic",
                "position_id",
                "volume_initial",
                "volume_current",
                "price_open",
                "sl",
                "tp",
                "symbol",
                "comment",
            ],
        )
        write_csv(
            OUT_DIR / "live_first_signal_trade_log_hits.csv",
            log_rows,
            ["log_file", "log_mtime", "line_no", "hit_type", "snippet"],
        )
        write_csv(OUT_DIR / "live_first_signal_trade_checks.csv", checks, list(checks[0].keys()))
        write_csv(OUT_DIR / "live_first_signal_trade_reconciliation_decision.csv", [decision], list(decision.keys()))
        write_json(OUT_DIR / "live_first_signal_trade_reconciliation_decision.json", decision)

        report = f"""# Live First Signal / Trade Reconciliation Snapshot

Generated: {collected_at}

## Decision

- Status: `{decision["status"]}`
- Terminal connected / AutoTrading: `{decision["terminal_connected"]} / {decision["terminal_trade_allowed"]}`
- Account alias/server: `{account_alias} / {terminal_row["server"]}`
- Symbol: `{SYMBOL}`
- Signal rows / accepted signals: `{decision["signal_export_rows"]} / {decision["accepted_signal_count"]}`
- Latest signal: `{decision["latest_signal_bar_time"]}` `{decision["latest_signal_decision"]}` `{decision["latest_signal_skip_reason"]}`
- Trade ledger rows: `{decision["trade_ledger_rows"]}`
- Positions / orders: `{decision["positions_count"]} / {decision["orders_count"]}`
- Deal history count today: `{decision["deal_history_count_today"]}`
- First signal seen: `{decision["first_signal_seen"]}`
- First trade seen: `{decision["first_trade_seen"]}`
- LIVE_RISK_BLOCK count: `{decision["live_risk_block_count"]}`
- Ready to continue monitoring: `{decision["ready_to_continue_monitoring"]}`
- Ready to live trade: `{decision["ready_to_live_trade"]}`

## Interpretation

The current export state is consistent with a live EA waiting for the first accepted signal. No Python runner or collector order activity was performed by this snapshot.
"""
        (OUT_DIR / "live_first_signal_trade_reconciliation.md").write_text(report, encoding="utf-8-sig")
        return 0 if not blocker_failures else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
