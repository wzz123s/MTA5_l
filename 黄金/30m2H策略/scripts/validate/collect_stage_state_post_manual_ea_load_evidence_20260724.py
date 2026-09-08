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
OUT_DIR = VALIDATION_DIR / "stage_state_post_manual_ea_load_evidence_20260724"

TERMINAL_PATH = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")
SYMBOL = "XAUUSDm"
EA_NAME = "30m2H_Strategy_EA"
EA_EX5 = ROOT / "auto_trade" / "30m2H_Strategy_EA.ex5"
WORKSPACE_SET = (
    VALIDATION_DIR
    / "stage_state_exact_mt5_ea_live_loading_package_20260723"
    / "30m2H_Strategy_EA.live_loading_owner_local_20260723.set"
)
POST_STOP_REMOVAL_DECISION_JSON = (
    VALIDATION_DIR
    / "stage_state_post_stop_flag_removal_manual_loading_execution_20260724"
    / "post_stop_flag_removal_decision.json"
)


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


def recent_log_files(data_path: Path) -> List[Path]:
    candidates: List[Path] = []
    for folder in [data_path / "MQL5" / "Logs", data_path / "Logs"]:
        if folder.exists():
            candidates.extend(folder.glob("*.log"))
    cutoff = datetime.now() - timedelta(days=3)
    return sorted(
        [p for p in candidates if datetime.fromtimestamp(p.stat().st_mtime) >= cutoff],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:12]


