# -*- coding: utf-8 -*-
"""Audit the mt5_0068 Layer3/time-axis boundary.

The previous P0 bridge prototype showed that mt5_0068 can pass StopSpec and
Layer1, but fails Layer3 under the current +90 M15 SLOT1 evaluation time. This
script isolates whether that failure is a true Layer3 rejection or a mixed
time-axis artifact.
"""
from __future__ import annotations


import bisect
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = STRATEGY_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
VALIDATION_DIR = DATA_DIR / "validation"

SIGNAL_ROOT = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714"
SIGNAL_DIR = SIGNAL_ROOT / "python_h2_context_q2early"
H2_CONTEXT = SIGNAL_ROOT / "h2_mt5_barlevel_shift90_context.csv"
M30_SHIFT90 = SIGNAL_ROOT / "m30_prepared_with_mt5_shift90.csv"
M15_CONTEXT = PROCESSED_DIR / "m15_context_bars.csv"

P0_DIR = VALIDATION_DIR / "p0_data_axis_bridge_prototype_20260715"
OUT_DIR = VALIDATION_DIR / "mt5_0068_layer3_time_axis_boundary_20260715"

TARGET_ID = "mt5_0068"
TOP_PCT = 34.0
H2_LOOKBACK = 500
BIAS55_THRESHOLD = 3.0


def read_csv(path: Path, encoding: str = "utf-8-sig") -> pd.DataFrame:
    return pd.read_csv(path, encoding=encoding, low_memory=False)


