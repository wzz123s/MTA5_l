# -*- coding: utf-8 -*-
"""Nan-lun (难论) improvement research for 2H_M30_6H ABC (2026-09).

Research the Nan-lun gaps vs the aligned ABC EA:
  1. 55SMA trailing stop (高点取低点): stage2 trail base SMA13 -> SMA55,
     trigger = min(price/5/13 segment highs) makes a new high (long).
  2. 三九原则 / 盘整第三段 55SMA 回归: gate = signal bar close within X% of M30 SMA55.
  3. 止损小+流畅: fluency gate (stop/ATR small AND amplitude large).
  4. 历史段活跃: activity gate (past N segments avg max-R).  [TODO: 细化]

All causal (no lookahead). Reuses combined_abc + experiment pipelines.
"""
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

from combined_abc_30m2h_2h_20260814 import (  # noqa: E402
    STRATS,
    load_strategy,
    build_combo,
    per_trade,
    summarize_combo,
    simulate_compounded,
    metric,
)
from experiment_1h_m30_4h_variants_20260813 import (  # noqa: E402
    add_m30_state,
    build_three_opportunities,
    replay_signals,
    replay_three_stage,
)
from replay_raw_signals_with_stops import attach_context  # noqa: E402


OUT_DIR = ROOT / "黄金" / "2H_M30_6H策略" / "data" / "validation" / "nan"

# ---- constants (mirror experiment module) ----
STAGE1_R = 2.0
STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0
SPEC_LO = 5.0
SPEC_HI = 35.0
START_CAPITAL = 500.0


# ======================================================================
# 改进 1: 55SMA trailing (高点取低点)
# ======================================================================
def first_opposite_idx(direction_merged, i, is_long):
    opp = "bad" if is_long else "good"
    for j in range(i + 1, len(direction_merged)):
        if direction_merged[j] == opp:
            return j
    return len(direction_merged) - 1


def stage2_exec_nan55(m30, direction_merged, entry_idx, is_long, entry, stop, r):
    """难论高点取低点移损: 低点=55SMA, 高点=min(price/5/13 段内高点), 创新高才移损."""
    trail_start = entry + STAGE2_TRAIL_R * r if is_long else entry - STAGE2_TRAIL_R * r
    force = entry + STAGE2_FORCE_R * r if is_long else entry - STAGE2_FORCE_R * r
    trail_sl = stop
    m30_end = first_opposite_idx(direction_merged, entry_idx, is_long)
    hp = -1e18; h5 = -1e18; h13 = -1e18; H_prev = -1e18
    lp = 1e18; l5 = 1e18; l13 = 1e18; L_prev = 1e18
    for j in range(entry_idx, m30_end + 1):
        row = m30.iloc[j]
        sma55 = float(row["SMA_55"])
        has55 = math.isfinite(sma55) and sma55 > 0
        if is_long:
            if row["high"] >= force:
                return STAGE2_FORCE_R * r, f"{STAGE2_FORCE_R:.1f}R forced", row["date"], force
            if row["low"] <= trail_sl:
                return trail_sl - entry, "trail/SL hit(nan55)", row["date"], trail_sl
            # 高点取低点: 三个段内高点的最低者
            hp = max(hp, float(row["high"]))
            if math.isfinite(float(row["SMA_5"])): h5 = max(h5, float(row["SMA_5"]))
            if math.isfinite(float(row["SMA_13"])): h13 = max(h13, float(row["SMA_13"]))
            H = min(hp, h5, h13)
            if has55 and H > H_prev:
                H_prev = H
                if sma55 > trail_sl:
                    trail_sl = sma55
        else:
            if row["low"] <= force:
                return STAGE2_FORCE_R * r, f"{STAGE2_FORCE_R:.1f}R forced", row["date"], force
            if row["high"] >= trail_sl:
                return entry - trail_sl, "trail/SL hit(nan55)", row["date"], trail_sl
            # 做空镜像: 低点取高点
            lp = min(lp, float(row["low"]))
            if math.isfinite(float(row["SMA_5"])): l5 = min(l5, float(row["SMA_5"]))
            if math.isfinite(float(row["SMA_13"])): l13 = min(l13, float(row["SMA_13"]))
            L = max(lp, l5, l13)
            if has55 and L < L_prev:
                L_prev = L
                if sma55 < trail_sl:
                    trail_sl = sma55
    exit_price = m30.iloc[m30_end]["close"]
    pnl = (exit_price - entry) if is_long else (entry - exit_price)
    return pnl, "M30 merged cross", m30.iloc[m30_end]["date"], exit_price


