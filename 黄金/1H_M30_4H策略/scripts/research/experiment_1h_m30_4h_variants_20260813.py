# -*- coding: utf-8 -*-

"""1H_M30_4H variant experiments (2026-08-13).

Three research questions from the user:
  A. Apply 30m2H Layer-2 three opportunities (pre_cross / cross / post_n)
     with previous-segment SMA13 extreme stops on the 1H_M30_4H strategy.
  B. Apply the 30m2H three-stage exit (2.0R / 1.5R trail + 4.0R force /
     M30 merged cross), stop spec [5,35] and 3% balance-risk dynamic lots.
  C. H4 opportunity pool: require H4 bias55 and H4 bias5 to be high in the
     same direction; scan whether "both high" opportunities are better.

All variants use the 1H_M30_4H strategy's own raw MT5 history (2020-2023).
Baseline reproduction (current candidate, 88 trades / PF 3.19) is included
to validate the pipeline before the variants are computed.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)


import bisect
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from replay_raw_signals_with_stops import (  # noqa: E402
    LOT_FOR_REPORT,
    markdown_table,
    metric,
    read_csv,
    split_test,
    trade_sign,
    yearly_positive_count,
)
from replay_1h_bias55_h1_stop_optimization import load_frames  # noqa: E402
from replay_1h_way_momentum_filter_scan import (  # noqa: E402
    BIAS55_THRESHOLD,
    add_h1_way_and_momentum,
    filter_short_segments_causal,
    mark_direction,
    side_extreme_features,
    side_extreme_opportunity_mask,
    third_filter_mask,
)
from validate_1h_way_momentum_candidates import (  # noqa: E402
    CandidateSpec,
    select_candidate,
)


STRATEGY = "1H_M30_4H"
OUT_DIR = ROOT / "黄金" / f"{STRATEGY}策略" / "data" / "validation" / "experiments_20260813"
ENRICHED_PATH = (
    ROOT / "黄金" / f"{STRATEGY}策略" / "data" / "validation" / "way_momentum_filter" / "way_momentum_enriched_trades.csv"
)

# ---- current candidate (baseline reference) ----
BASE_CANDIDATE = CandidateSpec(
    name="fd1_8_28_side_pool_base",
    base_candidate="fd1_h1last6_8_28",
    filter_desc="fixed_delay_1 + H1 last6 stop + 8-28pt + side-extreme pool",
)
CURRENT_CANDIDATE = CandidateSpec(
    name="fd1_8_28_side_pool_close_mom_ge_-0.4__short_vol_way_le_0.7",
    base_candidate="fd1_h1last6_8_28",
    filter_desc="8-28pt base + close momentum signed >= -0.4 + SHORT vol_way_s_way <= 0.7",
    use_close_momentum=True,
    close_momentum_min=-0.4,
    short_vol_way_le=0.7,
)

# ---- 30m2H Layer-2 constants ----
PRE_CROSS_GAP = 0.003  # 0.3%
POST_N_MIN = 2
POST_N_MAX = 6
SPEC_8_28 = (8.0, 28.0)
SPEC_5_35 = (5.0, 35.0)

# ---- variant B stage / risk constants ----
STAGE1_R = 2.0
STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0
STAGE_UNITS = (0.5, 1.0, 1.5)  # stage lot ratio (same as 30m2H final mainline)
START_CAPITAL = 500.0
RISK_PCT = 3.0
USD_PER_POINT_PER_LOT = 10.0
LOT_MIN = 0.01
LOT_MAX = 10.0


# --------------------------------------------------------------------------
# M30 direction / three-opportunity signal builder (30m2H semantics)
# --------------------------------------------------------------------------
def add_m30_state(m30: pd.DataFrame) -> pd.DataFrame:
    """Attach 方向 / 方向_合并后 / merged_post_cross_n to the M30 frame."""
    out = m30.copy().sort_values("date").reset_index(drop=True)
    out = mark_direction(out)
    out = filter_short_segments_causal(out, min_len=8)  # P1-1 因果化
    direction = out["方向_合并后"].values
    n = len(out)
    post_n = np.zeros(n, dtype=int)
    counter = 0
    last_cross = None
    for i in range(n):
        d = direction[i]
        if d == "good":
            counter = 1
            last_cross = "good"
            post_n[i] = counter
        elif d == "bad":
            counter = -1
            last_cross = "bad"
            post_n[i] = counter
        elif d == "up" and last_cross == "good":
            counter += 1
            post_n[i] = counter
        elif d == "down" and last_cross == "bad":
            counter -= 1
            post_n[i] = counter
        else:
            counter = 0
            last_cross = None
    out["merged_post_cross_n"] = post_n
    return out


def prior_segment_stop(direction: np.ndarray, sma13: np.ndarray, i: int, is_long: bool) -> float:
    """Previous-segment SMA13 extreme, matching 30m2H build_pre_cross/build_cross."""
    k = i - 1
    while k >= 0 and direction[k] not in ("good", "bad"):
        k -= 1
    if k < 0:
        return float("nan")
    seg = sma13[k:i]
    seg = seg[~np.isnan(seg)]
    if len(seg) == 0:
        return float("nan")
    return float(np.nanmin(seg)) if is_long else float(np.nanmax(seg))


def build_three_opportunities(
    m30: pd.DataFrame,
    *,
    spec_lo: float,
    spec_hi: float,
    gap_thr: float = PRE_CROSS_GAP,
) -> pd.DataFrame:
    """pre_cross / cross / post_n(2-6) with entry at next M30 open.

    Stop rules (30m2H mainline):
      - pre_cross / cross: previous-segment SMA13 extreme
      - post_n: current bar SMA13
    Dedupe priority per signal bar + dir: pre_cross > cross > post_n.
    Planned exit: first opposite raw cross, next M30 open (or bar close).
    """
    out = add_m30_state(m30)
    direction = out["方向"].values.astype(object)
    direction_merged = out["方向_合并后"].values.astype(object)
    merged_post_n = out["merged_post_cross_n"].to_numpy()
    sma5 = out["SMA_5"].to_numpy()
    sma13 = out["SMA_13"].to_numpy()
    close = out["close"].to_numpy()
    high = out["high"].to_numpy()
    low = out["low"].to_numpy()
    n = len(out)

    def planned_exit(i: int, side: str) -> tuple[int, int] | None:
        opp = "bad" if side == "L" else "good"
        for j in range(i + 1, n):
            if direction[j] == opp:
                return (j, j + 1 if j + 1 < n else j)
        return None

    rows: list[dict] = []
    for i in range(1, n - 1):
        d = direction[i]
        if i + 1 >= n:
            continue
        if any(pd.isna(x) for x in (sma5[i], sma13[i], close[i])):
            continue
        # ---- cross ----
        if d in ("good", "bad"):
            is_long = d == "good"
            entry = float(out.iloc[i + 1]["open"])
            sl = prior_segment_stop(direction, sma13, i, is_long)
            if not math.isfinite(sl):
                continue
            if (is_long and sl >= entry) or ((not is_long) and sl <= entry):
                continue
            sd = abs(entry - sl)
            if not (spec_lo <= sd <= spec_hi):
                continue
            exit_plan = planned_exit(i, "L" if is_long else "S")
            if exit_plan is None:
                continue
            cross_idx, exit_idx = exit_plan
            rows.append(
                {
                    "signal_bar_idx": i,
                    "entry_bar_idx": i + 1,
                    "mode": "cross",
                    "dir": "L" if is_long else "S",
                    "signal_time": out.iloc[i]["bar_close_time"],
                    "entry_time": out.iloc[i + 1]["bar_open_time"],
                    "entry": round(entry, 3),
                    "stop": round(sl, 3),
                    "stop_source": "prev_segment_sma13_extreme",
                    "stop_distance": round(sd, 3),
                    "planned_cross_idx": cross_idx,
                    "planned_exit_idx": exit_idx,
                }
            )
            continue

        # ---- pre_cross ----
        if i - 1 >= 0 and not pd.isna(sma13[i - 1]) and not pd.isna(close[i - 1]):
            gap = abs(sma5[i] - sma13[i]) / sma13[i]
            long_setup = close[i - 1] <= sma13[i - 1] and close[i] > sma13[i] and sma5[i] < sma13[i]
            short_setup = close[i - 1] >= sma13[i - 1] and close[i] < sma13[i] and sma5[i] > sma13[i]
            if gap <= gap_thr and (long_setup or short_setup):
                is_long = long_setup
                entry = float(out.iloc[i + 1]["open"])
                sl = prior_segment_stop(direction, sma13, i, is_long)
                if math.isfinite(sl):
                    if (is_long and sl < entry) or ((not is_long) and sl > entry):
                        sd = abs(entry - sl)
                        if spec_lo <= sd <= spec_hi:
                            exit_plan = planned_exit(i, "L" if is_long else "S")
                            if exit_plan is not None:
                                cross_idx, exit_idx = exit_plan
                                rows.append(
                                    {
                                        "signal_bar_idx": i,
                                        "entry_bar_idx": i + 1,
                                        "mode": "pre_cross",
                                        "dir": "L" if is_long else "S",
                                        "signal_time": out.iloc[i]["bar_close_time"],
                                        "entry_time": out.iloc[i + 1]["bar_open_time"],
                                        "entry": round(entry, 3),
                                        "stop": round(sl, 3),
                                        "stop_source": "prev_segment_sma13_extreme",
                                        "stop_distance": round(sd, 3),
                                        "planned_cross_idx": cross_idx,
                                        "planned_exit_idx": exit_idx,
                                    }
                                )

        # ---- post_n ----
        pn = int(merged_post_n[i])
        if POST_N_MIN <= abs(pn) <= POST_N_MAX:
            is_long = pn > 0
            entry = float(out.iloc[i + 1]["open"])
            sl = float(sma13[i])
            if not math.isnan(sl):
                if (is_long and sl < entry) or ((not is_long) and sl > entry):
                    sd = abs(entry - sl)
                    if spec_lo <= sd <= spec_hi:
                        exit_plan = planned_exit(i, "L" if is_long else "S")
                        if exit_plan is not None:
                            cross_idx, exit_idx = exit_plan
                            rows.append(
                                {
                                    "signal_bar_idx": i,
                                    "entry_bar_idx": i + 1,
                                    "mode": f"post_n{abs(pn)}",
                                    "dir": "L" if is_long else "S",
                                    "signal_time": out.iloc[i]["bar_close_time"],
                                    "entry_time": out.iloc[i + 1]["bar_open_time"],
                                    "entry": round(entry, 3),
                                    "stop": round(sl, 3),
                                    "stop_source": "current_bar_sma13",
                                    "stop_distance": round(sd, 3),
                                    "planned_cross_idx": cross_idx,
                                    "planned_exit_idx": exit_idx,
                                }
                            )

    if not rows:
        return pd.DataFrame(
            columns=[
                "signal_bar_idx",
                "entry_bar_idx",
                "mode",
                "dir",
                "signal_time",
                "entry_time",
                "entry",
                "stop",
                "stop_source",
                "stop_distance",
                "planned_cross_idx",
                "planned_exit_idx",
            ]
        )
    tdf = pd.DataFrame(rows)
    priority = {"pre_cross": 0, "cross": 1}
    for n_ in range(POST_N_MIN, POST_N_MAX + 1):
        priority[f"post_n{n_}"] = 2
    tdf["_pri"] = tdf["mode"].map(priority).fillna(99)
    tdf = tdf.sort_values(["signal_bar_idx", "dir", "_pri"])
    tdf = tdf.drop_duplicates(subset=["signal_bar_idx", "dir"], keep="first")
    tdf = tdf.drop(columns=["_pri"]).reset_index(drop=True)
    tdf["signal_time"] = pd.to_datetime(tdf["signal_time"])
    tdf["entry_time"] = pd.to_datetime(tdf["entry_time"])
    return tdf


def replay_signals(signals: pd.DataFrame, m30: pd.DataFrame) -> pd.DataFrame:
    """Bar-by-bar replay: stop first, else planned opposite-cross exit."""
    rows = []
    for _, row in signals.iterrows():
        side = str(row["dir"])
        entry = float(row["entry"])
        stop = float(row["stop"])
        entry_idx = int(row["entry_bar_idx"])
        cross_idx = int(row["planned_cross_idx"])
        exit_idx = int(row["planned_exit_idx"])
        result = None
        for idx in range(entry_idx, exit_idx):
            bar = m30.iloc[idx]
            open_price = float(bar["open"])
            high = float(bar["high"])
            low = float(bar["low"])
            if side == "L":
                if open_price <= stop:
                    exit_price, reason = open_price, "stop_gap"
                elif low <= stop:
                    exit_price, reason = stop, "stop"
                else:
                    continue
                pnl = exit_price - entry
            else:
                if open_price >= stop:
                    exit_price, reason = open_price, "stop_gap"
                elif high >= stop:
                    exit_price, reason = stop, "stop"
                else:
                    continue
                pnl = entry - exit_price
            result = {
                "exit_time": bar["bar_open_time"],
                "exit": round(float(exit_price), 3),
                "exit_reason": reason,
                "pnl_points": round(float(pnl), 3),
                "holding_bars": idx - entry_idx + 1,
                "stop_hit": True,
            }
            break
        if result is None:
            exit_bar = m30.iloc[exit_idx]
            exit_price = float(exit_bar["close"]) if exit_idx == cross_idx else float(exit_bar["open"])
            pnl = (exit_price - entry) if side == "L" else (entry - exit_price)
            result = {
                "exit_time": exit_bar["bar_open_time"],
                "exit": round(exit_price, 3),
                "exit_reason": "opposite_cross_next_open",
                "pnl_points": round(float(pnl), 3),
                "holding_bars": max(0, exit_idx - entry_idx),
                "stop_hit": False,
            }
        rows.append(result)
    out = pd.concat([signals.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    out["pnl_usd_001"] = pd.to_numeric(out["pnl_points"], errors="coerce") * 100.0 * LOT_FOR_REPORT
    out["risk_r"] = pd.to_numeric(out["pnl_points"], errors="coerce") / pd.to_numeric(out["stop_distance"], errors="coerce")
    return out


def attach_side_extreme(trades: pd.DataFrame, h1_way: pd.DataFrame, h4: pd.DataFrame) -> pd.DataFrame:
    """Attach side-extreme pool features (with extra H4 bias5 column)."""
    from replay_raw_signals_with_stops import attach_context

    trades = attach_context(trades, h1_way, "1h")
    feats = side_extreme_features(trades, h1_way, h4)
    out = pd.concat([trades.reset_index(drop=True), feats], axis=1)
    h4_times = pd.to_datetime(h4["date"]).values.astype("datetime64[ns]")
    extreme_prices = pd.to_numeric(out["side_extreme_price"], errors="coerce")
    sma5_list = []
    for t in pd.to_datetime(out["entry_time"]):
        idx = bisect.bisect_right(h4_times, t.to_datetime64()) - 1
        if idx < 0:
            sma5_list.append(np.nan)
        else:
            sma5_list.append(float(h4.iloc[idx]["SMA_5"]) if not pd.isna(h4.iloc[idx]["SMA_5"]) else np.nan)
    sma5 = pd.Series(sma5_list, index=out.index)
    out["side_extreme_bias5_h4sma_pct"] = np.where(
        sma5.notna() & sma5.ne(0) & extreme_prices.notna(),
        (extreme_prices - sma5) / sma5 * 100.0,
        np.nan,
    )
    out["side_extreme_bias5_abs_pct"] = pd.to_numeric(out["side_extreme_bias5_h4sma_pct"], errors="coerce").abs()
    return out


def pool_mask(frame: pd.DataFrame, threshold55: float = BIAS55_THRESHOLD, threshold5: float | None = None) -> pd.Series:
    bias55 = pd.to_numeric(frame["side_extreme_bias55_h4sma_pct"], errors="coerce")
    side = frame["dir"].astype(str).str.upper()
    mask = (side.eq("S") & bias55.ge(threshold55)) | (side.eq("L") & bias55.le(-threshold55))
    if threshold5 is not None:
        bias5 = pd.to_numeric(frame["side_extreme_bias5_h4sma_pct"], errors="coerce")
        mask &= (side.eq("S") & bias5.ge(threshold5)) | (side.eq("L") & bias5.le(-threshold5))
    return mask


def summarize_trades(frame: pd.DataFrame, *, label: str, desc: str) -> dict:
    m = metric(frame["pnl_points"])
    test = split_test(frame, "pnl_points")
    pos_years, total_years = yearly_positive_count(frame, "pnl_points")
    side = frame["dir"].astype(str).str.upper()
    return {
        "label": label,
        "desc": desc,
        "n": m["n"],
        "long_n": int(side.eq("L").sum()) if len(frame) else 0,
        "short_n": int(side.eq("S").sum()) if len(frame) else 0,
        "wr": m["wr"],
        "pf": m["pf"],
        "ev": m["ev"],
        "pnl_points": m["pnl"],
        "pnl_usd_001": m["pnl"] * 100.0 * LOT_FOR_REPORT,
        "pnl_usd_dynamic": m["pnl"] * 100.0 * LOT_FOR_REPORT,
        "test_pf": test["test_pf"],
        "test_ev": test["test_ev"],
        "test_n": test["test_n"],
        "stop_hits": int(frame["stop_hit"].sum()) if len(frame) else 0,
        "stop_hit_rate": float(frame["stop_hit"].mean() * 100.0) if len(frame) else 0.0,
        "avg_stop": float(pd.to_numeric(frame["stop_distance"], errors="coerce").mean()) if len(frame) else 0.0,
        "positive_years": pos_years,
        "total_years": total_years,
    }


# --------------------------------------------------------------------------
# Variant B: three-stage exit replay (30m2H semantics)
# --------------------------------------------------------------------------
def first_opposite_idx(direction_merged: np.ndarray, i: int, is_long: bool) -> int:
    opp = "bad" if is_long else "good"
    for j in range(i + 1, len(direction_merged)):
        if direction_merged[j] == opp:
            return j
    return len(direction_merged) - 1


def stage1_exec(m30: pd.DataFrame, entry_idx: int, is_long: bool, entry: float, stop: float, r: float):
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


def stage2_exec(m30: pd.DataFrame, direction_merged: np.ndarray, entry_idx: int, is_long: bool, entry: float, stop: float, r: float):
    trail_start = entry + STAGE2_TRAIL_R * r if is_long else entry - STAGE2_TRAIL_R * r
    force = entry + STAGE2_FORCE_R * r if is_long else entry - STAGE2_FORCE_R * r
    trail_sl = stop
    m30_end = first_opposite_idx(direction_merged, entry_idx, is_long)
    for j in range(entry_idx, m30_end + 1):
        row = m30.iloc[j]
        if is_long:
            if row["high"] >= force:
                return STAGE2_FORCE_R * r, f"{STAGE2_FORCE_R:.1f}R forced", row["date"], force
            if row["low"] <= trail_sl:
                return trail_sl - entry, "trail/SL hit", row["date"], trail_sl
            if row["high"] >= trail_start and row["SMA_13"] > trail_sl:
                trail_sl = row["SMA_13"]
        else:
            if row["low"] <= force:
                return STAGE2_FORCE_R * r, f"{STAGE2_FORCE_R:.1f}R forced", row["date"], force
            if row["high"] >= trail_sl:
                return entry - trail_sl, "trail/SL hit", row["date"], trail_sl
            if row["low"] <= trail_start and (row["SMA_13"] < trail_sl or trail_sl == stop):
                trail_sl = row["SMA_13"]
    exit_price = m30.iloc[m30_end]["close"]
    pnl = (exit_price - entry) if is_long else (entry - exit_price)
    return pnl, "M30 merged cross", m30.iloc[m30_end]["date"], exit_price


def stage3_exec(m30: pd.DataFrame, direction_merged: np.ndarray, entry_idx: int, is_long: bool, entry: float, stop: float):
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


def replay_three_stage(m30: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    """Run 3-stage exit for each trade; return one row per stage."""
    direction_merged = m30["方向_合并后"].values.astype(object)
    rows = []
    for _, tr in trades.iterrows():
        entry_idx = int(tr["entry_bar_idx"])
        is_long = str(tr["dir"]).upper() == "L"
        entry = float(tr["entry"])
        stop = float(tr["stop"]) if "stop" in tr.index else float(tr["structural_stop_price"])
        r = abs(entry - stop)
        if r <= 0 or not math.isfinite(r):
            continue
        stages = [
            (1, stage1_exec(m30, entry_idx, is_long, entry, stop, r)),
            (2, stage2_exec(m30, direction_merged, entry_idx, is_long, entry, stop, r)),
            (3, stage3_exec(m30, direction_merged, entry_idx, is_long, entry, stop)),
        ]
        for stage, (pnl, reason, exit_time, exit_price) in stages:
            rows.append(
                {
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
                }
            )
    return pd.DataFrame(rows)


def weighted_stage_points(stage_frame: pd.DataFrame) -> pd.Series:
    units = dict(enumerate(STAGE_UNITS, start=1))
    return stage_frame["stage_pnl"].astype(float) * stage_frame["stage"].map(units)


def dynamic_lot(row: pd.Series) -> float:
    r = float(row["stop_distance"])
    if r <= 0 or not math.isfinite(r):
        return LOT_MIN
    risk_usd = START_CAPITAL * RISK_PCT / 100.0
    unit_lot = risk_usd / (sum(STAGE_UNITS) * r * USD_PER_POINT_PER_LOT)
    return float(np.clip(unit_lot, LOT_MIN, LOT_MAX))


def stage_dollars(stage_frame: pd.DataFrame) -> pd.Series:
    lots = stage_frame.apply(dynamic_lot, axis=1) * stage_frame["stage"].map(dict(enumerate(STAGE_UNITS, start=1)))
    return lots * stage_frame["stage_pnl"].astype(float) * USD_PER_POINT_PER_LOT


def per_trade_from_stages(st: pd.DataFrame) -> pd.DataFrame:
    """Aggregate a 3-stage ledger into one row per trade (index-safe)."""
    units = dict(enumerate(STAGE_UNITS, start=1))
    st = st.copy()
    st["_unit"] = st["stage"].map(units)
    st["_weighted"] = st["stage_pnl"].astype(float) * st["_unit"]
    st["_lot"] = st.apply(dynamic_lot, axis=1) * st["_unit"]
    st["_usd_dynamic"] = st["_lot"] * st["stage_pnl"].astype(float) * USD_PER_POINT_PER_LOT
    per = (
        st.groupby(["signal_time", "dir"], sort=False)
        .agg(
            entry=("entry", "first"),
            stop=("stop", "first"),
            stop_distance=("stop_distance", "first"),
            stage_pnl_sum=("stage_pnl", "sum"),
            stage_pnl_weighted=("_weighted", "sum"),
            pnl_usd_dynamic=("_usd_dynamic", "sum"),
            stages=("stage", "count"),
        )
        .reset_index()
    )
    return per


# --------------------------------------------------------------------------
# Variant C helpers
# --------------------------------------------------------------------------
def bias5_bucket(value: float) -> str:
    if not np.isfinite(value):
        return "nan"
    v = abs(value)
    edges = [0.2, 0.4, 0.6, 0.8, 1.0]
    if v < edges[0]:
        return "<0.2"
    for prev, cur in zip(edges, edges[1:]):
        if prev <= v < cur:
            return f"{prev:.1f}-{cur:.1f}"
    return ">=1.0"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest, m30, h1, contexts = load_frames()
    h4 = contexts["4H"]
    h1_way = add_h1_way_and_momentum(h1)
    m30_state = add_m30_state(m30)

    # ------------------------------------------------------------------
    # 0) Baseline reproduction
    # ------------------------------------------------------------------
    enriched = read_csv(ENRICHED_PATH)
    enriched["signal_time"] = pd.to_datetime(enriched["signal_time"])
    enriched["entry_time"] = pd.to_datetime(enriched["entry_time"])
    baseline = select_candidate(enriched, CURRENT_CANDIDATE).copy()
    base_m = metric(baseline["pnl_points"])
    print(f"[baseline] current candidate: n={base_m['n']} pf={base_m['pf']:.4f} "
          f"pnl_usd001={base_m['pnl'] * 100 * LOT_FOR_REPORT:.2f}")
    assert len(baseline) == 88, f"Baseline reproduction mismatch: expected 88, got {len(baseline)}"

    summary_rows = []
    summary_rows.append(
        summarize_trades(
            baseline,
            label="baseline_current_candidate",
            desc="当前候选 88 笔基线 (cross + H1 last6 + 8-28pt + pool + 质量过滤)",
        )
    )

    # ------------------------------------------------------------------
    # Variant A: three opportunities + previous-segment SMA13 extreme stop
    # ------------------------------------------------------------------
    va_rows = []
    for spec_name, spec in [("8_28", SPEC_8_28), ("5_35", SPEC_5_35)]:
        sig = build_three_opportunities(m30, spec_lo=spec[0], spec_hi=spec[1])
        replayed = replay_signals(sig, m30)
        enriched_a = attach_side_extreme(replayed, h1_way, h4)
        enriched_a["1h_bias5_signed_pct"] = pd.to_numeric(enriched_a["1h_bias5_signed_pct"], errors="coerce")
        enriched_a["1h_bias13_signed_pct"] = pd.to_numeric(enriched_a["1h_bias13_signed_pct"], errors="coerce")
        third = third_filter_mask(enriched_a)
        pool = pool_mask(enriched_a)
        va_rows.append(enriched_a)
        summary_rows.append(
            summarize_trades(
                enriched_a.loc[pool & third].copy(),
                label=f"variantA_three_opp_{spec_name}_pool_third",
                desc=f"A: 三机会 + 段SMA13极值止损 [{spec[0]:.0f}-{spec[1]:.0f}]pt + 机会池 + 1H bias5&13",
            )
        )
        # quality filters same as current candidate
        close_mom = pd.to_numeric(enriched_a["side_extreme_close_momentum_signed_pct"], errors="coerce")
        vol_way = pd.to_numeric(enriched_a["side_extreme_vol_way_s_way"], errors="coerce")
        short_side = enriched_a["dir"].astype(str).str.upper().eq("S")
        quality = close_mom.ge(-0.4) & ((~short_side) | vol_way.le(0.7))
        summary_rows.append(
            summarize_trades(
                enriched_a.loc[pool & third & quality].copy(),
                label=f"variantA_three_opp_{spec_name}_full",
                desc=f"A: 三机会 + 段SMA13极值止损 [{spec[0]:.0f}-{spec[1]:.0f}]pt + 完整1H过滤链",
            )
        )
    va_no_pool = va_rows[0].copy()
    summary_rows.append(
        summarize_trades(
            va_no_pool.loc[third_filter_mask(va_no_pool)].copy(),
            label="variantA_three_opp_8_28_no_pool_third",
            desc="A: 三机会 + 段SMA13极值止损 8-28pt + 1H bias5&13 (不加4H机会池)",
        )
    )
    all_va = pd.concat(va_rows, ignore_index=True)

    # ------------------------------------------------------------------
    # Variant B: three-stage exit + 5-35pt + 3% risk
    # ------------------------------------------------------------------
    def stage_frame_for(trades: pd.DataFrame) -> pd.DataFrame:
        return replay_three_stage(m30_state, trades)

    # B1: current 1H entry framework (cross + H1 last6 + pool + 1H bias5&13),
    #     with 5-35pt instead of 8-28pt, three-stage exit.
    b1_cfg_5_35 = {
        "entry_rule": "fixed_delay_1",
        "stop_variant": "h1_last6_hilo",
        "stop_lo": 5.0,
        "stop_hi": 35.0,
    }
    b1_cfg_8_28 = {
        "entry_rule": "fixed_delay_1",
        "stop_variant": "h1_last6_hilo",
        "stop_lo": 8.0,
        "stop_hi": 28.0,
    }
    for cfg, label in [(b1_cfg_5_35, "B1_5_35"), (b1_cfg_8_28, "B1_8_28")]:
        stop_distance = pd.to_numeric(enriched["stop_distance"], errors="coerce")
        mask = (
            enriched["entry_rule"].astype(str).eq(cfg["entry_rule"])
            & enriched["stop_variant"].astype(str).eq(cfg["stop_variant"])
            & stop_distance.between(cfg["stop_lo"], cfg["stop_hi"], inclusive="both")
            & third_filter_mask(enriched)
            & side_extreme_opportunity_mask(enriched)
        )
        trades = enriched.loc[mask].copy().reset_index(drop=True)
        trades["entry_bar_idx"] = pd.to_numeric(trades["entry_bar_idx"], errors="coerce").astype(int)
        st = stage_frame_for(trades)
        per_trade = per_trade_from_stages(st)
        m2 = metric(per_trade["stage_pnl_weighted"])
        test2 = split_test(per_trade, "stage_pnl_weighted")
        pos_years, total_years = yearly_positive_count(per_trade, "stage_pnl_weighted")
        summary_rows.append(
            {
                "label": label,
                "desc": f"B: 三段退出(2.0R/1.5R trail+4.0R/合并段反向) [{cfg['stop_lo']:.0f}-{cfg['stop_hi']:.0f}]pt + 3%风险动态手数",
                "n": m2["n"],
                "long_n": int((per_trade["dir"].astype(str).str.upper() == "L").sum()),
                "short_n": int((per_trade["dir"].astype(str).str.upper() == "S").sum()),
                "wr": m2["wr"],
                "pf": m2["pf"],
                "ev": m2["ev"],
                "pnl_points": m2["pnl"],
                "pnl_usd_001": float(per_trade["pnl_usd_dynamic"].sum()),
                "pnl_usd_dynamic": float(per_trade["pnl_usd_dynamic"].sum()),
                "test_pf": test2["test_pf"],
                "test_ev": test2["test_ev"],
                "test_n": test2["test_n"],
                "stop_hits": int((per_trade["stage_pnl_sum"] < 0).sum()),
                "stop_hit_rate": float((per_trade["stage_pnl_sum"] < 0).mean() * 100.0) if len(per_trade) else 0.0,
                "avg_stop": float(pd.to_numeric(per_trade["stop_distance"], errors="coerce").mean()) if len(per_trade) else 0.0,
                "positive_years": pos_years,
                "total_years": total_years,
            }
        )
        st.to_csv(OUT_DIR / f"{label}_stage_ledger.csv", index=False, encoding="utf-8-sig")

    # B2: three-stage exit on variant A entries (5-35pt)
    trades_a = va_rows[1].loc[pool_mask(va_rows[1]) & third_filter_mask(va_rows[1])].copy().reset_index(drop=True)
    trades_a["entry_bar_idx"] = pd.to_numeric(trades_a["entry_bar_idx"], errors="coerce").astype(int)
    st_a = stage_frame_for(trades_a)
    per_trade_a = per_trade_from_stages(st_a)
    m_a = metric(per_trade_a["stage_pnl_weighted"])
    test_a = split_test(per_trade_a, "stage_pnl_weighted")
    pos_years_a, total_years_a = yearly_positive_count(per_trade_a, "stage_pnl_weighted")
    summary_rows.append(
        {
            "label": "B2_three_opp_5_35",
            "desc": "B: 三段退出应用于A的三机会入场 (5-35pt) + 3%风险动态手数",
            "n": m_a["n"],
            "long_n": int((per_trade_a["dir"].astype(str).str.upper() == "L").sum()),
            "short_n": int((per_trade_a["dir"].astype(str).str.upper() == "S").sum()),
            "wr": m_a["wr"],
            "pf": m_a["pf"],
            "ev": m_a["ev"],
            "pnl_points": m_a["pnl"],
            "pnl_usd_001": float(per_trade_a["pnl_usd_dynamic"].sum()),
            "pnl_usd_dynamic": float(per_trade_a["pnl_usd_dynamic"].sum()),
            "test_pf": test_a["test_pf"],
            "test_ev": test_a["test_ev"],
            "test_n": test_a["test_n"],
            "stop_hits": int((per_trade_a["stage_pnl_sum"] < 0).sum()),
            "stop_hit_rate": float((per_trade_a["stage_pnl_sum"] < 0).mean() * 100.0) if len(per_trade_a) else 0.0,
            "avg_stop": float(pd.to_numeric(per_trade_a["stop_distance"], errors="coerce").mean()) if len(per_trade_a) else 0.0,
            "positive_years": pos_years_a,
            "total_years": total_years_a,
        }
    )
    st_a.to_csv(OUT_DIR / "B2_three_opp_5_35_stage_ledger.csv", index=False, encoding="utf-8-sig")

    # ------------------------------------------------------------------
    # Variant C: H4 bias55 + bias5 same-direction scan
    # ------------------------------------------------------------------
    base_c_trades = select_candidate(enriched, BASE_CANDIDATE).copy()
    bias5 = pd.to_numeric(base_c_trades["4h_sma5"], errors="coerce")
    extreme = pd.to_numeric(base_c_trades["side_extreme_price"], errors="coerce")
    base_c_trades["side_extreme_bias5_h4sma_pct"] = np.where(
        bias5.notna() & bias5.ne(0) & extreme.notna(),
        (extreme - bias5) / bias5 * 100.0,
        np.nan,
    )
    base_c_trades["side_extreme_bias5_abs_pct"] = pd.to_numeric(
        base_c_trades["side_extreme_bias5_h4sma_pct"], errors="coerce"
    ).abs()
    base_c_trades["bias5_bucket"] = base_c_trades["side_extreme_bias5_abs_pct"].map(bias5_bucket)

    bucket_rows = []
    ordered_buckets = ["<0.2", "0.2-0.4", "0.4-0.6", "0.6-0.8", "0.8-1.0", ">=1.0"]
    bucket_rows.append(summarize_trades(base_c_trades, label="C_bias5_all", desc="C: 机会池全体 (bias55>=2%)"))
    for bucket in ordered_buckets:
        scoped = base_c_trades.loc[base_c_trades["bias5_bucket"].eq(bucket)].copy()
        bucket_rows.append(
            summarize_trades(scoped, label=f"C_bias5_{bucket.replace('.', '_').replace('<', 'lt').replace('>=', 'ge')}",
                             desc=f"C: 机会池 + |H4 bias5| {bucket}%")
        )
    bucket_df = pd.DataFrame(bucket_rows)

    combo_rows = []
    for t55 in [1.5, 2.0, 2.5, 3.0]:
        for t5 in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
            mask = pool_mask(base_c_trades, threshold55=t55, threshold5=t5)
            scoped = base_c_trades.loc[mask].copy()
            combo_rows.append(
                summarize_trades(
                    scoped,
                    label=f"C_bias55_{t55:.1f}_bias5_{t5:.1f}",
                    desc=f"C: bias55>={t55:.1f}% 且 bias5>={t5:.1f}% 同向",
                )
            )
    combo_df = pd.DataFrame(combo_rows)

    # ------------------------------------------------------------------
    # Write outputs
    # ------------------------------------------------------------------
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT_DIR / "variant_summary.csv", index=False, encoding="utf-8-sig")
    bucket_df.to_csv(OUT_DIR / "variantC_bias5_buckets.csv", index=False, encoding="utf-8-sig")
    combo_df.to_csv(OUT_DIR / "variantC_bias55_bias5_combo.csv", index=False, encoding="utf-8-sig")
    all_va.to_csv(OUT_DIR / "variantA_all_trades.csv", index=False, encoding="utf-8-sig")

    cols = [
        "label", "n", "long_n", "short_n", "wr", "pf", "ev", "pnl_points",
        "pnl_usd_001", "pnl_usd_dynamic", "test_pf", "test_ev", "test_n", "stop_hits",
        "stop_hit_rate", "avg_stop", "positive_years", "total_years", "desc",
    ]
    lines = [
        "# 1H_M30_4H 变体实验（2026-08-13）",
        "",
        "> 数据：策略自有 MT5 原始历史 2020-01 ~ 2023-12；收益为 0.01 lot 口径 points×100，未扣点差/滑点/手续费。",
        "",
        "## 总览",
        "",
        markdown_table(summary[cols], cols, money_cols={"pnl_usd_001", "pnl_usd_dynamic"}),
        "",
        "## 变体C：H4 bias5 分桶（bias55>=2.0% 机会池内）",
        "",
        markdown_table(bucket_df[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## 变体C：bias55 × bias5 同向双阈值扫描",
        "",
        markdown_table(combo_df[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## 输出文件",
        "",
        "- `variant_summary.csv`",
        "- `variantA_all_trades.csv`",
        "- `variantC_bias5_buckets.csv`",
        "- `variantC_bias55_bias5_combo.csv`",
        "- `B1_5_35_stage_ledger.csv` / `B1_8_28_stage_ledger.csv` / `B2_three_opp_5_35_stage_ledger.csv`",
    ]
    report = "\n".join(lines) + "\n"
    (OUT_DIR / "experiment_report.md").write_text(report, encoding="utf-8")
    print(f"\nWrote report: {OUT_DIR / 'experiment_report.md'}")


if __name__ == "__main__":
    main()
