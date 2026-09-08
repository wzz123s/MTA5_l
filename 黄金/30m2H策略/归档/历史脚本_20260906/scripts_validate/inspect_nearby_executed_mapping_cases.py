# -*- coding: utf-8 -*-
"""Inspect comparable-period MT5-only cases that already have nearby Python executed signals."""
from __future__ import annotations


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


REFINED_DIAG_PATH = (
    VALIDATION_DIR
    / "mt5_log_session_diag_v326_full_20260711_ea_diag_refined"
    / "session_01"
    / "mt5_only_cause_diag.csv"
)
SESSION_DIR = (
    VALIDATION_DIR
    / "mt5_log_session_diff_v326_full_20260711_ea_diag"
    / "session_01"
    / "session_01"
)
OUTPUT_DIR = VALIDATION_DIR / "nearby_executed_mapping_cases_v326_full_20260711_ea_diag" / "session_01"


def make_key(anchor_time: pd.Timestamp, direction: str) -> str:
    return pd.Timestamp(anchor_time).strftime("%Y-%m-%d %H:%M:%S") + "|" + str(direction)


def annotate_trigger(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if out.empty:
        return out
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["entry_time"] = pd.to_datetime(out["entry_time"], errors="coerce")
    out["trigger"] = out.apply(
        lambda row: "M15 SLOT1" if pd.notna(row["entry_time"]) and pd.notna(row["date"]) and row["entry_time"] < row["date"] else "M30 CLOSE",
        axis=1,
    )
    out["mode_norm"] = out["mode"].astype(str)
    out["key"] = out.apply(lambda row: make_key(pd.Timestamp(row["date"]), str(row["dir"])), axis=1)
    return out


def load_python_context() -> tuple[pd.Timestamp, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    result = cb.summarize_strategy(ea_executable_diag=True)
    df, h2, m15 = cb.load_market_context()
    q2_pass_set, q2_factor_map, _, _ = h2t.early_precompute(h2, df, 2, False)
    raw_df, accepted = combo.build_candidate_frames(df, q2_pass_set, q2_factor_map)
    raw_df = annotate_trigger(raw_df)
    accepted = annotate_trigger(accepted)
    picked = annotate_trigger(result["picked"])
    m15["date"] = pd.to_datetime(m15["date"], errors="coerce")
    return pd.Timestamp(m15["date"].min()), raw_df, accepted, picked


def classify_group(row: pd.Series) -> str:
    same_trigger = str(row["trigger"]) == str(row["nearest_python_trigger"])
    same_mode = str(row["mode_norm"]) == str(row["nearest_python_mode_norm"])
    if same_trigger and same_mode:
        return "pure_anchor_shift"
    if same_trigger and not same_mode:
        return "same_trigger_mode_drift"
    if (not same_trigger) and same_mode:
        return "cross_trigger_same_mode"
    return "cross_trigger_cross_mode"


def extract_exact(frame: pd.DataFrame, anchor_time: pd.Timestamp, direction: str, prefix: str) -> dict[str, object]:
    if frame.empty:
        return {}
    key = make_key(anchor_time, direction)
    subset = frame[frame["key"] == key].copy()
    if subset.empty:
        return {
            f"{prefix}_exists": False,
            f"{prefix}_mode": "",
            f"{prefix}_trigger": "",
            f"{prefix}_variant": "",
            f"{prefix}_entry_time": pd.NaT,
            f"{prefix}_sd": None,
            f"{prefix}_bias5": None,
        }
    row = subset.sort_values(["date", "entry_time"]).iloc[0]
    return {
        f"{prefix}_exists": True,
        f"{prefix}_mode": row.get("mode", ""),
        f"{prefix}_trigger": row.get("trigger", ""),
        f"{prefix}_variant": row.get("variant", ""),
        f"{prefix}_entry_time": pd.Timestamp(row["entry_time"]) if pd.notna(row.get("entry_time")) else pd.NaT,
        f"{prefix}_sd": row.get("sd", None),
        f"{prefix}_bias5": row.get("Bias_5", None),
    }


def render_markdown(summary: pd.DataFrame, detail: pd.DataFrame) -> str:
    lines = [
        "# Nearby Executed Mapping Cases",
        "",
        "## Summary",
        "",
        summary.to_markdown(index=False),
        "",
        "## Detail",
        "",
        detail.to_markdown(index=False),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    diag = pd.read_csv(REFINED_DIAG_PATH, encoding="utf-8-sig")
    cause_col = diag.columns[10]
    diag["anchor_time"] = pd.to_datetime(diag["anchor_time"], errors="coerce")
    diag["mt5_raw_anchor_time"] = pd.to_datetime(diag["mt5_raw_anchor_time"], errors="coerce")
    diag["nearest_python_anchor"] = pd.to_datetime(diag["nearest_python_anchor"], errors="coerce")

    py_exec = pd.read_csv(SESSION_DIR / "python_executed_signals.csv", encoding="utf-8-sig")
    py_exec["anchor_time"] = pd.to_datetime(py_exec["anchor_time"], errors="coerce")
    py_exec["entry_time"] = pd.to_datetime(py_exec["entry_time"], errors="coerce")
    py_exec["stage3_time"] = pd.to_datetime(py_exec["stage3_time"], errors="coerce")
    py_exec["key"] = py_exec.apply(lambda row: make_key(pd.Timestamp(row["anchor_time"]), str(row["dir"])), axis=1)

    comparable_start, raw_df, accepted, picked = load_python_context()

    cases = diag[
        (diag["anchor_time"] >= comparable_start)
        & diag[cause_col].astype(str).str.contains("近邻 executed", na=False)
    ].copy()
    cases = cases.sort_values("anchor_time").reset_index(drop=True)
    cases["case_group"] = cases.apply(classify_group, axis=1)

    rows: list[dict[str, object]] = []
    for _, row in cases.iterrows():
        out = {
            "anchor_time": pd.Timestamp(row["anchor_time"]),
            "mt5_raw_anchor_time": pd.Timestamp(row["mt5_raw_anchor_time"]),
            "dir": row["dir"],
            "mt5_trigger": row["trigger"],
            "mt5_mode_norm": row["mode_norm"],
            "nearest_python_anchor": pd.Timestamp(row["nearest_python_anchor"]) if pd.notna(row["nearest_python_anchor"]) else pd.NaT,
            "nearest_python_trigger": row.get("nearest_python_trigger", ""),
            "nearest_python_mode_norm": row.get("nearest_python_mode_norm", ""),
            "nearest_python_delta_minutes": row.get("nearest_python_delta_minutes", None),
            "case_group": row["case_group"],
            "refined_cause": row[cause_col],
        }

        out.update(extract_exact(raw_df, pd.Timestamp(row["anchor_time"]), str(row["dir"]), "exact_raw"))
        if pd.notna(row["nearest_python_anchor"]):
            out.update(extract_exact(raw_df, pd.Timestamp(row["nearest_python_anchor"]), str(row["dir"]), "nearest_raw"))
            out.update(extract_exact(accepted, pd.Timestamp(row["nearest_python_anchor"]), str(row["dir"]), "nearest_accepted"))
            out.update(extract_exact(picked, pd.Timestamp(row["nearest_python_anchor"]), str(row["dir"]), "nearest_picked"))
            py_match = py_exec[py_exec["key"] == make_key(pd.Timestamp(row["nearest_python_anchor"]), str(row["dir"]))].copy()
            if py_match.empty:
                out.update(
                    {
                        "nearest_exec_variant": "",
                        "nearest_exec_entry_time": pd.NaT,
                        "nearest_exec_stop_dist_1dp": None,
                    }
                )
            else:
                exec_row = py_match.sort_values(["anchor_time", "entry_time"]).iloc[0]
                out.update(
                    {
                        "nearest_exec_variant": exec_row.get("variant", ""),
                        "nearest_exec_entry_time": pd.Timestamp(exec_row["entry_time"]) if pd.notna(exec_row.get("entry_time")) else pd.NaT,
                        "nearest_exec_stop_dist_1dp": exec_row.get("python_stop_dist_1dp", None),
                    }
                )
        rows.append(out)

    detail = pd.DataFrame(rows)
    summary = (
        detail.groupby("case_group", as_index=False)
        .agg(
            samples=("anchor_time", "size"),
            triggers=("mt5_trigger", lambda s: ", ".join(sorted(set(str(v) for v in s)))),
            nearest_exec_triggers=("nearest_python_trigger", lambda s: ", ".join(sorted(set(str(v) for v in s)))),
        )
        .sort_values(["samples", "case_group"], ascending=[False, True])
        .reset_index(drop=True)
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    export_csv(summary, OUTPUT_DIR / "nearby_executed_mapping_summary.csv")
    export_csv(detail, OUTPUT_DIR / "nearby_executed_mapping_detail.csv")
    write_text(OUTPUT_DIR / "nearby_executed_mapping_cases.md", render_markdown(summary, detail))
    print(f"comparable_start={comparable_start}")
    print(summary.to_string(index=False))
    print(f"\nWrote {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
