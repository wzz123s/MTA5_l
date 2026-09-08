# -*- coding: utf-8 -*-
"""Replay the corrected hybrid entry/stop rule for 1H_M30_4H.

Rule:
- fixed_delay_1 keeps the H1 structural stop used by the formal 1H_M30_4H line.
- fixed_delay_2..N and window_2_to_N use the M30 SMA13 visible at entry time.
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

import numpy as np
import pandas as pd

from replay_1h_bias55_h1_stop_optimization import load_frames, stop_from_h1
from replay_1h_delayed_entry_sma13_stop import (
    STOP_HIS,
    STOP_LOS,
    THIRD_FILTERS,
    WINDOW_MAX_DELAYS,
    attach_context_at_time,
    high_bias_features,
    make_plan_row,
    opportunity_mask,
    stop_range_label,
    third_filter_mask,
)
from replay_raw_signals_with_stops import (
    LOT_FOR_REPORT,
    ROOT,
    build_cross_events,
    contract_size,
    markdown_table,
    metric,
    replay_trade,
    split_test,
    strategy_dir,
    yearly_positive_count,
)


STRATEGY = "1H_M30_4H"
OUT_DIR = strategy_dir(STRATEGY) / "data" / "validation" / "hybrid_entry_stop"
FIXED_DELAYS = list(range(1, 13))
H1_STOP_VARIANTS = ["h1_last6_hilo", "h1_last3_hilo", "h1_dir_segment_hilo"]
M30_SMA13_STOP = "m30_entry_prev_closed_sma13"
MIN_SAMPLE = 30


def make_h1_plan_row(
    m30: pd.DataFrame,
    h1: pd.DataFrame,
    *,
    signal_idx: int,
    side: str,
    entry_idx: int,
    planned_cross_idx: int,
    planned_exit_idx: int,
    stop_variant: str,
) -> dict | None:
    if entry_idx <= signal_idx or entry_idx >= len(m30) or entry_idx >= planned_exit_idx:
        return None

    signal_bar = m30.iloc[signal_idx]
    entry_bar = m30.iloc[entry_idx]
    entry_time = entry_bar["bar_open_time"]
    stop_price = stop_from_h1(h1, entry_time, side, stop_variant)
    entry_price = float(entry_bar["open"])
    stop_distance = entry_price - stop_price if side == "L" else stop_price - entry_price
    if not math.isfinite(stop_distance) or stop_distance <= 0:
        return None

    planned_cross_bar = m30.iloc[planned_cross_idx]
    planned_exit_bar = m30.iloc[planned_exit_idx]
    return {
        "signal_bar_idx": signal_idx,
        "entry_bar_idx": entry_idx,
        "planned_cross_idx": planned_cross_idx,
        "planned_exit_idx": planned_exit_idx,
        "signal_time": signal_bar["bar_close_time"],
        "entry_time": entry_time,
        "dir": side,
        "entry": round(entry_price, 3),
        "structural_stop_price": round(float(stop_price), 3),
        "structural_stop_source": stop_variant,
        "stop_variant": stop_variant,
        "stop_sma13_bar_idx": np.nan,
        "stop_sma13_time": pd.NaT,
        "stop_distance": round(float(stop_distance), 3),
        "entry_rule": "fixed_delay_1",
        "entry_delay_bars": 1,
        "window_min_delay": 1,
        "window_max_delay": 1,
        "planned_exit_signal_time": planned_cross_bar["bar_close_time"],
        "planned_exit_time": planned_exit_bar["bar_open_time"]
        if planned_exit_idx != planned_cross_idx
        else planned_cross_bar["date"],
        "planned_exit": round(
            float(planned_exit_bar["open"] if planned_exit_idx != planned_cross_idx else planned_cross_bar["close"]),
            3,
        ),
    }


def with_m30_stop_variant(row: dict) -> dict:
    out = dict(row)
    out["stop_variant"] = M30_SMA13_STOP
    return out


def build_hybrid_plans(m30: pd.DataFrame, h1: pd.DataFrame) -> pd.DataFrame:
    events = build_cross_events(m30)
    rows: list[dict] = []
    for pos, event in enumerate(events):
        side = str(event["side"])
        signal_idx = int(event["idx"])
        opposite = next((later for later in events[pos + 1 :] if later["side"] != side), None)
        if opposite is None:
            continue
        planned_cross_idx = int(opposite["idx"])
        planned_exit_idx = planned_cross_idx + 1
        if planned_exit_idx >= len(m30):
            planned_exit_idx = planned_cross_idx

        for stop_variant in H1_STOP_VARIANTS:
            row = make_h1_plan_row(
                m30,
                h1,
                signal_idx=signal_idx,
                side=side,
                entry_idx=signal_idx + 1,
                planned_cross_idx=planned_cross_idx,
                planned_exit_idx=planned_exit_idx,
                stop_variant=stop_variant,
            )
            if row is not None:
                rows.append(row)

        for delay in FIXED_DELAYS:
            if delay == 1:
                continue
            row = make_plan_row(
                m30,
                signal_idx=signal_idx,
                side=side,
                entry_idx=signal_idx + delay,
                planned_cross_idx=planned_cross_idx,
                planned_exit_idx=planned_exit_idx,
                entry_rule=f"fixed_delay_{delay}",
            )
            if row is not None:
                rows.append(with_m30_stop_variant(row))

        for max_delay in WINDOW_MAX_DELAYS:
            selected = None
            for delay in range(2, max_delay + 1):
                selected = make_plan_row(
                    m30,
                    signal_idx=signal_idx,
                    side=side,
                    entry_idx=signal_idx + delay,
                    planned_cross_idx=planned_cross_idx,
                    planned_exit_idx=planned_exit_idx,
                    entry_rule=f"window_2_to_{max_delay}_first_valid",
                    window_max_delay=max_delay,
                )
                if selected is not None:
                    break
            if selected is not None:
                rows.append(with_m30_stop_variant(selected))
    return pd.DataFrame(rows)


def summarize(frame: pd.DataFrame, *, entry_rule: str, stop_variant: str, third_filter: str, third_desc: str, stop_range: str = "all") -> dict:
    m = metric(frame["pnl_points"])
    test = split_test(frame, "pnl_points")
    pos_years, total_years = yearly_positive_count(frame, "pnl_points")
    side = frame["dir"].astype(str).str.upper() if len(frame) else pd.Series(dtype=str)
    return {
        "entry_rule": entry_rule,
        "stop_variant": stop_variant,
        "third_filter": third_filter,
        "third_desc": third_desc,
        "stop_range": stop_range,
        "n": m["n"],
        "long_n": int(side.eq("L").sum()) if len(frame) else 0,
        "short_n": int(side.eq("S").sum()) if len(frame) else 0,
        "pf": m["pf"],
        "test_pf": test["test_pf"],
        "ev_points": m["ev"],
        "pnl_points": m["pnl"],
        "pnl_usd_001": m["pnl"] * 100.0 * LOT_FOR_REPORT,
        "test_n": test["test_n"],
        "test_ev_points": test["test_ev"],
        "test_pnl_points": test["test_pnl"],
        "stop_hits": int(frame["stop_hit"].sum()) if len(frame) else 0,
        "stop_hit_rate_pct": float(frame["stop_hit"].mean() * 100.0) if len(frame) else 0.0,
        "avg_entry_delay_bars": float(pd.to_numeric(frame["entry_delay_bars"], errors="coerce").mean()) if len(frame) else 0.0,
        "avg_stop_distance": float(pd.to_numeric(frame["stop_distance"], errors="coerce").mean()) if len(frame) else 0.0,
        "median_stop_distance": float(pd.to_numeric(frame["stop_distance"], errors="coerce").median()) if len(frame) else 0.0,
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
    metric_score = (
        out["pnl_usd_001"].astype(float) * 0.025
        + out["test_pf"].astype(float).clip(upper=10) * 14.0
        + out["pf"].astype(float).clip(upper=10) * 9.0
        + out["positive_years"].astype(float) * 5.0
        + out["n"].astype(float).clip(upper=200) * 0.015
    )
    weak_score = out["n"].astype(float) + out["pnl_usd_001"].astype(float) * 0.005
    out["score"] = np.where(out["quality_ok"], 1000.0 + metric_score, np.where(out["sample_ok"], weak_score, -1000.0 + out["n"].astype(float)))
    return out.sort_values(["score", "pnl_usd_001", "test_pf", "pf", "n"], ascending=[False, False, False, False, False]).reset_index(drop=True)


def build_replay() -> pd.DataFrame:
    manifest, m30, h1, contexts = load_frames()
    h4 = contexts["4H"]
    plans = build_hybrid_plans(m30, h1)
    replay_rows = [replay_trade(row, m30) for _, row in plans.iterrows()]
    replay = pd.concat([plans.reset_index(drop=True), pd.DataFrame(replay_rows)], axis=1)
    replay["pnl_usd_001"] = pd.to_numeric(replay["pnl_points"], errors="coerce") * contract_size(manifest) * LOT_FOR_REPORT
    replay["risk_r"] = pd.to_numeric(replay["pnl_points"], errors="coerce") / pd.to_numeric(replay["stop_distance"], errors="coerce")
    replay["signal_time"] = pd.to_datetime(replay["signal_time"])
    replay["entry_time"] = pd.to_datetime(replay["entry_time"])
    for label, tf in contexts.items():
        replay = attach_context_at_time(replay, tf, label.lower(), "entry_time")
    replay = pd.concat([replay.reset_index(drop=True), high_bias_features(replay["entry_time"], h1, h4)], axis=1)
    return replay


def scan(replay: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = replay.loc[opportunity_mask(replay)].copy()
    delay_rows: list[dict] = []
    third_rows: list[dict] = []
    stop_rows: list[dict] = []

    groups = sorted(base.groupby(["entry_rule", "stop_variant"]).groups.keys())
    for entry_rule, stop_variant in groups:
        scoped_rule = base.loc[base["entry_rule"].astype(str).eq(entry_rule) & base["stop_variant"].astype(str).eq(stop_variant)].copy()
        delay_rows.append(
            summarize(
                scoped_rule,
                entry_rule=str(entry_rule),
                stop_variant=str(stop_variant),
                third_filter="none",
                third_desc="no_third_filter",
            )
        )

        for filter_name, filter_desc in THIRD_FILTERS:
            filtered = scoped_rule.loc[third_filter_mask(scoped_rule, filter_name)].copy()
            third_rows.append(
                summarize(
                    filtered,
                    entry_rule=str(entry_rule),
                    stop_variant=str(stop_variant),
                    third_filter=filter_name,
                    third_desc=filter_desc,
                )
            )
            for lo in STOP_LOS:
                for hi in STOP_HIS:
                    if hi <= lo:
                        continue
                    stopped = filtered.loc[
                        pd.to_numeric(filtered["stop_distance"], errors="coerce").between(lo, hi, inclusive="both")
                    ].copy()
                    stop_rows.append(
                        summarize(
                            stopped,
                            entry_rule=str(entry_rule),
                            stop_variant=str(stop_variant),
                            third_filter=filter_name,
                            third_desc=filter_desc,
                            stop_range=stop_range_label(lo, hi),
                        )
                    )

    return score(pd.DataFrame(delay_rows)), score(pd.DataFrame(third_rows)), score(pd.DataFrame(stop_rows))


def write_report(delay_summary: pd.DataFrame, third_summary: pd.DataFrame, stop_summary: pd.DataFrame) -> None:
    cols = [
        "entry_rule",
        "stop_variant",
        "third_filter",
        "stop_range",
        "n",
        "long_n",
        "short_n",
        "pf",
        "test_pf",
        "pnl_usd_001",
        "stop_hits",
        "stop_hit_rate_pct",
        "avg_entry_delay_bars",
        "avg_stop_distance",
        "positive_years",
        "total_years",
        "sample_status",
    ]
    fixed1 = delay_summary.loc[delay_summary["entry_rule"].eq("fixed_delay_1")].copy()
    delayed = delay_summary.loc[delay_summary["entry_rule"].astype(str).str.startswith("fixed_delay_") & ~delay_summary["entry_rule"].eq("fixed_delay_1")].copy()
    window = delay_summary.loc[delay_summary["entry_rule"].astype(str).str.startswith("window_")].copy()
    main_filter = third_summary.loc[third_summary["third_filter"].eq("1h_bias5_13_pos")].copy()
    stop_main = stop_summary.loc[stop_summary["third_filter"].eq("1h_bias5_13_pos")].copy()
    stop_main_pnl = (
        stop_main.loc[stop_main.get("quality_ok", pd.Series(False, index=stop_main.index)).astype(bool)]
        .sort_values(["pnl_usd_001", "pf", "test_pf", "n"], ascending=[False, False, False, False])
        .reset_index(drop=True)
    )

    lines = [
        "# 1H_M30_4H hybrid entry stop test",
        "",
        "Date: 2026-07-25",
        "",
        "## Rules",
        "",
        "- Opportunity layer is rechecked at entry time: short when `H1roll4 high vs H4 SMA55 >= 2%`, long when `<= -2%`.",
        "- `fixed_delay_1` enters at the first M30 open after the cross and uses an H1 structural stop.",
        "- H1 structural stop variants for `fixed_delay_1`: `h1_last6_hilo`, `h1_last3_hilo`, `h1_dir_segment_hilo`.",
        "- `fixed_delay_2..12` enters at the open of the k-th M30 bar after the cross and uses the M30 SMA13 visible at entry time.",
        "- `window_2_to_n_first_valid` enters on the first bar in `2..n` whose entry price is on the valid side of the SMA13 stop.",
        "- USD PnL is `pnl_points * 100 * 0.01 lot`; spread, slippage, and commission are not deducted.",
        "",
        "## First Bar With H1 Structural Stop",
        "",
        markdown_table(fixed1[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## Delayed Fixed Entry With M30 SMA13 Stop",
        "",
        markdown_table(delayed.head(20)[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## Window 2..n With M30 SMA13 Stop",
        "",
        markdown_table(window.head(15)[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## Hybrid + 1H bias5&bias13",
        "",
        markdown_table(main_filter.head(25)[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## Hybrid + 1H bias5&bias13 + Stop Distance Top",
        "",
        markdown_table(stop_main.head(30)[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## Hybrid + 1H bias5&bias13 + Stop Distance Highest PnL",
        "",
        markdown_table(stop_main_pnl.head(25)[cols], cols, money_cols={"pnl_usd_001"}),
        "",
        "## Output Files",
        "",
        "- `hybrid_entry_all_trades.csv`",
        "- `hybrid_entry_delay_summary.csv`",
        "- `hybrid_entry_third_filter_summary.csv`",
        "- `hybrid_entry_stop_range_summary.csv`",
    ]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report = "\n".join(lines) + "\n"
    (OUT_DIR / "hybrid_entry_stop_report.md").write_text(report, encoding="utf-8")
    (ROOT / "1H_M30_4H混合入场止损测试记录.md").write_text(report, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    replay = build_replay()
    delay_summary, third_summary, stop_summary = scan(replay)
    replay.to_csv(OUT_DIR / "hybrid_entry_all_trades.csv", index=False, encoding="utf-8-sig")
    delay_summary.to_csv(OUT_DIR / "hybrid_entry_delay_summary.csv", index=False, encoding="utf-8-sig")
    third_summary.to_csv(OUT_DIR / "hybrid_entry_third_filter_summary.csv", index=False, encoding="utf-8-sig")
    stop_summary.to_csv(OUT_DIR / "hybrid_entry_stop_range_summary.csv", index=False, encoding="utf-8-sig")
    write_report(delay_summary, third_summary, stop_summary)

    print(f"{STRATEGY}: hybrid entry stop test")
    for _, row in delay_summary.head(8).iterrows():
        print(
            f"  {row['entry_rule']} stop={row['stop_variant']} n={int(row['n'])} "
            f"pf={float(row['pf']):.4f} test_pf={float(row['test_pf']):.4f} "
            f"usd001={float(row['pnl_usd_001']):.2f}"
        )
    main_filter = third_summary.loc[third_summary["third_filter"].eq("1h_bias5_13_pos")]
    if not main_filter.empty:
        best = main_filter.iloc[0]
        print(
            f"best_1h_bias5_13 entry={best['entry_rule']} stop={best['stop_variant']} "
            f"n={int(best['n'])} pf={float(best['pf']):.4f} test_pf={float(best['test_pf']):.4f} "
            f"usd001={float(best['pnl_usd_001']):.2f}"
        )
    stop_main = stop_summary.loc[stop_summary["third_filter"].eq("1h_bias5_13_pos")]
    stop_main_quality = stop_main.loc[stop_main["quality_ok"].astype(bool)] if "quality_ok" in stop_main.columns else stop_main
    if not stop_main_quality.empty:
        best_stop = stop_main_quality.sort_values(["pnl_usd_001", "pf", "test_pf"], ascending=[False, False, False]).iloc[0]
        print(
            f"best_stop_pnl entry={best_stop['entry_rule']} stop={best_stop['stop_variant']} "
            f"range={best_stop['stop_range']} n={int(best_stop['n'])} "
            f"pf={float(best_stop['pf']):.4f} test_pf={float(best_stop['test_pf']):.4f} "
            f"usd001={float(best_stop['pnl_usd_001']):.2f}"
        )


if __name__ == "__main__":
    main()
