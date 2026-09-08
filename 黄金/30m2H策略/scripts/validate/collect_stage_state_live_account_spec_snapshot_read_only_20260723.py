from __future__ import annotations


import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_live_account_spec_snapshot_read_only_20260723"

TERMINAL_PATH = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")
SYMBOL = "XAUUSDm"
BALANCE_CAP = 2000.0
REQUESTED_LEVERAGE = 2000
SAMPLE_LOTS = [0.01, 0.03, 0.05, 0.09, 0.10]


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def account_alias(login: object) -> str:
    text = str(login or "")
    return f"MT5_ACCOUNT_***{text[-3:]}" if len(text) >= 3 else "MT5_ACCOUNT_REDACTED"


def terminal_process_snapshot() -> List[Dict[str, object]]:
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Get-Process terminal64 -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,Path,StartTime | ConvertTo-Json -Compress",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    raw = result.stdout.strip()
    if not raw:
        return []
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        parsed = [parsed]
    return [
        {
            "id": row.get("Id", ""),
            "process_name": row.get("ProcessName", ""),
            "path": row.get("Path", ""),
            "start_time": row.get("StartTime", ""),
        }
        for row in parsed
    ]


def as_dict(obj: object, fields: List[str]) -> Dict[str, object]:
    return {field: getattr(obj, field, "") for field in fields}


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


