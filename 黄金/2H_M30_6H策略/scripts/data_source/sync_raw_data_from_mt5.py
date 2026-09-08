# -*- coding: utf-8 -*-
"""Pull 2H_M30_6H strategy-dedicated raw data directly from MT5."""
from __future__ import annotations


import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = Path(__file__).resolve().parents[2]
STRATEGY = "2H_M30_6H"
DEFAULT_TIMEFRAMES = "M30,H2,H6"

sys.path.insert(0, str(ROOT / "scripts"))

from mt5.mt5_history import export_history_bundle, plan_history_bundle, split_timeframes  # noqa: E402


def default_source_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{STRATEGY.lower()}_mt5_{stamp}"


def write_raw_readme(manifest: dict) -> None:
    raw_dir = STRATEGY_DIR / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    text = f"""# {STRATEGY} raw data

This folder is reserved for strategy-dedicated raw data.

- source_type: {manifest.get("source_type", "")}
- source_id: {manifest.get("source_id", "")}
- symbol: {manifest.get("symbol", "")}
- timeframes: {", ".join(manifest.get("timeframes", []))}
- bundle_sha256: {manifest.get("bundle_sha256", "")}
- compatibility raw: {manifest.get("compatibility_raw_file", "")}

Do not replace this folder with another strategy's raw files. Regenerate it with
`scripts/data_source/sync_raw_data_from_mt5.py` when the MT5 source or date range changes.
"""
    (raw_dir / "README.md").write_text(text, encoding="utf-8-sig")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"Sync {STRATEGY} raw data from MT5.")
    parser.add_argument("--symbol", default="XAUUSDm")
    parser.add_argument("--timeframes", default=DEFAULT_TIMEFRAMES)
    parser.add_argument("--from", dest="date_from", required=True, help="UTC start date, e.g. 2022-01-01.")
    parser.add_argument("--to", dest="date_to", required=True, help="UTC end date, e.g. 2026-07-25.")
    parser.add_argument("--source-id", default="")
    parser.add_argument("--terminal-path", default="")
    parser.add_argument("--login", type=int, default=None)
    parser.add_argument("--password", default="")
    parser.add_argument("--server", default="")
    parser.add_argument("--portable", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    source_id = args.source_id or default_source_id()
    timeframes = split_timeframes(args.timeframes)
    if args.dry_run:
        plan = plan_history_bundle(
            strategy=STRATEGY,
            strategy_dir=STRATEGY_DIR,
            symbol=args.symbol,
            timeframes=timeframes,
            date_from=args.date_from,
            date_to=args.date_to,
            source_id=source_id,
        )
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return

    manifest = export_history_bundle(
        strategy=STRATEGY,
        strategy_dir=STRATEGY_DIR,
        symbol=args.symbol,
        timeframes=timeframes,
        date_from=args.date_from,
        date_to=args.date_to,
        source_id=source_id,
        terminal_path=args.terminal_path or None,
        login=args.login,
        password=args.password or None,
        server=args.server or None,
        portable=args.portable,
    )
    write_raw_readme(manifest)
    print(
        f"{STRATEGY}: MT5 raw data exported; "
        f"source_id={manifest.get('source_id', '')}; bundle_sha256={manifest.get('bundle_sha256', '')}"
    )


if __name__ == "__main__":
    main()

