# -*- coding: utf-8 -*-
"""Review remaining shift90 M15 SLOT1 post_n mismatches."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
INPUT = DATA_DIR / "validation" / "unmatched_signal_cause_shift90_20260713" / "m15_slot1_postn_raw_parent_cause.csv"
OUT_DIR = DATA_DIR / "validation" / "m15_slot1_postn_shift90_review_20260713"


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def read_input() -> pd.DataFrame:
    df = pd.read_csv(INPUT, encoding="utf-8-sig")
    for col in [
        "target_time",
        "parent_time",
        "accepted_date",
        "picked_date",
        "executed_date",
        "mt5_date",
    ]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in [
        "profit",
        "parent_abs_minutes",
        "accepted_abs_minutes",
        "accepted_signed_minutes",
        "picked_abs_minutes",
        "picked_signed_minutes",
        "executed_abs_minutes",
        "executed_signed_minutes",
    ]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


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


def action_class(row: pd.Series) -> str:
    cause = str(row.get("cause_bucket", ""))
    parent = str(row.get("parent_status", ""))
    accepted_status = str(row.get("accepted_status", ""))
    picked_status = str(row.get("picked_status", ""))
    executed_status = str(row.get("executed_status", ""))
    accepted_abs = row.get("accepted_abs_minutes")

    if cause == "mapping_conflict_or_profit_diff":
        return "keep_for_mapping_or_profit_review"
    if cause == "layer3_reject":
        return "keep_for_layer3_review"
    if parent == "has_nearby_m30_parent":
        return "keep_parent_exists_trigger_family_drift"
    if accepted_status == "same_trigger_mode" and pd.notna(accepted_abs):
        if float(accepted_abs) <= 180:
            return "keep_same_trigger_candidate_local"
        return "keep_same_trigger_candidate_far"
    if picked_status == "same_trigger_mode" or executed_status == "same_trigger_mode":
        return "keep_same_trigger_after_layer3_or_stage"
    if parent == "missing_raw_parent" and accepted_status == "none":
        return "diagnostic_candidate_true_missing_parent"
    return "diagnostic_candidate_family_drift"


def ea_action(row: pd.Series) -> str:
    klass = str(row["action_class"])
    if klass.startswith("keep_"):
        return "do_not_filter"
    if klass == "diagnostic_candidate_true_missing_parent":
        return "diagnostic_only_possible_filter_candidate"
    return "diagnostic_only"


def build_review() -> pd.DataFrame:
    df = read_input()
    target = df[
        (df["source"] == "python_mt5")
        & (df["side"] == "mt5_unmatched")
        & (df["trigger_family"] == "M15 SLOT1")
        & (df["mode_family"] == "post_n")
    ].copy()
    target["parent_time_bucket"] = target["parent_abs_minutes"].map(time_bucket)
    target["accepted_time_bucket"] = target["accepted_abs_minutes"].map(time_bucket)
    target["picked_time_bucket"] = target["picked_abs_minutes"].map(time_bucket)
    target["executed_time_bucket"] = target["executed_abs_minutes"].map(time_bucket)
    target["action_class"] = target.apply(action_class, axis=1)
    target["ea_action"] = target.apply(ea_action, axis=1)
    return target


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
    keep_cols = [
        "trade_id",
        "target_time",
        "dir_norm",
        "profit",
        "cause_bucket",
        "parent_status",
        "parent_time_bucket",
        "accepted_status",
        "accepted_time_bucket",
        "accepted_trigger_family",
        "accepted_mode_family",
        "accepted_mode",
        "accepted_variant",
        "action_class",
        "ea_action",
    ]
    lines = [
        "# M15 SLOT1 post_n Shift90 Review",
        "",
        "## Cause Summary",
        "",
        summaries["cause"].to_markdown(index=False),
        "",
        "## Parent Summary",
        "",
        summaries["parent"].to_markdown(index=False),
        "",
        "## Action Summary",
        "",
        summaries["action"].to_markdown(index=False),
        "",
        "## EA Action Summary",
        "",
        summaries["ea_action"].to_markdown(index=False),
        "",
        "## Case Details",
        "",
        details[keep_cols].to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        "- The remaining `M15 SLOT1 / post_n` MT5-only set is mixed; it is not a pure missing-parent set.",
        "- Parent-only filtering remains unsafe because several rows without a nearby M30 parent still have Python same-trigger candidates or Layer3 candidates.",
        "- The only behaviorally plausible EA work here is diagnostic enrichment first; filtering needs a local, testable condition that does not depend on offline match labels.",
        "",
        "## Output Files",
        "",
        "- `m15_slot1_postn_shift90_review_details.csv`",
        "- `m15_slot1_postn_shift90_cause_summary.csv`",
        "- `m15_slot1_postn_shift90_parent_summary.csv`",
        "- `m15_slot1_postn_shift90_action_summary.csv`",
        "- `m15_slot1_postn_shift90_ea_action_summary.csv`",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    details = build_review()
    summaries = {
        "cause": grouped(details, ["cause_bucket"]),
        "parent": grouped(details, ["parent_status", "parent_time_bucket", "parent_mode_family"]),
        "action": grouped(details, ["action_class", "cause_bucket"]),
        "ea_action": grouped(details, ["ea_action"]),
    }

    export_csv(details, OUT_DIR / "m15_slot1_postn_shift90_review_details.csv")
    export_csv(summaries["cause"], OUT_DIR / "m15_slot1_postn_shift90_cause_summary.csv")
    export_csv(summaries["parent"], OUT_DIR / "m15_slot1_postn_shift90_parent_summary.csv")
    export_csv(summaries["action"], OUT_DIR / "m15_slot1_postn_shift90_action_summary.csv")
    export_csv(summaries["ea_action"], OUT_DIR / "m15_slot1_postn_shift90_ea_action_summary.csv")
    write_text(OUT_DIR / "m15_slot1_postn_shift90_review_report.md", render_report(details, summaries))

    print(summaries["cause"].to_string(index=False))
    print()
    print(summaries["ea_action"].to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
