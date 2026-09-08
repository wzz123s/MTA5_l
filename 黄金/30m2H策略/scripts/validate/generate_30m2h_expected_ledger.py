# -*- coding: utf-8 -*-
"""Generate Python expected 3-stage ledger for 30m2H ABC EA (2025-2026)."""
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

import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from combined_abc_30m2h_2h_20260814 import (
    STRATS,
    add_m30_state,
    attach_context,
    build_combo,
    build_three_opportunities,
    load_strategy,
    replay_signals,
    replay_three_stage,
)

OUT = (
    Path(r"F:\use_code\MTA5_l\黄金\30m2H策略\auto_trade")
    / "python_expected_2025_2026"
)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = STRATS["30m2H"]
    m30, gate_tf = load_strategy(cfg)
    m30_state = add_m30_state(m30)
    sig = build_three_opportunities(m30, spec_lo=5.0, spec_hi=35.0)
    replayed = replay_signals(sig, m30)
    enriched = attach_context(replayed, gate_tf, "h2")
    trades = build_combo(enriched, cfg, 0.2)  # 30m2H 推荐组合: |H2 bias55|>3% 且 bias5 同向>=0.2%
    trades["entry_bar_idx"] = pd.to_numeric(trades["entry_bar_idx"], errors="coerce").astype(int)
    st = replay_three_stage(m30_state, trades)
    st["signal_time"] = pd.to_datetime(st["signal_time"])
    st["entry_time"] = pd.to_datetime(st["entry_time"])
    st = st[st["signal_time"].dt.year.isin([2025, 2026])].copy().reset_index(drop=True)
    st["trade_key"] = (
        pd.to_datetime(st["entry_time"]).dt.strftime("%Y.%m.%d %H:%M:%S")
        + "|" + st["dir"].astype(str).str.upper() + "|S" + st["stage"].astype(str)
    )
    out = st[
        ["trade_key", "signal_time", "entry_time", "dir", "mode", "stage",
         "entry", "stop", "stop_distance", "stage_exit_time", "stage_exit_price",
         "stage_reason", "stage_pnl"]
    ].copy()
    out.columns = [
        "trade_key", "signal_time", "entry_time", "dir", "mode", "stage",
        "entry", "stop", "stop_distance", "exit_time", "exit_price", "exit_reason", "pnl_points",
    ]
    out.to_csv(OUT / "python_expected_30m2h_2025_2026.csv", index=False, encoding="utf-8-sig")
    n_trades = st.drop_duplicates(["signal_time", "dir"]).shape[0]
    print("expected stage rows:", len(st), "| expected trades:", n_trades)
    print("by year:", st["signal_time"].dt.year.value_counts().sort_index().to_dict())
    print("wrote:", OUT / "python_expected_30m2h_2025_2026.csv")


if __name__ == "__main__":
    main()
