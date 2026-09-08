# -*- coding: utf-8 -*-
"""Create three independent USOIL gate strategies with their own raw data."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



import sys
from pathlib import Path


ROOT = Path(r"F:\use_code\MTA5_l")
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mt5.mt5_history import export_history_bundle  # noqa: E402


STRATEGIES = [
    {
        "name": "原油4H门策略",
        "timeframes": ["M30", "H2", "H4"],
        "source_id": "usoil_4h_gate_gen_20200101_20260815",
    },
    {
        "name": "原油6H门策略",
        "timeframes": ["M30", "H2", "H6"],
        "source_id": "usoil_6h_gate_gen_20200101_20260815",
    },
    {
        "name": "原油8H门策略",
        "timeframes": ["M30", "H2"],
        "source_id": "usoil_8h_gate_gen_20200101_20260815",
    },
]


def main() -> None:
    for cfg in STRATEGIES:
        strategy_dir = ROOT / "原油" / cfg["name"]
        strategy_dir.mkdir(parents=True, exist_ok=True)
        manifest = export_history_bundle(
            strategy=cfg["name"],
            strategy_dir=strategy_dir,
            symbol="USOILm",
            timeframes=cfg["timeframes"],
            date_from="2020-01-01",
            date_to="2026-08-15",
            source_id=cfg["source_id"],
        )
        print(cfg["name"], "->", [(f["timeframe"], f["rows"]) for f in manifest["files"]])


if __name__ == "__main__":
    main()
