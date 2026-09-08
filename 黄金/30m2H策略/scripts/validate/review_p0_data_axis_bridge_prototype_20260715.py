# -*- coding: utf-8 -*-
"""P0 data-axis bridge prototype for MT5-only M15 SLOT1 candidates.

This diagnostic proves whether selected MT5-only rows can be reconstructed as
Python-MT5 raw/accepted/picked candidates from data-axis evidence. It does not
inject MT5 ledger profit and does not modify the main signal snapshots.
"""
from __future__ import annotations


import bisect
import re
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

SIGNAL_ROOT = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714"
SIGNAL_DIR = SIGNAL_ROOT / "python_h2_context_q2early"
H2_CONTEXT = SIGNAL_ROOT / "h2_mt5_barlevel_shift90_context.csv"
M30_SHIFT90 = SIGNAL_ROOT / "m30_prepared_with_mt5_shift90.csv"
M15_CONTEXT = DATA_DIR / "processed" / "m15_context_bars.csv"

FEASIBILITY_DIR = VALIDATION_DIR / "mt5_bridge_signal_chain_feasibility_20260715"
TIME_AXIS_BRIDGE_DIR = VALIDATION_DIR / "m15_slot1_time_axis_bridge_20260714"
OUT_DIR = VALIDATION_DIR / "p0_data_axis_bridge_prototype_20260715"

P0_IDS = ("mt5_0068", "mt5_0005", "mt5_0019")

SPEC_LO = 5.0
SPEC_HI = 35.0
BIAS55_THRESHOLD = 3.0
TOP_PCT = 34.0
H2_LOOKBACK = 500


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def as_float(value: object, default: float = np.nan) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return default
    return float(parsed)


def parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def norm_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"L", "LONG", "BUY", "1"}:
        return "BUY"
    if text in {"S", "SHORT", "SELL", "-1"}:
        return "SELL"
    return text


def py_dir(value: object) -> str:
    direction = norm_dir(value)
    if direction == "BUY":
        return "L"
    if direction == "SELL":
        return "S"
    return direction


def derive_mode(signal_src: object, mode_family: object) -> str:
    text = str(signal_src)
    match = re.search(r"post_n\d+", text)
    if match:
        return match.group(0)
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    family = str(mode_family)
    return family if family and family != "nan" else text


def find_signal_file(*tokens: str) -> Path:
    for path in SIGNAL_DIR.glob("*.csv"):
        name = path.name
        if all(token in name for token in tokens):
            return path
    raise FileNotFoundError(f"Cannot find signal CSV with tokens: {tokens}")


