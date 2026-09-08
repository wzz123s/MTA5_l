# -*- coding: utf-8 -*-
"""Generate Python expected ledger for reg55 gate (InpNanRegOn=true, 0.5%)."""
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

from experiment_1h_m30_4h_variants_20260813 import replay_three_stage
from nan_improvements_2h_abc import OUT_DIR, load_pipeline, attach_reg55

REGPCT = 0.5


def main():
    m30_state, trades = load_pipeline()
    t = attach_reg55(trades, m30_state)
    sub = t[t["reg55_dist_pct"] < REGPCT].copy().reset_index(drop=True)
    print(f"gate 前 trades={len(trades)} | reg55<{REGPCT}% trades={len(sub)}")
    st = replay_three_stage(m30_state, sub)
    st["signal_time"] = pd.to_datetime(st["signal_time"])
    st["entry_time"] = pd.to_datetime(st["entry_time"])
    st = st[st["signal_time"].dt.year.isin([2025, 2026])].copy().reset_index(drop=True)
    st["trade_key"] = (
        st["entry_time"].dt.strftime("%Y.%m.%d %H:%M:%S")
        + "|" + st["dir"].astype(str).str.upper() + "|S" + st["stage"].astype(str)
    )
    out = st[[
        "trade_key", "signal_time", "entry_time", "dir", "mode", "stage",
        "entry", "stop", "stop_distance", "stage_exit_time", "stage_exit_price",
        "stage_reason", "stage_pnl",
    ]].copy()
    out.columns = [
        "trade_key", "signal_time", "entry_time", "dir", "mode", "stage",
        "entry", "stop", "stop_distance", "exit_time", "exit_price", "exit_reason", "pnl_points",
    ]
    dest = OUT_DIR / "python_expected_reg55_0p5_ledger_2025_2026.csv"
    out.to_csv(dest, index=False, encoding="utf-8-sig")
    n_trades = st.drop_duplicates(["signal_time", "dir"]).shape[0]
    print("expected stage rows:", len(st), "| expected trades:", n_trades)
    print("by year:", st["signal_time"].dt.year.value_counts().sort_index().to_dict())
    print("wrote:", dest)


if __name__ == "__main__":
    main()