def main() -> int:
    import MetaTrader5 as mt5

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now().isoformat(timespec="seconds")
    processes_before = terminal_process_snapshot()

    initialized = mt5.initialize(path=str(TERMINAL_PATH))
    if not initialized:
        decision = {
            "decision_time": collected_at,
            "check_id": "stage_state_live_account_spec_snapshot_read_only",
            "status": "mt5_initialize_failed",
            "mt5_last_error": str(mt5.last_error()),
            "orders_placed": False,
            "runner_executed": False,
            "ready_to_live_trade": False,
        }
        write_json(OUT_DIR / "live_account_spec_snapshot_decision.json", decision)
        return 1

    try:
        account = mt5.account_info()
        selected = mt5.symbol_select(SYMBOL, True)
        symbol = mt5.symbol_info(SYMBOL)
        tick = mt5.symbol_info_tick(SYMBOL)
        terminal = mt5.terminal_info()
        positions = mt5.positions_get(symbol=SYMBOL)
        orders = mt5.orders_get(symbol=SYMBOL)

        account_fields = [
            "server",
            "trade_mode",
            "leverage",
            "currency",
            "balance",
            "equity",
            "margin",
            "margin_free",
            "margin_level",
            "profit",
        ]
        account_row = as_dict(account, account_fields) if account else {}
        account_row["login_alias"] = account_alias(getattr(account, "login", ""))
        account_row["login"] = "REDACTED"
        account_row["snapshot_type"] = "read_only_account_info"
        account_row["balance_cap"] = BALANCE_CAP
        account_row["ready_to_live_trade"] = False
        account_row["collected_at"] = collected_at

        symbol_fields = [
            "name",
            "description",
            "path",
            "digits",
            "point",
            "spread",
            "spread_float",
            "trade_contract_size",
            "trade_tick_size",
            "trade_tick_value",
            "trade_tick_value_profit",
            "trade_tick_value_loss",
            "volume_min",
            "volume_max",
            "volume_step",
            "trade_mode",
            "trade_calc_mode",
            "margin_initial",
            "margin_maintenance",
            "margin_hedged",
            "currency_base",
            "currency_profit",
            "currency_margin",
        ]
        symbol_row = as_dict(symbol, symbol_fields) if symbol else {}
        bid = getattr(tick, "bid", 0.0) if tick else 0.0
        ask = getattr(tick, "ask", 0.0) if tick else 0.0
        price = ask or bid
        symbol_row["bid"] = bid
        symbol_row["ask"] = ask
        symbol_row["snapshot_type"] = "read_only_symbol_info"
        symbol_row["collected_at"] = collected_at

        contract = float(getattr(symbol, "trade_contract_size", 0.0) or 0.0) if symbol else 0.0
        margin_rows: List[Dict[str, object]] = []
        for lot in SAMPLE_LOTS:
            margin = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, SYMBOL, lot, price) if price else None
            implied_leverage = ""
            if margin and margin > 0 and price and contract:
                implied_leverage = round((lot * price * contract) / margin, 2)
            margin_rows.append(
                {
                    "symbol": SYMBOL,
                    "order_type": "BUY",
                    "lot": lot,
                    "price": price,
                    "order_calc_margin": margin if margin is not None else "",
                    "implied_leverage_from_margin": implied_leverage,
                    "collected_at": collected_at,
                }
            )

        position_count = len(positions) if positions is not None else 0
        order_count = len(orders) if orders is not None else 0
        terminal_row = {
            "terminal_path": str(TERMINAL_PATH),
            "build": getattr(terminal, "build", "") if terminal else "",
            "connected": getattr(terminal, "connected", "") if terminal else "",
            "trade_allowed": getattr(terminal, "trade_allowed", "") if terminal else "",
            "process_count_before": len(processes_before),
            "process_count_after": len(terminal_process_snapshot()),
            "collected_at": collected_at,
        }
        exposure_row = {
            "symbol": SYMBOL,
            "positions_count": position_count,
            "orders_count": order_count,
            "snapshot_type": "counts_only_no_ticket_export",
            "ready_to_live_trade": False,
            "collected_at": collected_at,
        }

        implied_values = [
            round(float(row["implied_leverage_from_margin"]))
            for row in margin_rows
            if row.get("implied_leverage_from_margin") != ""
        ]
        implied_unique = sorted(set(implied_values))
        leverage = int(getattr(account, "leverage", 0) or 0) if account else 0
        balance = float(getattr(account, "balance", 0.0) or 0.0) if account else 0.0
        matches_requested = leverage == REQUESTED_LEVERAGE and (
            not implied_unique or all(abs(value - REQUESTED_LEVERAGE) <= 2 for value in implied_unique)
        )
        balance_matches_cap = abs(balance - BALANCE_CAP) <= 0.01
        checks = [
            check("mt5_initialized", True, True, True),
            check("symbol_selected", selected is True, selected, True),
            check("account_snapshot_collected", bool(account_row), "collected" if account_row else "missing", "collected"),
            check("symbol_snapshot_collected", bool(symbol_row), "collected" if symbol_row else "missing", "collected"),
            check("account_leverage_matches_requested", leverage == REQUESTED_LEVERAGE, leverage, REQUESTED_LEVERAGE),
            check("margin_basis_matches_requested", matches_requested, implied_unique, f"~{REQUESTED_LEVERAGE}"),
            check("balance_matches_cap", balance_matches_cap, balance, BALANCE_CAP),
            check("positions_count_zero", position_count == 0, position_count, 0, "warning", "Existing positions would require operator review before live gate."),
            check("orders_count_zero", order_count == 0, order_count, 0, "warning", "Existing pending orders would require operator review before live gate."),
            check("no_orders_placed", True, False, False),
            check("full_login_redacted", account_row.get("login") == "REDACTED", account_row.get("login"), "REDACTED"),
        ]
        blocker_failures = [row for row in checks if row["severity"] == "blocker" and not row["pass"]]
        warning_failures = [row for row in checks if row["severity"] == "warning" and not row["pass"]]

        decision = {
            "decision_time": collected_at,
            "check_id": "stage_state_live_account_spec_snapshot_read_only",
            "status": "live_account_spec_snapshot_collected_demo_context",
            "account_alias": account_row.get("login_alias", ""),
            "server": account_row.get("server", ""),
            "symbol": SYMBOL,
            "account_leverage": leverage,
            "requested_leverage": REQUESTED_LEVERAGE,
            "balance": balance,
            "balance_cap": BALANCE_CAP,
            "positions_count": position_count,
            "orders_count": order_count,
            "implied_leverage_unique_from_margin": implied_unique,
            "orders_placed": False,
            "runner_executed": False,
            "credential_values_output": False,
            "live_gap_009_closed": False,
            "ready_to_live_trade": False,
            "blocker_failure_count": len(blocker_failures),
            "warning_count": len(warning_failures),
            "recommended_next_action": "update_live_gate_with_demo_account_spec_snapshot_but_keep_live_blocked_pending_real_approval",
        }

        write_csv(OUT_DIR / "live_account_spec_snapshot_account.csv", [account_row], list(account_row.keys()))
        write_csv(OUT_DIR / "live_account_spec_snapshot_symbol.csv", [symbol_row], list(symbol_row.keys()))
        write_csv(
            OUT_DIR / "live_account_spec_snapshot_margin_samples.csv",
            margin_rows,
            ["symbol", "order_type", "lot", "price", "order_calc_margin", "implied_leverage_from_margin", "collected_at"],
        )
        write_csv(OUT_DIR / "live_account_spec_snapshot_terminal.csv", [terminal_row], list(terminal_row.keys()))
        write_csv(OUT_DIR / "live_account_spec_snapshot_exposure_counts.csv", [exposure_row], list(exposure_row.keys()))
        write_csv(OUT_DIR / "live_account_spec_snapshot_checks.csv", checks, ["check_id", "status", "pass", "actual", "expected", "severity", "note"])
        write_csv(OUT_DIR / "live_account_spec_snapshot_decision.csv", [decision], list(decision.keys()))
        write_json(OUT_DIR / "live_account_spec_snapshot_decision.json", decision)

        report = f"""# LIVE-GAP-009 Account / Broker / Symbol Spec Snapshot

Generated: {collected_at}

## Decision

- Status: `{decision["status"]}`
- Account alias: `{decision["account_alias"]}`
- Server: `{decision["server"]}`
- Symbol: `{SYMBOL}`
- Leverage: `1:{leverage}`
- Balance: `{balance:.2f}`
- Balance cap: `{BALANCE_CAP:.2f}`
- Positions/orders: `{position_count} / {order_count}`
- Margin basis: `{implied_unique}`
- LIVE-GAP-009 closed: `false`
- Ready to live trade: `false`

## Boundary

This was a read-only MT5 query. It did not place orders, did not run a Python runner, and did not output the full account number.
"""
        (OUT_DIR / "live_account_spec_snapshot_review.md").write_text(report, encoding="utf-8-sig")
        return 1 if blocker_failures else 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
