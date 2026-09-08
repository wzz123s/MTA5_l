# -*- coding: utf-8 -*-
"""Scan extreme-bar way_s_way and momentum filters for 1H_M30_4H."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_ROOT = _Path(r"F:\use_code\MTA5_l")
for _p in [_ROOT / "scripts", _ROOT / "黄金" / "30m2H策略" / "参考实现工程", *_ROOT.glob("*/scripts"), *_ROOT.glob("*/scripts/*"), *_ROOT.glob("黄金/*/scripts"), *_ROOT.glob("黄金/*/scripts/*"), *_ROOT.glob("原油/*/scripts"), *_ROOT.glob("原油/*/scripts/*")]:
    _s = str(_p)
    if _s not in _sys.path:
        _sys.path.insert(0, _s)



import bisect
from pathlib import Path

import numpy as np
import pandas as pd

from replay_raw_signals_with_stops import (
    LOT_FOR_REPORT,
    ROOT,
    markdown_table,
    metric,
    split_test,
    trade_sign,
    yearly_positive_count,
)
from replay_1h_bias55_h1_stop_optimization import load_frames


STRATEGY = "1H_M30_4H"
IN_PATH = ROOT / "黄金" / f"{STRATEGY}策略" / "data" / "validation" / "hybrid_entry_stop" / "hybrid_entry_all_trades.csv"
OUT_DIR = ROOT / "黄金" / f"{STRATEGY}策略" / "data" / "validation" / "way_momentum_filter"
MIN_SAMPLE = 30
BIAS55_THRESHOLD = 2.0


BASE_CANDIDATES = [
    {
        "candidate": "fd1_h1last6_8_28",
        "desc": "fixed_delay_1 + h1_last6_hilo + 8-28pt + 1H bias5&bias13",
        "entry_rule": "fixed_delay_1",
        "stop_variant": "h1_last6_hilo",
        "stop_lo": 8.0,
        "stop_hi": 28.0,
    },
    {
        "candidate": "fd1_h1last6_6_28",
        "desc": "fixed_delay_1 + h1_last6_hilo + 6-28pt + 1H bias5&bias13",
        "entry_rule": "fixed_delay_1",
        "stop_variant": "h1_last6_hilo",
        "stop_lo": 6.0,
        "stop_hi": 28.0,
    },
    {
        "candidate": "fd3_m30sma13_6_28",
        "desc": "fixed_delay_3 + M30 SMA13 + 6-28pt + 1H bias5&bias13",
        "entry_rule": "fixed_delay_3",
        "stop_variant": "m30_entry_prev_closed_sma13",
        "stop_lo": 6.0,
        "stop_hi": 28.0,
    },
]


WAY_THRESHOLDS = [round(x / 10.0, 1) for x in range(0, 11)]
WAY_COMBO_THRESHOLDS = [0.2, 0.4, 0.6, 0.8]
MOM_THRESHOLDS = [round(x / 10.0, 1) for x in range(-6, 7, 2)]
MOM_COMBO_THRESHOLDS = [-0.4, -0.2, 0.0, 0.2, 0.4]


def read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def mark_direction(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    valid = out["SMA_13"].notna() & out["SMA_5"].notna()
    out["方向"] = None
    scoped = out.loc[valid].copy()
    if scoped.empty:
        out["方向_合并后"] = out["方向"]
        return out
    gt = scoped["SMA_5"] > scoped["SMA_13"]
    prev = gt.shift(1, fill_value=False)
    scoped["方向"] = np.select(
        [gt & ~prev, ~gt & prev, gt & prev, ~gt & ~prev],
        ["good", "bad", "up", "down"],
        default=None,
    )
    first_idx = scoped.index[0]
    scoped.loc[first_idx, "方向"] = "up" if bool(gt.loc[first_idx]) else "down"
    out.loc[scoped.index, "方向"] = scoped["方向"]
    return out


def filter_short_segments(frame: pd.DataFrame, min_len: int = 8) -> pd.DataFrame:
    out = frame.copy()
    direction = out["方向"].values.astype(object)
    n = len(out)
    good_pos_all = np.where(direction == "good")[0]
    bad_pos_all = np.where(direction == "bad")[0]
    all_crossings = sorted([(int(p), "good") for p in good_pos_all] + [(int(p), "bad") for p in bad_pos_all])
    if not all_crossings:
        out["方向_合并后"] = direction
        return out

    _, first_type = all_crossings[0]
    state = "down" if first_type == "good" else "up"
    i = 0
    while i < len(all_crossings):
        pos, type_ = all_crossings[i]
        if i + 1 >= len(all_crossings):
            break
        next_pos, _ = all_crossings[i + 1]
        region = direction[pos + 1 : next_pos] if pos + 1 < next_pos else np.array([], dtype=object)
        region_count = int(np.sum(region == ("up" if type_ == "good" else "down")))
        if region_count < min_len:
            direction[pos] = state
            for k in range(pos + 1, next_pos):
                direction[k] = state
            direction[next_pos] = state
            all_crossings.pop(i + 1)
            all_crossings.pop(i)
        else:
            state = "up" if type_ == "good" else "down"
            i += 1
    out["方向_合并后"] = direction
    return out


def filter_short_segments_causal(frame: pd.DataFrame, min_len: int = 8) -> pd.DataFrame:
    """因果版短段合并：逐 bar 前缀，末穿越保留，段内 bar 不改写（与 EA BuildMergedCodes 逐 bar 语义一致）。

    与 filter_short_segments(全序列未来回溯) 的区别：
      - 全序列版用"未来穿越"回溯吸收短段(lookahead)，回测数字与实盘 EA 不可比。
      - 因果版每个 bar 的"方向_合并后"= 截至该 bar 窗口的合并结果(末穿越保留)，与 EA 逐 bar 一致。
    """
    out = frame.copy()
    direction = out["方向"].values.astype(object)
    n = len(out)
    raw = np.zeros(n, dtype=int)
    raw[direction == "good"] = 2
    raw[direction == "bad"] = -2
    raw[direction == "up"] = 1
    raw[direction == "down"] = -1
    merged = raw.copy()
    stack = []
    state = None
    for i in range(n):
        d = raw[i]
        if abs(d) == 2:
            if state is None:
                state = -1 if d == 2 else 1
            if stack:
                prev = stack[-1]
                typ = raw[prev]
                rc = 0
                for k in range(prev + 1, i):
                    if (typ == 2 and raw[k] == 1) or (typ == -2 and raw[k] == -1):
                        rc += 1
                if rc < min_len:
                    merged[i] = state  # 当前穿越点被前一个短段吸收
                    stack.pop()       # 前一个也吸收(不改写历史 merged)
                else:
                    merged[i] = raw[i]  # 保留
                    state = 1 if typ == 2 else -1
                    stack.pop()
                    stack.append(i)
            else:
                merged[i] = raw[i]
                stack.append(i)
    code_to_dir = {2: "good", -2: "bad", 1: "up", -1: "down", 0: ""}
    out["方向_合并后"] = np.array([code_to_dir.get(m, "") for m in merged], dtype=object)
    return out


def add_way_grade(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    direction = out["方向_合并后"].values if "方向_合并后" in out.columns else out["方向"].values
    sma13 = pd.to_numeric(out["SMA_13"], errors="coerce").to_numpy()
    low = pd.to_numeric(out["low"], errors="coerce").to_numpy()
    high = pd.to_numeric(out["high"], errors="coerce").to_numpy()
    vol = pd.to_numeric(out["volume"], errors="coerce").fillna(0).to_numpy()
    vol_ma = pd.to_numeric(out["vol_ma_120"], errors="coerce").fillna(0).to_numpy()

    way = np.zeros(len(out))
    way_s = np.zeros(len(out))
    way_s_way = np.zeros(len(out))
    vol_way = np.zeros(len(out))
    vol_way_s_way = np.zeros(len(out))
    y = x = z = 0
    prev_d = None
    for i, d in enumerate(direction):
        if d in ("good", "bad"):
            y = x = z = 0
            wsw = 0.0
            vwsw = 0.0
        elif d == "up":
            if prev_d == "up":
                y += 1
                if low[i] >= sma13[i] and high[i] >= high[i - 1]:
                    x += 1
                if vol[i] <= vol_ma[i]:
                    z += 1
            else:
                y = 1
                x = 1
                z = 1 if vol[i] <= vol_ma[i] else 0
            wsw = round(x / y, 2) if y else 0.0
            vwsw = round(z / y, 2) if y else 0.0
        elif d == "down":
            if prev_d == "down":
                y -= 1
                if high[i] <= sma13[i] and low[i] <= low[i - 1]:
                    x -= 1
                if vol[i] <= vol_ma[i]:
                    z -= 1
            else:
                y = -1
                x = -1
                z = -1 if vol[i] <= vol_ma[i] else 0
            wsw = round(x / y, 2) if y else 0.0
            vwsw = round(z / y, 2) if y else 0.0
        else:
            wsw = 0.0
            vwsw = 0.0
        way[i] = y
        way_s[i] = x
        way_s_way[i] = wsw
        vol_way[i] = z
        vol_way_s_way[i] = vwsw
        prev_d = d

    out["way"] = way
    out["way_s"] = way_s
    out["way_s_way"] = way_s_way
    out["vol_way"] = vol_way
    out["vol_way_s_way"] = vol_way_s_way
    return out


def add_h1_way_and_momentum(h1: pd.DataFrame) -> pd.DataFrame:
    out = h1.copy().sort_values("date").reset_index(drop=True)
    out["vol_ma_120"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0).rolling(120, min_periods=1).mean()
    out = add_way_grade(filter_short_segments_causal(mark_direction(out), min_len=8))  # P1-1 因果化(消除 lookahead)
    rng = (pd.to_numeric(out["high"], errors="coerce") - pd.to_numeric(out["low"], errors="coerce")).replace(0, np.nan)
    out["body_momentum"] = (pd.to_numeric(out["close"], errors="coerce") - pd.to_numeric(out["open"], errors="coerce")) / rng
    out["close_momentum_pct"] = pd.to_numeric(out["close"], errors="coerce").pct_change() * 100.0
    gap = pd.to_numeric(out["close"], errors="coerce") - pd.to_numeric(out["SMA_13"], errors="coerce")
    out["sma13_gap_momentum_pct"] = gap.diff() / pd.to_numeric(out["SMA_13"], errors="coerce") * 100.0
    return out


def side_extreme_features(trades: pd.DataFrame, h1: pd.DataFrame, h4: pd.DataFrame) -> pd.DataFrame:
    h1_times = pd.to_datetime(h1["date"]).values.astype("datetime64[ns]")
    h4_times = pd.to_datetime(h4["date"]).values.astype("datetime64[ns]")
    rows: list[dict] = []
    for _, trade in trades.iterrows():
        t = pd.Timestamp(trade["entry_time"]).to_datetime64()
        side = str(trade["dir"]).upper()
        sign = trade_sign(side)
        h1_idx = bisect.bisect_right(h1_times, t) - 1
        h4_idx = bisect.bisect_right(h4_times, t) - 1
        if h1_idx < 0 or h4_idx < 0:
            rows.append({})
            continue
        window = h1.iloc[max(0, h1_idx - 3) : h1_idx + 1].copy()
        if window.empty:
            rows.append({})
            continue
        if side == "S":
            extreme_idx = pd.to_numeric(window["high"], errors="coerce").idxmax()
            extreme_price = float(window.loc[extreme_idx, "high"])
            extreme_kind = "high"
        else:
            extreme_idx = pd.to_numeric(window["low"], errors="coerce").idxmin()
            extreme_price = float(window.loc[extreme_idx, "low"])
            extreme_kind = "low"
        h4_sma55 = float(h4.iloc[h4_idx]["SMA_55"]) if not pd.isna(h4.iloc[h4_idx]["SMA_55"]) else np.nan
        row = h1.loc[extreme_idx]
        bias55 = (extreme_price - h4_sma55) / h4_sma55 * 100.0 if np.isfinite(h4_sma55) and h4_sma55 != 0 else np.nan
        body = float(row["body_momentum"]) if not pd.isna(row["body_momentum"]) else np.nan
        close_mom = float(row["close_momentum_pct"]) if not pd.isna(row["close_momentum_pct"]) else np.nan
        gap_mom = float(row["sma13_gap_momentum_pct"]) if not pd.isna(row["sma13_gap_momentum_pct"]) else np.nan
        rows.append(
            {
                "side_extreme_kind": extreme_kind,
                "side_extreme_time": row["date"],
                "side_extreme_price": extreme_price,
                "side_extreme_bias55_h4sma_pct": bias55,
                "side_extreme_way_s_way": float(row["way_s_way"]) if not pd.isna(row["way_s_way"]) else np.nan,
                "side_extreme_way": float(row["way"]) if not pd.isna(row["way"]) else np.nan,
                "side_extreme_vol_way_s_way": float(row["vol_way_s_way"]) if not pd.isna(row["vol_way_s_way"]) else np.nan,
                "side_extreme_body_momentum": body,
                "side_extreme_close_momentum_signed_pct": sign * close_mom if sign else np.nan,
                "side_extreme_body_momentum_signed": sign * body if sign else np.nan,
                "side_extreme_sma13_gap_momentum_signed_pct": sign * gap_mom if sign else np.nan,
                "side_extreme_h1_direction": row["方向_合并后"],
            }
        )
    return pd.DataFrame(rows)


def side_extreme_opportunity_mask(frame: pd.DataFrame) -> pd.Series:
    bias = pd.to_numeric(frame["side_extreme_bias55_h4sma_pct"], errors="coerce")
    side = frame["dir"].astype(str).str.upper()
    return (side.eq("S") & bias.ge(BIAS55_THRESHOLD)) | (side.eq("L") & bias.le(-BIAS55_THRESHOLD))


def legacy_high_opportunity_mask(frame: pd.DataFrame) -> pd.Series:
    bias = pd.to_numeric(frame["h1roll4_high_bias55_h4sma_pct"], errors="coerce")
    side = frame["dir"].astype(str).str.upper()
    return (side.eq("S") & bias.ge(BIAS55_THRESHOLD)) | (side.eq("L") & bias.le(-BIAS55_THRESHOLD))


def third_filter_mask(frame: pd.DataFrame) -> pd.Series:
    return pd.to_numeric(frame["1h_bias5_signed_pct"], errors="coerce").gt(0) & pd.to_numeric(
        frame["1h_bias13_signed_pct"], errors="coerce"
    ).gt(0)


def candidate_mask(frame: pd.DataFrame, cfg: dict) -> pd.Series:
    stop_distance = pd.to_numeric(frame["stop_distance"], errors="coerce")
    return (
        frame["entry_rule"].astype(str).eq(str(cfg["entry_rule"]))
        & frame["stop_variant"].astype(str).eq(str(cfg["stop_variant"]))
        & stop_distance.between(float(cfg["stop_lo"]), float(cfg["stop_hi"]), inclusive="both")
        & third_filter_mask(frame)
    )


def summarize(frame: pd.DataFrame, *, candidate: str, desc: str, pool: str, filter_name: str, filter_desc: str) -> dict:
    m = metric(frame["pnl_points"])
    test = split_test(frame, "pnl_points")
    pos_years, total_years = yearly_positive_count(frame, "pnl_points")
    side = frame["dir"].astype(str).str.upper() if len(frame) else pd.Series(dtype=str)
    return {
        "candidate": candidate,
        "desc": desc,
        "pool": pool,
        "filter_name": filter_name,
        "filter_desc": filter_desc,
        "n": m["n"],
        "long_n": int(side.eq("L").sum()) if len(frame) else 0,
        "short_n": int(side.eq("S").sum()) if len(frame) else 0,
        "pf": m["pf"],
        "test_pf": test["test_pf"],
        "ev_points": m["ev"],
        "pnl_points": m["pnl"],
        "pnl_usd_001": m["pnl"] * 100.0 * LOT_FOR_REPORT,
        "stop_hits": int(frame["stop_hit"].sum()) if len(frame) else 0,
        "stop_hit_rate_pct": float(frame["stop_hit"].mean() * 100.0) if len(frame) else 0.0,
        "avg_way_s_way": float(pd.to_numeric(frame["side_extreme_way_s_way"], errors="coerce").mean()) if len(frame) else 0.0,
        "avg_body_momentum_signed": float(pd.to_numeric(frame["side_extreme_body_momentum_signed"], errors="coerce").mean()) if len(frame) else 0.0,
        "avg_close_momentum_signed_pct": float(pd.to_numeric(frame["side_extreme_close_momentum_signed_pct"], errors="coerce").mean())
        if len(frame)
        else 0.0,
        "positive_years": pos_years,
        "total_years": total_years,
        "sample_status": "ok" if m["n"] >= MIN_SAMPLE else "insufficient",
    }


def score(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    out = frame.copy()
    out["sample_ok"] = out["n"].astype(float).ge(MIN_SAMPLE)
    out["quality_ok"] = (
        out["sample_ok"]
        & out["pf"].astype(float).gt(1.0)
        & out["test_pf"].astype(float).gt(1.0)
        & out["pnl_usd_001"].astype(float).gt(0.0)
    )
    out["score"] = np.where(
        out["quality_ok"],
        1000.0
        + out["pnl_usd_001"].astype(float) * 0.025
        + out["test_pf"].astype(float).clip(upper=10) * 14.0
        + out["pf"].astype(float).clip(upper=10) * 9.0
        + out["positive_years"].astype(float) * 5.0
        + out["n"].astype(float).clip(upper=200) * 0.015,
        out["n"].astype(float) + out["pnl_usd_001"].astype(float) * 0.005,
    )
    return out.sort_values(["score", "pnl_usd_001", "test_pf", "pf", "n"], ascending=[False, False, False, False, False]).reset_index(drop=True)


def add_filter_rows(rows: list[dict], frame: pd.DataFrame, *, cfg: dict, pool: str) -> None:
    candidate = str(cfg["candidate"])
    desc = str(cfg["desc"])
    rows.append(summarize(frame, candidate=candidate, desc=desc, pool=pool, filter_name="baseline", filter_desc="no extra filter"))

    way = pd.to_numeric(frame["side_extreme_way_s_way"], errors="coerce")
    body = pd.to_numeric(frame["side_extreme_body_momentum_signed"], errors="coerce")
    close_mom = pd.to_numeric(frame["side_extreme_close_momentum_signed_pct"], errors="coerce")
    gap_mom = pd.to_numeric(frame["side_extreme_sma13_gap_momentum_signed_pct"], errors="coerce")

    for threshold in WAY_THRESHOLDS:
        rows.append(
            summarize(
                frame.loc[way.ge(threshold)].copy(),
                candidate=candidate,
                desc=desc,
                pool=pool,
                filter_name=f"way_ge_{threshold:.1f}",
                filter_desc=f"side extreme way_s_way >= {threshold:.1f}",
            )
        )
        rows.append(
            summarize(
                frame.loc[way.le(threshold)].copy(),
                candidate=candidate,
                desc=desc,
                pool=pool,
                filter_name=f"way_le_{threshold:.1f}",
                filter_desc=f"side extreme way_s_way <= {threshold:.1f}",
            )
        )

    for col_name, values, label in [
        ("body", body, "body momentum signed"),
        ("close", close_mom, "close momentum signed pct"),
        ("gap", gap_mom, "SMA13 gap momentum signed pct"),
    ]:
        for threshold in MOM_THRESHOLDS:
            rows.append(
                summarize(
                    frame.loc[values.ge(threshold)].copy(),
                    candidate=candidate,
                    desc=desc,
                    pool=pool,
                    filter_name=f"{col_name}_mom_ge_{threshold:.1f}",
                    filter_desc=f"{label} >= {threshold:.1f}",
                )
            )
            rows.append(
                summarize(
                    frame.loc[values.le(threshold)].copy(),
                    candidate=candidate,
                    desc=desc,
                    pool=pool,
                    filter_name=f"{col_name}_mom_le_{threshold:.1f}",
                    filter_desc=f"{label} <= {threshold:.1f}",
                )
            )

    for way_thr in WAY_COMBO_THRESHOLDS:
        for mom_thr in MOM_COMBO_THRESHOLDS:
            rows.append(
                summarize(
                    frame.loc[way.ge(way_thr) & body.ge(mom_thr)].copy(),
                    candidate=candidate,
                    desc=desc,
                    pool=pool,
                    filter_name=f"way_ge_{way_thr:.1f}__body_ge_{mom_thr:.1f}",
                    filter_desc=f"way_s_way >= {way_thr:.1f} and body momentum >= {mom_thr:.1f}",
                )
            )
            rows.append(
                summarize(
                    frame.loc[way.ge(way_thr) & body.le(mom_thr)].copy(),
                    candidate=candidate,
                    desc=desc,
                    pool=pool,
                    filter_name=f"way_ge_{way_thr:.1f}__body_le_{mom_thr:.1f}",
                    filter_desc=f"way_s_way >= {way_thr:.1f} and body momentum <= {mom_thr:.1f}",
                )
            )


def scan(enriched: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    baseline_rows: list[dict] = []
    filter_rows: list[dict] = []
    pools = [
        ("legacy_high_pool", legacy_high_opportunity_mask(enriched)),
        ("side_extreme_pool", side_extreme_opportunity_mask(enriched)),
    ]
    for cfg in BASE_CANDIDATES:
        base_mask = candidate_mask(enriched, cfg)
        for pool_name, pool_mask in pools:
            scoped = enriched.loc[base_mask & pool_mask].copy()
            baseline_rows.append(
                summarize(
                    scoped,
                    candidate=str(cfg["candidate"]),
                    desc=str(cfg["desc"]),
                    pool=pool_name,
                    filter_name="baseline",
                    filter_desc="candidate baseline after opportunity pool",
                )
            )
            add_filter_rows(filter_rows, scoped, cfg=cfg, pool=pool_name)
    return score(pd.DataFrame(baseline_rows)), score(pd.DataFrame(filter_rows))


def write_report(baseline: pd.DataFrame, filters: pd.DataFrame) -> None:
    cols = [
        "candidate",
        "pool",
        "filter_name",
        "n",
        "long_n",
        "short_n",
        "pf",
        "test_pf",
        "pnl_usd_001",
        "avg_way_s_way",
        "avg_body_momentum_signed",
        "positive_years",
        "total_years",
        "sample_status",
    ]
    quality = filters.loc[filters.get("quality_ok", pd.Series(False, index=filters.index)).astype(bool)].copy()
    pnl_top = quality.sort_values(["pnl_usd_001", "pf", "test_pf", "n"], ascending=[False, False, False, False]).head(25)
    lines = [
        "# 1H_M30_4H extreme way_s_way and momentum filter scan",
        "",
        "Date: 2026-07-25",
        "",
        "## Rules",
        "",
        "- Rebuild `way_s_way` from this strategy's own MT5 H1 bars.",
        "- Short side uses the H1 bar with the highest high in the last four closed H1 bars.",
        "- Long side uses the H1 bar with the lowest low in the last four closed H1 bars.",
        "- `side_extreme_way_s_way` is taken from that exact high/low bar.",
        "- Momentum controls: signed candle body, signed close-to-close momentum, and signed SMA13-gap momentum.",
        "- Report PnL uses `pnl_points * 100 * 0.01 lot`; spread, slippage, and commission are not deducted.",
        "",
        "## Candidate Baselines",
        "",
        markdown_table(baseline[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## Filter Top By Score",
        "",
        markdown_table(quality.head(30)[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## Filter Top By Actual PnL",
        "",
        markdown_table(pnl_top[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## Output Files",
        "",
        "- `way_momentum_enriched_trades.csv`",
        "- `way_momentum_baseline_summary.csv`",
        "- `way_momentum_filter_summary.csv`",
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = "\n".join(lines) + "\n"
    (OUT_DIR / "way_momentum_filter_report.md").write_text(report, encoding="utf-8")
    (ROOT / "1H_M30_4H极值way动能过滤测试记录.md").write_text(report, encoding="utf-8")


def main() -> None:
    _, _, h1, contexts = load_frames()
    h4 = contexts["4H"]
    h1_way = add_h1_way_and_momentum(h1)
    trades = read_csv(IN_PATH)
    trades["signal_time"] = pd.to_datetime(trades["signal_time"])
    trades["entry_time"] = pd.to_datetime(trades["entry_time"])
    features = side_extreme_features(trades, h1_way, h4)
    enriched = pd.concat([trades.reset_index(drop=True), features], axis=1)
    baseline, filters = scan(enriched)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    enriched.to_csv(OUT_DIR / "way_momentum_enriched_trades.csv", index=False, encoding="utf-8-sig")
    baseline.to_csv(OUT_DIR / "way_momentum_baseline_summary.csv", index=False, encoding="utf-8-sig")
    filters.to_csv(OUT_DIR / "way_momentum_filter_summary.csv", index=False, encoding="utf-8-sig")
    write_report(baseline, filters)

    print(f"{STRATEGY}: extreme way_s_way + momentum filter scan")
    for _, row in baseline.iterrows():
        print(
            f"  base {row['candidate']} pool={row['pool']} n={int(row['n'])} "
            f"pf={float(row['pf']):.4f} test_pf={float(row['test_pf']):.4f} "
            f"usd001={float(row['pnl_usd_001']):.2f}"
        )
    quality = filters.loc[filters["quality_ok"].astype(bool)] if "quality_ok" in filters.columns else filters
    if not quality.empty:
        best_pnl = quality.sort_values(["pnl_usd_001", "pf", "test_pf", "n"], ascending=[False, False, False, False]).iloc[0]
        print(
            f"best_pnl candidate={best_pnl['candidate']} pool={best_pnl['pool']} "
            f"filter={best_pnl['filter_name']} n={int(best_pnl['n'])} "
            f"pf={float(best_pnl['pf']):.4f} test_pf={float(best_pnl['test_pf']):.4f} "
            f"usd001={float(best_pnl['pnl_usd_001']):.2f}"
        )


if __name__ == "__main__":
    main()
