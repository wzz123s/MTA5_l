# -*- coding: utf-8 -*-
"""Diagnose residual EA vs Python signal gaps after time-axis alignment."""
from __future__ import annotations

import argparse
import bisect
import os
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import _current_baseline as cb
import _h2_early_gate_test as h2t
import _m15_h2_combo_test as combo
from _ea_python_signal_diff import EA_ALIGN_DELTA, key_frame, overlap_frame, parse_ea_log, build_python_signals


RESULT_ROOT = os.path.join(ROOT, "data", "results", "ea_python_signal_diff_20260704")
DIAG_CSV = os.path.join(RESULT_ROOT, "ea_gap_diagnosis.csv")


def _build_raw_candidates():
    df, h2, _ = cb.load_market_context()
    q2_pass_set, q2_factor_map, _, _ = h2t.early_precompute(h2, df, 2, False)
    raw_df, accepted = combo.build_candidate_frames(df, q2_pass_set, q2_factor_map)
    raw_df = raw_df.copy()
    raw_df["anchor_time"] = pd.to_datetime(raw_df["date"])
    accepted = accepted.copy()
    accepted["anchor_time"] = pd.to_datetime(accepted["date"])
    return df, h2, raw_df, accepted


def _lookup_bias5(h2: pd.DataFrame, t: pd.Timestamp) -> tuple[pd.Timestamp | None, float | None]:
    times = pd.to_datetime(h2["date"]).tolist()
    idx = bisect.bisect_right(times, pd.Timestamp(t)) - 1
    if idx < 0:
        return None, None
    row = h2.iloc[idx]
    return pd.Timestamp(row["date"]), float(abs((row["close"] - row["SMA_5"]) / row["SMA_5"] * 100.0))


def _rolling_bias5_threshold(h2: pd.DataFrame, t: pd.Timestamp, top_pct: float = 34.0, lookback: int = 500) -> float | None:
    times = pd.to_datetime(h2["date"]).tolist()
    idx = bisect.bisect_right(times, pd.Timestamp(t)) - 1
    if idx < 0:
        return None
    sub = h2.iloc[max(0, idx - lookback + 1) : idx + 1].copy()
    sub = sub[(sub["SMA_5"].notna()) & (sub["SMA_5"] != 0)]
    if len(sub) < 10:
        return None
    bias = ((sub["close"] - sub["SMA_5"]).abs() / sub["SMA_5"] * 100.0).sort_values().reset_index(drop=True)
    q_idx = int(len(bias) * (1.0 - top_pct / 100.0))
    q_idx = max(0, min(q_idx, len(bias) - 1))
    return float(bias.iloc[q_idx])


def _nearest_same_dir(raw_df: pd.DataFrame, t: pd.Timestamp, direction: str, minutes: int = 60) -> pd.Series | None:
    same = raw_df[raw_df["dir"] == direction].copy()
    if same.empty:
        return None
    same["delta_min"] = (pd.to_datetime(same["anchor_time"]) - pd.Timestamp(t)).dt.total_seconds().abs() / 60.0
    same = same[same["delta_min"] <= minutes].sort_values(["delta_min", "anchor_time"])
    if same.empty:
        return None
    return same.iloc[0]


def _find_prev_executed(executed: pd.DataFrame, t: pd.Timestamp) -> pd.Series | None:
    prev = executed[pd.to_datetime(executed["anchor_time"]) < pd.Timestamp(t)].copy()
    if prev.empty:
        return None
    prev = prev.sort_values("anchor_time")
    return prev.iloc[-1]


