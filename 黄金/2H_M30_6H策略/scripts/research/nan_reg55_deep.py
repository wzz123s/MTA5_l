# -*- coding: utf-8 -*-
"""深化改进2: 回归55SMA gate 稳健性 + 组合验证 (2H_M30_6H ABC)."""
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

from combined_abc_30m2h_2h_20260814 import summarize_combo, simulate_compounded
from experiment_1h_m30_4h_variants_20260813 import replay_three_stage
from nan_improvements_2h_abc import (
    OUT_DIR,
    load_pipeline,
    replay_three_stage_nan55,
    attach_reg55,
)


def yearly_breakdown(st):
    """年度分解: 每交易加权 pnl (stage_pnl * units 求和), 按年汇总."""
    units = {1: 0.5, 2: 1.0, 3: 1.5}
    st = st.copy()
    st["w"] = st["stage_pnl"].astype(float) * st["stage"].map(units)
    per = st.groupby(["signal_time", "dir"], sort=False).agg(
        ts=("signal_time", "first"), w=("w", "sum")
    ).reset_index()
    per["year"] = pd.to_datetime(per["ts"]).dt.year
    rows = []
    for y, g in per.groupby("year", sort=True):
        wins = g["w"][g["w"] > 0].sum()
        losses = -g["w"][g["w"] < 0].sum()
        pf = wins / losses if losses > 0 else float("inf")
        rows.append({"year": int(y), "n": len(g), "wr": float((g["w"] > 0).mean() * 100), "pf": pf, "pnl": float(g["w"].sum())})
    return pd.DataFrame(rows)


def summarize(st, label, desc):
    s = summarize_combo(st)
    sim = simulate_compounded(st, risk_pct=1.0, cost=0.0)
    final = float(sim["balance"].iloc[-1]) if len(sim) else np.nan
    maxdd = float(sim["max_dd_pct"].max()) if len(sim) else np.nan
    return {
        "label": label, "desc": desc, "n": s["n"], "wr": s["wr"], "pf": s["pf"],
        "ev": s["ev"], "pnl_points": s["pnl_points"], "test_pf": s["test_pf"],
        "test_n": s["test_n"], "pos_years": s["positive_years"], "tot_years": s["total_years"],
        "sim_final_1pct": final, "sim_maxdd_pct": maxdd,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    m30_state, trades = load_pipeline()
    t = attach_reg55(trades, m30_state)

    results = []

    # 1) 阈值细扫 0.3-0.7
    print("===== 改进2 阈值细扫 (reg55_dist_pct < thr) =====")
    for thr in [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70]:
        sub = t[t["reg55_dist_pct"] < thr].copy().reset_index(drop=True)
        if len(sub) == 0:
            continue
        st = replay_three_stage(m30_state, sub)
        results.append(summarize(st, f"reg55_{thr}", f"回归55SMA<{thr}%"))
    df = pd.DataFrame(results)
    cols = ["label", "n", "wr", "pf", "ev", "pnl_points", "test_pf", "test_n", "pos_years", "sim_final_1pct", "sim_maxdd_pct"]
    print(df[cols].to_string(index=False))

    # 2) 组合: reg55 gate + nan55 trail
    print()
    print("===== 组合: reg55 gate + 55SMA 移损 (nan55 trail) =====")
    comb = []
    for thr in [0.4, 0.5, 0.6]:
        sub = t[t["reg55_dist_pct"] < thr].copy().reset_index(drop=True)
        st = replay_three_stage_nan55(m30_state, sub)
        comb.append(summarize(st, f"reg55_{thr}_nan55", f"回归<{thr}% + nan55移损"))
    dfc = pd.DataFrame(comb)
    print(dfc[cols].to_string(index=False))

    # 3) 年度分解 (最优 reg55_lt_0.5)
    print()
    print("===== 年度分解: reg55_lt_0.5 =====")
    sub = t[t["reg55_dist_pct"] < 0.5].copy().reset_index(drop=True)
    st = replay_three_stage(m30_state, sub)
    print(yearly_breakdown(st).to_string(index=False))
    print()
    print("===== 年度分解: baseline =====")
    stb = replay_three_stage(m30_state, trades)
    print(yearly_breakdown(stb).to_string(index=False))

    # 4) 口径对比: 方向性 (做多 close>=sma55 附近 / 做空 close<=sma55 附近)
    print()
    print("===== 口径对比: 方向性回归 (做多 close 在 55SMA 上方附近 / 做空在下方附近) =====")
    sma55 = m30_state["SMA_55"].to_numpy()
    close = m30_state["close"].to_numpy()
    signed = []
    for _, tr in t.iterrows():
        sidx = int(tr["signal_bar_idx"])
        s55 = float(sma55[sidx]); c = float(close[sidx])
        is_long = str(tr["dir"]).upper() == "L"
        if not math.isfinite(s55) or s55 == 0:
            signed.append(np.nan); continue
        d = (c - s55) / s55 * 100.0
        signed.append(d if is_long else -d)  # 做多: 正=在55上方; 做空: 正=在55下方
    t["reg55_signed_pct"] = signed
    for thr in [0.0, 0.1, 0.3, 0.5]:
        sub = t[(t["reg55_signed_pct"] >= -0.1) & (t["reg55_signed_pct"] <= thr)].copy().reset_index(drop=True)
        if len(sub) == 0:
            continue
        st = replay_three_stage(m30_state, sub)
        results.append(summarize(st, f"signed_reg_{thr}", f"方向回归: -0.1%~+{thr}%"))
    df2 = pd.DataFrame(results)
    print(df2[["label", "n", "wr", "pf", "ev", "test_pf", "test_n", "pos_years", "sim_final_1pct", "sim_maxdd_pct"]].to_string(index=False))

    # 保存
    df2.to_csv(OUT_DIR / "nan_reg55_deep.csv", index=False, encoding="utf-8-sig")
    print()
    print("wrote:", OUT_DIR / "nan_reg55_deep.csv")


if __name__ == "__main__":
    main()
