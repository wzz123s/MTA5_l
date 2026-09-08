# -*- coding: utf-8 -*-
"""Optimize 1H_M30_4H after fixing 4H bias55 >= 2% and H1-based stops."""
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
    add_indicators,
    attach_context,
    contract_size,
    fmt,
    manifest_file,
    manifest_timeframe,
    markdown_table,
    metric,
    money,
    read_json,
    replay_trade,
    standardize_mt5_csv,
    strategy_dir,
    trade_sign,
    yearly_positive_count,
    split_test,
)


STRATEGY = "1H_M30_4H"
BASE_FIELD = "4h_bias55_signed_pct"
BASE_THRESHOLD = 2.0
MIN_SAMPLE = 30

STOP_VARIANTS = [
    ("h1_last1_hilo", "最近1根已收盘H1的低/高点"),
    ("h1_last3_hilo", "最近3根已收盘H1的低/高点"),
    ("h1_last6_hilo", "最近6根已收盘H1的低/高点"),
    ("h1_dir_segment_hilo", "最近一次H1方向切换后的低/高点"),
    ("h1_dir_segment_sma13", "最近一次H1方向切换后的SMA13低/高点"),
]


def build_signal_plans(m30: pd.DataFrame) -> pd.DataFrame:
    direction = m30["dir"].astype(int).to_numpy()
    events: list[dict] = []
    for idx in range(1, len(m30)):
        prev_dir = int(direction[idx - 1])
        cur_dir = int(direction[idx])
        if cur_dir > 0 and prev_dir <= 0:
            events.append({"idx": idx, "side": "L"})
        elif cur_dir < 0 and prev_dir >= 0:
            events.append({"idx": idx, "side": "S"})

    rows: list[dict] = []
    for pos, event in enumerate(events):
        side = str(event["side"])
        signal_idx = int(event["idx"])
        opposite = next((later for later in events[pos + 1 :] if later["side"] != side), None)
        if opposite is None:
            continue
        entry_idx = signal_idx + 1
        planned_cross_idx = int(opposite["idx"])
        planned_exit_idx = planned_cross_idx + 1
        if entry_idx >= len(m30):
            continue
        if planned_exit_idx >= len(m30):
            planned_exit_idx = planned_cross_idx

        signal_bar = m30.iloc[signal_idx]
        entry_bar = m30.iloc[entry_idx]
        planned_cross_bar = m30.iloc[planned_cross_idx]
        planned_exit_bar = m30.iloc[planned_exit_idx]
        rows.append(
            {
                "signal_bar_idx": signal_idx,
                "entry_bar_idx": entry_idx,
                "planned_cross_idx": planned_cross_idx,
                "planned_exit_idx": planned_exit_idx,
                "signal_time": signal_bar["bar_close_time"],
                "entry_time": entry_bar["bar_open_time"],
                "dir": side,
                "entry": round(float(entry_bar["open"]), 3),
                "planned_exit_signal_time": planned_cross_bar["bar_close_time"],
                "planned_exit_time": planned_exit_bar["bar_open_time"]
                if planned_exit_idx != planned_cross_idx
                else planned_cross_bar["date"],
                "planned_exit": round(
                    float(planned_exit_bar["open"] if planned_exit_idx != planned_cross_idx else planned_cross_bar["close"]),
                    3,
                ),
            }
        )
    return pd.DataFrame(rows)


def latest_h1_idx(h1: pd.DataFrame, signal_time: object) -> int:
    times = pd.to_datetime(h1["date"]).values.astype("datetime64[ns]")
    t = pd.Timestamp(signal_time).to_datetime64()
    return bisect.bisect_right(times, t) - 1


def dir_segment_start(h1: pd.DataFrame, idx: int) -> int:
    if idx <= 0:
        return 0
    current = int(h1.iloc[idx]["dir"])
    pos = idx
    while pos - 1 >= 0 and int(h1.iloc[pos - 1]["dir"]) == current:
        pos -= 1
    return pos


