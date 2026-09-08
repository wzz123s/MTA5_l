# -*- coding: utf-8 -*-
"""Replay strategy-owned raw MT5 bars with executable entries and structural stops.

This script rebuilds the core M30 SMA5/SMA13 cross signals from each strategy's
own raw MT5 files, attaches closed higher-timeframe context, then replays each
trade bar-by-bar with the structural stop checked before the planned opposite
cross exit.
"""
from __future__ import annotations

import bisect
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from strategy_research_common import calc_smma, tf_label_to_hours, tf_slug


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGIES: dict[str, dict[str, object]] = {
    "1H_M30_4H": {
        "frames": ["30M", "1H", "4H"],
        "threshold_prefix": "4h",
        "threshold_period": 55,
        "thresholds": [round(value / 10.0, 1) for value in range(20, 61, 2)],
        "selected_filters": [
            ("baseline", "全部 M30 cross"),
            ("1h_dir_align", "1H 方向同向"),
            ("4h_bias55_ge_2.0", "4H bias55 >= 2.0%"),
        ],
    },
    "2H_M30_6H": {
        "frames": ["30M", "2H", "6H"],
        "threshold_prefix": "6h",
        "threshold_period": 55,
        "thresholds": [round(value / 10.0, 1) for value in range(30, 61, 2)],
        "selected_filters": [
            ("baseline", "全部 M30 cross"),
            ("6h_bias55_ge_3.6", "6H bias55 >= 3.6%"),
            ("6h_bias5_13_55_signed_pos", "6H bias5/bias13/bias55 均为正"),
        ],
    },
}
CONTRACT_SIZE_FALLBACK = 100.0
LOT_FOR_REPORT = 0.01
MIN_SAMPLE = 30


def read_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def read_json(path: Path) -> dict:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return json.loads(path.read_text(encoding=encoding))
        except UnicodeDecodeError:
            continue
    return json.loads(path.read_text())


def strategy_dir(strategy: str) -> Path:
    return ROOT / "黄金" / f"{strategy}策略"


def timeframe_minutes(label: str) -> int:
    if label == "30M":
        return 30
    return int(tf_label_to_hours(label) * 60)


def manifest_timeframe(label: str) -> str:
    if label == "30M":
        return "M30"
    if label.endswith("H"):
        return f"H{int(label[:-1])}"
    return label


def manifest_file(manifest: dict, timeframe: str) -> Path:
    for item in manifest.get("files", []) or []:
        if str(item.get("timeframe", "")).upper() == timeframe.upper():
            return Path(str(item["path"]))
    raise KeyError(f"Manifest is missing timeframe {timeframe}")


def contract_size(manifest: dict) -> float:
    try:
        return float(manifest.get("snapshot", {}).get("symbol", {}).get("trade_contract_size"))
    except Exception:
        return CONTRACT_SIZE_FALLBACK


