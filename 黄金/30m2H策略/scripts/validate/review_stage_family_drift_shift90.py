# -*- coding: utf-8 -*-
"""Review shift90 Stage/family and trigger-family drift cases."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
INPUT = DATA_DIR / "validation" / "unmatched_signal_cause_shift90_20260713" / "all_unmatched_signal_causes.csv"
OUT_DIR = DATA_DIR / "validation" / "stage_family_drift_shift90_review_20260713"

CAUSES = {"stage_execution_diff_or_family_drift", "trigger_family_drift"}


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def time_bucket(minutes: object) -> str:
    try:
        value = abs(float(minutes))
    except Exception:
        return "none"
    if pd.isna(value):
        return "none"
    if value == 0:
        return "0"
    if value <= 30:
        return "<=30"
    if value <= 90:
        return "<=90"
    if value <= 180:
        return "<=180"
    if value <= 1440:
        return "<=1d"
    if value <= 7 * 1440:
        return "<=7d"
    return ">7d"


def load_target() -> pd.DataFrame:
    df = pd.read_csv(INPUT, encoding="utf-8-sig")
    target = df[
        (df["source"] == "python_mt5")
        & (df["side"] == "mt5_unmatched")
        & (df["cause_bucket"].isin(CAUSES))
    ].copy()
    for col in ["target_time", "accepted_date", "picked_date", "executed_date"]:
        target[col] = pd.to_datetime(target[col], errors="coerce")
    for col in ["profit", "accepted_abs_minutes", "picked_abs_minutes", "executed_abs_minutes"]:
        target[col] = pd.to_numeric(target[col], errors="coerce")
    target["accepted_time_bucket"] = target["accepted_abs_minutes"].map(time_bucket)
    target["picked_time_bucket"] = target["picked_abs_minutes"].map(time_bucket)
    target["executed_time_bucket"] = target["executed_abs_minutes"].map(time_bucket)
    target["drift_pattern"] = target.apply(drift_pattern, axis=1)
    target["review_action"] = target.apply(review_action, axis=1)
    return target


def drift_pattern(row: pd.Series) -> str:
    target_trigger = str(row.get("trigger_family", ""))
    accepted_trigger = str(row.get("accepted_trigger_family", ""))
    accepted_status = str(row.get("accepted_status", ""))
    accepted_abs = row.get("accepted_abs_minutes")
    target_mode = str(row.get("mode_family", ""))
    accepted_mode = str(row.get("accepted_mode_family", ""))

    if accepted_status == "trigger_drift" and pd.notna(accepted_abs):
        if target_trigger == "M30 CLOSE" and accepted_trigger == "M15 SLOT1" and target_mode == accepted_mode:
            if float(accepted_abs) <= 30:
                return "mt5_m30_python_m15_same_or_next_slot"
            return "mt5_m30_python_m15_far"
        if target_trigger == "M15 SLOT1" and accepted_trigger == "M30 CLOSE" and target_mode == accepted_mode:
            if float(accepted_abs) <= 90:
                return "mt5_m15_python_m30_near_parent"
            return "mt5_m15_python_m30_far_parent"
        return "trigger_drift_other"
    if accepted_status == "none":
        return "no_near_accepted_candidate"
    return str(accepted_status)


def review_action(row: pd.Series) -> str:
    pattern = str(row["drift_pattern"])
    if pattern in {"mt5_m30_python_m15_same_or_next_slot", "mt5_m15_python_m30_near_parent"}:
        return "review_m15_replace_trigger_family_semantics"
    if pattern in {"mt5_m30_python_m15_far", "mt5_m15_python_m30_far_parent"}:
        return "review_time_window_or_one_to_one_conflict"
    if pattern == "no_near_accepted_candidate":
        return "review_missing_candidate_or_layer1"
    return "manual_review"


def grouped(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=columns + ["rows"])
    return (
        frame.groupby(columns, dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(columns + ["rows"], ascending=[True] * len(columns) + [False])
    )


def render_report(details: pd.DataFrame, summaries: dict[str, pd.DataFrame]) -> str:
    detail_cols = [
        "trade_id",
        "target_time",
        "dir_norm",
        "trigger_family",
        "mode_family",
        "profit",
        "cause_bucket",
        "accepted_status",
        "accepted_time_bucket",
        "accepted_trigger_family",
        "accepted_mode_family",
        "accepted_mode",
        "accepted_variant",
        "picked_status",
        "picked_time_bucket",
        "executed_status",
        "executed_time_bucket",
        "drift_pattern",
        "review_action",
    ]
    lines = [
        "# Stage / Trigger Family Drift Shift90 Review",
        "",
        "## Trigger/Mode Cause Summary",
        "",
        summaries["trigger_mode"].to_markdown(index=False),
        "",
        "## Drift Pattern Summary",
        "",
        summaries["pattern"].to_markdown(index=False),
        "",
        "## Review Action Summary",
        "",
        summaries["action"].to_markdown(index=False),
        "",
        "## Details",
        "",
        details[detail_cols].to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        "- Most drift cases are not pure Stage exit differences; they are trigger-family replacement semantics around M15 SLOT1 versus M30 CLOSE.",
        "- Same-time or near-time `M30 CLOSE <-> M15 SLOT1` drift should be reviewed before changing stops, funds, or post_n counters.",
        "- The next executable step is to inspect the M15 replace/rescue decision path and decide whether mapping should treat same-time replacement as equivalent, or Python/EA trigger labels need to be normalized.",
        "",
        "## Output Files",
        "",
        "- `stage_family_drift_shift90_details.csv`",
        "- `stage_family_drift_shift90_trigger_mode_summary.csv`",
        "- `stage_family_drift_shift90_pattern_summary.csv`",
        "- `stage_family_drift_shift90_action_summary.csv`",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    details = load_target()
    summaries = {
        "trigger_mode": grouped(details, ["trigger_family", "mode_family", "cause_bucket"]),
        "pattern": grouped(details, ["drift_pattern", "cause_bucket"]),
        "action": grouped(details, ["review_action"]),
    }
    export_csv(details, OUT_DIR / "stage_family_drift_shift90_details.csv")
    export_csv(summaries["trigger_mode"], OUT_DIR / "stage_family_drift_shift90_trigger_mode_summary.csv")
    export_csv(summaries["pattern"], OUT_DIR / "stage_family_drift_shift90_pattern_summary.csv")
    export_csv(summaries["action"], OUT_DIR / "stage_family_drift_shift90_action_summary.csv")
    write_text(OUT_DIR / "stage_family_drift_shift90_review_report.md", render_report(details, summaries))

    print(summaries["pattern"].to_string(index=False))
    print()
    print(summaries["action"].to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
