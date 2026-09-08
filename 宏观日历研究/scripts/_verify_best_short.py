# -*- coding: utf-8 -*-
"""验证 gate=4.0+rise>=5 的年度明细与每笔分布。"""
import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*")]:
    if str(_p) not in _sys.path:
        _sys.path.insert(0, str(_p))

import numpy as np
import pandas as pd
from grid_short import sim_short, stats
from bias_reversal_replay import pipeline

ROOT = _Path(r"F:\use_code\MTA5_l")
bdir = ROOT / "黄金" / "乖离反转策略" / "data" / "raw" / "mt5_history" / "bias_reversal_live"
h4 = pipeline(bdir / "XAUUSDm_H4.csv", "4H")
h2 = pipeline(bdir / "XAUUSDm_H2.csv", "2H")

for label, kw in [("现状 gate3.5", dict(gate_thr=3.5)), ("加严 gate4.0+rise>=5", dict(gate_thr=4.0, rise_thr=5.0))]:
    st = sim_short(h4, h2, **kw)
    print(f"\n=== {label}: {len(st)} 笔 ===")
    ys = {}
    for t in st:
        ys[t["year"]] = ys.get(t["year"], 0.0) + t["pnl"]
    print("年度:", {k: f"{v:+,.0f}" for k, v in sorted(ys.items())})
    for t in sorted(st, key=lambda x: x["signal_time"]):
        print(f"  {t['signal_time']}  {t['pnl']:+,.0f}pts  {t['reason']}")
