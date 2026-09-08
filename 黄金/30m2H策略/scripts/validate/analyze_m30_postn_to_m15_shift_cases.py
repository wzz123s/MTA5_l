# -*- coding: utf-8 -*-
"""Analyze M30 post_n signals that reappear as M15 slot1 post_n signals."""
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
import _h2_early_gate_test as h2t  # type: ignore  # noqa: E402
import _m15_h2_combo_test as combo  # type: ignore  # noqa: E402


DEFAULT_BASELINE_DIR = (
    VALIDATION_DIR / "mt5_log_session_diff_v326_full_20260711_ea_diag" / "session_01" / "session_01"
)
DEFAULT_CURRENT_DIR = (
    VALIDATION_DIR
    / "mt5_log_session_diff_v326_full_20260712_m30postn_strict_veto_initfix_ea_diag"
    / "session_03"
)
DEFAULT_OUTPUT_DIR = (
    VALIDATION_DIR / "m30_postn_to_m15_shift_v326_full_20260712_m30postn_strict_veto_initfix_ea_diag" / "session_03"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-dir", type=Path, default=DEFAULT_BASELINE_DIR)
    parser.add_argument("--current-dir", type=Path, default=DEFAULT_CURRENT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--max-shift-minutes", type=int, default=90)
    return parser.parse_args()


def parse_dt(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for col in columns:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    return out


def signal_key(row: pd.Series) -> tuple[str, str, str, str]:
    return (
        pd.Timestamp(row["anchor_time"]).strftime("%Y-%m-%d %H:%M:%S"),
        str(row["dir"]),
        str(row["trigger"]),
        str(row["mode_norm"]),
    )


def make_anchor_dir_key(anchor_time: pd.Timestamp, direction: str) -> str:
    return pd.Timestamp(anchor_time).strftime("%Y-%m-%d %H:%M:%S") + "|" + str(direction)


def annotate_trigger(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if out.empty:
        return out
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["entry_time"] = pd.to_datetime(out["entry_time"], errors="coerce")
    out["trigger"] = out.apply(
        lambda row: "M15 SLOT1"
        if pd.notna(row["entry_time"]) and pd.notna(row["date"]) and row["entry_time"] < row["date"]
        else "M30 CLOSE",
        axis=1,
    )
    out["mode_norm"] = out["mode"].astype(str)
    out["anchor_dir_key"] = out.apply(
        lambda row: make_anchor_dir_key(pd.Timestamp(row["date"]), str(row["dir"])),
        axis=1,
    )
    return out


def load_python_context(current_dir: Path) -> tuple[pd.Timestamp, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    result = cb.summarize_strategy(ea_executable_diag=True)
    df, h2, m15 = cb.load_market_context()
    q2_pass_set, q2_factor_map, _, _ = h2t.early_precompute(h2, df, 2, False)
    raw_df, accepted = combo.build_candidate_frames(df, q2_pass_set, q2_factor_map)
    raw_df = annotate_trigger(raw_df)
    accepted = annotate_trigger(accepted)
    picked = annotate_trigger(result["picked"])

    py_exec = pd.read_csv(current_dir / "python_executed_signals.csv", encoding="utf-8-sig")
    py_exec = parse_dt(py_exec, ["anchor_time", "entry_time", "stage3_time"])
    py_exec["anchor_dir_key"] = py_exec.apply(
        lambda row: make_anchor_dir_key(pd.Timestamp(row["anchor_time"]), str(row["dir"])),
        axis=1,
    )

    m15["date"] = pd.to_datetime(m15["date"], errors="coerce")
    return pd.Timestamp(m15["date"].min()), raw_df, accepted, picked, py_exec


def extract_exact(frame: pd.DataFrame, anchor_time: pd.Timestamp, direction: str, prefix: str) -> dict[str, object]:
    if frame.empty:
        return {f"{prefix}_exists": False}
    subset = frame[frame["anchor_dir_key"] == make_anchor_dir_key(anchor_time, direction)].copy()
    if subset.empty:
        return {f"{prefix}_exists": False}
    row = subset.sort_values([col for col in ["date", "anchor_time", "entry_time"] if col in subset.columns]).iloc[0]
    return {
        f"{prefix}_exists": True,
        f"{prefix}_trigger": row.get("trigger", ""),
        f"{prefix}_mode_norm": row.get("mode_norm", row.get("mode", "")),
        f"{prefix}_variant": row.get("variant", ""),
        f"{prefix}_entry_time": row.get("entry_time", pd.NaT),
        f"{prefix}_sd": row.get("sd", row.get("python_stop_dist_1dp", None)),
        f"{prefix}_spec_pass": row.get("spec_pass", ""),
        f"{prefix}_spec_reason": row.get("spec_reason", ""),
    }


def extract_nearest(
    frame: pd.DataFrame,
    anchor_col: str,
    anchor_time: pd.Timestamp,
    direction: str,
    prefix: str,
    max_minutes: int = 180,
) -> dict[str, object]:
    if frame.empty or anchor_col not in frame.columns:
        return {f"{prefix}_exists": False}
    subset = frame[frame["dir"].astype(str) == str(direction)].copy()
    if subset.empty:
        return {f"{prefix}_exists": False}
    subset["_delta_minutes"] = (subset[anchor_col] - anchor_time) / pd.Timedelta(minutes=1)
    subset["_abs_delta_minutes"] = subset["_delta_minutes"].abs()
    subset = subset[subset["_abs_delta_minutes"] <= max_minutes].copy()
    if subset.empty:
        return {f"{prefix}_exists": False}
    row = subset.sort_values(["_abs_delta_minutes", "_delta_minutes"]).iloc[0]
    return {
        f"{prefix}_exists": True,
        f"{prefix}_anchor_time": row.get(anchor_col, pd.NaT),
        f"{prefix}_delta_minutes": row.get("_delta_minutes", None),
        f"{prefix}_trigger": row.get("trigger", ""),
        f"{prefix}_mode_norm": row.get("mode_norm", row.get("mode", "")),
        f"{prefix}_variant": row.get("variant", ""),
        f"{prefix}_entry_time": row.get("entry_time", pd.NaT),
        f"{prefix}_sd": row.get("sd", row.get("python_stop_dist_1dp", None)),
        f"{prefix}_spec_pass": row.get("spec_pass", ""),
        f"{prefix}_spec_reason": row.get("spec_reason", ""),
    }


def find_shift_pairs(
    baseline: pd.DataFrame,
    current: pd.DataFrame,
    max_shift_minutes: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    baseline_keys = set(baseline["signal_key"])
    current_keys = set(current["signal_key"])

    removed = baseline[~baseline["signal_key"].isin(current_keys)].copy()
    added = current[~current["signal_key"].isin(baseline_keys)].copy()

    removed_m30_postn = removed[
        (removed["trigger"] == "M30 CLOSE") & removed["mode_norm"].astype(str).str.startswith("post_n")
    ].copy()
    added_m15_postn = added[
        (added["trigger"] == "M15 SLOT1") & added["mode_norm"].astype(str).str.startswith("post_n")
    ].copy()

    rows: list[dict[str, object]] = []
    used_added: set[int] = set()
    for ridx, removed_row in removed_m30_postn.sort_values("anchor_time").iterrows():
        candidates = added_m15_postn[added_m15_postn["dir"].astype(str) == str(removed_row["dir"])].copy()
        candidates["shift_minutes"] = (candidates["anchor_time"] - removed_row["anchor_time"]) / pd.Timedelta(minutes=1)
        candidates["same_mode"] = candidates["mode_norm"].astype(str) == str(removed_row["mode_norm"])
        candidates = candidates[
            (candidates["shift_minutes"] > 0) & (candidates["shift_minutes"] <= max_shift_minutes)
        ].copy()
        candidates = candidates[~candidates.index.isin(used_added)].copy()
        if candidates.empty:
            rows.append(
                {
                    "pair_status": "removed_without_added_m15",
                    "removed_index": ridx,
                    "added_index": None,
                    "shift_minutes": None,
                    "same_mode": False,
                }
            )
            continue
        candidate = candidates.sort_values(["same_mode", "shift_minutes"], ascending=[False, True]).iloc[0]
        used_added.add(int(candidate.name))
        rows.append(
            {
                "pair_status": "paired",
                "removed_index": ridx,
                "added_index": int(candidate.name),
                "shift_minutes": candidate["shift_minutes"],
                "same_mode": bool(candidate["same_mode"]),
            }
        )

    paired = pd.DataFrame(rows)
    return removed_m30_postn, added_m15_postn, paired


def render_markdown(summary: pd.DataFrame, paired_detail: pd.DataFrame, unpaired_added: pd.DataFrame) -> str:
    lines = [
        "# M30 post_n to M15 slot1 shift analysis",
        "",
        "## Summary",
        "",
        summary.to_markdown(index=False),
        "",
        "## Paired detail",
        "",
        paired_detail.to_markdown(index=False),
        "",
        "## Unpaired added M15 post_n",
        "",
        unpaired_added.to_markdown(index=False) if not unpaired_added.empty else "_None_",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    baseline = pd.read_csv(args.baseline_dir / "mt5_signals.csv", encoding="utf-8-sig")
    current = pd.read_csv(args.current_dir / "mt5_signals.csv", encoding="utf-8-sig")
    baseline = parse_dt(baseline, ["anchor_time", "mt5_raw_anchor_time", "log_time"])
    current = parse_dt(current, ["anchor_time", "mt5_raw_anchor_time", "log_time"])
    baseline["signal_key"] = baseline.apply(signal_key, axis=1)
    current["signal_key"] = current.apply(signal_key, axis=1)

    comparable_start, raw_df, accepted, picked, py_exec = load_python_context(args.current_dir)
    removed_m30_postn, added_m15_postn, paired = find_shift_pairs(baseline, current, args.max_shift_minutes)

    detail_rows: list[dict[str, object]] = []
    used_added = set()
    for _, pair in paired.iterrows():
        removed_row = baseline.loc[int(pair["removed_index"])]
        out = {
            "pair_status": pair["pair_status"],
            "removed_anchor_time": removed_row["anchor_time"],
            "removed_raw_anchor_time": removed_row.get("mt5_raw_anchor_time", pd.NaT),
            "removed_dir": removed_row["dir"],
            "removed_mode_norm": removed_row["mode_norm"],
            "removed_stop_dist": removed_row.get("mt5_stop_dist", None),
            "shift_minutes": pair["shift_minutes"],
            "same_mode": pair["same_mode"],
            "in_comparable_period": pd.Timestamp(removed_row["anchor_time"]) >= comparable_start,
        }
        if pd.notna(pair["added_index"]):
            added_row = current.loc[int(pair["added_index"])]
            used_added.add(int(pair["added_index"]))
            out.update(
                {
                    "added_anchor_time": added_row["anchor_time"],
                    "added_raw_anchor_time": added_row.get("mt5_raw_anchor_time", pd.NaT),
                    "added_dir": added_row["dir"],
                    "added_mode_norm": added_row["mode_norm"],
                    "added_stop_dist": added_row.get("mt5_stop_dist", None),
                }
            )
            added_anchor = pd.Timestamp(added_row["anchor_time"])
            direction = str(added_row["dir"])
            out.update(extract_exact(raw_df, added_anchor, direction, "added_exact_raw"))
            out.update(extract_exact(accepted, added_anchor, direction, "added_exact_accepted"))
            out.update(extract_exact(picked, added_anchor, direction, "added_exact_picked"))
            out.update(extract_exact(py_exec, added_anchor, direction, "added_exact_exec"))
            out.update(extract_nearest(raw_df, "date", added_anchor, direction, "added_nearest_raw"))
            out.update(extract_nearest(py_exec, "anchor_time", added_anchor, direction, "added_nearest_exec"))
        else:
            out.update(
                {
                    "added_anchor_time": pd.NaT,
                    "added_raw_anchor_time": pd.NaT,
                    "added_dir": "",
                    "added_mode_norm": "",
                    "added_stop_dist": None,
                }
            )

        removed_anchor = pd.Timestamp(removed_row["anchor_time"])
        removed_direction = str(removed_row["dir"])
        out.update(extract_exact(raw_df, removed_anchor, removed_direction, "removed_exact_raw"))
        out.update(extract_exact(py_exec, removed_anchor, removed_direction, "removed_exact_exec"))
        detail_rows.append(out)

    paired_detail = pd.DataFrame(detail_rows)
    unpaired_added = added_m15_postn[~added_m15_postn.index.isin(used_added)].copy()

    summary = pd.DataFrame(
        [
            {
                "comparable_start": comparable_start,
                "removed_m30_postn": len(removed_m30_postn),
                "added_m15_postn": len(added_m15_postn),
                "paired": int((paired["pair_status"] == "paired").sum()) if not paired.empty else 0,
                "removed_in_comparable_period": int(paired_detail["in_comparable_period"].sum())
                if not paired_detail.empty
                else 0,
                "paired_in_comparable_period": int(
                    (
                        (paired_detail["pair_status"] == "paired")
                        & paired_detail["in_comparable_period"].astype(bool)
                    ).sum()
                )
                if not paired_detail.empty
                else 0,
                "same_mode_pairs": int(paired_detail["same_mode"].sum()) if not paired_detail.empty else 0,
                "added_exact_raw_exists": int(paired_detail.get("added_exact_raw_exists", pd.Series(dtype=bool)).sum())
                if not paired_detail.empty
                else 0,
                "added_exact_accepted_exists": int(
                    paired_detail.get("added_exact_accepted_exists", pd.Series(dtype=bool)).sum()
                )
                if not paired_detail.empty
                else 0,
                "added_exact_picked_exists": int(
                    paired_detail.get("added_exact_picked_exists", pd.Series(dtype=bool)).sum()
                )
                if not paired_detail.empty
                else 0,
                "added_exact_exec_exists": int(paired_detail.get("added_exact_exec_exists", pd.Series(dtype=bool)).sum())
                if not paired_detail.empty
                else 0,
                "unpaired_added_m15_postn": len(unpaired_added),
            }
        ]
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    export_csv(summary, args.output_dir / "m30_postn_to_m15_shift_summary.csv")
    export_csv(removed_m30_postn, args.output_dir / "removed_m30_postn.csv")
    export_csv(added_m15_postn, args.output_dir / "added_m15_postn.csv")
    export_csv(paired_detail, args.output_dir / "m30_postn_to_m15_shift_detail.csv")
    export_csv(unpaired_added, args.output_dir / "unpaired_added_m15_postn.csv")
    write_text(
        args.output_dir / "m30_postn_to_m15_shift_analysis.md",
        render_markdown(summary, paired_detail, unpaired_added),
    )

    print(summary.to_string(index=False))
    if not paired_detail.empty:
        cols = [
            "removed_anchor_time",
            "removed_mode_norm",
            "added_anchor_time",
            "added_mode_norm",
            "shift_minutes",
            "same_mode",
            "added_exact_raw_exists",
            "added_exact_accepted_exists",
            "added_exact_picked_exists",
            "added_exact_exec_exists",
            "added_nearest_raw_anchor_time",
            "added_nearest_raw_delta_minutes",
            "added_nearest_raw_mode_norm",
            "added_nearest_exec_anchor_time",
            "added_nearest_exec_delta_minutes",
            "added_nearest_exec_mode_norm",
        ]
        print()
        print(paired_detail[[col for col in cols if col in paired_detail.columns]].to_string(index=False))
    print(f"\nWrote {args.output_dir}")


if __name__ == "__main__":
    main()
