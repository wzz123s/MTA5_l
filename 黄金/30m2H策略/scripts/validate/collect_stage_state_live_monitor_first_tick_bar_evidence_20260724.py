from __future__ import annotations


import csv
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_live_monitor_first_tick_bar_evidence_20260724"

TERMINAL_PATH = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")
SYMBOL = "XAUUSDm"
EA_NAME = "30m2H_Strategy_EA"
POST_LOAD_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_post_manual_ea_load_evidence_20260724"
    / "post_manual_ea_load_decision.json"
)
EXPORT_NAMES = [
    "30m2H_strategy_signals_export.csv",
    "30m2H_strategy_trade_ledger.csv",
    "30m2H_strategy_stage_price_diag.csv",
    "30m2H_strategy_m15_entry_diag.csv",
]


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


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
        ("expert_loaded_successfully", "loaded successfully"),
        ("ea_init_banner", "30m x 2H EA v3.26"),
        ("mode_live_trading", "Mode:     LIVE TRADING"),
        ("csv_export", "CSV export:"),
        ("trade_ledger_export", "Trade ledger export:"),
        ("new_m30_bar", "--- New M30 bar:"),
        ("new_h2_bar", "--- New H2 bar:"),
        ("status_line", "[STATUS]"),
        ("csv_row_written", "[CSV] row #"),
        ("live_risk_block", "[LIVE_RISK_BLOCK]"),
        ("trade_send", "OrderSend"),
        ("trade_result", "TRADE_RETCODE"),
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
                            "snippet": redact(line.strip())[:500],
                        }
                    )
    return rows


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
                "note": "zero_length_can_be_open_file_before_flush" if exists and path.stat().st_size == 0 else "",
            }
        )
    return rows


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
    post_load = read_json(POST_LOAD_DECISION_JSON)

    initialized = mt5.initialize(path=str(TERMINAL_PATH))
    if not initialized:
        decision = {
            "decision_time": collected_at,
            "check_id": "stage_state_live_monitor_first_tick_bar_evidence",
            "status": "mt5_initialize_failed",
            "mt5_last_error": str(mt5.last_error()),
            "ready_to_live_trade": False,
        }
        write_json(OUT_DIR / "live_monitor_first_tick_bar_decision.json", decision)
        return 1

    try:
        terminal = mt5.terminal_info()
        terminal_dict = terminal._asdict() if terminal else {}
        account = mt5.account_info()
        selected = mt5.symbol_select(SYMBOL, True)
        tick = mt5.symbol_info_tick(SYMBOL)
        positions = mt5.positions_get(symbol=SYMBOL)
        orders = mt5.orders_get(symbol=SYMBOL)
        day_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(day_start, datetime.now() + timedelta(minutes=1))
        data_path = Path(terminal_dict.get("data_path", ""))
        login = str(getattr(account, "login", "") if account else "")
        account_alias = f"MT5_ACCOUNT_***{login[-3:]}" if len(login) >= 3 else "MT5_ACCOUNT_REDACTED"

        log_rows = scan_today_logs(data_path)
        hit_types = {str(row["hit_type"]) for row in log_rows}
        exports = export_file_rows(data_path)
        zero_len_exports = [row for row in exports if row["exists"] and row["length"] == 0]
        live_risk_block_count = sum(1 for row in log_rows if row["hit_type"] == "live_risk_block")
        trade_log_count = sum(1 for row in log_rows if row["hit_type"] in {"trade_send", "trade_result"})

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
            "positions_count": len(positions) if positions is not None else "",
            "orders_count": len(orders) if orders is not None else "",
            "deal_history_count_today": len(deals) if deals is not None else "",
            "orders_placed_by_collector": False,
            "runner_executed_by_collector": False,
        }

        first_bar_seen = "new_m30_bar" in hit_types
        status_seen = "status_line" in hit_types
        csv_row_seen = "csv_row_written" in hit_types
        live_mode_seen = "mode_live_trading" in hit_types
        ea_loaded_seen = "expert_loaded_successfully" in hit_types or "ea_init_banner" in hit_types
        exports_log_seen = "csv_export" in hit_types and "trade_ledger_export" in hit_types
        terminal_ok = terminal_dict.get("connected") is True and terminal_dict.get("trade_allowed") is True
        exposure_ok = positions is not None and orders is not None
        no_unexpected_trade_activity = (len(positions) if positions is not None else 0) == 0 and (
            len(orders) if orders is not None else 0
        ) == 0

        checks = [
            check_row("post_load_ready", post_load.get("ready_to_live_trade") is True, post_load.get("status"), "post_manual_ea_load_evidence_ready_to_monitor_live"),
            check_row("terminal_connected_and_autotrading", terminal_ok, f"{terminal_dict.get('connected')} / {terminal_dict.get('trade_allowed')}", "True / True"),
            check_row("ea_loaded_evidence_seen", ea_loaded_seen, sorted(hit_types), "EA loaded/init log"),
            check_row("live_mode_seen", live_mode_seen, sorted(hit_types), "Mode: LIVE TRADING"),
            check_row("first_m30_bar_seen", first_bar_seen, sorted(hit_types), "New M30 bar"),
            check_row("status_line_seen", status_seen, sorted(hit_types), "[STATUS]"),
            check_row("csv_row_seen", csv_row_seen, sorted(hit_types), "[CSV] row #"),
            check_row("exports_log_seen", exports_log_seen, sorted(hit_types), "CSV export and trade ledger export"),
            check_row("exposure_snapshot_collected", exposure_ok, f"{terminal_row['positions_count']} / {terminal_row['orders_count']}", "counts collected"),
            check_row("no_unexpected_open_exposure", no_unexpected_trade_activity, f"{terminal_row['positions_count']} / {terminal_row['orders_count']}", "0 / 0"),
            check_row("live_risk_block_absent", live_risk_block_count == 0, live_risk_block_count, 0),
            check_row("orders_placed_by_collector", True, False, False),
            check_row("runner_executed_by_collector", True, False, False),
            check_row(
                "export_files_may_be_unflushed",
                len(zero_len_exports) == 0,
                len(zero_len_exports),
                0,
                "warning",
                "EA logs show export rows; zero-length files can occur while handles remain open before flush/deinit.",
            ),
        ]
        blocker_failures = [row for row in checks if row["severity"] == "blocker" and not row["pass"]]
        warnings = [row for row in checks if row["severity"] == "warning" and not row["pass"]]
        ready_to_monitor_live = not blocker_failures

        decision = {
            "decision_time": collected_at,
            "check_id": "stage_state_live_monitor_first_tick_bar_evidence",
            "status": (
                "live_monitor_first_tick_bar_evidence_passed"
                if ready_to_monitor_live
                else "live_monitor_first_tick_bar_evidence_blocked"
            ),
            "terminal_connected": terminal_dict.get("connected"),
            "terminal_trade_allowed": terminal_dict.get("trade_allowed"),
            "account_alias": account_alias,
            "server": terminal_row["server"],
            "symbol": SYMBOL,
            "positions_count": terminal_row["positions_count"],
            "orders_count": terminal_row["orders_count"],
            "deal_history_count_today": terminal_row["deal_history_count_today"],
            "ea_loaded_evidence_seen": ea_loaded_seen,
            "live_mode_seen": live_mode_seen,
            "first_m30_bar_seen": first_bar_seen,
            "status_line_seen": status_seen,
            "csv_row_seen": csv_row_seen,
            "exports_log_seen": exports_log_seen,
            "live_risk_block_count": live_risk_block_count,
            "trade_log_count": trade_log_count,
            "zero_length_export_file_count": len(zero_len_exports),
            "orders_placed_by_collector": False,
            "runner_executed_by_collector": False,
            "ready_to_monitor_live": ready_to_monitor_live,
            "ready_to_live_trade": post_load.get("ready_to_live_trade") is True,
            "blocker_failure_count": len(blocker_failures),
            "warning_count": len(warnings),
            "recommended_next_action": "continue_live_monitoring_until_first_signal_or_trade_then_reconcile_ledger_and_deals",
        }

        write_csv(OUT_DIR / "live_monitor_first_tick_bar_terminal_snapshot.csv", [terminal_row], list(terminal_row.keys()))
        write_csv(
            OUT_DIR / "live_monitor_first_tick_bar_log_hits.csv",
            log_rows,
            ["log_file", "log_mtime", "line_no", "hit_type", "snippet"],
        )
        write_csv(
            OUT_DIR / "live_monitor_first_tick_bar_export_files.csv",
            exports,
            ["file_name", "path", "exists", "length", "last_write_time", "note"],
        )
        write_csv(OUT_DIR / "live_monitor_first_tick_bar_checks.csv", checks, list(checks[0].keys()))
        write_csv(OUT_DIR / "live_monitor_first_tick_bar_decision.csv", [decision], list(decision.keys()))
        write_json(OUT_DIR / "live_monitor_first_tick_bar_decision.json", decision)

        report = f"""# Live Monitor First Tick / First Bar Evidence

Generated: {collected_at}

## Decision

- Status: `{decision["status"]}`
- Terminal connected: `{decision["terminal_connected"]}`
- AutoTrading allowed: `{decision["terminal_trade_allowed"]}`
- Account alias/server: `{account_alias} / {terminal_row["server"]}`
- Symbol: `{SYMBOL}`
- Positions / orders: `{terminal_row["positions_count"]} / {terminal_row["orders_count"]}`
- Deal history count today: `{terminal_row["deal_history_count_today"]}`
- EA loaded evidence seen: `{ea_loaded_seen}`
- LIVE TRADING mode seen: `{live_mode_seen}`
- First M30 bar seen: `{first_bar_seen}`
- Status line seen: `{status_seen}`
- CSV row seen: `{csv_row_seen}`
- LIVE_RISK_BLOCK count: `{live_risk_block_count}`
- Ready to monitor live: `{ready_to_monitor_live}`
- Ready to live trade: `{decision["ready_to_live_trade"]}`

## Note

EA logs show export initialization and row writes. Current export CSV file sizes may remain zero while the EA keeps file handles open before flush/deinitialization.
"""
        (OUT_DIR / "live_monitor_first_tick_bar_evidence.md").write_text(report, encoding="utf-8-sig")
        return 0 if not blocker_failures else 2
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