def standardize_mt5_csv(path: Path, timeframe: str, *, closed_time: bool) -> pd.DataFrame:
    raw = read_csv(path)
    if "date_utc" in raw.columns:
        dates = pd.to_datetime(raw["date_utc"], utc=True).dt.tz_convert(None)
    elif "time" in raw.columns:
        dates = pd.to_datetime(raw["time"], utc=True).dt.tz_convert(None)
    elif "date" in raw.columns:
        dates = pd.to_datetime(raw["date"], utc=True).dt.tz_convert(None)
    else:
        raise RuntimeError(f"Missing time column: {path}")

    if closed_time:
        dates = dates + pd.to_timedelta(timeframe_minutes(timeframe), unit="m")
    bar_close_time = dates if closed_time else dates + pd.to_timedelta(timeframe_minutes(timeframe), unit="m")

    volume = raw["tick_volume"] if "tick_volume" in raw.columns else raw.get("volume", 0)
    out = pd.DataFrame(
        {
            "date": dates,
            "bar_open_time": pd.to_datetime(dates) - pd.to_timedelta(timeframe_minutes(timeframe), unit="m")
            if closed_time
            else dates,
            "bar_close_time": bar_close_time,
            "open": pd.to_numeric(raw["open"], errors="coerce"),
            "high": pd.to_numeric(raw["high"], errors="coerce"),
            "low": pd.to_numeric(raw["low"], errors="coerce"),
            "close": pd.to_numeric(raw["close"], errors="coerce"),
            "volume": pd.to_numeric(volume, errors="coerce").fillna(0),
            "spread": pd.to_numeric(raw["spread"], errors="coerce").fillna(0) if "spread" in raw.columns else 0,
            "real_volume": pd.to_numeric(raw["real_volume"], errors="coerce").fillna(0)
            if "real_volume" in raw.columns
            else 0,
            "symbol": raw["symbol"] if "symbol" in raw.columns else "",
            "time_diff": 0,
        }
    )
    return out.dropna(subset=["date", "open", "high", "low", "close"]).sort_values("date").reset_index(drop=True)


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy().sort_values("date").reset_index(drop=True)
    out["SMA_5"] = calc_smma(out["close"], 5).values
    out["SMA_13"] = calc_smma(out["close"], 13).values
    out["SMA_55"] = calc_smma(out["close"], 55).values
    out["sma5"] = out["SMA_5"]
    out["sma13"] = out["SMA_13"]
    out["sma55"] = out["SMA_55"]
    out["dir"] = np.where(out["SMA_5"] > out["SMA_13"], 1, -1)
    out.loc[out["SMA_5"].isna() | out["SMA_13"].isna(), "dir"] = 0
    out["close_side"] = np.where(
        out["SMA_13"].isna(),
        0,
        np.where(out["close"] > out["SMA_13"], 1, np.where(out["close"] < out["SMA_13"], -1, 0)),
    )
    for period, sma_col in [(5, "SMA_5"), (13, "SMA_13"), (55, "SMA_55")]:
        raw_col = f"bias{period}_raw"
        pct_col = f"bias{period}_raw_pct"
        out[raw_col] = out["close"] - out[sma_col]
        out[pct_col] = np.where(out[sma_col].notna() & out[sma_col].ne(0), out[raw_col] / out[sma_col] * 100.0, np.nan)
    return out


def trade_sign(side: object) -> int:
    text = str(side).strip().upper()
    if text in {"L", "LONG", "BUY", "1"}:
        return 1
    if text in {"S", "SHORT", "SELL", "-1"}:
        return -1
    return 0


def build_cross_events(m30: pd.DataFrame) -> list[dict]:
    direction = m30["dir"].astype(int).to_numpy()
    events: list[dict] = []
    for idx in range(1, len(m30)):
        prev_dir = int(direction[idx - 1])
        cur_dir = int(direction[idx])
        if cur_dir > 0 and prev_dir <= 0:
            side = "L"
        elif cur_dir < 0 and prev_dir >= 0:
            side = "S"
        else:
            continue
        events.append({"idx": idx, "side": side})
    return events


