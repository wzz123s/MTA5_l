# -*- coding: utf-8 -*-
"""Compare EA tester signal lines against the current Python mainline signals."""
from __future__ import annotations

import argparse
import os
import re
import sys

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts import _current_baseline as cb


RESULT_ROOT = os.path.join(ROOT, "data", "results", "ea_python_signal_diff_20260704")
EA_SIGNALS_CSV = os.path.join(RESULT_ROOT, "ea_signals.csv")
EA_ALIGN_DIAG_CSV = os.path.join(RESULT_ROOT, "ea_signal_alignment_diag.csv")
PY_ACCEPTED_CSV = os.path.join(RESULT_ROOT, "python_accepted_signals.csv")
PY_PICKED_CSV = os.path.join(RESULT_ROOT, "python_picked_signals.csv")
PY_EXECUTED_CSV = os.path.join(RESULT_ROOT, "python_executed_signals.csv")
EA_EXTRA_CSV = os.path.join(RESULT_ROOT, "ea_extra_vs_python_executed.csv")
PY_MISSING_CSV = os.path.join(RESULT_ROOT, "python_executed_missing_vs_ea.csv")
MODE_MISMATCH_CSV = os.path.join(RESULT_ROOT, "shared_anchor_mode_mismatch.csv")
EA_ALIGN_DELTA = pd.Timedelta(minutes=90)


SIGNAL_RE = re.compile(
    r"""
    \)\s+
    (?P<anchor>\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s+
    \[(?P<trigger>M15\s+SLOT1|M30\s+CLOSE)\]\s+
    \[SIGNAL\]\s+
    (?P<dir>BUY|SELL)!\s+
    mode=(?P<mode>[A-Za-z0-9_]+)
    .*?
    anchor=(?P<signal_anchor>\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2})
    """,
    re.VERBOSE,
)

INIT_RE = re.compile(r"30m x 2H EA v\d+\.\d+ - Initializing")
RUN_TS_RE = re.compile(r"\)\s+(?P<ts>\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})\s+")


def normalize_mode(mode: str) -> str:
    if mode.startswith("pre_cross"):
        return "pre_cross"
    if mode.startswith("cross"):
        return "cross"
    m = re.match(r"(post_n\d+)", mode)
    if m:
        return m.group(1)
    return mode


def parse_ea_log(path: str) -> tuple[pd.DataFrame, pd.Timestamp | None, pd.Timestamp | None]:
    with open(path, "r", encoding="utf-16-le", errors="ignore") as fh:
        lines = fh.readlines()

    start_idx = 0
    for idx, line in enumerate(lines):
        if INIT_RE.search(line):
            start_idx = idx

    run_times = []
    rows = []
    for line in lines[start_idx:]:
        ts_match = RUN_TS_RE.search(line)
        if ts_match:
            run_times.append(pd.Timestamp(ts_match.group("ts").replace(".", "-")))
        if "[SIGNAL]" not in line:
            continue
        m = SIGNAL_RE.search(line)
        if not m:
            continue
        mode_raw = m.group("mode")
        rows.append(
            {
                "log_time": pd.Timestamp(m.group("anchor").replace(".", "-")),
                "anchor_time": pd.Timestamp(m.group("signal_anchor").replace(".", "-")),
                "dir": "L" if m.group("dir") == "BUY" else "S",
                "trigger": m.group("trigger").replace("  ", " "),
                "mode_raw": mode_raw,
                "mode_norm": normalize_mode(mode_raw),
                "source": "ea",
            }
        )
    out = pd.DataFrame(rows).sort_values(["anchor_time", "dir", "trigger"]).reset_index(drop=True)
    if not out.empty:
        out = out.drop_duplicates(subset=["anchor_time", "dir"], keep="first").reset_index(drop=True)
    run_start = min(run_times) if run_times else None
    run_end = max(run_times) if run_times else None
    return out, run_start, run_end


def _derive_trigger(df: pd.DataFrame) -> pd.Series:
    if "trigger" in df.columns:
        return df["trigger"].fillna("python")
    if {"date", "entry_time"}.issubset(df.columns):
        date = pd.to_datetime(df["date"])
        entry_time = pd.to_datetime(df["entry_time"])
        return pd.Series(["M15 SLOT1" if e < d else "M30 CLOSE" for d, e in zip(date, entry_time)], index=df.index)
    return pd.Series(["python"] * len(df), index=df.index)