def load_layers() -> dict[str, pd.DataFrame]:
    paths = {
        "raw": SIGNAL_DIR / "raw_candidates.csv",
        "accepted": find_signal_file("Layer1_Layer2"),
        "picked": find_signal_file("Layer3"),
        "stage": find_signal_file("Stage"),
    }
    layers: dict[str, pd.DataFrame] = {}
    for name, path in paths.items():
        frame = read_csv(path).copy()
        frame["date_dt"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["dir_norm"] = frame["dir"].map(norm_dir)
        if "mode" in frame.columns:
            frame["mode_family"] = frame["mode"].astype(str).str.replace(r"\d+$", "", regex=True)
        else:
            frame["mode_family"] = ""
        layers[name] = frame
    return layers


def exact_layer_counts(layers: dict[str, pd.DataFrame], target: pd.Timestamp, direction: str, mode: str) -> dict[str, int]:
    out: dict[str, int] = {}
    mode_family = re.sub(r"\d+$", "", mode)
    for name, frame in layers.items():
        same_time_dir = frame[(frame["date_dt"] == target) & (frame["dir_norm"] == direction)]
        exact_mode = same_time_dir[same_time_dir["mode"].astype(str) == mode] if "mode" in same_time_dir else same_time_dir.iloc[0:0]
        same_family = same_time_dir[same_time_dir["mode_family"].astype(str) == mode_family]
        out[f"current_{name}_same_time_dir_count"] = int(len(same_time_dir))
        out[f"current_{name}_exact_mode_count"] = int(len(exact_mode))
        out[f"current_{name}_same_family_count"] = int(len(same_family))
    return out


def load_seed() -> pd.DataFrame:
    feasibility = read_csv(FEASIBILITY_DIR / "bridge_signal_chain_feasibility.csv")
    feasibility = feasibility[feasibility["mt5_trade_id"].isin(P0_IDS)].copy()

    bridge = read_csv(TIME_AXIS_BRIDGE_DIR / "m15_slot1_time_axis_bridge_candidates.csv")
    bridge = bridge.rename(columns={"remaining_trade_id": "mt5_trade_id"})
    bridge = bridge[bridge["mt5_trade_id"].isin(P0_IDS)].copy()

    bridge_cols = [
        "mt5_trade_id",
        "mode_raw",
        "ledger_fill_price",
        "ledger_actual_stop",
        "processed_m30_prev",
        "processed_m30_next",
        "processed_m15_prev",
        "processed_m15_next",
        "bridge_decision",
    ]
    bridge_cols = [c for c in bridge_cols if c in bridge.columns]
    seed = feasibility.merge(bridge[bridge_cols], on="mt5_trade_id", how="left", suffixes=("", "_bridge"))
    order = {trade_id: idx for idx, trade_id in enumerate(P0_IDS)}
    seed["_order"] = seed["mt5_trade_id"].map(order)
    return seed.sort_values("_order").drop(columns=["_order"]).reset_index(drop=True)


def load_h2_context() -> pd.DataFrame:
    h2 = read_csv(H2_CONTEXT).copy()
    h2["date_dt"] = pd.to_datetime(h2["date"], errors="coerce")
    for col in ["close", "SMA_5", "SMA_13", "SMA_55"]:
        h2[col] = pd.to_numeric(h2[col], errors="coerce")
    h2 = h2.dropna(subset=["date_dt", "close", "SMA_5", "SMA_13", "SMA_55"])
    h2 = h2[(h2["SMA_5"] != 0) & (h2["SMA_13"] != 0) & (h2["SMA_55"] != 0)].copy()
    h2["Bias_5_calc"] = (h2["close"] - h2["SMA_5"]).abs() / h2["SMA_5"] * 100.0
    h2["Bias_13_calc"] = (h2["close"] - h2["SMA_13"]).abs() / h2["SMA_13"] * 100.0
    h2["Bias_55_calc"] = (h2["close"] - h2["SMA_55"]).abs() / h2["SMA_55"] * 100.0
    return h2.sort_values("date_dt").reset_index(drop=True)


def rolling_threshold(values: list[float], top_pct: float) -> float:
    if len(values) < 10:
        return np.nan
    arr = np.sort(np.asarray(values, dtype=float))
    idx = int(np.floor(len(arr) * (1.0 - top_pct / 100.0)))
    idx = max(0, min(idx, len(arr) - 1))
    return float(arr[idx])


def h2_eval(h2: pd.DataFrame, eval_time: pd.Timestamp) -> dict[str, object]:
    h2_times = h2["date_dt"].tolist()
    idx = bisect.bisect_right(h2_times, eval_time) - 1
    if idx < 0:
        return {
            "h2_context_available": False,
            "h2_lookup_time": pd.NaT,
            "h2_source_bar_time": "",
            "h2_close": np.nan,
            "h2_sma5": np.nan,
            "h2_sma13": np.nan,
            "h2_sma55": np.nan,
            "Bias_5": np.nan,
            "Bias_13": np.nan,
            "Bias_55": np.nan,
            "layer1_pass": False,
            "layer3_eval_time": eval_time,
            "layer3_threshold_ea": np.nan,
            "layer3_hist_count": 0,
            "layer3_pass_ea": False,
        }

    row = h2.iloc[idx]
    start = max(0, idx - H2_LOOKBACK + 1)
    hist = h2["Bias_5_calc"].iloc[start : idx + 1].dropna().astype(float).tolist()
    threshold = rolling_threshold(hist, TOP_PCT)
    bias5 = float(row["Bias_5_calc"])
    layer3_pass = True if pd.isna(threshold) else bool(bias5 >= threshold)
    bias55 = float(row["Bias_55_calc"])

    return {
        "h2_context_available": True,
        "h2_lookup_time": row["date_dt"],
        "h2_source_bar_time": row.get("source_bar_time", ""),
        "h2_close": float(row["close"]),
        "h2_sma5": float(row["SMA_5"]),
        "h2_sma13": float(row["SMA_13"]),
        "h2_sma55": float(row["SMA_55"]),
        "Bias_5": bias5,
        "Bias_13": float(row["Bias_13_calc"]),
        "Bias_55": bias55,
        "layer1_pass": bool(bias55 > BIAS55_THRESHOLD),
        "layer3_eval_time": eval_time,
        "layer3_threshold_ea": threshold,
        "layer3_hist_count": int(len(hist)),
        "layer3_pass_ea": layer3_pass,
    }


def load_time_sets() -> tuple[set[pd.Timestamp], set[pd.Timestamp], pd.DataFrame]:
    m30 = read_csv(M30_SHIFT90).copy()
    m30["date_dt"] = pd.to_datetime(m30["date"], errors="coerce")
    m15 = read_csv(M15_CONTEXT).copy()
    m15["date_dt"] = pd.to_datetime(m15["date"], errors="coerce")
    return set(m30["date_dt"].dropna()), set(m15["date_dt"].dropna()), m30


def spec_reason(sd: float) -> str:
    if SPEC_LO <= sd <= SPEC_HI:
        return "ok"
    if sd > SPEC_HI:
        return "too_wide"
    return "too_tight"


def bridge_action(row: pd.Series) -> str:
    missing_m30 = not bool(row["m30_has_aligned_time"])
    missing_m15 = not bool(row["m15_has_entry_bar_minute"])
    current_raw = int(row["current_raw_same_time_dir_count"])
    if missing_m30 and missing_m15:
        return "backfill_m30_shift90_and_m15_entry_window"
    if missing_m15 and current_raw > 0:
        return "backfill_m15_entry_window_then_rebuild_m15_slot1_over_existing_m30_parent"
    if missing_m15:
        return "backfill_m15_entry_window_then_add_m15_slot1_bridge_parent"
    if missing_m30:
        return "backfill_m30_shift90_anchor"
    return "data_axis_available_run_full_chain_replay"


def build_bridge_rows() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    seed = load_seed()
    layers = load_layers()
    h2 = load_h2_context()
    m30_dates, m15_dates, m30 = load_time_sets()

    rows: list[dict[str, object]] = []
    for _, src in seed.iterrows():
        aligned_time = pd.to_datetime(src["aligned_time"], errors="coerce")
        log_time_plus90 = pd.to_datetime(src["log_time_plus90"], errors="coerce")
        entry_bar_minute = log_time_plus90.floor("min") if not pd.isna(log_time_plus90) else pd.NaT
        direction = norm_dir(src["dir_norm"])
        mode = derive_mode(src.get("signal_src", ""), src.get("mode_family", ""))
        entry = as_float(src.get("ledger_entry"))
        stop = as_float(src.get("ledger_stop"))
        sd = abs(entry - stop)
        dir_short = py_dir(direction)
        side_valid = bool((direction == "BUY" and entry > stop) or (direction == "SELL" and entry < stop))
        spec_pass = bool(SPEC_LO <= sd <= SPEC_HI)
        m30_future_rows = int((m30["date_dt"] > aligned_time).sum()) if not pd.isna(aligned_time) else 0
        eval_time = aligned_time
        h2_status = h2_eval(h2, eval_time)

        current_counts = exact_layer_counts(layers, aligned_time, direction, mode)
        row = {
            "mt5_trade_id": src["mt5_trade_id"],
            "priority": src.get("priority", ""),
            "date": aligned_time,
            "entry_time": log_time_plus90,
            "entry_bar_minute": entry_bar_minute,
            "raw_anchor": pd.to_datetime(src.get("raw_anchor"), errors="coerce"),
            "signal_anchor_time": pd.to_datetime(src.get("signal_anchor_time"), errors="coerce"),
            "log_time": pd.to_datetime(src.get("log_time"), errors="coerce"),
            "mode": mode,
            "mode_family": src.get("mode_family", ""),
            "signal_src": src.get("signal_src", ""),
            "dir": dir_short,
            "dir_norm": direction,
            "trigger": src.get("trigger_family", "M15 SLOT1"),
            "variant": "p0_data_axis_m15_bridge",
            "entry": entry,
            "stop": stop,
            "sd": sd,
            "ledger_stop_pts_spec": as_float(src.get("ledger_stop_pts_spec")),
            "ledger_sd_diff": sd - as_float(src.get("ledger_stop_pts_spec")),
            "side_valid": side_valid,
            "spec_pass": spec_pass,
            "spec_reason": spec_reason(sd),
            "raw_bridge_pass": bool(side_valid and h2_status["h2_context_available"]),
            "accepted_bridge_pass": bool(side_valid and h2_status["h2_context_available"] and h2_status["layer1_pass"] and spec_pass),
            "picked_bridge_pass": bool(
                side_valid
                and h2_status["h2_context_available"]
                and h2_status["layer1_pass"]
                and spec_pass
                and h2_status["layer3_pass_ea"]
            ),
            "processed_m30_has_shifted_anchor_reported": parse_bool(src.get("processed_m30_has_shifted_anchor")),
            "processed_m15_has_log_plus90_reported": parse_bool(src.get("processed_m15_has_log_plus90")),
            "m30_has_aligned_time": aligned_time in m30_dates,
            "m15_has_entry_bar_exact": log_time_plus90 in m15_dates,
            "m15_has_entry_bar_minute": entry_bar_minute in m15_dates,
            "m30_future_rows_after_signal": m30_future_rows,
            "stage_replay_min_ready_current": bool(
                side_valid
                and spec_pass
                and h2_status["layer1_pass"]
                and h2_status["layer3_pass_ea"]
                and aligned_time in m30_dates
                and m30_future_rows > 0
            ),
            "full_chain_ready_now": False,
        }
        row.update(h2_status)
        row.update(current_counts)
        row["full_chain_ready_now"] = bool(
            row["picked_bridge_pass"] and row["m30_has_aligned_time"] and row["m15_has_entry_bar_minute"]
        )
        rows.append(row)

    raw_bridge = pd.DataFrame(rows)
    raw_bridge["required_m15_window_start"] = pd.to_datetime(raw_bridge["date"]) - pd.Timedelta(minutes=30)
    raw_bridge["required_m15_window_end"] = pd.to_datetime(raw_bridge["date"])
    raw_bridge["required_m30_time"] = pd.to_datetime(raw_bridge["date"])
    raw_bridge["required_rule_change"] = raw_bridge.apply(bridge_action, axis=1)
    raw_bridge["data_source_requirement"] = np.where(
        raw_bridge["m15_has_entry_bar_minute"],
        "current_m15_context_has_entry_bar",
        "export_or_backfill_MT5_M15_bars_for_required_m15_window",
    )

    acceptance_cols = [
        "mt5_trade_id",
        "date",
        "mode",
        "dir",
        "trigger",
        "entry",
        "stop",
        "sd",
        "side_valid",
        "spec_pass",
        "spec_reason",
        "Bias_55",
        "layer1_pass",
        "raw_bridge_pass",
        "accepted_bridge_pass",
        "picked_bridge_pass",
        "current_raw_same_time_dir_count",
        "current_raw_exact_mode_count",
        "current_accepted_same_time_dir_count",
        "current_picked_same_time_dir_count",
        "current_stage_same_time_dir_count",
    ]
    acceptance = raw_bridge[[c for c in acceptance_cols if c in raw_bridge.columns]].copy()

    layer3_cols = [
        "mt5_trade_id",
        "date",
        "trigger",
        "layer3_eval_time",
        "h2_lookup_time",
        "h2_source_bar_time",
        "Bias_5",
        "layer3_threshold_ea",
        "layer3_hist_count",
        "layer3_pass_ea",
        "accepted_bridge_pass",
        "picked_bridge_pass",
    ]
    layer3 = raw_bridge[[c for c in layer3_cols if c in raw_bridge.columns]].copy()

    missing_cols = [
        "mt5_trade_id",
        "date",
        "entry_time",
        "entry_bar_minute",
        "m30_has_aligned_time",
        "m15_has_entry_bar_exact",
        "m15_has_entry_bar_minute",
        "required_m30_time",
        "required_m15_window_start",
        "required_m15_window_end",
        "stage_replay_min_ready_current",
        "full_chain_ready_now",
        "required_rule_change",
        "data_source_requirement",
    ]
    missing = raw_bridge[[c for c in missing_cols if c in raw_bridge.columns]].copy()
    return raw_bridge, acceptance, layer3, missing


def build_report(raw_bridge: pd.DataFrame, acceptance: pd.DataFrame, layer3: pd.DataFrame, missing: pd.DataFrame) -> str:
    pass_count = int(raw_bridge["picked_bridge_pass"].sum())
    ready_now = int(raw_bridge["full_chain_ready_now"].sum())
    accepted_count = int(raw_bridge["accepted_bridge_pass"].sum())
    missing_m15 = int((~raw_bridge["m15_has_entry_bar_minute"]).sum())
    missing_m30 = int((~raw_bridge["m30_has_aligned_time"]).sum())

    decision = []
    if pass_count == len(raw_bridge) and ready_now == len(raw_bridge):
        decision.append("All P0 rows can enter a full-chain replay immediately.")
    elif pass_count == len(raw_bridge):
        decision.append("All P0 rows pass raw/accepted/Layer3 reconstruction, but data-axis backfill is still required before a full-chain replay.")
    else:
        decision.append("At least one P0 row fails accepted/Layer3 reconstruction; do not enter full-chain replay before resolving the failed boundary.")

    lines = [
        "# P0 data-axis bridge prototype review",
        "",
        "## Scope",
        "",
        "- Candidates: `mt5_0068`, `mt5_0005`, `mt5_0019`.",
        "- This prototype uses MT5 ledger signal entry/stop and time-axis metadata only.",
        "- It does not use MT5 ledger net profit to create Python PnL.",
        "- Layer3 uses the current EA-executable H2 rolling threshold: top 34%, lookback 500 H2 rows.",
        "",
        "## Summary",
        "",
        f"- Raw bridge candidates: `{len(raw_bridge)}`.",
        f"- Accepted bridge pass: `{accepted_count}/{len(raw_bridge)}`.",
        f"- Picked bridge pass: `{pass_count}/{len(raw_bridge)}`.",
        f"- Full-chain ready now: `{ready_now}/{len(raw_bridge)}`.",
        f"- Missing M15 entry window rows: `{missing_m15}`.",
        f"- Missing M30 aligned rows: `{missing_m30}`.",
        "",
        "## Decision",
        "",
        f"- {decision[0]}",
        "- Next mergeable step must be data backfill or explicit data-axis bridge generation, followed by a real Stage/dynamic-risk replay.",
        "",
        "## Acceptance Matrix",
        "",
        markdown_table(
            acceptance[
                [
                    "mt5_trade_id",
                    "date",
                    "mode",
                    "dir",
                    "sd",
                    "spec_pass",
                    "Bias_55",
                    "layer1_pass",
                    "raw_bridge_pass",
                    "accepted_bridge_pass",
                    "picked_bridge_pass",
                ]
                if "picked_bridge_pass" in acceptance.columns
                else acceptance.columns
            ],
            10,
        ),
        "",
        "## Layer3 Matrix",
        "",
        markdown_table(layer3, 10),
        "",
        "## Missing Data Requirements",
        "",
        markdown_table(missing, 10),
        "",
        "## Output Files",
        "",
        "- `p0_bridge_raw_candidates.csv`",
        "- `p0_bridge_acceptance_matrix.csv`",
        "- `p0_bridge_layer3_matrix.csv`",
        "- `p0_bridge_missing_data_requirements.csv`",
    ]
    return "\n".join(lines)


def main() -> None:
    raw_bridge, acceptance, layer3, missing = build_bridge_rows()
    export_csv(raw_bridge, OUT_DIR / "p0_bridge_raw_candidates.csv")
    export_csv(acceptance, OUT_DIR / "p0_bridge_acceptance_matrix.csv")
    export_csv(layer3, OUT_DIR / "p0_bridge_layer3_matrix.csv")
    export_csv(missing, OUT_DIR / "p0_bridge_missing_data_requirements.csv")
    write_text(OUT_DIR / "p0_data_axis_bridge_prototype_review.md", build_report(raw_bridge, acceptance, layer3, missing))
    write_text(OUT_DIR / "README.md", "# P0 data-axis bridge prototype\n\nSee `p0_data_axis_bridge_prototype_review.md`.\n")
    print(f"Wrote {OUT_DIR}")


if __name__ == "__main__":
    main()