def build_signals(m30: pd.DataFrame) -> pd.DataFrame:
    events = build_cross_events(m30)
    rows: list[dict] = []
    for pos, event in enumerate(events):
        if pos == 0:
            continue
        idx = int(event["idx"])
        side = str(event["side"])
        prev_cross_idx = int(events[pos - 1]["idx"])
        opposite = next((later for later in events[pos + 1 :] if later["side"] != side), None)
        if opposite is None:
            continue
        planned_cross_idx = int(opposite["idx"])
        entry_idx = idx + 1
        exit_idx = planned_cross_idx + 1
        if entry_idx >= len(m30):
            continue
        if exit_idx >= len(m30):
            exit_idx = planned_cross_idx

        segment = m30["SMA_13"].iloc[max(0, prev_cross_idx) : idx].dropna().astype(float)
        if segment.empty:
            continue
        stop_price = float(segment.min() if side == "L" else segment.max())
        signal_bar = m30.iloc[idx]
        entry_bar = m30.iloc[entry_idx]
        planned_cross_bar = m30.iloc[planned_cross_idx]
        planned_exit_bar = m30.iloc[exit_idx]
        entry_price = float(entry_bar["open"])
        stop_distance = entry_price - stop_price if side == "L" else stop_price - entry_price
        if not math.isfinite(stop_distance) or stop_distance <= 0:
            continue
        rows.append(
            {
                "signal_bar_idx": idx,
                "entry_bar_idx": entry_idx,
                "planned_cross_idx": planned_cross_idx,
                "planned_exit_idx": exit_idx,
                "signal_time": signal_bar["bar_close_time"],
                "entry_time": entry_bar["bar_open_time"],
                "dir": side,
                "entry": round(entry_price, 3),
                "structural_stop_price": round(stop_price, 3),
                "structural_stop_source": "m30_prev_cross_sma13_extreme",
                "stop_distance": round(float(stop_distance), 3),
                "planned_exit_signal_time": planned_cross_bar["bar_close_time"],
                "planned_exit_time": planned_exit_bar["bar_open_time"] if exit_idx != planned_cross_idx else planned_cross_bar["date"],
                "planned_exit": round(float(planned_exit_bar["open"] if exit_idx != planned_cross_idx else planned_cross_bar["close"]), 3),
            }
        )
    return pd.DataFrame(rows)


def replay_trade(row: pd.Series, m30: pd.DataFrame) -> dict:
    side = str(row["dir"])
    entry = float(row["entry"])
    stop = float(row["structural_stop_price"])
    entry_idx = int(row["entry_bar_idx"])
    exit_idx = int(row["planned_exit_idx"])

    for idx in range(entry_idx, exit_idx):
        bar = m30.iloc[idx]
        open_price = float(bar["open"])
        high = float(bar["high"])
        low = float(bar["low"])
        if side == "L":
            if open_price <= stop:
                exit_price = open_price
                reason = "stop_gap"
            elif low <= stop:
                exit_price = stop
                reason = "stop"
            else:
                continue
            pnl = exit_price - entry
        else:
            if open_price >= stop:
                exit_price = open_price
                reason = "stop_gap"
            elif high >= stop:
                exit_price = stop
                reason = "stop"
            else:
                continue
            pnl = entry - exit_price
        return {
            "exit_time": bar["bar_open_time"],
            "exit": round(float(exit_price), 3),
            "exit_reason": reason,
            "pnl_points": round(float(pnl), 3),
            "holding_bars": idx - entry_idx + 1,
            "stop_hit": True,
        }

    planned_exit = float(row["planned_exit"])
    pnl = planned_exit - entry if side == "L" else entry - planned_exit
    return {
        "exit_time": row["planned_exit_time"],
        "exit": round(planned_exit, 3),
        "exit_reason": "opposite_cross_next_open",
        "pnl_points": round(float(pnl), 3),
        "holding_bars": max(0, exit_idx - entry_idx),
        "stop_hit": False,
    }