def stage1_exec(m30, entry_idx, is_long, entry, stop, r):
    target = entry + STAGE1_R * r if is_long else entry - STAGE1_R * r
    for j in range(entry_idx, len(m30)):
        row = m30.iloc[j]
        if is_long:
            if row["low"] <= stop:
                return -r, "SL hit", row["date"], stop
            if row["high"] >= target:
                return STAGE1_R * r, f"{STAGE1_R:.1f}R TP", row["date"], target
        else:
            if row["high"] >= stop:
                return -r, "SL hit", row["date"], stop
            if row["low"] <= target:
                return STAGE1_R * r, f"{STAGE1_R:.1f}R TP", row["date"], target
    return 0.0, "data end", m30.iloc[-1]["date"], m30.iloc[-1]["close"]


def stage3_exec(m30, direction_merged, entry_idx, is_long, entry, stop):
    r = abs(entry - stop)
    end_i = first_opposite_idx(direction_merged, entry_idx, is_long)
    for j in range(entry_idx, end_i + 1):
        row = m30.iloc[j]
        if is_long and row["low"] <= stop:
            return -r, "SL hit", row["date"], stop
        if (not is_long) and row["high"] >= stop:
            return -r, "SL hit", row["date"], stop
    exit_price = m30.iloc[end_i]["close"]
    pnl = (exit_price - entry) if is_long else (entry - exit_price)
    return pnl, "M30 merged cross", m30.iloc[end_i]["date"], exit_price


def replay_three_stage_nan55(m30, trades):
    """三阶段出场, stage2 用难论 55SMA 高点取低点移损 (stage1/3 不变)."""
    direction_merged = m30["方向_合并后"].values.astype(object)
    rows = []
    for _, tr in trades.iterrows():
        entry_idx = int(tr["entry_bar_idx"])
        is_long = str(tr["dir"]).upper() == "L"
        entry = float(tr["entry"])
        stop = float(tr["stop"])
        r = abs(entry - stop)
        if r <= 0 or not math.isfinite(r):
            continue
        stages = [
            (1, stage1_exec(m30, entry_idx, is_long, entry, stop, r)),
            (2, stage2_exec_nan55(m30, direction_merged, entry_idx, is_long, entry, stop, r)),
            (3, stage3_exec(m30, direction_merged, entry_idx, is_long, entry, stop)),
        ]
        for stage, (pnl, reason, exit_time, exit_price) in stages:
            rows.append({
                "signal_time": tr["signal_time"],
                "entry_time": tr["entry_time"],
                "dir": tr["dir"],
                "entry": entry,
                "stop": stop,
                "stop_distance": r,
                "mode": tr.get("mode", "cross"),
                "stage": stage,
                "stage_pnl": pnl,
                "stage_reason": reason,
                "stage_exit_time": exit_time,
                "stage_exit_price": exit_price,
            })
    return pd.DataFrame(rows)


# ======================================================================
# 改进 2: 三九原则 / 回归 55SMA gate
# ======================================================================
def attach_reg55(trades, m30):
    sma55 = m30["SMA_55"].to_numpy()
    close = m30["close"].to_numpy()
    dist = []
    for _, tr in trades.iterrows():
        sidx = int(tr["signal_bar_idx"])
        s55 = float(sma55[sidx]); c = float(close[sidx])
        if not math.isfinite(s55) or not math.isfinite(c) or s55 == 0:
            dist.append(np.nan)
        else:
            dist.append(abs(c - s55) / s55 * 100.0)
    trades = trades.copy()
    trades["reg55_dist_pct"] = dist
    return trades


# ======================================================================
# 改进 3: 止损小 + 流畅 gate (简版: stop/ATR20 小 + 波幅大)
# ======================================================================
def attach_fluency(trades, m30):
    high = m30["high"].to_numpy()
    low = m30["low"].to_numpy()
    close = m30["close"].to_numpy()
    sd = trades["stop_distance"].to_numpy()
    atr = np.full(len(trades), np.nan)
    atr_rel = np.full(len(trades), np.nan)
    for k, tr in trades.iterrows():
        sidx = int(tr["signal_bar_idx"])
        s = max(0, sidx - 20)
        hl = high[s:sidx] - low[s:sidx]
        if len(hl) == 0:
            continue
        a = float(hl.mean())
        if math.isfinite(a) and a > 0:
            atr[k] = a
            c = float(close[sidx])
            if math.isfinite(c) and c > 0:
                atr_rel[k] = a / c * 100.0
    trades = trades.copy()
    trades["atr20"] = atr
    trades["stop_over_atr"] = sd / atr
    trades["atr_rel_pct"] = atr_rel
    return trades