def stop_from_h1(h1: pd.DataFrame, signal_time: object, side: str, source: str) -> float:
    idx = latest_h1_idx(h1, signal_time)
    if idx < 0:
        return float("nan")
    if source == "h1_last1_hilo":
        window = h1.iloc[idx : idx + 1]
        field = "low" if side == "L" else "high"
    elif source == "h1_last3_hilo":
        window = h1.iloc[max(0, idx - 2) : idx + 1]
        field = "low" if side == "L" else "high"
    elif source == "h1_last6_hilo":
        window = h1.iloc[max(0, idx - 5) : idx + 1]
        field = "low" if side == "L" else "high"
    elif source == "h1_dir_segment_hilo":
        window = h1.iloc[dir_segment_start(h1, idx) : idx + 1]
        field = "low" if side == "L" else "high"
    elif source == "h1_dir_segment_sma13":
        window = h1.iloc[dir_segment_start(h1, idx) : idx + 1]
        field = "SMA_13"
    else:
        raise KeyError(source)

    values = pd.to_numeric(window[field], errors="coerce").dropna()
    if values.empty:
        return float("nan")
    return float(values.min() if side == "L" else values.max())


def apply_h1_stop(plans: pd.DataFrame, h1: pd.DataFrame, source: str) -> pd.DataFrame:
    out = plans.copy()
    stops = []
    for _, row in out.iterrows():
        stops.append(stop_from_h1(h1, row["signal_time"], str(row["dir"]), source))
    out["structural_stop_price"] = pd.Series(stops, index=out.index)
    sign = out["dir"].map(lambda value: trade_sign(value)).astype(int)
    out["stop_distance"] = np.where(
        sign > 0,
        pd.to_numeric(out["entry"], errors="coerce") - pd.to_numeric(out["structural_stop_price"], errors="coerce"),
        pd.to_numeric(out["structural_stop_price"], errors="coerce") - pd.to_numeric(out["entry"], errors="coerce"),
    )
    out["structural_stop_source"] = source
    out = out.loc[pd.to_numeric(out["stop_distance"], errors="coerce").gt(0)].copy().reset_index(drop=True)
    out["structural_stop_price"] = pd.to_numeric(out["structural_stop_price"], errors="coerce").round(3)
    out["stop_distance"] = pd.to_numeric(out["stop_distance"], errors="coerce").round(3)
    return out