def attach_context(trades: pd.DataFrame, tf: pd.DataFrame, prefix: str) -> pd.DataFrame:
    out = trades.copy()
    times = pd.to_datetime(tf["date"]).values.astype("datetime64[ns]")
    signal_times = pd.to_datetime(out["signal_time"]).values.astype("datetime64[ns]")
    dirs = out["dir"].tolist()

    cols: dict[str, list] = {
        f"{prefix}_idx": [],
        f"{prefix}_date": [],
        f"{prefix}_dir": [],
        f"{prefix}_close_side": [],
        f"{prefix}_dir_prev1": [],
        f"{prefix}_dir_prev2": [],
    }
    for name in ["open", "high", "low", "close", "sma5", "sma13", "sma55"]:
        cols[f"{prefix}_{name}"] = []
    for period in (5, 13, 55):
        for suffix in ["_signed", "_signed_pct", "_raw", "_raw_pct", "_abs_pct"]:
            cols[f"{prefix}_bias{period}{suffix}"] = []

    for pos, signal_time in enumerate(signal_times):
        idx = bisect.bisect_right(times, signal_time) - 1
        if idx < 0:
            cols[f"{prefix}_idx"].append(-1)
            cols[f"{prefix}_date"].append(pd.NaT)
            cols[f"{prefix}_dir"].append(0)
            cols[f"{prefix}_close_side"].append(0)
            cols[f"{prefix}_dir_prev1"].append(0)
            cols[f"{prefix}_dir_prev2"].append(0)
            for name in ["open", "high", "low", "close", "sma5", "sma13", "sma55"]:
                cols[f"{prefix}_{name}"].append(np.nan)
            for period in (5, 13, 55):
                for suffix in ["_signed", "_signed_pct", "_raw", "_raw_pct", "_abs_pct"]:
                    cols[f"{prefix}_bias{period}{suffix}"].append(np.nan)
            continue
        bar = tf.iloc[idx]
        sign = trade_sign(dirs[pos])
        cols[f"{prefix}_idx"].append(idx)
        cols[f"{prefix}_date"].append(bar["date"])
        cols[f"{prefix}_dir"].append(int(bar["dir"]))
        cols[f"{prefix}_close_side"].append(int(bar["close_side"]))
        cols[f"{prefix}_dir_prev1"].append(int(tf.iloc[idx - 1]["dir"]) if idx - 1 >= 0 else 0)
        cols[f"{prefix}_dir_prev2"].append(int(tf.iloc[idx - 2]["dir"]) if idx - 2 >= 0 else 0)
        for name, source in [("open", "open"), ("high", "high"), ("low", "low"), ("close", "close"), ("sma5", "SMA_5"), ("sma13", "SMA_13"), ("sma55", "SMA_55")]:
            cols[f"{prefix}_{name}"].append(float(bar[source]) if not pd.isna(bar[source]) else np.nan)
        for period in (5, 13, 55):
            raw = float(bar[f"bias{period}_raw"]) if not pd.isna(bar[f"bias{period}_raw"]) else np.nan
            raw_pct = float(bar[f"bias{period}_raw_pct"]) if not pd.isna(bar[f"bias{period}_raw_pct"]) else np.nan
            cols[f"{prefix}_bias{period}_signed"].append(raw * sign if sign else np.nan)
            cols[f"{prefix}_bias{period}_signed_pct"].append(raw_pct * sign if sign else np.nan)
            cols[f"{prefix}_bias{period}_raw"].append(raw)
            cols[f"{prefix}_bias{period}_raw_pct"].append(raw_pct)
            cols[f"{prefix}_bias{period}_abs_pct"].append(abs(raw_pct) if not pd.isna(raw_pct) else np.nan)

    for key, values in cols.items():
        out[key] = values
    return out


def metric(values: Iterable[float]) -> dict:
    vals = pd.to_numeric(pd.Series(list(values)), errors="coerce").dropna()
    if vals.empty:
        return {"n": 0, "wr": 0.0, "pf": 0.0, "ev": 0.0, "pnl": 0.0, "maxcl": 0}
    wins = vals[vals > 0]
    losses = vals[vals < 0]
    gross_win = float(wins.sum())
    gross_loss = abs(float(losses.sum()))
    pf = gross_win / gross_loss if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0)
    maxcl = 0
    run = 0
    for value in vals:
        if value < 0:
            run += 1
            maxcl = max(maxcl, run)
        else:
            run = 0
    return {
        "n": int(len(vals)),
        "wr": float((vals > 0).mean() * 100.0),
        "pf": float(pf),
        "ev": float(vals.mean()),
        "pnl": float(vals.sum()),
        "maxcl": int(maxcl),
    }


