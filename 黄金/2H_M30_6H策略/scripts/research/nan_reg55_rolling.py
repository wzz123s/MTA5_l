# -*- coding: utf-8 -*-
"""reg55 gate 滚动窗口稳健性验证 (rolling PF)."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from combined_abc_30m2h_2h_20260814 import rolling_windows, per_trade
from experiment_1h_m30_4h_variants_20260813 import replay_three_stage
from nan_improvements_2h_abc import OUT_DIR, load_pipeline, attach_reg55


def main():
    m30_state, trades = load_pipeline()
    t = attach_reg55(trades, m30_state)

    for months in [12, 18]:
        print(f"===== rolling {months}m PF: baseline vs reg55_lt_0.5 =====")
        sub = t[t["reg55_dist_pct"] < 0.5].copy().reset_index(drop=True)
        stb = replay_three_stage(m30_state, trades)
        sts = replay_three_stage(m30_state, sub)
        pb = per_trade(stb)
        ps = per_trade(sts)
        rb = rolling_windows(pb, months)
        rs = rolling_windows(ps, months)
        rb = rb.rename(columns={"n": "base_n", "pf": "base_pf", "ev": "base_ev", "pnl_points": "base_pnl"})
        rs = rs.rename(columns={"n": "reg_n", "pf": "reg_pf", "ev": "reg_ev", "pnl_points": "reg_pnl"})
        m = pd.merge(rb[["window_start", "window_end", "base_n", "base_pf", "base_pnl"]],
                     rs[["window_start", "window_end", "reg_n", "reg_pf", "reg_pnl"]],
                     on=["window_start", "window_end"], how="outer")
        # 只显示 reg55 有数据的窗口
        m = m[m["reg_n"].notna()]
        print(m.to_string(index=False))
        print()

    # 汇总: 各窗口 PF<1 的数量
    print("===== 窗口 PF<1 计数 =====")
    for months in [12, 18]:
        sub = t[t["reg55_dist_pct"] < 0.5].copy().reset_index(drop=True)
        stb = replay_three_stage(m30_state, trades)
        sts = replay_three_stage(m30_state, sub)
        rb = rolling_windows(per_trade(stb), months)
        rs = rolling_windows(per_trade(sts), months)
        b_bad = int((rb["pf"] < 1).sum()); b_tot = len(rb)
        s_bad = int((rs["pf"] < 1).sum()); s_tot = len(rs)
        print(f"{months}m: baseline PF<1 窗口 {b_bad}/{b_tot}, reg55 PF<1 窗口 {s_bad}/{s_tot}")


if __name__ == "__main__":
    main()