# ======================================================================
# pipeline
# ======================================================================
def load_pipeline():
    cfg = STRATS["2H_M30_6H"]
    m30, gate_tf = load_strategy(cfg)
    m30_state = add_m30_state(m30)
    sig = build_three_opportunities(m30, spec_lo=SPEC_LO, spec_hi=SPEC_HI)
    replayed = replay_signals(sig, m30)
    enriched = attach_context(replayed, gate_tf, "h6")
    trades = build_combo(enriched, cfg, 0.0)
    trades["entry_bar_idx"] = trades["entry_bar_idx"].astype(int)
    return m30_state, trades


def summarize(st, label, desc):
    s = summarize_combo(st)
    # 复利模拟 (1% 与基线 EA 口径一致)
    sim = simulate_compounded(st, risk_pct=1.0, cost=0.0)
    final = float(sim["balance"].iloc[-1]) if len(sim) else np.nan
    maxdd = float(sim["max_dd_pct"].max()) if len(sim) else np.nan
    return {
        "label": label,
        "desc": desc,
        "n": s["n"],
        "long_n": s["long_n"],
        "short_n": s["short_n"],
        "wr": s["wr"],
        "pf": s["pf"],
        "ev": s["ev"],
        "pnl_points": s["pnl_points"],
        "test_pf": s["test_pf"],
        "test_ev": s["test_ev"],
        "test_n": s["test_n"],
        "pos_years": s["positive_years"],
        "tot_years": s["total_years"],
        "sim_final_1pct": final,
        "sim_maxdd_pct": maxdd,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    m30_state, trades = load_pipeline()
    print(f"[pipeline] gate 后 trades={len(trades)} | 信号(去重)={trades.drop_duplicates(['signal_time','dir']).shape[0]}")
    print(f"[pipeline] M30 bar={len(m30_state)} | 时间范围 {m30_state['date'].min()} -> {m30_state['date'].max()}")
    print(f"[pipeline] SMA_55 列存在={('SMA_55' in m30_state.columns)} | 非NaN数={m30_state['SMA_55'].notna().sum()}")

    results = []

    # ---- baseline ----
    st_base = replay_three_stage(m30_state, trades)
    results.append(summarize(st_base, "baseline", "现基线: stage2 SMA13 trailing"))

    # ---- 改进 1: 55SMA trailing (高点取低点) ----
    st_n1 = replay_three_stage_nan55(m30_state, trades)
    results.append(summarize(st_n1, "nan55_trail", "改进1: stage2 55SMA 高点取低点移损"))

    # ---- 改进 2: 回归 55SMA gate (阈值扫描) ----
    t_reg = attach_reg55(trades, m30_state)
    for thr in [0.3, 0.5, 1.0, 1.5, 2.0]:
        sub = t_reg[t_reg["reg55_dist_pct"] < thr].copy().reset_index(drop=True)
        if len(sub) == 0:
            continue
        st_sub = replay_three_stage(m30_state, sub)
        results.append(summarize(st_sub, f"reg55_lt_{thr}", f"改进2: 回归55SMA<{thr}% gate (baseline trailing)"))

    # ---- 改进 3: 流畅 gate (止损小+波幅大, 阈值扫描) ----
    t_flu = attach_fluency(trades, m30_state)
    for soa_thr in [1.0, 1.5, 2.0, 3.0]:
        for amp_thr in [0.10, 0.15, 0.20]:
            sub = t_flu[(t_flu["stop_over_atr"] <= soa_thr) & (t_flu["atr_rel_pct"] >= amp_thr)].copy().reset_index(drop=True)
            if len(sub) == 0:
                continue
            st_sub = replay_three_stage(m30_state, sub)
            results.append(summarize(st_sub, f"flu_soa{soa_thr}_amp{amp_thr}", f"改进3: stop/ATR<={soa_thr} 且 波幅>={amp_thr}% gate"))

    # ---- 输出 ----
    df = pd.DataFrame(results)
    df.to_csv(OUT_DIR / "nan_improvements_summary.csv", index=False, encoding="utf-8-sig")
    cols = ["label", "n", "wr", "pf", "ev", "pnl_points", "test_pf", "test_n", "pos_years", "sim_final_1pct", "sim_maxdd_pct"]
    pd.set_option("display.width", 200)
    pd.set_option("display.max_columns", 30)
    print()
    print(df[cols].to_string(index=False))
    print()
    print("wrote:", OUT_DIR / "nan_improvements_summary.csv")
    return df


if __name__ == "__main__":
    main()