def split_test(frame: pd.DataFrame, value_col: str) -> dict:
    scoped = frame.dropna(subset=["signal_time"]).sort_values("signal_time").reset_index(drop=True)
    if len(scoped) < 2:
        return {"split_date": "", "test_pf": 0.0, "test_ev": 0.0, "test_pnl": 0.0, "test_n": 0}
    cutoff_idx = min(max(int(len(scoped) * 0.70), 1), len(scoped) - 1)
    cutoff = pd.Timestamp(scoped.loc[cutoff_idx, "signal_time"])
    test = scoped.loc[pd.to_datetime(scoped["signal_time"]) >= cutoff, value_col]
    test_metric = metric(test)
    return {
        "split_date": cutoff.strftime("%Y-%m-%d"),
        "test_pf": test_metric["pf"],
        "test_ev": test_metric["ev"],
        "test_pnl": test_metric["pnl"],
        "test_n": test_metric["n"],
    }


def yearly_positive_count(frame: pd.DataFrame, value_col: str) -> tuple[int, int]:
    if frame.empty:
        return 0, 0
    scoped = frame.copy()
    scoped["year"] = pd.to_datetime(scoped["signal_time"]).dt.year
    by_year = scoped.groupby("year")[value_col].sum()
    return int((by_year > 0).sum()), int(len(by_year))


def parse_stop_range(strategy: str) -> tuple[float, float] | None:
    pack_path = strategy_dir(strategy) / "data" / "validation" / "ea_parameter_pack.json"
    if not pack_path.exists():
        return None
    pack = read_json(pack_path)
    value = str(pack.get("stop_spec", {}).get("primary", "")).lower().replace("pt", "")
    if "-" not in value:
        return None
    left, right = value.split("-", 1)
    try:
        return float(left), float(right)
    except ValueError:
        return None


def summarize_subset(strategy: str, name: str, desc: str, frame: pd.DataFrame, *, contract: float, stop_range: tuple[float, float] | None) -> dict:
    scoped = frame.copy()
    all_m = metric(scoped["pnl_points"])
    test = split_test(scoped, "pnl_points")
    pos_years, total_years = yearly_positive_count(scoped, "pnl_points")
    if stop_range is not None:
        lo, hi = stop_range
        stopped = scoped.loc[scoped["stop_distance"].between(lo, hi, inclusive="both")].copy()
    else:
        stopped = scoped.copy()
    stop_m = metric(stopped["pnl_points"])
    stop_test = split_test(stopped, "pnl_points")
    stop_pos_years, stop_total_years = yearly_positive_count(stopped, "pnl_points")
    return {
        "strategy": strategy,
        "filter": name,
        "desc": desc,
        "n": all_m["n"],
        "pf": all_m["pf"],
        "ev_points": all_m["ev"],
        "pnl_points": all_m["pnl"],
        "pnl_usd_001": all_m["pnl"] * contract * LOT_FOR_REPORT,
        "test_n": test["test_n"],
        "test_pf": test["test_pf"],
        "test_ev_points": test["test_ev"],
        "test_pnl_points": test["test_pnl"],
        "stop_hits": int(scoped["stop_hit"].sum()) if "stop_hit" in scoped.columns else 0,
        "stop_hit_rate_pct": float(scoped["stop_hit"].mean() * 100.0) if len(scoped) else 0.0,
        "positive_years": pos_years,
        "total_years": total_years,
        "stop_spec": "" if stop_range is None else f"{stop_range[0]:g}-{stop_range[1]:g}",
        "stop_n": stop_m["n"],
        "stop_pf": stop_m["pf"],
        "stop_ev_points": stop_m["ev"],
        "stop_pnl_points": stop_m["pnl"],
        "stop_pnl_usd_001": stop_m["pnl"] * contract * LOT_FOR_REPORT,
        "stop_test_n": stop_test["test_n"],
        "stop_test_pf": stop_test["test_pf"],
        "stop_test_ev_points": stop_test["test_ev"],
        "stop_positive_years": stop_pos_years,
        "stop_total_years": stop_total_years,
    }


