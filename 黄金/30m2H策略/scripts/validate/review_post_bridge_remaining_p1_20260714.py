# -*- coding: utf-8 -*-
"""Review remaining P1 priorities after applying the M15 SLOT1 time-axis bridge cause view."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"
OUT_DIR = VALIDATION_DIR / "post_bridge_remaining_p1_review_20260714"

BRIDGE_DIR = VALIDATION_DIR / "m15_slot1_time_axis_bridge_20260714"
RUNTIME_REMAINING_DIR = VALIDATION_DIR / "runtime_style_remaining_diff_review_20260714"
POLICY_DIR = VALIDATION_DIR / "next_p1_policy_review_20260714"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def as_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def safe_float(value: object) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return 0.0
    return float(parsed)


def bool_value(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.loc[:, [c for c in columns if c in frame.columns]].copy()
    columns = list(display.columns)
    rows = [[as_text(value) for value in row] for row in display.to_numpy()]
    widths = [len(col) for col in columns]
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def render(row: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(row)) + " |"

    return "\n".join(
        [
            render(columns),
            "| " + " | ".join("-" * width for width in widths) + " |",
            *[render(row) for row in rows],
        ]
    )


def signal_action_bucket(row: pd.Series) -> tuple[str, str]:
    cause = str(row.get("effective_cause_bucket", ""))
    side = str(row.get("side", ""))
    if cause == "time_axis_bridge_candidate":
        return (
            "bridge_data_axis_accounting",
            "Keep as classification/data-axis work; do not treat as Layer3, StopSpec, or EA behavior evidence.",
        )
    if side == "python_unmatched" and cause == "unique_match_conflict":
        return (
            "resolve_unique_match_or_mapping_conflict",
            "Review whether this Python trade is competing with a nearby MT5 trade before changing signal rules.",
        )
    if side == "python_unmatched":
        return (
            "review_python_only_signal_or_time_drift",
            "Check Python accepted/picked/executed path and whether the MT5 ledger has a nearby equivalent.",
        )
    if cause == "layer3_reject":
        return (
            "review_python_layer3_or_time_axis_after_bridge",
            "Now that bridge cases are separated, inspect real Layer3/accepted-parent evidence for this MT5-only trade.",
        )
    if cause in {"trigger_family_drift", "stage_execution_diff_or_family_drift"}:
        return (
            "review_trigger_family_or_execution_boundary",
            "Check whether M30/M15 family equivalence or order-lifecycle evidence should reclassify this trade.",
        )
    return (
        "review_remaining_signal_set_case",
        "Inspect raw/accepted/picked/executed and mapping policy evidence before code changes.",
    )


def build_signal_review() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    signal = read_csv(BRIDGE_DIR / "remaining_signal_set_drift_bridge_reclass.csv")
    signal["bridge_reclass_applied_bool"] = signal["bridge_reclass_applied"].map(bool_value)
    signal["effective_cause_bucket"] = signal.apply(
        lambda row: row["bridge_cause_bucket"] if row["bridge_reclass_applied_bool"] else row["cause_bucket"],
        axis=1,
    )
    actions = signal.apply(signal_action_bucket, axis=1, result_type="expand")
    signal["post_bridge_action_bucket"] = actions[0]
    signal["post_bridge_action_note"] = actions[1]
    signal["post_bridge_abs_gap_effect_$"] = pd.to_numeric(signal["abs_gap_effect_$"], errors="coerce").fillna(0.0)
    signal["post_bridge_gap_effect_$"] = pd.to_numeric(signal["gap_effect_$"], errors="coerce").fillna(0.0)

    top_cases = signal.sort_values("post_bridge_abs_gap_effect_$", ascending=False).head(20).reset_index(drop=True)
    p1_non_bridge = signal[
        (signal["action_priority"].astype(str) == "P1")
        & (signal["effective_cause_bucket"].astype(str) != "time_axis_bridge_candidate")
    ].sort_values("post_bridge_abs_gap_effect_$", ascending=False).reset_index(drop=True)

    cause_summary = (
        signal.groupby(["side", "effective_cause_bucket"], dropna=False)
        .agg(
            rows=("trade_id", "count"),
            gap_sum_usd=("post_bridge_gap_effect_$", "sum"),
            abs_gap_sum_usd=("post_bridge_abs_gap_effect_$", "sum"),
        )
        .reset_index()
        .sort_values("abs_gap_sum_usd", ascending=False)
        .reset_index(drop=True)
    )
    return signal, top_cases, cause_summary


def build_matched_review() -> pd.DataFrame:
    matched = read_csv(RUNTIME_REMAINING_DIR / "remaining_matched_residual_cases.csv")
    policy = read_csv(POLICY_DIR / "python_mt5_0061_relaxed_policy_review.csv")
    policy_decision = str(policy["decision"].iloc[0]) if not policy.empty else ""
    policy_status = str(policy["status"].iloc[0]) if not policy.empty else ""

    rows = []
    for _, row in matched.iterrows():
        out = row.to_dict()
        py_trade_id = str(row.get("py_trade_id", ""))
        mt5_trade_id = str(row.get("mt5_trade_id", ""))
        if py_trade_id == "python_mt5_0061" and mt5_trade_id == "mt5_0045":
            out["post_bridge_status"] = "accounting_only_nonreliable_relaxed_mapping"
            out["post_bridge_action_bucket"] = "exclude_from_runtime_behavior_blocker"
            out["post_bridge_action_note"] = policy_decision
            out["policy_status"] = policy_status
        else:
            out["post_bridge_status"] = "unchanged_matched_residual"
            out["post_bridge_action_bucket"] = row.get("action_bucket", "")
            out["post_bridge_action_note"] = row.get("action_note", "")
            out["policy_status"] = ""
        rows.append(out)
    out_df = pd.DataFrame(rows)
    out_df["runtime_abs_residual_$"] = pd.to_numeric(out_df["runtime_abs_residual_$"], errors="coerce").fillna(0.0)
    return out_df.sort_values("runtime_abs_residual_$", ascending=False).reset_index(drop=True)


def build_summary(signal: pd.DataFrame, cause_summary: pd.DataFrame, matched: pd.DataFrame) -> pd.DataFrame:
    bridge_mask = signal["effective_cause_bucket"].astype(str) == "time_axis_bridge_candidate"
    p1_non_bridge = signal[
        (signal["action_priority"].astype(str) == "P1")
        & (~bridge_mask)
    ]
    matched_behavior_blockers = matched[
        (matched["action_priority"].astype(str) == "P1")
        & (matched["post_bridge_status"].astype(str) != "accounting_only_nonreliable_relaxed_mapping")
    ]
    rows = [
        {
            "metric": "signal_set_gap_effect_sum_no_fund_change",
            "value": round(float(signal["post_bridge_gap_effect_$"].sum()), 6),
            "note": "Bridge reclassifies cause only; gap effect is unchanged.",
        },
        {
            "metric": "time_axis_bridge_candidate_rows",
            "value": int(bridge_mask.sum()),
            "note": "These are data/time-axis classification items, not direct Layer3/EA fixes.",
        },
        {
            "metric": "time_axis_bridge_candidate_gap_sum",
            "value": round(float(signal.loc[bridge_mask, "post_bridge_gap_effect_$"].sum()), 6),
            "note": "Signed gap now isolated under bridge cause.",
        },
        {
            "metric": "p1_signal_cases_after_excluding_bridge",
            "value": int(len(p1_non_bridge)),
            "note": "Remaining P1 signal-set cases that still need mapping/signal review.",
        },
        {
            "metric": "p1_matched_behavior_candidates_after_policy",
            "value": int(len(matched_behavior_blockers)),
            "note": "python_mt5_0061/mt5_0045 is excluded from runtime behavior blockers.",
        },
        {
            "metric": "ea_price_side_repair_gate",
            "value": "closed",
            "note": "No current post-bridge evidence requires EA Stage1/2 price-side change.",
        },
    ]
    if not cause_summary.empty:
        top = cause_summary.iloc[0]
        rows.append(
            {
                "metric": "largest_effective_signal_cause_by_abs_gap",
                "value": f"{top['side']} / {top['effective_cause_bucket']}",
                "note": f"abs_gap_sum={float(top['abs_gap_sum_usd']):.6f}",
            }
        )
    return pd.DataFrame(rows)


def build_next_work_items(signal: pd.DataFrame, matched: pd.DataFrame) -> pd.DataFrame:
    bridge_mask = signal["effective_cause_bucket"].astype(str) == "time_axis_bridge_candidate"
    p1_signal = signal[
        (signal["action_priority"].astype(str) == "P1")
        & (~bridge_mask)
    ].sort_values("post_bridge_abs_gap_effect_$", ascending=False)
    matched_p1 = matched[
        (matched["action_priority"].astype(str) == "P1")
        & (matched["post_bridge_status"].astype(str) != "accounting_only_nonreliable_relaxed_mapping")
    ].sort_values("runtime_abs_residual_$", ascending=False)

    rows = []
    for _, row in p1_signal.head(8).iterrows():
        rows.append(
            {
                "work_type": "signal_set",
                "id": row.get("trade_id", ""),
                "priority": row.get("action_priority", ""),
                "side": row.get("side", ""),
                "target_time": row.get("target_time", ""),
                "effective_cause": row.get("effective_cause_bucket", ""),
                "gap_or_residual_$": row.get("gap_effect_$", ""),
                "abs_$": row.get("abs_gap_effect_$", ""),
                "next_action": row.get("post_bridge_action_bucket", ""),
                "note": row.get("post_bridge_action_note", ""),
            }
        )
    for _, row in matched_p1.head(5).iterrows():
        rows.append(
            {
                "work_type": "matched_residual",
                "id": f"{row.get('py_trade_id', '')}/{row.get('mt5_trade_id', '')}",
                "priority": row.get("action_priority", ""),
                "side": "matched",
                "target_time": row.get("date", ""),
                "effective_cause": row.get("primary_diff_class", ""),
                "gap_or_residual_$": row.get("runtime_residual_$", ""),
                "abs_$": row.get("runtime_abs_residual_$", ""),
                "next_action": row.get("post_bridge_action_bucket", ""),
                "note": row.get("post_bridge_action_note", ""),
            }
        )
    return pd.DataFrame(rows)


def write_report(summary: pd.DataFrame, cause_summary: pd.DataFrame, next_items: pd.DataFrame, matched: pd.DataFrame) -> None:
    accounting_only = matched[matched["post_bridge_status"].astype(str) == "accounting_only_nonreliable_relaxed_mapping"]
    lines = [
        "# Post-Bridge Remaining P1 Review 20260714",
        "",
        "## Summary",
        "",
        markdown_table(summary, ["metric", "value", "note"]),
        "",
        "## Signal Cause Summary",
        "",
        markdown_table(cause_summary, ["side", "effective_cause_bucket", "rows", "gap_sum_usd", "abs_gap_sum_usd"]),
        "",
        "## Next Work Items",
        "",
        markdown_table(
            next_items,
            [
                "work_type",
                "id",
                "priority",
                "side",
                "target_time",
                "effective_cause",
                "gap_or_residual_$",
                "abs_$",
                "next_action",
            ],
        ),
        "",
        "## Accounting-Only Matched Case",
        "",
        markdown_table(
            accounting_only,
            [
                "py_trade_id",
                "mt5_trade_id",
                "primary_diff_class",
                "runtime_residual_$",
                "runtime_abs_residual_$",
                "post_bridge_status",
                "post_bridge_action_bucket",
            ],
        ),
        "",
        "## Decision",
        "",
        "- Bridge reclassification does not change the fund curve.",
        "- `python_mt5_0061 / mt5_0045` is excluded from runtime behavior blockers because its selected match is non-reliable trigger-relaxed.",
        "- The next code-facing work is mapping/signal review for remaining non-bridge P1 cases, not EA price-side behavior changes.",
    ]
    write_text(OUT_DIR / "post_bridge_remaining_p1_report.md", "\n".join(lines))


def write_readme() -> None:
    lines = [
        "# Post-Bridge Remaining P1 Review 20260714",
        "",
        "Generated by `review_post_bridge_remaining_p1_20260714.py`.",
        "",
        "## Files",
        "",
        "- `post_bridge_signal_set_cases.csv`",
        "- `post_bridge_signal_cause_summary.csv`",
        "- `post_bridge_signal_top_cases.csv`",
        "- `post_bridge_matched_residual_review.csv`",
        "- `post_bridge_next_work_items.csv`",
        "- `post_bridge_priority_summary.csv`",
        "- `post_bridge_remaining_p1_report.md`",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    signal, top_cases, cause_summary = build_signal_review()
    matched = build_matched_review()
    summary = build_summary(signal, cause_summary, matched)
    next_items = build_next_work_items(signal, matched)

    export_csv(signal, OUT_DIR / "post_bridge_signal_set_cases.csv")
    export_csv(cause_summary, OUT_DIR / "post_bridge_signal_cause_summary.csv")
    export_csv(top_cases, OUT_DIR / "post_bridge_signal_top_cases.csv")
    export_csv(matched, OUT_DIR / "post_bridge_matched_residual_review.csv")
    export_csv(next_items, OUT_DIR / "post_bridge_next_work_items.csv")
    export_csv(summary, OUT_DIR / "post_bridge_priority_summary.csv")
    write_report(summary, cause_summary, next_items, matched)
    write_readme()

    print(summary.to_string(index=False))
    print()
    print(next_items.head(12).to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
