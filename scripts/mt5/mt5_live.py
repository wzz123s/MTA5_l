# -*- coding: utf-8 -*-
"""Capture live MT5 ticks and latest bars for deployment smoke tests."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time as time_module
from typing import Any

import pandas as pd

try:
    from .mt5_connection import (
        ensure_symbol,
        initialize_mt5,
        normalize_timeframe,
        public_account_snapshot,
        public_symbol_snapshot,
        public_terminal_snapshot,
        shutdown_mt5,
        timeframe_constant,
    )
except ImportError:  # pragma: no cover
    from mt5_connection import (  # type: ignore
        ensure_symbol,
        initialize_mt5,
        normalize_timeframe,
        public_account_snapshot,
        public_symbol_snapshot,
        public_terminal_snapshot,
        shutdown_mt5,
        timeframe_constant,
    )


def split_timeframes(value: str) -> list[str]:
    frames = [normalize_timeframe(item) for item in value.split(",") if item.strip()]
    if not frames:
        raise ValueError("At least one timeframe is required.")
    return list(dict.fromkeys(frames))


def tick_to_public_dict(tick, symbol: str) -> dict[str, Any]:
    if tick is None:
        raise RuntimeError(f"No tick returned for {symbol}.")
    data = tick._asdict()
    return {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "time": data.get("time"),
        "time_msc": data.get("time_msc"),
        "bid": data.get("bid"),
        "ask": data.get("ask"),
        "last": data.get("last"),
        "volume": data.get("volume"),
        "flags": data.get("flags"),
    }


def latest_bars_to_frame(rates, symbol: str, timeframe: str) -> pd.DataFrame:
    frame = pd.DataFrame(rates)
    if frame.empty:
        return frame
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    frame.insert(1, "date_utc", frame["time"].dt.strftime("%Y-%m-%d %H:%M:%S%z"))
    frame["symbol"] = symbol
    frame["timeframe"] = timeframe
    columns = [
        "time",
        "date_utc",
        "symbol",
        "timeframe",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
        "spread",
        "real_volume",
    ]
    return frame[columns]


def capture_live_once(mt5, *, symbol: str, timeframes: list[str], out_dir: Path, bars: int) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tick = tick_to_public_dict(mt5.symbol_info_tick(symbol), symbol)
    tick_path = out_dir / f"ticks_{symbol}.jsonl"
    with tick_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(tick, ensure_ascii=False) + "\n")

    bar_files = []
    for timeframe in timeframes:
        rates = mt5.copy_rates_from_pos(symbol, timeframe_constant(mt5, timeframe), 0, bars)
        if rates is None:
            raise RuntimeError(f"copy_rates_from_pos failed for {symbol} {timeframe}: {mt5.last_error()}")
        frame = latest_bars_to_frame(rates, symbol, timeframe)
        path = out_dir / f"bars_{symbol}_{timeframe}_latest.csv"
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        bar_files.append({"timeframe": timeframe, "path": str(path.resolve()), "rows": int(len(frame))})

    return {"tick_path": str(tick_path.resolve()), "tick": tick, "bar_files": bar_files}


def run_live_capture(
    *,
    strategy: str,
    strategy_dir: Path,
    symbol: str,
    timeframes: list[str],
    source_id: str,
    terminal_path: str | None,
    login: int | None,
    password: str | None,
    server: str | None,
    portable: bool,
    poll_seconds: float,
    max_iterations: int,
    bars: int,
) -> dict[str, Any]:
    live_dir = strategy_dir / "data" / "live" / source_id
    mt5 = initialize_mt5(
        terminal_path=terminal_path,
        login=login,
        password=password,
        server=server,
        portable=portable,
    )
    captures: list[dict[str, Any]] = []
    try:
        ensure_symbol(mt5, symbol)
        iteration = 0
        while True:
            captures.append(capture_live_once(mt5, symbol=symbol, timeframes=timeframes, out_dir=live_dir, bars=bars))
            iteration += 1
            if max_iterations > 0 and iteration >= max_iterations:
                break
            time_module.sleep(poll_seconds)
        manifest = {
            "strategy": strategy,
            "source_type": "mt5_api_live",
            "source_id": source_id,
            "symbol": symbol,
            "timeframes": timeframes,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "poll_seconds": poll_seconds,
            "max_iterations": max_iterations,
            "bars_per_timeframe": bars,
            "live_dir": str(live_dir.resolve()),
            "snapshot": {
                "terminal": public_terminal_snapshot(mt5),
                "account": public_account_snapshot(mt5),
                "symbol": public_symbol_snapshot(mt5, symbol),
            },
            "captures": captures,
        }
        (live_dir / "live_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8-sig",
        )
        return manifest
    finally:
        shutdown_mt5(mt5)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Capture direct MT5 live ticks and latest bars.")
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--strategy-dir", required=True)
    parser.add_argument("--symbol", default="XAUUSDm")
    parser.add_argument("--timeframes", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--terminal-path", default="")
    parser.add_argument("--login", type=int, default=None)
    parser.add_argument("--password", default="")
    parser.add_argument("--server", default="")
    parser.add_argument("--portable", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--max-iterations", type=int, default=1, help="Use 0 for continuous capture.")
    parser.add_argument("--bars", type=int, default=200)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    manifest = run_live_capture(
        strategy=args.strategy,
        strategy_dir=Path(args.strategy_dir),
        symbol=args.symbol,
        timeframes=split_timeframes(args.timeframes),
        source_id=args.source_id,
        terminal_path=args.terminal_path or None,
        login=args.login,
        password=args.password or None,
        server=args.server or None,
        portable=args.portable,
        poll_seconds=args.poll_seconds,
        max_iterations=args.max_iterations,
        bars=args.bars,
    )
    print(
        f"{manifest['strategy']}: captured MT5 live data; "
        f"source_id={manifest['source_id']}; live_dir={manifest['live_dir']}"
    )


if __name__ == "__main__":
    main()