def read_market_csv(path: Path) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "gbk", "gb18030", "utf-8"):
        try:
            df = pd.read_csv(path, encoding=encoding, low_memory=False)
            break
        except UnicodeDecodeError:
            continue
    else:
        df = pd.read_csv(path, low_memory=False)
    df = df.copy()
    if "date" not in df.columns:
        base_cols = [
            "date",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "spread",
            "real_volume",
            "symbol",
            "time_diff",
        ]
        rename = {old: new for old, new in zip(df.columns[: len(base_cols)], base_cols)}
        df = df.rename(columns=rename)
    df["date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["open", "high", "low", "close", "volume", "spread"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("date_dt").reset_index(drop=True)


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


def load_target() -> pd.Series:
    p0 = read_csv(P0_DIR / "p0_bridge_raw_candidates.csv")
    row = p0[p0["mt5_trade_id"].astype(str) == TARGET_ID]
    if row.empty:
        raise RuntimeError(f"{TARGET_ID} not found in P0 bridge output")
    out = row.iloc[0].copy()
    for col in [
        "date",
        "entry_time",
        "entry_bar_minute",
        "raw_anchor",
        "signal_anchor_time",
        "log_time",
        "required_m15_window_start",
        "required_m15_window_end",
        "required_m30_time",
    ]:
        if col in out.index:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    return out


def load_h2() -> pd.DataFrame:
    h2 = read_csv(H2_CONTEXT).copy()
    h2["date_dt"] = pd.to_datetime(h2["date"], errors="coerce")
    h2["source_bar_time_dt"] = pd.to_datetime(h2.get("source_bar_time", pd.NaT), errors="coerce")
    for col in ["close", "SMA_5", "SMA_13", "SMA_55"]:
        h2[col] = pd.to_numeric(h2[col], errors="coerce")
    h2 = h2.dropna(subset=["date_dt", "close", "SMA_5", "SMA_13", "SMA_55"])
    h2 = h2[(h2["SMA_5"] != 0) & (h2["SMA_13"] != 0) & (h2["SMA_55"] != 0)].copy()
    h2["Bias_5"] = (h2["close"] - h2["SMA_5"]).abs() / h2["SMA_5"] * 100.0
    h2["Bias_13"] = (h2["close"] - h2["SMA_13"]).abs() / h2["SMA_13"] * 100.0
    h2["Bias_55"] = (h2["close"] - h2["SMA_55"]).abs() / h2["SMA_55"] * 100.0
    return h2.sort_values("date_dt").reset_index(drop=True)


def rolling_threshold(values: list[float]) -> float:
    if len(values) < 10:
        return np.nan
    arr = np.sort(np.asarray(values, dtype=float))
    idx = int(np.floor(len(arr) * (1.0 - TOP_PCT / 100.0)))
    idx = max(0, min(idx, len(arr) - 1))
    return float(arr[idx])


def h2_eval(h2: pd.DataFrame, eval_time: pd.Timestamp) -> dict[str, object]:
    h2_times = h2["date_dt"].tolist()
    idx = bisect.bisect_right(h2_times, eval_time) - 1
    if idx < 0:
        return {
            "eval_time": eval_time,
            "h2_lookup_time": pd.NaT,
            "h2_source_bar_time": pd.NaT,
            "Bias_5": np.nan,
            "Bias_13": np.nan,
            "Bias_55": np.nan,
            "layer1_pass": False,
            "layer3_threshold": np.nan,
            "layer3_pass": False,
            "hist_count": 0,
        }
    row = h2.iloc[idx]
    start = max(0, idx - H2_LOOKBACK + 1)
    hist = h2["Bias_5"].iloc[start : idx + 1].dropna().astype(float).tolist()
    threshold = rolling_threshold(hist)
    bias5 = float(row["Bias_5"])
    return {
        "eval_time": eval_time,
        "h2_lookup_time": row["date_dt"],
        "h2_source_bar_time": row["source_bar_time_dt"],
        "h2_close": float(row["close"]),
        "h2_sma5": float(row["SMA_5"]),
        "h2_sma13": float(row["SMA_13"]),
        "h2_sma55": float(row["SMA_55"]),
        "Bias_5": bias5,
        "Bias_13": float(row["Bias_13"]),
        "Bias_55": float(row["Bias_55"]),
        "layer1_pass": bool(float(row["Bias_55"]) > BIAS55_THRESHOLD),
        "layer3_threshold": threshold,
        "layer3_pass": bool(True if pd.isna(threshold) else bias5 >= threshold),
        "hist_count": int(len(hist)),
    }


def exact_or_nearest(frame: pd.DataFrame, target: pd.Timestamp, label: str) -> dict[str, object]:
    out = {
        f"{label}_target": target,
        f"{label}_exact_exists": False,
        f"{label}_nearest_before": pd.NaT,
        f"{label}_nearest_after": pd.NaT,
        f"{label}_nearest_before_delta_min": np.nan,
        f"{label}_nearest_after_delta_min": np.nan,
    }
    times = pd.to_datetime(frame["date_dt"], errors="coerce").dropna().drop_duplicates().sort_values()
    if times.empty or pd.isna(target):
        return out
    out[f"{label}_exact_exists"] = bool((times == target).any())
    before = times[times <= target]
    after = times[times >= target]
    if not before.empty:
        value = before.iloc[-1]
        out[f"{label}_nearest_before"] = value
        out[f"{label}_nearest_before_delta_min"] = float((target - value).total_seconds() / 60.0)
    if not after.empty:
        value = after.iloc[0]
        out[f"{label}_nearest_after"] = value
        out[f"{label}_nearest_after_delta_min"] = float((value - target).total_seconds() / 60.0)
    return out


def rows_around(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, source: str) -> pd.DataFrame:
    cols = [c for c in ["date_dt", "open", "high", "low", "close", "volume", "spread", "SMA_5", "SMA_13"] if c in frame.columns]
    out = frame[(frame["date_dt"] >= start) & (frame["date_dt"] <= end)][cols].copy()
    out.insert(0, "source", source)
    return out.reset_index(drop=True)


def build_time_axis_summary(target: pd.Series) -> pd.DataFrame:
    raw_anchor = pd.Timestamp(target["raw_anchor"])
    log_time = pd.Timestamp(target["log_time"])
    rows = [
        {
            "item": "raw_anchor",
            "raw_time": raw_anchor,
            "plus90": raw_anchor + pd.Timedelta(minutes=90),
            "plus120": raw_anchor + pd.Timedelta(minutes=120),
            "current_bridge_uses": "plus90",
        },
        {
            "item": "m15_log_time",
            "raw_time": log_time,
            "plus90": log_time + pd.Timedelta(minutes=90),
            "plus120": log_time + pd.Timedelta(minutes=120),
            "current_bridge_uses": "plus90",
        },
    ]
    return pd.DataFrame(rows)


def build_presence_matrix(target: pd.Series) -> pd.DataFrame:
    raw_m15 = read_market_csv(RAW_DIR / "XAUUSDm15.csv")
    raw_m30 = read_market_csv(RAW_DIR / "XAUUSDm30.csv")
    proc_m15 = read_market_csv(M15_CONTEXT)
    shift_m30 = read_market_csv(M30_SHIFT90)
    h2 = load_h2()

    raw_anchor = pd.Timestamp(target["raw_anchor"])
    log_time = pd.Timestamp(target["log_time"])
    checks = [
        ("m15_log_raw", "raw_m15", log_time, raw_m15),
        ("m15_log_plus90", "processed_m15", log_time + pd.Timedelta(minutes=90), proc_m15),
        ("m15_log_plus120", "processed_m15", log_time + pd.Timedelta(minutes=120), proc_m15),
        ("m30_anchor_raw", "raw_m30", raw_anchor, raw_m30),
        ("m30_anchor_plus90", "shift_m30", raw_anchor + pd.Timedelta(minutes=90), shift_m30),
        ("m30_anchor_plus120", "shift_m30", raw_anchor + pd.Timedelta(minutes=120), shift_m30),
        ("h2_eval_plus90", "h2_context", raw_anchor + pd.Timedelta(minutes=90), h2.rename(columns={"date_dt": "date_dt"})),
        ("h2_eval_plus120", "h2_context", raw_anchor + pd.Timedelta(minutes=120), h2.rename(columns={"date_dt": "date_dt"})),
    ]
    rows = []
    for name, source, ts, frame in checks:
        row = {"check": name, "source": source}
        row.update(exact_or_nearest(frame, ts, "time"))
        rows.append(row)
    return pd.DataFrame(rows)


def build_window_matrix(target: pd.Series) -> pd.DataFrame:
    raw_m15 = read_market_csv(RAW_DIR / "XAUUSDm15.csv")
    raw_m30 = read_market_csv(RAW_DIR / "XAUUSDm30.csv")
    proc_m15 = read_market_csv(M15_CONTEXT)
    shift_m30 = read_market_csv(M30_SHIFT90)

    raw_anchor = pd.Timestamp(target["raw_anchor"])
    log_time = pd.Timestamp(target["log_time"])
    frames = [
        rows_around(raw_m15, log_time - pd.Timedelta(minutes=15), raw_anchor, "raw_m15_server_time"),
        rows_around(proc_m15, log_time + pd.Timedelta(minutes=90), raw_anchor + pd.Timedelta(minutes=90), "processed_m15_plus90_window"),
        rows_around(proc_m15, log_time + pd.Timedelta(minutes=120), raw_anchor + pd.Timedelta(minutes=120), "processed_m15_plus120_window"),
        rows_around(raw_m30, raw_anchor - pd.Timedelta(minutes=60), raw_anchor + pd.Timedelta(minutes=60), "raw_m30_server_time"),
        rows_around(shift_m30, raw_anchor + pd.Timedelta(minutes=30), raw_anchor + pd.Timedelta(minutes=150), "shift_m30_window"),
    ]
    out = pd.concat(frames, ignore_index=True, sort=False)
    out["ledger_entry_inside_hilo"] = (
        (pd.to_numeric(out.get("low"), errors="coerce") <= float(target["entry"]))
        & (pd.to_numeric(out.get("high"), errors="coerce") >= float(target["entry"]))
    )
    out["ledger_stop_inside_hilo"] = (
        (pd.to_numeric(out.get("low"), errors="coerce") <= float(target["stop"]))
        & (pd.to_numeric(out.get("high"), errors="coerce") >= float(target["stop"]))
    )
    return out


def build_layer3_matrix(target: pd.Series) -> pd.DataFrame:
    h2 = load_h2()
    raw_anchor = pd.Timestamp(target["raw_anchor"])
    log_time = pd.Timestamp(target["log_time"])
    aligned_plus90 = raw_anchor + pd.Timedelta(minutes=90)
    aligned_plus120 = raw_anchor + pd.Timedelta(minutes=120)
    log_plus90 = log_time + pd.Timedelta(minutes=90)
    log_plus120 = log_time + pd.Timedelta(minutes=120)
    variants = [
        ("current_m15_slot1_aligned_plus90", aligned_plus90, "Current bridge date/eval_time; this is the P0 prototype result."),
        ("m15_entry_log_plus90_lookup", log_plus90, "Entry-bar +90 boundary; H2 lookup falls to latest <= 00:45."),
        ("m15_entry_log_plus120_lookup", log_plus120, "Processed M15 +2h boundary; still evaluates at H2 01:00."),
        ("m30_anchor_plus120", aligned_plus120, "Consistent raw +2h M30 processed boundary."),
        ("m30_close_rule_on_plus90_date_plus30", aligned_plus90 + pd.Timedelta(minutes=30), "If the +90 date were treated like M30 CLOSE Layer3 shift."),
        ("raw_anchor_no_shift", raw_anchor, "Server-time raw anchor only, diagnostic control."),
    ]
    rows = []
    for name, eval_time, note in variants:
        row = {"variant": name, "note": note}
        row.update(h2_eval(h2, eval_time))
        rows.append(row)
    out = pd.DataFrame(rows)
    out["threshold_margin"] = out["Bias_5"] - out["layer3_threshold"]
    return out


def load_current_raw_window(target: pd.Series) -> pd.DataFrame:
    raw = read_csv(SIGNAL_DIR / "raw_candidates.csv")
    raw = raw.copy()
    raw["date_dt"] = pd.to_datetime(raw["date"], errors="coerce")
    target_time = pd.Timestamp(target["date"])
    out = raw[
        (raw["date_dt"] >= target_time - pd.Timedelta(days=5))
        & (raw["date_dt"] <= target_time + pd.Timedelta(hours=3))
        & (raw["dir"].astype(str).isin(["L", "BUY"]))
    ].copy()
    cols = [
        "date",
        "entry_time",
        "mode",
        "dir",
        "entry",
        "stop",
        "sd",
        "variant",
        "Bias_5",
        "Bias_55",
        "spec_pass",
        "spec_reason",
    ]
    return out[[c for c in cols if c in out.columns]].reset_index(drop=True)


def build_decision(target: pd.Series, layer3: pd.DataFrame, presence: pd.DataFrame) -> pd.DataFrame:
    current = layer3[layer3["variant"] == "current_m15_slot1_aligned_plus90"].iloc[0]
    plus120 = layer3[layer3["variant"] == "m30_anchor_plus120"].iloc[0]
    plus90_m30_exists = bool(
        presence.loc[presence["check"] == "m30_anchor_plus90", "time_exact_exists"].iloc[0]
    )
    plus120_m30_exists = bool(
        presence.loc[presence["check"] == "m30_anchor_plus120", "time_exact_exists"].iloc[0]
    )
    plus90_m15_exists = bool(
        presence.loc[presence["check"] == "m15_log_plus90", "time_exact_exists"].iloc[0]
    )
    plus120_m15_exists = bool(
        presence.loc[presence["check"] == "m15_log_plus120", "time_exact_exists"].iloc[0]
    )
    entry = float(target["entry"])
    stop = float(target["stop"])
    return pd.DataFrame(
        [
            {
                "item": TARGET_ID,
                "current_plus90_layer3_pass": bool(current["layer3_pass"]),
                "current_plus90_bias5": float(current["Bias_5"]),
                "current_plus90_threshold": float(current["layer3_threshold"]),
                "plus120_layer3_pass": bool(plus120["layer3_pass"]),
                "plus120_bias5": float(plus120["Bias_5"]),
                "plus120_threshold": float(plus120["layer3_threshold"]),
                "plus90_m30_exists": plus90_m30_exists,
                "plus90_m15_exists": plus90_m15_exists,
                "plus120_m30_exists": plus120_m30_exists,
                "plus120_m15_exists": plus120_m15_exists,
                "ledger_entry": entry,
                "ledger_stop": stop,
                "decision": "do_not_include_in_current_plus90_full_chain",
                "reason": "Current +90 M15 SLOT1 Layer3 fails; +120 can pass but that is a time-axis semantics change, not a Layer3 fix.",
                "next_step": "Run a Python-MT5 +90/+120 time-axis normalization gate before any merge involving mt5_0068; P0 subset can only use mt5_0005/mt5_0019 for now.",
            }
        ]
    )


def build_report(
    target: pd.Series,
    time_axis: pd.DataFrame,
    presence: pd.DataFrame,
    layer3: pd.DataFrame,
    windows: pd.DataFrame,
    decision: pd.DataFrame,
) -> str:
    current = decision.iloc[0]
    lines = [
        "# mt5_0068 Layer3/time-axis boundary audit",
        "",
        "## Scope",
        "",
        "- Target: `mt5_0068`.",
        "- Purpose: separate true Layer3 rejection from mixed +90/+120 data-axis effects.",
        "- This is read-only and does not modify signal, Stage, dynamic-risk, or EA files.",
        "",
        "## Decision",
        "",
        f"- Current +90 M15 SLOT1 Layer3 pass: `{current['current_plus90_layer3_pass']}` "
        f"(`Bias_5={current['current_plus90_bias5']:.5f}`, threshold `{current['current_plus90_threshold']:.5f}`).",
        f"- +120/M30-aligned Layer3 pass: `{current['plus120_layer3_pass']}` "
        f"(`Bias_5={current['plus120_bias5']:.5f}`, threshold `{current['plus120_threshold']:.5f}`).",
        "- `mt5_0068` must not be injected into the current +90 full-chain prototype.",
        "- Passing under +120 is evidence of a time-axis semantics issue, not permission to loosen Layer3.",
        "",
        "## Target Signal",
        "",
        markdown_table(
            pd.DataFrame(
                [
                    {
                        "mt5_trade_id": TARGET_ID,
                        "raw_anchor": target["raw_anchor"],
                        "aligned_plus90": target["date"],
                        "log_time": target["log_time"],
                        "log_plus90": target["entry_time"],
                        "entry": target["entry"],
                        "stop": target["stop"],
                        "sd": target["sd"],
                    }
                ]
            )
        ),
        "",
        "## Time-Axis Summary",
        "",
        markdown_table(time_axis),
        "",
        "## Presence Matrix",
        "",
        markdown_table(presence),
        "",
        "## Layer3 Eval Matrix",
        "",
        markdown_table(
            layer3[
                [
                    "variant",
                    "eval_time",
                    "h2_lookup_time",
                    "h2_source_bar_time",
                    "Bias_5",
                    "layer3_threshold",
                    "threshold_margin",
                    "layer3_pass",
                    "note",
                ]
            ],
            20,
        ),
        "",
        "## Raw/Processed Window Evidence",
        "",
        markdown_table(windows, 30),
        "",
        "## Output Files",
        "",
        "- `mt5_0068_time_axis_summary.csv`",
        "- `mt5_0068_presence_matrix.csv`",
        "- `mt5_0068_layer3_eval_matrix.csv`",
        "- `mt5_0068_raw_processed_windows.csv`",
        "- `mt5_0068_current_raw_window.csv`",
        "- `mt5_0068_boundary_decision.csv`",
    ]
    return "\n".join(lines)


def main() -> None:
    target = load_target()
    time_axis = build_time_axis_summary(target)
    presence = build_presence_matrix(target)
    windows = build_window_matrix(target)
    layer3 = build_layer3_matrix(target)
    current_raw = load_current_raw_window(target)
    decision = build_decision(target, layer3, presence)

    export_csv(time_axis, OUT_DIR / "mt5_0068_time_axis_summary.csv")
    export_csv(presence, OUT_DIR / "mt5_0068_presence_matrix.csv")
    export_csv(layer3, OUT_DIR / "mt5_0068_layer3_eval_matrix.csv")
    export_csv(windows, OUT_DIR / "mt5_0068_raw_processed_windows.csv")
    export_csv(current_raw, OUT_DIR / "mt5_0068_current_raw_window.csv")
    export_csv(decision, OUT_DIR / "mt5_0068_boundary_decision.csv")
    write_text(
        OUT_DIR / "mt5_0068_layer3_time_axis_boundary_review.md",
        build_report(target, time_axis, presence, layer3, windows, decision),
    )
    write_text(OUT_DIR / "README.md", "# mt5_0068 Layer3/time-axis boundary audit\n\nSee review markdown.\n")
    print(f"Wrote {OUT_DIR}")


if __name__ == "__main__":
    main()
