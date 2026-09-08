from __future__ import annotations


import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
OUT_DIR = VALIDATION_DIR / "stage_state_broker_symbol_spec_read_only_20260721"

TERMINAL_PATH = Path(r"F:\Program Files\MetaTrader 5 EXNESS\terminal64.exe")
SYMBOL = "XAUUSDm"
APPROVAL_PHRASE = "USER_APPROVES_READ_ONLY_MT5_SYMBOL_SPEC_QUERY_NO_ORDERS"


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")


def terminal_process_count() -> int:
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Measure-Object).Count",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return -1
    try:
        return int(result.stdout.strip() or "0")
    except ValueError:
        return -1


def spread_policy(info: Dict[str, object]) -> str:
    mode = "floating" if bool(info.get("spread_float")) else "fixed"
    spread = info.get("spread", "")
    return f"{mode};current_spread_points={spread}"


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def build_symbol_row(info: Dict[str, object], terminal_info: Dict[str, object], process_before: int, process_after: int, collected_at: str) -> Dict[str, object]:
    return {
        "symbol": info.get("name", SYMBOL),
        "contract_size": info.get("trade_contract_size", ""),
        "min_lot": info.get("volume_min", ""),
        "lot_step": info.get("volume_step", ""),
        "margin_initial": info.get("margin_initial", ""),
        "digits": info.get("digits", ""),
        "spread_policy": spread_policy(info),
        "spread_points_current": info.get("spread", ""),
        "spread_float": info.get("spread_float", ""),
        "volume_max": info.get("volume_max", ""),
        "trade_mode": info.get("trade_mode", ""),
        "trade_calc_mode": info.get("trade_calc_mode", ""),
        "tick_size": info.get("trade_tick_size", ""),
        "tick_value": info.get("trade_tick_value", ""),
        "currency_base": info.get("currency_base", ""),
        "currency_profit": info.get("currency_profit", ""),
        "currency_margin": info.get("currency_margin", ""),
        "margin_hedged": info.get("margin_hedged", ""),
        "terminal_build": terminal_info.get("build", ""),
        "terminal_connected": terminal_info.get("connected", ""),
        "terminal_trade_allowed": terminal_info.get("trade_allowed", ""),
        "approval_phrase": APPROVAL_PHRASE,
        "collection_mode": "read_only_symbol_info",
        "terminal_process_count_before": process_before,
        "terminal_process_count_after": process_after,
        "terminal_spawned": process_after > process_before if process_before >= 0 and process_after >= 0 else "",
        "mt5_initialized": True,
        "orders_placed": False,
        "runner_executed": False,
        "live_set_switched": False,
        "credential_values_output": False,
        "gate_status": "open",
        "ready_to_live_trade": False,
        "collected_at": collected_at,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now().isoformat(timespec="seconds")
    process_before = terminal_process_count()
    decision: Dict[str, object] = {
        "decision_time": collected_at,
        "check_id": "stage_state_broker_symbol_spec_read_only",
        "approval_phrase": APPROVAL_PHRASE,
        "symbol": SYMBOL,
        "terminal_path": str(TERMINAL_PATH),
        "terminal_process_count_before": process_before,
        "terminal_process_count_after": "",
        "terminal_spawned": "",
        "mt5_initialized": False,
        "symbol_info_collected": False,
        "broker_symbol_spec_rows": 0,
        "orders_placed": False,
        "runner_executed": False,
        "live_set_switched": False,
        "credential_values_output": False,
        "gate_status": "open",
        "ready_to_live_trade": False,
    }

    if process_before <= 0:
        decision.update(
            {
                "status": "not_collected_terminal_not_running",
                "recommended_next_action": "start_terminal_manually_then_retry_read_only_spec_query",
            }
        )
        write_json(OUT_DIR / "broker_symbol_spec_read_only_decision.json", decision)
        write_csv(OUT_DIR / "broker_symbol_spec_read_only_decision.csv", [decision], list(decision.keys()))
        print("status=not_collected_terminal_not_running")
        return 1

    try:
        import MetaTrader5 as mt5
    except Exception as exc:  # pragma: no cover - depends on local terminal package
        decision.update({"status": "not_collected_mt5_package_unavailable", "error": type(exc).__name__})
        write_json(OUT_DIR / "broker_symbol_spec_read_only_decision.json", decision)
        write_csv(OUT_DIR / "broker_symbol_spec_read_only_decision.csv", [decision], list(decision.keys()))
        print("status=not_collected_mt5_package_unavailable")
        return 1

    initialized = mt5.initialize(path=str(TERMINAL_PATH))
    process_after_init = terminal_process_count()
    decision["terminal_process_count_after"] = process_after_init
    decision["terminal_spawned"] = process_after_init > process_before if process_after_init >= 0 else ""
    decision["mt5_initialized"] = bool(initialized)

    if not initialized:
        decision.update(
            {
                "status": "not_collected_mt5_initialize_failed",
                "mt5_last_error": str(mt5.last_error()),
                "recommended_next_action": "verify_terminal_session_then_retry_read_only_spec_query",
            }
        )
        write_json(OUT_DIR / "broker_symbol_spec_read_only_decision.json", decision)
        write_csv(OUT_DIR / "broker_symbol_spec_read_only_decision.csv", [decision], list(decision.keys()))
        print("status=not_collected_mt5_initialize_failed")
        return 1

    try:
        terminal_info_obj = mt5.terminal_info()
        symbol_info_obj = mt5.symbol_info(SYMBOL)
        if symbol_info_obj is None:
            decision.update(
                {
                    "status": "not_collected_symbol_info_unavailable",
                    "mt5_last_error": str(mt5.last_error()),
                    "recommended_next_action": "confirm_symbol_name_or_select_symbol_manually_then_retry",
                }
            )
            write_json(OUT_DIR / "broker_symbol_spec_read_only_decision.json", decision)
            write_csv(OUT_DIR / "broker_symbol_spec_read_only_decision.csv", [decision], list(decision.keys()))
            print("status=not_collected_symbol_info_unavailable")
            return 1

        terminal_info = terminal_info_obj._asdict() if terminal_info_obj is not None else {}
        symbol_info = symbol_info_obj._asdict()
        process_after = terminal_process_count()
        row = build_symbol_row(symbol_info, terminal_info, process_before, process_after, collected_at)
        fieldnames = [
            "symbol",
            "contract_size",
            "min_lot",
            "lot_step",
            "margin_initial",
            "digits",
            "spread_policy",
            "spread_points_current",
            "spread_float",
            "volume_max",
            "trade_mode",
            "trade_calc_mode",
            "tick_size",
            "tick_value",
            "currency_base",
            "currency_profit",
            "currency_margin",
            "margin_hedged",
            "terminal_build",
            "terminal_connected",
            "terminal_trade_allowed",
            "approval_phrase",
            "collection_mode",
            "terminal_process_count_before",
            "terminal_process_count_after",
            "terminal_spawned",
            "mt5_initialized",
            "orders_placed",
            "runner_executed",
            "live_set_switched",
            "credential_values_output",
            "gate_status",
            "ready_to_live_trade",
            "collected_at",
        ]
        write_csv(OUT_DIR / "broker_symbol_spec.csv", [row], fieldnames)
        decision.update(
            {
                "status": "broker_symbol_spec_collected_read_only_live_blocked",
                "terminal_process_count_after": process_after,
                "terminal_spawned": process_after > process_before if process_after >= 0 else "",
                "symbol_info_collected": True,
                "broker_symbol_spec_rows": 1,
                "recommended_next_action": "review_broker_symbol_spec_read_only_output",
            }
        )
        write_json(OUT_DIR / "broker_symbol_spec_read_only_decision.json", decision)
        write_csv(OUT_DIR / "broker_symbol_spec_read_only_decision.csv", [decision], list(decision.keys()))
        lines = [
            "# Broker Symbol Spec Read-only Collection",
            "",
            f"- status: `{decision['status']}`",
            f"- symbol: `{SYMBOL}`",
            "- collection_mode: `read_only_symbol_info`",
            f"- broker_symbol_spec_rows: `{decision['broker_symbol_spec_rows']}`",
            f"- terminal_spawned: `{decision['terminal_spawned']}`",
            "- orders_placed: `False`",
            "- runner_executed: `False`",
            "- live_set_switched: `False`",
            "- ready_to_live_trade: `False`",
            "",
        ]
        (OUT_DIR / "broker_symbol_spec_read_only.md").write_text("\n".join(lines), encoding="utf-8-sig")
        for key, value in decision.items():
            print(f"{key}={value}")
        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
