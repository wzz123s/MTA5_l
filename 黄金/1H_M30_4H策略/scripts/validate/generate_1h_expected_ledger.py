# -*- coding: utf-8 -*-
"""Generate Python expected 3-stage ledger for 1H_M30_4H ABC EA (A2, 2025-2026).

门: 4H side-extreme pool(bias55>=2%) + third_filter(1H bias5&13 signed>0)
    + H4 bias5 同向>=0.6%; IMP: 删 post_n5/post_n6 + Stage1 1.5R (spec 5-35).
EA 参数包同源: auto_trade/1H_M30_4H_ABC_EA.set
"""
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
STRATEGY_DIR = ROOT / "黄金" / "1H_M30_4H策略"
SCRIPTS = STRATEGY_DIR / "scripts"
for _d in [SCRIPTS, SCRIPTS / "research", SCRIPTS / "signals", SCRIPTS / "validate"]:
    _s = str(_d)
    if _s not in sys.path:
        sys.path.insert(0, _s)

import experiment_1h_m30_4h_variants_20260813 as v
from experiment_1h_m30_4h_combined_20260813 import build_combined_trades
from replay_1h_bias55_h1_stop_optimization import load_frames
from replay_1h_way_momentum_filter_scan import add_h1_way_and_momentum

OUT = STRATEGY_DIR / "auto_trade" / "python_expected_2025_2026"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    _, m30, h1, contexts = load_frames()
    h4 = contexts["4H"]
    h1_way = add_h1_way_and_momentum(h1)
    m30_state = v.add_m30_state(m30)
    trades = build_combined_trades(m30, h1_way, h4, 5.0, 35.0, 0.6)
    scoped = trades[~trades["mode"].isin({"post_n5", "post_n6"})].copy().reset_index(drop=True)
    v.STAGE1_R = 1.5  # IMP: Stage1 1.5R (validate_1h_improved 同口径)
    st = v.replay_three_stage(m30_state, scoped)
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
    out.to_csv(OUT / "python_expected_1h_2025_2026.csv", index=False, encoding="utf-8-sig")
    n_trades = st.drop_duplicates(["signal_time", "dir"]).shape[0]
    print("expected stage rows:", len(st), "| expected trades:", n_trades)
    print("by year:", st["signal_time"].dt.year.value_counts().sort_index().to_dict())
    print("by mode:", st.drop_duplicates(["signal_time","dir"])["mode"].value_counts().to_dict())
    print("by stage:", st["stage"].value_counts().sort_index().to_dict())
    print("by reason:", st["stage_reason"].value_counts().to_dict())
    print("last signal_time:", st["signal_time"].max())
    print("last entry_time:", st["entry_time"].max())
    print("wrote:", OUT / "python_expected_1h_2025_2026.csv")


if __name__ == "__main__":
    main()
