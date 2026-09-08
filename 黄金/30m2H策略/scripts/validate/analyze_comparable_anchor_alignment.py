# -*- coding: utf-8 -*-
"""Analyze comparable-period anchor alignment for MT5 vs Python executed signals."""
from __future__ import annotations


import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
ROOT_SCRIPTS_DIR = ROOT / "scripts"

sys.path.insert(0, str(STRATEGY_SCRIPTS_DIR))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT_SCRIPTS_DIR))

from strategy_30m2h_common import VALIDATION_DIR, export_csv, write_text  # noqa: E402
import _current_baseline as cb  # type: ignore  # noqa: E402


DEFAULT_SESSION_DIR = (
    VALIDATION_DIR / "mt5_log_session_diff_v326_full_20260711_ea_diag" / "session_01" / "session_01"
)
DEFAULT_DIAG_DIR = (
    VALIDATION_DIR / "mt5_log_session_diag_v326_full_20260711_ea_diag" / "session_01" / "session_01"
)
DEFAULT_OUTPUT_DIR = VALIDATION_DIR / "anchor_alignment_v326_full_20260711_ea_diag" / "session_01" / "session_01"
DEFAULT_DELTAS = [0, 30, 60, 90, 120]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", type=Path, default=DEFAULT_SESSION_DIR)
    parser.add_argument("--diag-dir", type=Path, default=DEFAULT_DIAG_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--deltas", default="0,30,60,90,120")
    parser.add_argument("--current-delta", type=int, default=90)
    return parser.parse_args()


def make_key(anchor_time: pd.Timestamp, direction: str) -> str:
    return pd.Timestamp(anchor_time).strftime("%Y-%m-%d %H:%M:%S") + "|" + str(direction)


def parse_datetime_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for col in columns:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    return out


def get_comparable_start() -> pd.Timestamp:
    _, _, m15 = cb.load_market_context()
    m15["date"] = pd.to_datetime(m15["date"], errors="coerce")
    return pd.Timestamp(m15["date"].min())


def prepare_frames(session_dir: Path, comparable_start: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    mt5 = pd.read_csv(session_dir / "mt5_signals.csv", encoding="utf-8-sig")
    py = pd.read_csv(session_dir / "python_executed_signals.csv", encoding="utf-8-sig")

    mt5 = parse_datetime_columns(mt5, ["anchor_time", "mt5_raw_anchor_time", "log_time"])
    py = parse_datetime_columns(py, ["anchor_time", "entry_time", "stage3_time"])

    mt5 = mt5.sort_values(["mt5_raw_anchor_time", "log_time"]).reset_index(drop=True)
    py = py.sort_values("anchor_time").reset_index(drop=True)
    py = py[py["anchor_time"] >= comparable_start].copy()
    py["key"] = py.apply(lambda row: make_key(pd.Timestamp(row["anchor_time"]), str(row["dir"])), axis=1)
    py = py.drop_duplicates(subset=["key"], keep="first").reset_index(drop=True)
    return mt5, py


def evaluate_delta(
    mt5: pd.DataFrame,
    py: pd.DataFrame,
    delta_minutes: int,
    comparable_start: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    mapped = mt5.copy()
    mapped["candidate_delta_minutes"] = int(delta_minutes)
    mapped["candidate_anchor_time"] = mapped["mt5_raw_anchor_time"] + pd.to_timedelta(delta_minutes, unit="m")
    mapped = mapped[mapped["candidate_anchor_time"] >= comparable_start].copy().reset_index(drop=True)
    mapped["key"] = mapped.apply(lambda row: make_key(pd.Timestamp(row["candidate_anchor_time"]), str(row["dir"])), axis=1)

    py_lookup = py.rename(
        columns={
            "anchor_time": "python_anchor_time",
            "trigger": "python_trigger",
            "mode_raw": "python_mode_raw",
            "mode_norm": "python_mode_norm",
            "entry_time": "python_entry_time",
            "stage3_time": "python_stage3_time",
            "sd": "python_sd",
            "total_$": "python_total_$",
            "total_points": "python_total_points",
        }
    )

    shared = mapped.merge(py_lookup, on="key", how="inner")
    if "dir_x" in shared.columns:
        shared = shared.rename(columns={"dir_x": "dir"})
    if "dir_y" in shared.columns:
        shared = shared.rename(columns={"dir_y": "python_dir"})
    shared["same_trigger"] = shared["trigger"] == shared["python_trigger"]
    shared["same_mode"] = shared["mode_norm"] == shared["python_mode_norm"]
    shared["offset_vs_current_anchor_min"] = (
        shared["candidate_anchor_time"] - shared["anchor_time"]
    ) / pd.Timedelta(minutes=1)

    shared_keys = set(shared["key"]) if not shared.empty else set()
    py_keys = set(py["key"]) if not py.empty else set()
    mt5_only = mapped[~mapped["key"].isin(shared_keys)].copy().reset_index(drop=True)
    py_only = py[~py["key"].isin(set(mapped["key"]))].copy().reset_index(drop=True)

    summary = pd.DataFrame(
        [
            {
                "delta_minutes": int(delta_minutes),
                "comparable_start": comparable_start,
                "mt5_signals": int(len(mapped)),
                "python_signals": int(len(py)),
                "shared_signals": int(len(shared)),
                "mt5_only_signals": int(len(mt5_only)),
                "python_only_signals": int(len(py_only)),
                "same_trigger_shared": int(shared["same_trigger"].sum()) if not shared.empty else 0,
                "same_mode_shared": int(shared["same_mode"].sum()) if not shared.empty else 0,
                "same_trigger_ratio": round(float(shared["same_trigger"].mean()) * 100.0, 4) if not shared.empty else 0.0,
                "same_mode_ratio": round(float(shared["same_mode"].mean()) * 100.0, 4) if not shared.empty else 0.0,
            }
        ]
    )

    per_trigger_rows: list[dict[str, object]] = []
    for trigger in ["M30 CLOSE", "M15 SLOT1"]:
        mt5_trigger = mapped[mapped["trigger"] == trigger].copy()
        shared_trigger = shared[shared["trigger"] == trigger].copy()
        per_trigger_rows.append(
            {
                "delta_minutes": int(delta_minutes),
                "trigger": trigger,
                "mt5_signals": int(len(mt5_trigger)),
                "shared_signals": int(len(shared_trigger)),
                "mt5_only_signals": int(len(mt5_trigger) - len(shared_trigger)),
                "same_trigger_shared": int(shared_trigger["same_trigger"].sum()) if not shared_trigger.empty else 0,
                "same_mode_shared": int(shared_trigger["same_mode"].sum()) if not shared_trigger.empty else 0,
                "same_trigger_ratio": round(float(shared_trigger["same_trigger"].mean()) * 100.0, 4)
                if not shared_trigger.empty
                else 0.0,
                "same_mode_ratio": round(float(shared_trigger["same_mode"].mean()) * 100.0, 4)
                if not shared_trigger.empty
                else 0.0,
            }
        )

    per_trigger = pd.DataFrame(per_trigger_rows)
    return summary, per_trigger, shared, mt5_only


def find_cause_column(frame: pd.DataFrame) -> str | None:
    known = {
        "anchor_time",
        "mt5_raw_anchor_time",
        "dir",
        "trigger",
        "mode_raw",
        "mode_norm",
        "log_time",
        "mt5_stop_dist",
        "key",
        "python_picked",
        "python_accepted",
        "raw_match_count",
        "slot1_time",
        "slot1_close",
        "slot1_sma13",
        "slot1_same_side",
        "slot1_stop_dist",
        "slot1_stop_side_ok",
        "slot1_stop_in_spec",
        "nearest_raw_anchor",
        "nearest_raw_mode",
        "nearest_raw_sd",
        "nearest_raw_spec_pass",
        "nearest_raw_spec_reason",
        "nearest_raw_delta_minutes",
        "blocked_by_anchor",
        "blocked_by_trigger",
        "blocked_by_mode",
        "blocked_until",
        "blocked_total_points",
    }
    for col in frame.columns:
        if col not in known:
            return col
    return None


def build_offset_samples(
    diag_dir: Path,
    py: pd.DataFrame,
    comparable_start: pd.Timestamp,
    current_delta: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cause_diag = pd.read_csv(diag_dir / "mt5_only_cause_diag.csv", encoding="utf-8-sig")
    cause_diag = parse_datetime_columns(
        cause_diag,
        [
            "anchor_time",
            "mt5_raw_anchor_time",
            "log_time",
            "slot1_time",
            "nearest_raw_anchor",
            "blocked_by_anchor",
            "blocked_until",
        ],
    )
    cause_col = find_cause_column(cause_diag)
    if cause_col is None:
        cause_diag["cause_text"] = ""
    else:
        cause_diag["cause_text"] = cause_diag[cause_col].astype(str)

    focus = cause_diag[
        (cause_diag["anchor_time"] >= comparable_start)
        & (cause_diag["python_picked"] == False)  # noqa: E712
        & (cause_diag["python_accepted"] == False)  # noqa: E712
        & (cause_diag["raw_match_count"] == 0)
    ].copy()

    py_lookup = py.rename(
        columns={
            "anchor_time": "python_anchor_time",
            "trigger": "python_trigger",
            "mode_raw": "python_mode_raw",
            "mode_norm": "python_mode_norm",
            "entry_time": "python_entry_time",
            "stage3_time": "python_stage3_time",
        }
    )[["key", "python_anchor_time", "python_trigger", "python_mode_raw", "python_mode_norm", "python_entry_time", "python_stage3_time"]]

    rows: list[dict[str, object]] = []
    for _, row in focus.sort_values("anchor_time").iterrows():
        nearest_anchor = row.get("nearest_raw_anchor")
        if pd.isna(nearest_anchor):
            nearest_key = ""
        else:
            nearest_key = make_key(pd.Timestamp(nearest_anchor), str(row["dir"]))
        py_match = py_lookup[py_lookup["key"] == nearest_key]
        py_row = py_match.iloc[0].to_dict() if not py_match.empty else {}
        nearest_anchor_ts = pd.Timestamp(nearest_anchor) if pd.notna(nearest_anchor) else pd.NaT
        candidate_delta_from_raw = (
            (nearest_anchor_ts - pd.Timestamp(row["mt5_raw_anchor_time"])) / pd.Timedelta(minutes=1)
            if pd.notna(nearest_anchor_ts)
            else None
        )
        offset_vs_current = (
            (nearest_anchor_ts - pd.Timestamp(row["anchor_time"])) / pd.Timedelta(minutes=1)
            if pd.notna(nearest_anchor_ts)
            else None
        )
        rows.append(
            {
                "anchor_time": pd.Timestamp(row["anchor_time"]),
                "mt5_raw_anchor_time": pd.Timestamp(row["mt5_raw_anchor_time"]),
                "dir": row["dir"],
                "trigger": row["trigger"],
                "mode_norm": row["mode_norm"],
                "current_delta_minutes": int(current_delta),
                "nearest_raw_anchor": nearest_anchor_ts,
                "nearest_raw_mode": row.get("nearest_raw_mode", ""),
                "nearest_raw_spec_reason": row.get("nearest_raw_spec_reason", ""),
                "offset_vs_current_anchor_min": offset_vs_current,
                "candidate_delta_from_raw_min": candidate_delta_from_raw,
                "python_match_exists": not py_match.empty,
                "python_match_trigger": py_row.get("python_trigger", ""),
                "python_match_mode_norm": py_row.get("python_mode_norm", ""),
                "python_match_same_trigger": bool(py_row) and py_row.get("python_trigger", "") == row["trigger"],
                "python_match_same_mode": bool(py_row) and py_row.get("python_mode_norm", "") == row["mode_norm"],
                "python_match_stage3_time": py_row.get("python_stage3_time", pd.NaT),
                "cause_text": row.get("cause_text", ""),
            }
        )

    detail = pd.DataFrame(rows)
    if detail.empty:
        summary = pd.DataFrame(
            columns=[
                "offset_vs_current_anchor_min",
                "samples",
                "python_match_exists_samples",
                "same_trigger_matches",
                "same_mode_matches",
                "candidate_delta_from_raw_min_values",
            ]
        )
        return detail, summary

    bucketed = detail[detail["offset_vs_current_anchor_min"].isin([30.0, 60.0, 120.0, -30.0, -60.0, -120.0])].copy()
    summary_rows: list[dict[str, object]] = []
    for offset, group in bucketed.groupby("offset_vs_current_anchor_min", dropna=False):
        candidate_values = sorted({int(v) for v in group["candidate_delta_from_raw_min"].dropna().tolist()})
        summary_rows.append(
            {
                "offset_vs_current_anchor_min": int(offset),
                "samples": int(len(group)),
                "python_match_exists_samples": int(group["python_match_exists"].sum()),
                "same_trigger_matches": int(group["python_match_same_trigger"].sum()),
                "same_mode_matches": int(group["python_match_same_mode"].sum()),
                "candidate_delta_from_raw_min_values": ",".join(str(v) for v in candidate_values),
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values("offset_vs_current_anchor_min").reset_index(drop=True)
    return detail, summary


def pick_best_rows(summary: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    ranked = summary.sort_values(
        ["shared_signals", "same_mode_shared", "mt5_only_signals", "python_only_signals", "delta_minutes"],
        ascending=[False, False, True, True, True],
    ).reset_index(drop=True)
    best_overall = ranked.iloc[0]
    return best_overall, ranked


def render_markdown(
    comparable_start: pd.Timestamp,
    overall: pd.DataFrame,
    per_trigger: pd.DataFrame,
    best_overall: pd.Series,
    best_by_trigger: pd.DataFrame,
    current_shared_detail: pd.DataFrame,
    offset_summary: pd.DataFrame,
    offset_detail: pd.DataFrame,
) -> str:
    lines = [
        "# Comparable Anchor Alignment",
        "",
        f"- comparable_start: `{pd.Timestamp(comparable_start)}`",
        f"- evaluated_deltas: `{', '.join(str(int(v)) for v in overall['delta_minutes'].tolist())}`",
        "",
        "## Overall",
        "",
        overall.to_markdown(index=False),
        "",
        "## By Trigger",
        "",
        per_trigger.to_markdown(index=False),
        "",
        "## Best Delta",
        "",
        f"- overall best: `{int(best_overall['delta_minutes'])}` minutes, shared `{int(best_overall['shared_signals'])}`, same_mode `{int(best_overall['same_mode_shared'])}`",
    ]
    for _, row in best_by_trigger.iterrows():
        lines.append(
            f"- {row['trigger']}: best `{int(row['delta_minutes'])}` minutes, shared `{int(row['shared_signals'])}`, same_mode `{int(row['same_mode_shared'])}`"
        )
    lines.extend(
        [
            "",
            "## Current Delta Shared Detail",
            "",
            current_shared_detail.to_markdown(index=False) if not current_shared_detail.empty else "_empty_",
            "",
            "## Offset Summary",
            "",
            offset_summary.to_markdown(index=False) if not offset_summary.empty else "_empty_",
            "",
            "## Offset Detail",
            "",
            offset_detail.to_markdown(index=False) if not offset_detail.empty else "_empty_",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    deltas = [int(part.strip()) for part in str(args.deltas).split(",") if part.strip()]
    comparable_start = get_comparable_start()
    mt5, py = prepare_frames(args.session_dir, comparable_start)

    overall_rows: list[pd.DataFrame] = []
    trigger_rows: list[pd.DataFrame] = []
    shared_by_delta: dict[int, pd.DataFrame] = {}
    mt5_only_by_delta: dict[int, pd.DataFrame] = {}

    for delta in deltas:
        summary, per_trigger, shared, mt5_only = evaluate_delta(mt5, py, delta, comparable_start)
        overall_rows.append(summary)
        trigger_rows.append(per_trigger)
        shared_by_delta[delta] = shared
        mt5_only_by_delta[delta] = mt5_only

    overall = pd.concat(overall_rows, ignore_index=True)
    per_trigger = pd.concat(trigger_rows, ignore_index=True)
    best_overall, ranked_overall = pick_best_rows(overall)
    best_by_trigger = (
        per_trigger.sort_values(
            ["trigger", "shared_signals", "same_mode_shared", "mt5_only_signals", "delta_minutes"],
            ascending=[True, False, False, True, True],
        )
        .groupby("trigger", as_index=False)
        .head(1)
        .reset_index(drop=True)
    )

    current_shared = shared_by_delta.get(args.current_delta, pd.DataFrame()).copy()
    if not current_shared.empty:
        current_shared_detail = current_shared[
            [
                "mt5_raw_anchor_time",
                "anchor_time",
                "candidate_anchor_time",
                "python_anchor_time",
                "dir",
                "trigger",
                "python_trigger",
                "mode_norm",
                "python_mode_norm",
                "same_trigger",
                "same_mode",
                "mt5_stop_dist",
                "python_stop_dist_1dp",
            ]
        ].copy()
        current_shared_detail["stop_dist_gap_1dp"] = (
            current_shared_detail["mt5_stop_dist"] - current_shared_detail["python_stop_dist_1dp"]
        ).round(4)
    else:
        current_shared_detail = current_shared

    offset_detail, offset_summary = build_offset_samples(
        args.diag_dir,
        py,
        comparable_start,
        args.current_delta,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    export_csv(overall, args.output_dir / "comparable_alignment_summary.csv")
    export_csv(per_trigger, args.output_dir / "comparable_alignment_by_trigger.csv")
    export_csv(ranked_overall, args.output_dir / "comparable_alignment_summary_ranked.csv")
    export_csv(best_by_trigger, args.output_dir / "comparable_alignment_best_by_trigger.csv")
    export_csv(current_shared_detail, args.output_dir / f"current_delta_{int(args.current_delta)}_shared_detail.csv")
    export_csv(mt5_only_by_delta.get(args.current_delta, pd.DataFrame()), args.output_dir / f"current_delta_{int(args.current_delta)}_mt5_only.csv")
    export_csv(offset_summary, args.output_dir / "offset_summary.csv")
    export_csv(offset_detail, args.output_dir / "offset_detail.csv")
    write_text(
        args.output_dir / "comparable_anchor_alignment_report.md",
        render_markdown(
            comparable_start,
            overall,
            per_trigger,
            best_overall,
            best_by_trigger,
            current_shared_detail,
            offset_summary,
            offset_detail,
        ),
    )

    print(f"comparable_start={comparable_start}")
    print(overall.to_string(index=False))
    print("")
    print(best_by_trigger.to_string(index=False))
    print(f"\nWrote {args.output_dir}")


if __name__ == "__main__":
    main()