def selected_mask(frame: pd.DataFrame, name: str) -> pd.Series:
    sign = np.where(frame["dir"].astype(str).str.upper() == "L", 1, -1)
    if name == "baseline":
        return pd.Series(True, index=frame.index)
    if name.endswith("_dir_align"):
        prefix = name.split("_dir_align", 1)[0]
        return pd.to_numeric(frame[f"{prefix}_dir"], errors="coerce").fillna(0).astype(int).eq(sign)
    if name == "6h_bias5_13_55_signed_pos":
        return (
            pd.to_numeric(frame["6h_bias5_signed_pct"], errors="coerce").gt(0)
            & pd.to_numeric(frame["6h_bias13_signed_pct"], errors="coerce").gt(0)
            & pd.to_numeric(frame["6h_bias55_signed_pct"], errors="coerce").gt(0)
        )
    if "_bias55_ge_" in name:
        prefix, threshold_text = name.split("_bias55_ge_", 1)
        threshold = float(threshold_text)
        return pd.to_numeric(frame[f"{prefix}_bias55_signed_pct"], errors="coerce").ge(threshold)
    raise KeyError(f"Unknown filter: {name}")


def analyze_strategy(strategy: str) -> dict[str, pd.DataFrame | dict]:
    cfg = STRATEGIES[strategy]
    sdir = strategy_dir(strategy)
    manifest = read_json(sdir / "data" / "raw" / "raw_source_manifest.json")
    frames = [str(item) for item in cfg["frames"]]  # type: ignore[index]

    m30_raw = standardize_mt5_csv(manifest_file(manifest, "M30"), "30M", closed_time=False)
    m30 = add_indicators(m30_raw)
    signals = build_signals(m30)
    replay_rows = []
    for _, row in signals.iterrows():
        replay_rows.append(replay_trade(row, m30))
    replay = pd.concat([signals.reset_index(drop=True), pd.DataFrame(replay_rows)], axis=1)
    replay["pnl_usd_001"] = pd.to_numeric(replay["pnl_points"], errors="coerce") * contract_size(manifest) * LOT_FOR_REPORT
    replay["risk_r"] = pd.to_numeric(replay["pnl_points"], errors="coerce") / pd.to_numeric(replay["stop_distance"], errors="coerce")
    replay["signal_time"] = pd.to_datetime(replay["signal_time"])

    for label in frames:
        timeframe = manifest_timeframe(label)
        closed = True
        tf = add_indicators(standardize_mt5_csv(manifest_file(manifest, timeframe), label, closed_time=closed))
        replay = attach_context(replay, tf, tf_slug(label))

    stop_range = parse_stop_range(strategy)
    selected_rows = []
    for name, desc in cfg["selected_filters"]:  # type: ignore[index]
        mask = selected_mask(replay, str(name))
        selected_rows.append(summarize_subset(strategy, str(name), str(desc), replay.loc[mask].copy(), contract=contract_size(manifest), stop_range=stop_range))
    selected_summary = pd.DataFrame(selected_rows)

    prefix = str(cfg["threshold_prefix"])
    period = int(cfg["threshold_period"])
    threshold_rows = []
    for threshold in cfg["thresholds"]:  # type: ignore[index]
        field = f"{prefix}_bias{period}_signed_pct"
        mask = pd.to_numeric(replay[field], errors="coerce").ge(float(threshold))
        threshold_rows.append(
            summarize_subset(
                strategy,
                f"{prefix}_bias{period}_ge_{threshold:.1f}",
                f"{prefix} bias{period} >= {threshold:.1f}%",
                replay.loc[mask].copy(),
                contract=contract_size(manifest),
                stop_range=stop_range,
            )
        )
        threshold_rows[-1]["threshold_pct"] = float(threshold)
        threshold_rows[-1]["sample_status"] = "ok" if threshold_rows[-1]["n"] >= MIN_SAMPLE else "insufficient"
    threshold_summary = pd.DataFrame(threshold_rows)

    metadata = {
        "strategy": strategy,
        "source_id": manifest.get("source_id", ""),
        "source_type": manifest.get("source_type", ""),
        "symbol": manifest.get("symbol", ""),
        "contract_size": contract_size(manifest),
        "lot_for_report": LOT_FOR_REPORT,
        "m30_rows": len(m30),
        "signals": len(replay),
        "stop_range": "" if stop_range is None else f"{stop_range[0]:g}-{stop_range[1]:g}",
    }
    return {
        "metadata": metadata,
        "replay": replay,
        "selected_summary": selected_summary,
        "threshold_summary": threshold_summary,
    }


