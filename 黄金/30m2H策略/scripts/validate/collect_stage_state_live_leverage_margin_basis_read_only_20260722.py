from __future__ import annotations


import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_live_leverage_margin_basis_read_only_20260722"

TERMINAL_EXE = r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"
SYMBOL = "XAUUSDm"
REQUESTED_LEVERAGE = 2000
SAMPLE_LOTS = [0.01, 0.03, 0.05, 0.09]


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def alias_login(login: object) -> str:
    s = str(login or "")
    return f"MT5_ACCOUNT_***{s[-3:]}" if len(s) >= 3 else "MT5_ACCOUNT_REDACTED"


def as_dict(obj: object, fields: List[str]) -> Dict[str, object]:
    return {field: getattr(obj, field, "") for field in fields}


def main() -> int:
    import MetaTrader5 as mt5

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now().isoformat(timespec="seconds")

    initialized = mt5.initialize(path=TERMINAL_EXE)
    last_error = mt5.last_error()
    if not initialized:
        decision = {
            "decision_time": collected_at,
            "status": "mt5_initialize_failed",
            "last_error": str(last_error),
            "ready_to_live_trade": False,
        }
        write_json(OUT_DIR / "live_leverage_margin_basis_decision.json", decision)
        return 1

    try:
        account = mt5.account_info()
        symbol_selected = mt5.symbol_select(SYMBOL, True)
        symbol = mt5.symbol_info(SYMBOL)
        tick = mt5.symbol_info_tick(SYMBOL)

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
        ]
        account_row = as_dict(account, account_fields) if account else {}
        account_row["login_alias"] = alias_login(getattr(account, "login", ""))
        account_row["login"] = "REDACTED"

        symbol_fields = [
            "name",
            "path",
            "description",
            "digits",
            "point",
            "spread",
            "trade_contract_size",
            "trade_calc_mode",
            "trade_mode",
            "margin_initial",
            "margin_maintenance",
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

        margin_rows: List[Dict[str, object]] = []
        contract = float(getattr(symbol, "trade_contract_size", 0.0) or 0.0) if symbol else 0.0
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
                }
            )

        account_leverage = int(getattr(account, "leverage", 0) or 0) if account else 0
        implied_values = [
            float(row["implied_leverage_from_margin"])
            for row in margin_rows
            if row.get("implied_leverage_from_margin") != ""
        ]
        implied_unique = sorted({round(value) for value in implied_values})
        matches_requested = account_leverage == REQUESTED_LEVERAGE or implied_unique == [REQUESTED_LEVERAGE]

        decision = {
            "decision_time": collected_at,
            "status": "leverage_margin_basis_collected",
            "initialized": initialized,
            "symbol_selected": symbol_selected,
            "account_alias": account_row.get("login_alias", ""),
            "account_leverage": account_leverage,
            "requested_leverage": REQUESTED_LEVERAGE,
            "implied_leverage_unique_from_order_calc_margin": implied_unique,
            "matches_requested_leverage": matches_requested,
            "ready_to_live_trade": False,
            "recommended_next_action": (
                "rerun_guard_rehearsal_after_confirming_1_2000_environment"
                if not matches_requested
                else "update_live_gate_with_confirmed_margin_basis"
            ),
        }

        write_csv(OUT_DIR / "live_leverage_margin_basis_account.csv", [account_row], list(account_row.keys()))
        write_csv(OUT_DIR / "live_leverage_margin_basis_symbol.csv", [symbol_row], list(symbol_row.keys()))
        write_csv(
            OUT_DIR / "live_leverage_margin_basis_order_calc_margin.csv",
            margin_rows,
            ["symbol", "order_type", "lot", "price", "order_calc_margin", "implied_leverage_from_margin"],
        )
        write_json(OUT_DIR / "live_leverage_margin_basis_decision.json", decision)
        write_csv(OUT_DIR / "live_leverage_margin_basis_decision.csv", [decision], list(decision.keys()))

        report = f"""# Live Leverage / Margin Basis Read-only Review

Generated: {collected_at}

## Decision

- Status: `{decision["status"]}`
- Account leverage: `1:{account_leverage}`
- Requested leverage: `1:{REQUESTED_LEVERAGE}`
- Implied leverage from `order_calc_margin`: `{implied_unique}`
- Matches requested leverage: `{matches_requested}`
- Ready to live trade: `false`

## Boundary

This was a read-only MT5 query. It did not send orders and does not approve live trading.
"""
        (OUT_DIR / "live_leverage_margin_basis_review.md").write_text(report, encoding="utf-8-sig")
        return 0 if matches_requested else 1
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
