# -*- coding: utf-8 -*-
"""Small, explicit wrappers around the MetaTrader5 Python package."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
from typing import Any


def import_mt5():
    try:
        import MetaTrader5 as mt5  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on local terminal setup
        raise RuntimeError(
            "MetaTrader5 Python package is not installed. "
            "Install it in the active Python environment before pulling MT5 data."
        ) from exc
    return mt5


def initialize_mt5(
    *,
    terminal_path: str | None = None,
    login: int | None = None,
    password: str | None = None,
    server: str | None = None,
    portable: bool = False,
):
    mt5 = import_mt5()
    kwargs: dict[str, Any] = {}
    if terminal_path:
        kwargs["path"] = str(Path(terminal_path))
    if login is not None:
        kwargs["login"] = int(login)
    if password:
        kwargs["password"] = password
    if server:
        kwargs["server"] = server
    if portable:
        kwargs["portable"] = True

    ok = mt5.initialize(**kwargs)
    if not ok:
        raise RuntimeError(f"mt5.initialize failed: {mt5.last_error()}")
    return mt5


def shutdown_mt5(mt5) -> None:
    try:
        mt5.shutdown()
    except Exception:
        pass


def ensure_symbol(mt5, symbol: str) -> None:
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"MT5 symbol is not available: {symbol}")
    if not info.visible and not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"MT5 symbol_select failed for {symbol}: {mt5.last_error()}")


def timeframe_constant(mt5, label: str) -> int:
    normalized = normalize_timeframe(label)
    attr = f"TIMEFRAME_{normalized}"
    if hasattr(mt5, attr):
        return int(getattr(mt5, attr))
    fallback_minutes = {
        "M1": 1,
        "M2": 2,
        "M3": 3,
        "M4": 4,
        "M5": 5,
        "M6": 6,
        "M10": 10,
        "M12": 12,
        "M15": 15,
        "M20": 20,
        "M30": 30,
        "H1": 60,
        "H2": 120,
        "H3": 180,
        "H4": 240,
        "H6": 360,
        "H8": 480,
        "H12": 720,
        "D1": 1440,
        "W1": 10080,
        "MN1": 43200,
    }
    if normalized not in fallback_minutes:
        raise ValueError(f"Unsupported timeframe: {label}")
    return fallback_minutes[normalized]


def normalize_timeframe(label: str) -> str:
    value = label.strip().upper().replace(" ", "")
    aliases = {
        "30M": "M30",
        "15M": "M15",
        "5M": "M5",
        "1M": "M1",
        "1H": "H1",
        "2H": "H2",
        "3H": "H3",
        "4H": "H4",
        "6H": "H6",
        "8H": "H8",
        "12H": "H12",
        "1D": "D1",
        "1W": "W1",
        "1MN": "MN1",
    }
    return aliases.get(value, value)


def parse_utc_datetime(value: str) -> datetime:
    text = value.strip()
    if not text:
        raise ValueError("datetime value cannot be empty")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        text = text + "T00:00:00+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def public_terminal_snapshot(mt5) -> dict[str, Any]:
    terminal = mt5.terminal_info()
    version = mt5.version()
    snapshot: dict[str, Any] = {"mt5_version": version}
    if terminal is not None:
        data = terminal._asdict()
        for key in ["name", "company", "path", "data_path", "commondata_path", "build", "connected"]:
            if key in data:
                snapshot[key] = data[key]
    return snapshot


def public_account_snapshot(mt5) -> dict[str, Any]:
    account = mt5.account_info()
    if account is None:
        return {"account_connected": False}
    data = account._asdict()
    login = str(data.get("login", ""))
    return {
        "account_connected": True,
        "login_sha256": hashlib.sha256(login.encode("utf-8")).hexdigest() if login else "",
        "server": data.get("server", ""),
        "currency": data.get("currency", ""),
        "trade_mode": data.get("trade_mode", ""),
        "leverage": data.get("leverage", ""),
    }


def public_symbol_snapshot(mt5, symbol: str) -> dict[str, Any]:
    info = mt5.symbol_info(symbol)
    if info is None:
        return {"symbol": symbol, "available": False}
    data = info._asdict()
    keys = [
        "name",
        "path",
        "digits",
        "point",
        "trade_contract_size",
        "currency_profit",
        "currency_margin",
        "spread",
        "trade_mode",
        "visible",
    ]
    return {"available": True, **{key: data.get(key) for key in keys}}

