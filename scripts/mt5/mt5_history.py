# -*- coding: utf-8 -*-
"""Export strategy-dedicated historical bars directly from a local MT5 terminal."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import numpy as np
from pathlib import Path
import re
import shutil
from typing import Any

import pandas as pd

try:  # Allows both `python -m mt5.mt5_history` and direct script execution.
    from .mt5_connection import (
        ensure_symbol,
        initialize_mt5,
        normalize_timeframe,
        parse_utc_datetime,
        public_account_snapshot,
        public_symbol_snapshot,
        public_terminal_snapshot,
        shutdown_mt5,
        timeframe_constant,
    )
except ImportError:  # pragma: no cover - direct script execution fallback
    from mt5_connection import (  # type: ignore
        ensure_symbol,
        initialize_mt5,
        normalize_timeframe,
        parse_utc_datetime,
        public_account_snapshot,
        public_symbol_snapshot,
        public_terminal_snapshot,
        shutdown_mt5,
        timeframe_constant,
    )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_id(text: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", text.strip())
    return cleaned.strip("._-") or "mt5_source"


def split_timeframes(value: str) -> list[str]:
    frames = [normalize_timeframe(item) for item in value.split(",") if item.strip()]
    if not frames:
        raise ValueError("At least one timeframe is required.")
    return list(dict.fromkeys(frames))


def bars_to_frame(rates, symbol: str, timeframe: str) -> pd.DataFrame:
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


def summarize_frame(frame: pd.DataFrame, path: Path, timeframe: str) -> dict[str, Any]:
    if frame.empty:
        raise RuntimeError(f"No bars exported for timeframe {timeframe}.")
    return {
        "timeframe": timeframe,
        "path": str(path.resolve()),
        "rows": int(len(frame)),
        "first_time_utc": str(frame["time"].iloc[0]),
        "last_time_utc": str(frame["time"].iloc[-1]),
        "sha256": file_sha256(path),
        "size": path.stat().st_size,
    }


def build_bundle_sha(manifest_seed: dict[str, Any]) -> str:
    payload = json.dumps(manifest_seed, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def plan_history_bundle(
    *,
    strategy: str,
    strategy_dir: Path,
    symbol: str,
    timeframes: list[str],
    date_from: str,
    date_to: str,
    source_id: str,
) -> dict[str, Any]:
    normalized_frames = [normalize_timeframe(item) for item in timeframes]
    safe_source_id = safe_id(source_id)
    raw_dir = strategy_dir / "data" / "raw"
    bundle_dir = raw_dir / "mt5_history" / safe_source_id
    return {
        "strategy": strategy,
        "strategy_dir": str(strategy_dir.resolve()),
        "raw_dir": str(raw_dir.resolve()),
        "bundle_dir": str(bundle_dir.resolve()),
        "raw_manifest": str((raw_dir / "raw_source_manifest.json").resolve()),
        "compatibility_raw_file": str((raw_dir / "XAUUSDm30.csv").resolve()),
        "source_type": "mt5_api_history",
        "source_id": safe_source_id,
        "symbol": symbol,
        "timeframes": normalized_frames,
        "date_from_utc": str(parse_utc_datetime(date_from)),
        "date_to_utc": str(parse_utc_datetime(date_to)),
    }


def export_history_bundle(
    *,
    strategy: str,
    strategy_dir: Path,
    symbol: str,
    timeframes: list[str],
    date_from: str,
    date_to: str,
    source_id: str,
    terminal_path: str | None = None,
    login: int | None = None,
    password: str | None = None,
    server: str | None = None,
    portable: bool = False,
) -> dict[str, Any]:
    plan = plan_history_bundle(
        strategy=strategy,
        strategy_dir=strategy_dir,
        symbol=symbol,
        timeframes=timeframes,
        date_from=date_from,
        date_to=date_to,
        source_id=source_id,
    )
    bundle_dir = Path(plan["bundle_dir"])
    raw_dir = Path(plan["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    start_utc = parse_utc_datetime(date_from)
    end_utc = parse_utc_datetime(date_to)
    if end_utc <= start_utc:
        raise ValueError("date_to must be later than date_from.")

    mt5 = initialize_mt5(
        terminal_path=terminal_path,
        login=login,
        password=password,
        server=server,
        portable=portable,
    )
    try:
        ensure_symbol(mt5, symbol)
        files: list[dict[str, Any]] = []
        m30_path: Path | None = None
        for timeframe in plan["timeframes"]:
            tf = timeframe_constant(mt5, timeframe)
            chunks = []
            cursor = start_utc
            while cursor < end_utc:
                chunk_end = min(cursor + timedelta(days=365), end_utc)
                chunk = mt5.copy_rates_range(symbol, tf, cursor, chunk_end)
                if chunk is None:
                    raise RuntimeError(
                        f"copy_rates_range failed for {symbol} {timeframe} "
                        f"[{cursor.isoformat()}..{chunk_end.isoformat()}]: {mt5.last_error()}"
                    )
                chunks.append(chunk)
                cursor = chunk_end
            if not chunks:
                raise RuntimeError(f"copy_rates_range returned no data for {symbol} {timeframe}.")
            rates = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
            rates = np.unique(rates, axis=0)
            rates = rates[np.argsort(rates["time"])]
            frame = bars_to_frame(rates, symbol, timeframe)
            out_path = bundle_dir / f"{symbol}_{timeframe}.csv"
            frame.to_csv(out_path, index=False, encoding="utf-8-sig")
            files.append(summarize_frame(frame, out_path, timeframe))
            if timeframe == "M30":
                m30_path = out_path

        if m30_path is None:
            raise RuntimeError("M30 timeframe is required because existing strategy builders consume XAUUSDm30.csv.")

        compatibility_raw_file = raw_dir / "XAUUSDm30.csv"
        shutil.copy2(m30_path, compatibility_raw_file)

        snapshot = {
            "terminal": public_terminal_snapshot(mt5),
            "account": public_account_snapshot(mt5),
            "symbol": public_symbol_snapshot(mt5, symbol),
        }
    finally:
        shutdown_mt5(mt5)

    now = datetime.now(timezone.utc).isoformat()
    seed = {
        "strategy": strategy,
        "source_type": "mt5_api_history",
        "source_id": plan["source_id"],
        "symbol": symbol,
        "timeframes": plan["timeframes"],
        "date_from_utc": plan["date_from_utc"],
        "date_to_utc": plan["date_to_utc"],
        "files": files,
        "compatibility_raw_sha256": file_sha256(compatibility_raw_file),
    }
    manifest = {
        **seed,
        "generated_at_utc": now,
        "bundle_dir": str(bundle_dir.resolve()),
        "bundle_sha256": build_bundle_sha(seed),
        "compatibility_raw_file": str(compatibility_raw_file.resolve()),
        "terminal_path_arg": terminal_path or "",
        "server_arg": server or "",
        "portable": bool(portable),
        "snapshot": snapshot,
        "rule": "strategy_dedicated_raw_source_required; direct_mt5_api_required",
    }

    bundle_manifest = bundle_dir / "mt5_history_manifest.json"
    bundle_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")
    raw_manifest = raw_dir / "raw_source_manifest.json"
    raw_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8-sig")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export direct MT5 historical bars for one strategy.")
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--strategy-dir", required=True)
    parser.add_argument("--symbol", default="XAUUSDm")
    parser.add_argument("--timeframes", required=True, help="Comma-separated list, e.g. M30,H1,H4.")
    parser.add_argument("--from", dest="date_from", required=True, help="UTC start date/time, e.g. 2022-01-01.")
    parser.add_argument("--to", dest="date_to", required=True, help="UTC end date/time, e.g. 2026-07-25.")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--terminal-path", default="")
    parser.add_argument("--login", type=int, default=None)
    parser.add_argument("--password", default="")
    parser.add_argument("--server", default="")
    parser.add_argument("--portable", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Print the planned output paths without connecting MT5.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    strategy_dir = Path(args.strategy_dir)
    timeframes = split_timeframes(args.timeframes)
    if args.dry_run:
        plan = plan_history_bundle(
            strategy=args.strategy,
            strategy_dir=strategy_dir,
            symbol=args.symbol,
            timeframes=timeframes,
            date_from=args.date_from,
            date_to=args.date_to,
            source_id=args.source_id,
        )
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    manifest = export_history_bundle(
        strategy=args.strategy,
        strategy_dir=strategy_dir,
        symbol=args.symbol,
        timeframes=timeframes,
        date_from=args.date_from,
        date_to=args.date_to,
        source_id=args.source_id,
        terminal_path=args.terminal_path or None,
        login=args.login,
        password=args.password or None,
        server=args.server or None,
        portable=args.portable,
    )
    print(
        f"{manifest['strategy']}: exported {len(manifest['files'])} MT5 history files; "
        f"source_id={manifest['source_id']}; bundle_sha256={manifest['bundle_sha256']}"
    )


if __name__ == "__main__":
    main()