def diagnose(log_path: str, ea_executable_diag: bool = False) -> pd.DataFrame:
    ea, run_start, run_end = parse_ea_log(log_path)
    ea["aligned_time"] = ea["anchor_time"] + EA_ALIGN_DELTA
    ea = key_frame(ea, "aligned_time")

    strategy = cb.summarize_strategy(ea_executable_diag=ea_executable_diag)
    global_threshold = float(strategy["threshold"])
    py_accepted, py_picked, py_executed, market_end = build_python_signals(ea_executable_diag=ea_executable_diag)
    py_accepted = key_frame(py_accepted)
    py_picked = key_frame(py_picked)
    py_executed = key_frame(py_executed)

    _, h2, raw_df, accepted_df = _build_raw_candidates()
    raw_key = key_frame(raw_df.rename(columns={"anchor_time": "time_for_key"}), "time_for_key")
    accepted_key = key_frame(accepted_df.rename(columns={"anchor_time": "time_for_key"}), "time_for_key")

    run_start_aligned = run_start + EA_ALIGN_DELTA if run_start is not None else py_accepted["anchor_time"].min()
    run_end_aligned = run_end + EA_ALIGN_DELTA if run_end is not None else ea["aligned_time"].max()
    overlap_start = max(run_start_aligned, py_accepted["anchor_time"].min())
    overlap_end = min(run_end_aligned, market_end)

    ea_overlap = ea[(ea["aligned_time"] >= overlap_start) & (ea["aligned_time"] <= overlap_end)].copy()
    py_accepted_overlap = overlap_frame(py_accepted, overlap_start, overlap_end)
    py_picked_overlap = overlap_frame(py_picked, overlap_start, overlap_end)
    py_executed_overlap = overlap_frame(py_executed, overlap_start, overlap_end)

    accepted_keys = set(py_accepted_overlap["key"])
    picked_keys = set(py_picked_overlap["key"])
    executed_keys = set(py_executed_overlap["key"])
    raw_keys = set(raw_key["key"])

    rows = []
    for _, ea_row in ea_overlap.sort_values(["aligned_time", "dir"]).iterrows():
        key = ea_row["key"]
        if key in executed_keys:
            continue

        aligned_t = pd.Timestamp(ea_row["aligned_time"])
        direction = ea_row["dir"]
        row = {
            "aligned_time": aligned_t,
            "dir": direction,
            "ea_trigger": ea_row["trigger"],
            "ea_mode": ea_row["mode_raw"],
            "status_vs_accepted": "shared" if key in accepted_keys else "ea_extra",
            "status_vs_picked": "shared" if key in picked_keys else "ea_extra",
            "status_vs_executed": "shared" if key in executed_keys else "ea_extra",
            "diagnosis": "",
            "python_mode": "",
            "python_trigger": "",
            "python_variant": "",
            "python_sd": None,
            "python_spec_reason": "",
            "python_bias5": None,
            "python_global_threshold": None,
            "python_rolling_threshold": None,
            "python_bias5_at_t_plus_30m": None,
            "nearest_raw_time": "",
            "notes": "",
        }

        exact_raw = raw_key[raw_key["key"] == key]
        exact_acc = accepted_key[accepted_key["key"] == key]
        exact_pick = py_picked_overlap[py_picked_overlap["key"] == key]

        if not exact_raw.empty:
            rr = exact_raw.iloc[0]
            row["python_mode"] = rr["mode"]
            row["python_sd"] = float(rr["sd"])
            row["python_spec_reason"] = rr["spec_reason"]
            row["python_bias5"] = float(rr["Bias_5"])
            if not bool(rr["spec_pass"]):
                row["diagnosis"] = f"spec_{rr['spec_reason']}"
                row["notes"] = "Exact raw candidate exists but spec rejected in Python."
        else:
            near = _nearest_same_dir(raw_df, aligned_t, direction)
            if near is not None:
                row["nearest_raw_time"] = str(pd.Timestamp(near["anchor_time"]))
                row["python_mode"] = near["mode"]
                row["python_sd"] = float(near["sd"])
                row["python_spec_reason"] = near["spec_reason"]
                row["python_bias5"] = float(near["Bias_5"])
                if not bool(near["spec_pass"]):
                    row["diagnosis"] = f"nearest_{near['spec_reason']}"
                    row["notes"] = "No exact raw candidate; nearest same-dir raw candidate is spec-rejected."

        exact_py_acc = py_accepted_overlap[py_accepted_overlap["key"] == key]
        if key in accepted_keys and key not in picked_keys and not exact_py_acc.empty:
            ar = exact_py_acc.iloc[0]
            row["python_mode"] = ar["mode_raw"]
            row["python_trigger"] = ar["trigger"]
            row["python_variant"] = ar["variant"] if "variant" in ar else ""
            if "Bias_5" in ar and pd.notna(ar["Bias_5"]):
                row["python_bias5"] = float(ar["Bias_5"])
            row["python_global_threshold"] = global_threshold
            row["python_rolling_threshold"] = _rolling_bias5_threshold(h2, aligned_t)
            _, bias5_plus_30m = _lookup_bias5(h2, aligned_t + pd.Timedelta(minutes=30))
            row["python_bias5_at_t_plus_30m"] = bias5_plus_30m
            if row["diagnosis"] == "":
                row["diagnosis"] = "layer3_filtered"
                row["notes"] = "Exact accepted signal exists but Python Layer 3 removed it."
            elif row["diagnosis"].startswith("spec_"):
                row["diagnosis"] = f"{row['diagnosis']}_but_diag_accepted"
                row["notes"] = "Exact raw candidate is spec-rejected in baseline Python, but EA executable mode rescues it into accepted before Layer 3."
            if bias5_plus_30m is not None and row["python_rolling_threshold"] is not None and bias5_plus_30m >= row["python_rolling_threshold"]:
                row["diagnosis"] = "layer3_h2_boundary_shift"
                row["notes"] = "Bias_5 at t+30m crosses the rolling Layer 3 threshold, suggesting an H2 boundary timing mismatch."

        if key in picked_keys and key not in executed_keys:
            prev = _find_prev_executed(py_executed_overlap, aligned_t)
            if prev is not None:
                row["diagnosis"] = "executed_blocked_by_active_stage3"
                row["notes"] = (
                    f"Python picked it, but prior executed signal stayed active until "
                    f"{pd.Timestamp(prev['stage3_time'])}."
                )
                row["nearest_raw_time"] = str(pd.Timestamp(prev["anchor_time"]))

        rows.append(row)

    out = pd.DataFrame(rows).sort_values(["aligned_time", "dir"]).reset_index(drop=True)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, help="Path to MT5 tester log file")
    parser.add_argument("--ea-executable-diag", action="store_true", help="Use EA-executable diagnostic rules for Layer 3 and M15 slot1 spec handling")
    args = parser.parse_args()

    os.makedirs(RESULT_ROOT, exist_ok=True)
    out = diagnose(args.log, ea_executable_diag=args.ea_executable_diag)
    out.to_csv(DIAG_CSV, index=False, encoding="utf-8-sig")

    print(out.to_string(index=False))
    print()
    print("Saved:")
    print(DIAG_CSV)


if __name__ == "__main__":
    main()