def scan_logs(data_path: Path) -> List[Dict[str, object]]:
    patterns = [
        ("ea_init_banner", "30m x 2H EA v3.26"),
        ("mode_live_trading", "Mode:     LIVE TRADING"),
        ("trade_ledger_export", "Trade ledger export:"),
        ("csv_export", "CSV export:"),
        ("live_risk_block", "[LIVE_RISK_BLOCK]"),
        ("ea_deinitialized", "EA Deinitialized"),
        ("expert_loaded_name", EA_NAME),
    ]
    rows: List[Dict[str, object]] = []
    today_log_stem = datetime.now().strftime("%Y%m%d")
    for path in recent_log_files(data_path):
        text = read_text_any_encoding(path)
        for line_no, line in enumerate(text.splitlines(), start=1):
            for hit_type, pattern in patterns:
                if hit_type == "expert_loaded_name":
                    matched = f"{EA_NAME} (" in line
                else:
                    matched = pattern in line
                if matched:
                    rows.append(
                        {
                            "log_file": str(path),
                            "log_stem": path.stem,
                            "is_today_log": path.stem == today_log_stem,
                            "log_mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds"),
                            "line_no": line_no,
                            "hit_type": hit_type,
                            "snippet": redact(line.strip())[:500],
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
    post_stop = read_json(POST_STOP_REMOVAL_DECISION_JSON)

    initialized = mt5.initialize(path=str(TERMINAL_PATH))
    if not initialized:
        decision = {
            "decision_time": collected_at,
            "check_id": "stage_state_post_manual_ea_load_evidence",
            "status": "mt5_initialize_failed",
            "mt5_last_error": str(mt5.last_error()),
            "ready_to_live_trade": False,
        }
        write_json(OUT_DIR / "post_manual_ea_load_decision.json", decision)
        return 1

    try:
        terminal = mt5.terminal_info()
        terminal_dict = terminal._asdict() if terminal else {}
        account = mt5.account_info()
        selected = mt5.symbol_select(SYMBOL, True)
        positions = mt5.positions_get(symbol=SYMBOL)
        orders = mt5.orders_get(symbol=SYMBOL)
        data_path = Path(terminal_dict.get("data_path", ""))

        login = str(getattr(account, "login", "") if account else "")
        account_alias = f"MT5_ACCOUNT_***{login[-3:]}" if len(login) >= 3 else "MT5_ACCOUNT_REDACTED"
        terminal_row = {
            "snapshot_time": collected_at,
            "terminal_connected": terminal_dict.get("connected", ""),
            "terminal_trade_allowed": terminal_dict.get("trade_allowed", ""),
            "terminal_tradeapi_disabled": terminal_dict.get("tradeapi_disabled", ""),
            "data_path": str(data_path),
            "account_alias": account_alias,
            "server": getattr(account, "server", "") if account else "",
            "symbol_selected": selected,
            "positions_count": len(positions) if positions is not None else "",
            "orders_count": len(orders) if orders is not None else "",
            "orders_placed_by_collector": False,
            "runner_executed_by_collector": False,
        }

        expert_path = data_path / "MQL5" / "Experts" / "Advisors" / "30m2H_Strategy_EA.ex5"
        preset_path = data_path / "MQL5" / "Presets" / "30m2H_Strategy_EA.live_loading_owner_local_20260723.set"
        tester_set_path = data_path / "MQL5" / "Profiles" / "Tester" / "30m2H_Strategy_EA.live_loading_owner_local_20260723.set"
        file_rows = [
            {"role": "terminal_expert_ex5", "path": str(expert_path), "exists": expert_path.exists()},
            {"role": "workspace_ex5", "path": str(EA_EX5), "exists": EA_EX5.exists()},
            {"role": "workspace_set", "path": str(WORKSPACE_SET), "exists": WORKSPACE_SET.exists()},
            {"role": "terminal_preset_set", "path": str(preset_path), "exists": preset_path.exists()},
            {"role": "terminal_tester_set", "path": str(tester_set_path), "exists": tester_set_path.exists()},
        ]

        log_hits = scan_logs(data_path) if data_path.exists() else []
        current_log_hits = [row for row in log_hits if row.get("is_today_log") is True]
        hit_types = {str(row["hit_type"]) for row in current_log_hits}
        ea_loaded_evidence_seen = "ea_init_banner" in hit_types or "expert_loaded_name" in hit_types
        live_mode_evidence_seen = "mode_live_trading" in hit_types
        export_evidence_seen = "trade_ledger_export" in hit_types or "csv_export" in hit_types
        trade_allowed = terminal_dict.get("trade_allowed") is True
        no_exposure_or_baseline_collected = positions is not None and orders is not None
        stop_flags_removed = post_stop.get("stop_flags_removed") is True

        ready_to_live_trade = (
            ea_loaded_evidence_seen
            and live_mode_evidence_seen
            and trade_allowed
            and no_exposure_or_baseline_collected
            and stop_flags_removed
        )
        checks = [
            check_row("stop_flags_removed_before_load", stop_flags_removed, stop_flags_removed, True),
            check_row("expert_ex5_present_in_terminal", expert_path.exists(), expert_path.exists(), True),
            check_row("approved_set_available_in_terminal", preset_path.exists() or tester_set_path.exists(), True, True),
            check_row("terminal_connected", terminal_dict.get("connected") is True, terminal_dict.get("connected"), True),
            check_row("ea_loaded_evidence_seen", ea_loaded_evidence_seen, sorted(hit_types), "ea init/name log hit", "manual_pending"),
            check_row("live_mode_evidence_seen", live_mode_evidence_seen, sorted(hit_types), "Mode: LIVE TRADING log hit", "manual_pending"),
            check_row("terminal_trade_allowed_true", trade_allowed, terminal_dict.get("trade_allowed"), True, "manual_pending"),
            check_row("positions_orders_snapshot_collected", no_exposure_or_baseline_collected, f"{terminal_row['positions_count']} / {terminal_row['orders_count']}", "counts collected"),
            check_row("orders_placed_by_collector", True, False, False),
            check_row("runner_executed_by_collector", True, False, False),
        ]
        blocker_failures = [row for row in checks if row["severity"] == "blocker" and not row["pass"]]
        manual_pending = [row for row in checks if row["severity"] == "manual_pending" and not row["pass"]]
        decision = {
            "decision_time": collected_at,
            "check_id": "stage_state_post_manual_ea_load_evidence",
            "status": (
                "post_manual_ea_load_evidence_ready_to_monitor_live"
                if ready_to_live_trade and not blocker_failures
                else "post_manual_ea_load_evidence_manual_load_or_autotrading_pending"
            ),
            "terminal_connected": terminal_dict.get("connected"),
            "terminal_trade_allowed": terminal_dict.get("trade_allowed"),
            "account_alias": account_alias,
            "server": terminal_row["server"],
            "symbol": SYMBOL,
            "positions_count": terminal_row["positions_count"],
            "orders_count": terminal_row["orders_count"],
            "ea_loaded_evidence_seen": ea_loaded_evidence_seen,
            "live_mode_evidence_seen": live_mode_evidence_seen,
            "export_evidence_seen": export_evidence_seen,
            "log_hit_count": len(log_hits),
            "current_log_hit_count": len(current_log_hits),
            "orders_placed_by_collector": False,
            "runner_executed_by_collector": False,
            "ready_to_live_trade": ready_to_live_trade,
            "blocker_failure_count": len(blocker_failures),
            "manual_pending_count": len(manual_pending),
            "recommended_next_action": (
                "monitor_live_ea_and_collect_first_tick_or_first_bar_evidence"
                if ready_to_live_trade
                else "load_ea_in_mt5_gui_enable_autotrading_then_rerun_this_collector"
            ),
        }

        write_csv(OUT_DIR / "post_manual_ea_load_terminal_snapshot.csv", [terminal_row], list(terminal_row.keys()))
        write_csv(OUT_DIR / "post_manual_ea_load_files.csv", file_rows, ["role", "path", "exists"])
        write_csv(
            OUT_DIR / "post_manual_ea_load_log_hits.csv",
            log_hits,
            ["log_file", "log_stem", "is_today_log", "log_mtime", "line_no", "hit_type", "snippet"],
        )
        write_csv(OUT_DIR / "post_manual_ea_load_checks.csv", checks, list(checks[0].keys()))
        write_csv(OUT_DIR / "post_manual_ea_load_decision.csv", [decision], list(decision.keys()))
        write_json(OUT_DIR / "post_manual_ea_load_decision.json", decision)

        report = f"""# Post Manual EA Load Evidence

Generated: {collected_at}

## Decision

- Status: `{decision["status"]}`
- Terminal connected: `{decision["terminal_connected"]}`
- Terminal AutoTrading allowed: `{decision["terminal_trade_allowed"]}`
- Account alias/server: `{account_alias} / {terminal_row["server"]}`
- Symbol: `{SYMBOL}`
- Positions / orders: `{terminal_row["positions_count"]} / {terminal_row["orders_count"]}`
- EA loaded evidence seen: `{ea_loaded_evidence_seen}`
- LIVE TRADING mode evidence seen: `{live_mode_evidence_seen}`
- Export evidence seen: `{export_evidence_seen}`
- Ready to live trade: `{ready_to_live_trade}`

## Boundary

This collector is read-only. It does not place orders, start the Python runner, remove files, or load the EA.
"""
        (OUT_DIR / "post_manual_ea_load_evidence.md").write_text(report, encoding="utf-8-sig")
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