def _signal_frame(df: pd.DataFrame, mode_col: str, extra_cols: list[str] | None = None) -> pd.DataFrame:
    keep_cols = ["date", "dir", mode_col]
    if extra_cols:
        keep_cols.extend([c for c in extra_cols if c in df.columns and c not in keep_cols])
    out = df[keep_cols].copy()
    out["anchor_time"] = pd.to_datetime(out["date"])
    out["mode_raw"] = out[mode_col]
    out["mode_norm"] = out[mode_col].map(normalize_mode)
    out["trigger"] = _derive_trigger(df)
    if "entry_time" in out.columns:
        out["entry_time"] = pd.to_datetime(out["entry_time"])
    if "layer3_eval_time" in out.columns:
        out["layer3_eval_time"] = pd.to_datetime(out["layer3_eval_time"])
    return out


def build_python_signals(h2_shift_hours: int = 0, ea_executable_diag: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    result = cb.summarize_strategy(h2_shift_hours=h2_shift_hours, ea_executable_diag=ea_executable_diag)
    accepted = _signal_frame(
        result["accepted"],
        "mode",
        extra_cols=["entry_time", "variant", "spec_reason", "sd", "Bias_5"],
    )
    picked = _signal_frame(
        result["picked"],
        "mode",
        extra_cols=[
            "entry_time",
            "variant",
            "spec_reason",
            "sd",
            "Bias_5",
            "Bias_5_ea",
            "layer3_eval_time",
            "layer3_threshold_ea",
            "layer3_pass_ea",
        ],
    )

    # Mirror the EA rule: as long as the prior signal's Stage 3 is still open,
    # the next anchor cannot create a new group of Stage1/2/3 positions.
    executed_rows = []
    active_until = None
    picked_meta = result["picked"].copy()
    if not picked_meta.empty:
        picked_meta["meta_key"] = pd.to_datetime(picked_meta["date"]).dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + picked_meta["dir"]
        picked_meta = picked_meta.drop_duplicates(subset=["meta_key"], keep="first").set_index("meta_key")
    trades = result["trades"].sort_values("date").reset_index(drop=True)
    for _, row in trades.iterrows():
        anchor_time = pd.Timestamp(row["date"])
        stage3_time = pd.Timestamp(row["stage3_time"])
        if active_until is not None and anchor_time <= active_until:
            continue
        meta_key = anchor_time.strftime("%Y-%m-%d %H:%M:%S") + "|" + row["dir"]
        meta = picked_meta.loc[meta_key] if meta_key in picked_meta.index else None
        entry_time = pd.Timestamp(meta["entry_time"]) if meta is not None and "entry_time" in meta else anchor_time
        executed_rows.append(
            {
                "anchor_time": anchor_time,
                "dir": row["dir"],
                "trigger": "M15 SLOT1" if entry_time < anchor_time else "M30 CLOSE",
                "mode_raw": row["mode"],
                "mode_norm": normalize_mode(row["mode"]),
                "entry_time": entry_time,
                "variant": meta["variant"] if meta is not None and "variant" in meta else "",
                "sd": meta["sd"] if meta is not None and "sd" in meta else None,
                "stage3_time": stage3_time,
            }
        )
        active_until = stage3_time
    executed = pd.DataFrame(executed_rows)

    for frame in (accepted, picked, executed):
        frame["source"] = "python"

    market_df, _, _ = cb.load_market_context(h2_shift_hours=h2_shift_hours)
    market_end = pd.to_datetime(market_df["date"]).max()
    accepted = accepted[[c for c in [
        "anchor_time", "dir", "trigger", "mode_raw", "mode_norm", "source",
        "entry_time", "variant", "spec_reason", "sd", "Bias_5",
    ] if c in accepted.columns]]
    picked = picked[[c for c in [
        "anchor_time", "dir", "trigger", "mode_raw", "mode_norm", "source",
        "entry_time", "variant", "spec_reason", "sd", "Bias_5",
        "Bias_5_ea", "layer3_eval_time", "layer3_threshold_ea", "layer3_pass_ea",
    ] if c in picked.columns]]
    executed = executed[[c for c in [
        "anchor_time", "dir", "trigger", "mode_raw", "mode_norm", "source",
        "entry_time", "variant", "sd", "stage3_time",
    ] if c in executed.columns]]
    return (
        accepted.sort_values(["anchor_time", "dir"]).reset_index(drop=True),
        picked.sort_values(["anchor_time", "dir"]).reset_index(drop=True),
        executed.sort_values(["anchor_time", "dir"]).reset_index(drop=True),
        market_end,
    )


def key_frame(df: pd.DataFrame, time_col: str = "anchor_time") -> pd.DataFrame:
    out = df.copy()
    out["key"] = out[time_col].dt.strftime("%Y-%m-%d %H:%M:%S") + "|" + out["dir"]
    return out


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def overlap_frame(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return df[(df["anchor_time"] >= start) & (df["anchor_time"] <= end)].copy()


def annotate_ea_alignment(ea: pd.DataFrame, market_times: pd.Series) -> pd.DataFrame:
    out = ea.copy()
    market_times = pd.to_datetime(market_times).dropna().drop_duplicates().sort_values().reset_index(drop=True)
    if market_times.empty:
        out["aligned_in_market"] = False
        out["market_prev_time"] = pd.NaT
        out["market_next_time"] = pd.NaT
        out["align_status"] = "market_empty"
        return out

    market_index = pd.DatetimeIndex(market_times)
    exact_times = set(market_index)
    prev_times: list[pd.Timestamp] = []
    next_times: list[pd.Timestamp] = []
    statuses: list[str] = []

    for ts in pd.to_datetime(out["aligned_time"]):
        left = market_index.searchsorted(ts, side="right") - 1
        right = market_index.searchsorted(ts, side="left")
        prev_time = market_index[left] if left >= 0 else pd.NaT
        next_time = market_index[right] if right < len(market_index) else pd.NaT
        prev_times.append(prev_time)
        next_times.append(next_time)
        if ts in exact_times:
            statuses.append("exact")
        elif pd.notna(next_time):
            statuses.append("missing_align_bar_next_available")
        else:
            statuses.append("after_market_end")

    out["aligned_in_market"] = out["aligned_time"].isin(exact_times)
    out["market_prev_time"] = prev_times
    out["market_next_time"] = next_times
    out["align_status"] = statuses
    return out


def diff_counts(left: pd.DataFrame, right: pd.DataFrame) -> tuple[int, int]:
    left_keys = set(left["key"])
    right_keys = set(right["key"])
    return len(left_keys - right_keys), len(right_keys - left_keys)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, help="Path to MT5 tester log file")
    parser.add_argument("--h2-shift-hours", type=int, default=0, help="Apply an extra H2 shift beyond the standard strategy-time alignment")
    parser.add_argument("--ea-executable-diag", action="store_true", help="Use EA-executable diagnostic rules for Layer 3 and M15 slot1 spec handling")
    args = parser.parse_args()

    ensure_dir(RESULT_ROOT)

    ea, run_start, run_end = parse_ea_log(args.log)
    py_accepted, py_picked, py_executed, market_end = build_python_signals(
        h2_shift_hours=args.h2_shift_hours,
        ea_executable_diag=args.ea_executable_diag,
    )
    market_df, _, _ = cb.load_market_context(h2_shift_hours=args.h2_shift_hours)
    market_times = pd.to_datetime(market_df["date"])

    if ea.empty:
        raise RuntimeError("No [SIGNAL] lines found in EA log.")

    ea["aligned_time"] = ea["anchor_time"] + EA_ALIGN_DELTA
    ea = annotate_ea_alignment(ea, market_times)
    ea = key_frame(ea, "aligned_time")
    py_accepted = key_frame(py_accepted)
    py_picked = key_frame(py_picked)
    py_executed = key_frame(py_executed)

    run_start_aligned = run_start + EA_ALIGN_DELTA if run_start is not None else None
    run_end_aligned = run_end + EA_ALIGN_DELTA if run_end is not None else None

    overlap_start = max(run_start_aligned, py_accepted["anchor_time"].min()) if run_start_aligned is not None else py_accepted["anchor_time"].min()
    overlap_end = min(run_end_aligned, market_end) if run_end_aligned is not None else min(ea["aligned_time"].max(), market_end)
    ea_overlap = ea[(ea["aligned_time"] >= overlap_start) & (ea["aligned_time"] <= overlap_end)].copy()
    py_accepted_overlap = overlap_frame(py_accepted, overlap_start, overlap_end)
    py_picked_overlap = overlap_frame(py_picked, overlap_start, overlap_end)
    py_executed_overlap = overlap_frame(py_executed, overlap_start, overlap_end)

    ea_keys = set(ea_overlap["key"])
    py_keys = set(py_executed_overlap["key"])

    ea_extra = ea_overlap[ea_overlap["key"].isin(ea_keys - py_keys)].copy()
    py_missing = py_executed_overlap[py_executed_overlap["key"].isin(py_keys - ea_keys)].copy()

    shared = ea_overlap[ea_overlap["key"].isin(ea_keys & py_keys)][["key", "mode_raw", "mode_norm", "trigger"]].copy()
    shared = shared.rename(columns={"mode_raw": "ea_mode_raw", "mode_norm": "ea_mode_norm", "trigger": "ea_trigger"})
    shared = shared.merge(
        py_executed_overlap[py_executed_overlap["key"].isin(ea_keys & py_keys)][["key", "mode_raw", "mode_norm"]],
        on="key",
        how="left",
        suffixes=("", "_py"),
    )
    shared = shared.rename(columns={"mode_raw": "py_mode_raw", "mode_norm": "py_mode_norm"})
    mode_mismatch = shared[shared["ea_mode_norm"] != shared["py_mode_norm"]].copy()

    accepted_extra_n, accepted_missing_n = diff_counts(ea_overlap, py_accepted_overlap)
    picked_extra_n, picked_missing_n = diff_counts(ea_overlap, py_picked_overlap)

    ea.drop(columns=["key"]).to_csv(EA_SIGNALS_CSV, index=False, encoding="utf-8-sig")
    ea.drop(columns=["key"])[
        [
            c
            for c in [
                "log_time",
                "anchor_time",
                "aligned_time",
                "dir",
                "trigger",
                "mode_raw",
                "mode_norm",
                "aligned_in_market",
                "market_prev_time",
                "market_next_time",
                "align_status",
                "source",
            ]
            if c in ea.columns
        ]
    ].to_csv(EA_ALIGN_DIAG_CSV, index=False, encoding="utf-8-sig")
    py_accepted.drop(columns=["key"]).to_csv(PY_ACCEPTED_CSV, index=False, encoding="utf-8-sig")
    py_picked.drop(columns=["key"]).to_csv(PY_PICKED_CSV, index=False, encoding="utf-8-sig")
    py_executed.drop(columns=["key"]).to_csv(PY_EXECUTED_CSV, index=False, encoding="utf-8-sig")
    ea_extra.drop(columns=["key"]).to_csv(EA_EXTRA_CSV, index=False, encoding="utf-8-sig")
    py_missing.drop(columns=["key"]).to_csv(PY_MISSING_CSV, index=False, encoding="utf-8-sig")
    mode_mismatch.to_csv(MODE_MISMATCH_CSV, index=False, encoding="utf-8-sig")

    print("Latest tester run:", run_start, "->", run_end)
    print("EA compare delta:", EA_ALIGN_DELTA)
    print("Python H2 extra shift hours:", args.h2_shift_hours)
    print("EA executable diagnostic mode:", args.ea_executable_diag)
    print("EA log signals:", len(ea), "range:", ea["anchor_time"].min(), "->", ea["anchor_time"].max())
    print("EA aligned range:", ea["aligned_time"].min(), "->", ea["aligned_time"].max())
    print("Python accepted signals:", len(py_accepted), "range:", py_accepted["anchor_time"].min(), "->", py_accepted["anchor_time"].max())
    print("Python picked signals:", len(py_picked), "range:", py_picked["anchor_time"].min(), "->", py_picked["anchor_time"].max())
    print("Python executed signals:", len(py_executed), "range:", py_executed["anchor_time"].min(), "->", py_executed["anchor_time"].max())
    print("Python market data end:", market_end)
    print("Overlap start:", overlap_start)
    print("Overlap end:", overlap_end)
    print("EA overlap:", len(ea_overlap))
    print("Python accepted overlap:", len(py_accepted_overlap))
    print("Python picked overlap:", len(py_picked_overlap))
    print("Python executed overlap:", len(py_executed_overlap))
    print("EA extra vs Python accepted:", accepted_extra_n)
    print("Python accepted missing vs EA:", accepted_missing_n)
    print("EA extra vs Python picked:", picked_extra_n)
    print("Python picked missing vs EA:", picked_missing_n)
    print("EA extra vs Python:", len(ea_extra))
    print("Python missing vs EA:", len(py_missing))
    print("Shared anchor mode mismatches:", len(mode_mismatch))

    if len(ea_extra):
        print("\n[EA extra sample]")
        print(ea_extra[["anchor_time", "aligned_time", "dir", "trigger", "mode_raw"]].head(15).to_string(index=False))
    if len(py_missing):
        print("\n[Python missing sample]")
        print(py_missing[["anchor_time", "dir", "mode_raw"]].head(15).to_string(index=False))
    if len(mode_mismatch):
        print("\n[Mode mismatch sample]")
        print(mode_mismatch.head(15).to_string(index=False))

    print("\nSaved:")
    print(EA_SIGNALS_CSV)
    print(EA_ALIGN_DIAG_CSV)
    print(PY_ACCEPTED_CSV)
    print(PY_PICKED_CSV)
    print(PY_EXECUTED_CSV)
    print(EA_EXTRA_CSV)
    print(PY_MISSING_CSV)
    print(MODE_MISMATCH_CSV)


if __name__ == "__main__":
    main()