def load_frames() -> tuple[dict, pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    manifest = read_json(strategy_dir(STRATEGY) / "data" / "raw" / "raw_source_manifest.json")
    m30 = add_indicators(standardize_mt5_csv(manifest_file(manifest, "M30"), "30M", closed_time=False))
    contexts: dict[str, pd.DataFrame] = {}
    for label in ["30M", "1H", "4H"]:
        tf_name = manifest_timeframe(label)
        contexts[label] = add_indicators(standardize_mt5_csv(manifest_file(manifest, tf_name), label, closed_time=True))
    return manifest, m30, contexts["1H"], contexts


def replay_with_stop_source(plans: pd.DataFrame, m30: pd.DataFrame, h1: pd.DataFrame, contexts: dict[str, pd.DataFrame], source: str, contract: float) -> pd.DataFrame:
    stopped = apply_h1_stop(plans, h1, source)
    replay_rows = [replay_trade(row, m30) for _, row in stopped.iterrows()]
    replay = pd.concat([stopped.reset_index(drop=True), pd.DataFrame(replay_rows)], axis=1)
    replay["pnl_usd_001"] = pd.to_numeric(replay["pnl_points"], errors="coerce") * contract * LOT_FOR_REPORT
    replay["risk_r"] = pd.to_numeric(replay["pnl_points"], errors="coerce") / pd.to_numeric(replay["stop_distance"], errors="coerce")
    replay["signal_time"] = pd.to_datetime(replay["signal_time"])
    for label, tf in contexts.items():
        replay = attach_context(replay, tf, label.lower())
    replay["stop_variant"] = source
    return replay


def filter_mask(frame: pd.DataFrame, name: str) -> pd.Series:
    base = pd.to_numeric(frame[BASE_FIELD], errors="coerce").ge(BASE_THRESHOLD)
    if name == "base":
        return base
    if name == "base_buy_only":
        return base & frame["dir"].astype(str).eq("L")
    if name == "base_sell_only":
        return base & frame["dir"].astype(str).eq("S")
    if name == "base_1h_dir_align":
        sign = frame["dir"].map(lambda value: trade_sign(value)).astype(int)
        return base & pd.to_numeric(frame["1h_dir"], errors="coerce").fillna(0).astype(int).eq(sign)
    if name == "base_1h_dir_against":
        sign = frame["dir"].map(lambda value: trade_sign(value)).astype(int)
        return base & pd.to_numeric(frame["1h_dir"], errors="coerce").fillna(0).astype(int).eq(-sign)
    if name == "base_1h_close_side":
        sign = frame["dir"].map(lambda value: trade_sign(value)).astype(int)
        return base & pd.to_numeric(frame["1h_close_side"], errors="coerce").fillna(0).astype(int).eq(sign)
    if name == "base_1h_bias5_pos":
        return base & pd.to_numeric(frame["1h_bias5_signed_pct"], errors="coerce").gt(0)
    if name == "base_1h_bias13_pos":
        return base & pd.to_numeric(frame["1h_bias13_signed_pct"], errors="coerce").gt(0)
    if name == "base_1h_bias55_pos":
        return base & pd.to_numeric(frame["1h_bias55_signed_pct"], errors="coerce").gt(0)
    if name == "base_1h_bias5_13_pos":
        return (
            base
            & pd.to_numeric(frame["1h_bias5_signed_pct"], errors="coerce").gt(0)
            & pd.to_numeric(frame["1h_bias13_signed_pct"], errors="coerce").gt(0)
        )
    raise KeyError(name)


FILTERS = [
    ("base", "4H bias55 >= 2.0%"),
    ("base_1h_dir_align", "base + 1H方向同向"),
    ("base_1h_dir_against", "base + 1H方向反向"),
    ("base_1h_close_side", "base + 1H close在交易方向侧"),
    ("base_1h_bias5_pos", "base + 1H bias5>0"),
    ("base_1h_bias13_pos", "base + 1H bias13>0"),
    ("base_1h_bias55_pos", "base + 1H bias55>0"),
    ("base_1h_bias5_13_pos", "base + 1H bias5&bias13>0"),
    ("base_buy_only", "base + BUY only"),
    ("base_sell_only", "base + SELL only"),
]


def summarize(frame: pd.DataFrame, source: str, filter_name: str, desc: str, contract: float) -> dict:
    values = pd.to_numeric(frame["pnl_points"], errors="coerce")
    m = metric(values)
    test = split_test(frame, "pnl_points")
    pos_years, total_years = yearly_positive_count(frame, "pnl_points")
    return {
        "stop_variant": source,
        "filter": filter_name,
        "desc": desc,
        "n": m["n"],
        "pf": m["pf"],
        "test_pf": test["test_pf"],
        "ev_points": m["ev"],
        "pnl_points": m["pnl"],
        "pnl_usd_001": m["pnl"] * contract * LOT_FOR_REPORT,
        "test_n": test["test_n"],
        "test_ev_points": test["test_ev"],
        "test_pnl_points": test["test_pnl"],
        "stop_hits": int(frame["stop_hit"].sum()) if len(frame) else 0,
        "stop_hit_rate_pct": float(frame["stop_hit"].mean() * 100.0) if len(frame) else 0.0,
        "avg_stop_distance": float(pd.to_numeric(frame["stop_distance"], errors="coerce").mean()) if len(frame) else 0.0,
        "median_stop_distance": float(pd.to_numeric(frame["stop_distance"], errors="coerce").median()) if len(frame) else 0.0,
        "positive_years": pos_years,
        "total_years": total_years,
        "sample_status": "ok" if m["n"] >= MIN_SAMPLE else "insufficient",
    }


def score_summary(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["sample_ok"] = out["n"].astype(float).ge(MIN_SAMPLE)
    out["score"] = (
        out["sample_ok"].astype(int) * 1000.0
        + out["test_pf"].astype(float).clip(upper=50) * 20.0
        + out["pf"].astype(float).clip(upper=50) * 8.0
        + out["pnl_usd_001"].astype(float) * 0.01
        + out["positive_years"].astype(float) * 3.0
    )
    return out.sort_values(["score", "test_pf", "pf", "n"], ascending=[False, False, False, False]).reset_index(drop=True)


def write_report(replays: pd.DataFrame, stop_summary: pd.DataFrame, filter_summary: pd.DataFrame, out_dir: Path) -> None:
    stop_cols = [
        "stop_variant",
        "n",
        "pf",
        "test_pf",
        "pnl_usd_001",
        "stop_hits",
        "stop_hit_rate_pct",
        "avg_stop_distance",
        "median_stop_distance",
        "positive_years",
        "total_years",
    ]
    filter_cols = [
        "stop_variant",
        "filter",
        "n",
        "pf",
        "test_pf",
        "pnl_usd_001",
        "stop_hits",
        "stop_hit_rate_pct",
        "avg_stop_distance",
        "positive_years",
        "total_years",
        "sample_status",
    ]
    best = filter_summary.head(12).copy()
    lines = [
        "# 1H_M30_4H 4H bias55 base + 1H止损优化",
        "",
        "日期：2026-07-25",
        "",
        "## 口径",
        "",
        "- 第一层固定条件：`4h_bias55_signed_pct >= 2.0`。",
        "- 信号：M30 SMA5/SMA13 交叉，M30 收盘确认，下一根 M30 开盘入场。",
        "- 止损：只使用入场前已收盘的 1H 数据，不再使用 M30 SMA13 止损。",
        "- 回放：入场后逐根 M30 K 线检查止损，未止损则下一次反向 M30 交叉确认后的下一根 M30 开盘退出。",
        "- 收益：`pnl_points * 100 * 0.01 lot`，未扣点差、滑点、手续费。",
        "",
        "## 1H止损定义对比",
        "",
        markdown_table(stop_summary[stop_cols], stop_cols, money_cols={"pnl_usd_001"}),
        "",
        "## 第二层过滤 Top",
        "",
        markdown_table(best[filter_cols], filter_cols, money_cols={"pnl_usd_001"}),
        "",
        "## 输出文件",
        "",
        "- `h1_stop_all_replay_trades.csv`",
        "- `h1_stop_base_summary.csv`",
        "- `h1_stop_second_filter_summary.csv`",
    ]
    report = "\n".join(lines) + "\n"
    (out_dir / "h1_stop_optimization_report.md").write_text(report, encoding="utf-8")
    (ROOT / "1H_4Hbias55_1H止损优化记录.md").write_text(report, encoding="utf-8")


def main() -> None:
    manifest, m30, h1, contexts = load_frames()
    plans = build_signal_plans(m30)
    contract = contract_size(manifest)

    replay_frames = []
    stop_rows = []
    filter_rows = []
    for source, source_desc in STOP_VARIANTS:
        replay = replay_with_stop_source(plans, m30, h1, contexts, source, contract)
        replay_frames.append(replay)
        base_frame = replay.loc[filter_mask(replay, "base")].copy()
        row = summarize(base_frame, source, "base", source_desc, contract)
        stop_rows.append(row)
        for filter_name, desc in FILTERS:
            scoped = replay.loc[filter_mask(replay, filter_name)].copy()
            filter_rows.append(summarize(scoped, source, filter_name, desc, contract))

    all_replay = pd.concat(replay_frames, ignore_index=True)
    stop_summary = score_summary(pd.DataFrame(stop_rows))
    filter_summary = score_summary(pd.DataFrame(filter_rows))

    out_dir = strategy_dir(STRATEGY) / "data" / "validation" / "h1_stop_optimization"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_replay.to_csv(out_dir / "h1_stop_all_replay_trades.csv", index=False, encoding="utf-8-sig")
    stop_summary.to_csv(out_dir / "h1_stop_base_summary.csv", index=False, encoding="utf-8-sig")
    filter_summary.to_csv(out_dir / "h1_stop_second_filter_summary.csv", index=False, encoding="utf-8-sig")
    write_report(all_replay, stop_summary, filter_summary, out_dir)

    print(f"{STRATEGY}: base {BASE_FIELD}>={BASE_THRESHOLD}%")
    for _, row in stop_summary.iterrows():
        print(
            f"  {row['stop_variant']}: n={int(row['n'])} pf={float(row['pf']):.4f} "
            f"test_pf={float(row['test_pf']):.4f} usd001={float(row['pnl_usd_001']):.2f}"
        )
    best = filter_summary.iloc[0]
    print(
        f"best_filter={best['filter']} stop={best['stop_variant']} n={int(best['n'])} "
        f"pf={float(best['pf']):.4f} test_pf={float(best['test_pf']):.4f} "
        f"usd001={float(best['pnl_usd_001']):.2f}"
    )


if __name__ == "__main__":
    main()