def fmt(value: object, digits: int = 4) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return str(value)


def money(value: object) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return str(value)


def markdown_table(frame: pd.DataFrame, columns: list[str], money_cols: set[str] | None = None) -> str:
    money_cols = money_cols or set()
    if frame.empty:
        return "| empty | empty |\n| --- | --- |"
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if column in money_cols:
                values.append(money(value))
            elif isinstance(value, float):
                values.append(fmt(value))
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_strategy_outputs(strategy: str, outputs: dict[str, pd.DataFrame | dict]) -> None:
    out_dir = strategy_dir(strategy) / "data" / "validation" / "raw_stop_replay"
    out_dir.mkdir(parents=True, exist_ok=True)
    replay = outputs["replay"]  # type: ignore[assignment]
    selected = outputs["selected_summary"]  # type: ignore[assignment]
    threshold = outputs["threshold_summary"]  # type: ignore[assignment]
    metadata = outputs["metadata"]  # type: ignore[assignment]

    assert isinstance(replay, pd.DataFrame)
    assert isinstance(selected, pd.DataFrame)
    assert isinstance(threshold, pd.DataFrame)
    assert isinstance(metadata, dict)

    replay.to_csv(out_dir / "raw_stop_replay_trades.csv", index=False, encoding="utf-8-sig")
    selected.to_csv(out_dir / "raw_stop_replay_selected_summary.csv", index=False, encoding="utf-8-sig")
    threshold.to_csv(out_dir / "raw_stop_replay_threshold_summary.csv", index=False, encoding="utf-8-sig")

    selected_cols = [
        "filter",
        "n",
        "pf",
        "test_pf",
        "pnl_usd_001",
        "stop_hits",
        "stop_hit_rate_pct",
        "stop_n",
        "stop_pf",
        "stop_test_pf",
        "stop_pnl_usd_001",
    ]
    threshold_cols = [
        "threshold_pct",
        "n",
        "pf",
        "test_pf",
        "pnl_usd_001",
        "stop_hits",
        "stop_n",
        "stop_pf",
        "stop_test_pf",
        "stop_pnl_usd_001",
        "sample_status",
    ]
    lines = [
        f"# {strategy} 原始 K 线止损回放",
        "",
        "日期：2026-07-25",
        "",
        "## 口径",
        "",
        "- 数据：策略目录 `data/raw/raw_source_manifest.json` 指向的 MT5 原始历史 CSV。",
        "- 信号：M30 SMA5/SMA13 交叉，M30 收盘确认，下一根 M30 开盘入场。",
        "- 高周期：使用策略专用 MT5 原始高周期 CSV，时间统一移动到 bar 收盘后再参与上下文，避免未完成 K 线偷看。",
        "- 止损：上一段 M30 SMA13 极值作为 `structural_stop_price`，每笔交易单独计算 `stop_distance`。",
        "- 退出：入场后逐根 M30 检查止损；未触发止损则在下一次反向 M30 交叉确认后的下一根 M30 开盘退出。",
        "- 同一根 K 线同时可能触发止损和计划退出时，按止损优先处理。",
        f"- 报告美元收益按 `{LOT_FOR_REPORT}` lot、合约大小 `{float(metadata['contract_size']):g}` 估算，未扣点差/滑点/手续费。",
        "",
        "## 数据摘要",
        "",
        f"- source_id：`{metadata['source_id']}`",
        f"- symbol：`{metadata['symbol']}`",
        f"- M30 rows：`{metadata['m30_rows']}`",
        f"- replay signals：`{metadata['signals']}`",
        f"- primary StopSpec：`{metadata['stop_range']}`",
        "",
        "## 重点过滤结果",
        "",
        markdown_table(selected[selected_cols], selected_cols, money_cols={"pnl_usd_001", "stop_pnl_usd_001"}),
        "",
        "## 阈值结果",
        "",
        markdown_table(threshold[threshold_cols], threshold_cols, money_cols={"pnl_usd_001", "stop_pnl_usd_001"}),
        "",
        "## 输出文件",
        "",
        "- `raw_stop_replay_trades.csv`：逐笔交易、入场、结构止损、退出原因、实际回放盈亏。",
        "- `raw_stop_replay_selected_summary.csv`：重点过滤汇总。",
        "- `raw_stop_replay_threshold_summary.csv`：固定阈值汇总。",
    ]
    (out_dir / "raw_stop_replay_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_root_report(all_outputs: dict[str, dict[str, pd.DataFrame | dict]]) -> None:
    lines = [
        "# 原始 K 线止损回放计算记录",
        "",
        "日期：2026-07-25",
        "",
        "## 说明",
        "",
        "本轮重新从各策略自己的 MT5 原始历史 CSV 生成 M30 交叉信号、绑定结构止损，并用后续 M30 K 线逐根回放止损与计划退出。",
        "这不是旧的 Stage 代理收益，也不是直接复用候选表里的 `pnl`。",
        "",
    ]
    selected_cols = [
        "strategy",
        "filter",
        "n",
        "pf",
        "test_pf",
        "pnl_usd_001",
        "stop_hits",
        "stop_n",
        "stop_pf",
        "stop_test_pf",
        "stop_pnl_usd_001",
    ]
    all_selected = []
    for strategy, outputs in all_outputs.items():
        selected = outputs["selected_summary"]
        assert isinstance(selected, pd.DataFrame)
        all_selected.append(selected)
    selected_summary = pd.concat(all_selected, ignore_index=True)
    lines.extend(
        [
            "## 重点结果",
            "",
            markdown_table(selected_summary[selected_cols], selected_cols, money_cols={"pnl_usd_001", "stop_pnl_usd_001"}),
            "",
            "## 输出文件",
            "",
        ]
    )
    for strategy in all_outputs:
        lines.append(f"- `{strategy}`: `{strategy}策略/data/validation/raw_stop_replay/raw_stop_replay_report.md`")
    (ROOT / "原始K线止损回放计算记录.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    all_outputs: dict[str, dict[str, pd.DataFrame | dict]] = {}
    for strategy in STRATEGIES:
        outputs = analyze_strategy(strategy)
        write_strategy_outputs(strategy, outputs)
        all_outputs[strategy] = outputs
        selected = outputs["selected_summary"]
        assert isinstance(selected, pd.DataFrame)
        print(f"{strategy}: signals={outputs['metadata']['signals']}")  # type: ignore[index]
        for _, row in selected.iterrows():
            print(
                f"  {row['filter']}: n={int(row['n'])} pf={float(row['pf']):.4f} "
                f"test_pf={float(row['test_pf']):.4f} usd001={float(row['pnl_usd_001']):.2f} "
                f"stop_n={int(row['stop_n'])} stop_usd001={float(row['stop_pnl_usd_001']):.2f}"
            )
    write_root_report(all_outputs)


if __name__ == "__main__":
    main()
