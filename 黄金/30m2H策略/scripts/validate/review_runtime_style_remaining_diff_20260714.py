# -*- coding: utf-8 -*-
"""Review residual matched PnL and signal-set drift after runtime adjustment."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

RUNTIME_DIR = VALIDATION_DIR / "runtime_style_dynamic_risk_alignment_20260714"
MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_shift90_close_retry_20260714"
CAUSE_DIR = VALIDATION_DIR / "unmatched_signal_cause_shift90_close_retry_20260714"
EQ_DIR = VALIDATION_DIR / "trigger_family_equivalence_shift90_close_retry_20260714"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_shift90_close_retry_20260714"
OUT_DIR = VALIDATION_DIR / "runtime_style_remaining_diff_review_20260714"

RUNTIME_TRADES = RUNTIME_DIR / "runtime_style_dynamic_risk_trades.csv"
PRIMARY_SUMMARY = RUNTIME_DIR / "runtime_style_primary_diff_class_summary.csv"
UNIQUE_SUMMARY = MAPPING_DIR / "unique_match_summary.csv"
POLICY_MATCHES = EQ_DIR / "bidirectional_m30_m15_90_profit20_selected_matches.csv"
MT5_UNIQUE = DYNAMIC_DIR / "mt5_ledger_unique_signals.csv"
PY_CAUSE = CAUSE_DIR / "python_mt5_python_unmatched_cause.csv"
MT5_CAUSE = CAUSE_DIR / "python_mt5_mt5_unmatched_cause.csv"


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


def safe_float(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL", "-1"}:
        return "SELL"
    if text in {"B", "BUY", "L", "LONG", "1"}:
        return "BUY"
    return text


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.loc[:, [c for c in columns if c in frame.columns]].copy()
    if max_rows is not None:
        display = display.head(max_rows)
    columns = list(display.columns)
    rows = [[as_text(value) for value in row] for row in display.to_numpy()]
    widths = [len(col) for col in columns]
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def render(row: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(row)) + " |"

    header = render(columns)
    sep = "| " + " | ".join("-" * width for width in widths) + " |"
    return "\n".join([header, sep, *[render(row) for row in rows]])


def classify_matched_case(row: pd.Series) -> tuple[str, str, str]:
    diff_class = as_text(row.get("primary_diff_class"))
    abs_residual = abs(safe_float(row.get("runtime_residual_$")))

    if diff_class == "pnl_aligned":
        return (
            "P3",
            "accept_or_rounding_audit",
            "Residual is already in the pnl_aligned bucket; keep as tolerance/rounding unless it grows after later reruns.",
        )
    if diff_class == "stop_distance_diff":
        return (
            "P1" if abs_residual >= 10 else "P2",
            "review_stop_distance_or_fill_price",
            "Stop distance/fill mismatch remains after Stage-exit adjustment; check stop_pts_spec/actual_stop/fill fields first.",
        )
    if diff_class == "exit_reason_diff":
        return (
            "P1" if abs_residual >= 10 else "P2",
            "review_exit_reason_runtime_ordering",
            "Exit reason differs but is not in the resolved Stage-exit class; check broker SL/TP/cross chronology and close retry.",
        )
    if diff_class == "minor_or_mixed_diff":
        return (
            "P2",
            "defer_after_p1_or_split_minor_mixed",
            "Mixed small causes remain; split only after P1 stop/exit cases are reviewed.",
        )
    if diff_class == "stage_exit_detail_diff":
        return (
            "P1",
            "resolve_remaining_stage_exit_blocker",
            "A Stage-exit residual remains after runtime adjustment; review integrated runtime blocker/journal evidence first.",
        )
    return ("P2", "review_unclassified_matched_residual", "Residual remains in an unclassified matched bucket.")


def build_matched_residual_cases(runtime_trades: pd.DataFrame) -> pd.DataFrame:
    matched = runtime_trades[runtime_trades["primary_diff_class"].notna()].copy()
    matched["runtime_residual_$"] = (
        matched["runtime_adjusted_total_$"].map(safe_float) - matched["mt5_profit"].map(safe_float)
    ).round(6)
    matched["runtime_abs_residual_$"] = matched["runtime_residual_$"].abs().round(6)
    remaining = matched[matched["runtime_abs_residual_$"] > 0.000001].copy()
    classifications = remaining.apply(classify_matched_case, axis=1, result_type="expand")
    classifications.columns = ["action_priority", "action_bucket", "action_note"]
    remaining = pd.concat([remaining, classifications], axis=1)
    remaining = remaining.sort_values(["action_priority", "runtime_abs_residual_$"], ascending=[True, False])

    cols = [
        "action_priority",
        "action_bucket",
        "py_trade_id",
        "mt5_trade_id",
        "date",
        "dir",
        "trigger_family",
        "mode_family",
        "mode",
        "primary_diff_class",
        "dynamic_total_$",
        "runtime_adjusted_total_$",
        "mt5_profit",
        "runtime_residual_$",
        "runtime_abs_residual_$",
        "stage1_exit",
        "stage2_exit",
        "stage3_exit",
        "mt5_deal_reasons",
        "py_stage_dynamic_profit",
        "mt5_stage_net_profit",
        "action_note",
    ]
    return remaining[[c for c in cols if c in remaining.columns]]


def matched_summary(remaining: pd.DataFrame) -> pd.DataFrame:
    if remaining.empty:
        return pd.DataFrame()
    grouped = (
        remaining.groupby(["primary_diff_class", "action_priority", "action_bucket"], dropna=False)
        .agg(
            rows=("py_trade_id", "count"),
            residual_sum=("runtime_residual_$", "sum"),
            abs_residual_sum=("runtime_abs_residual_$", "sum"),
            max_abs_residual=("runtime_abs_residual_$", "max"),
        )
        .reset_index()
    )
    for col in ["residual_sum", "abs_residual_sum", "max_abs_residual"]:
        grouped[col] = grouped[col].round(6)
    return grouped.sort_values(["action_priority", "abs_residual_sum"], ascending=[True, False])


def action_for_signal_case(side: str, cause_bucket: str, abs_effect: float) -> tuple[str, str, str]:
    high = abs_effect >= 50.0
    if side == "mt5_unmatched":
        mapping = {
            "mapping_conflict_or_profit_diff": ("P1", "recheck_mapping_with_runtime_pnl"),
            "stage_execution_diff_or_family_drift": ("P1", "split_family_drift_vs_execution_after_runtime"),
            "layer3_reject": ("P1", "review_python_layer3_acceptance_mismatch"),
            "trigger_family_drift": ("P1", "review_trigger_family_equivalence_or_anchor"),
            "missing_raw_parent": ("P2", "review_m15_raw_parent_or_rescue_gap"),
            "missing_python_candidate": ("P2", "review_missing_python_candidate"),
        }
    else:
        mapping = {
            "unique_match_conflict": ("P1", "resolve_unique_match_conflict_after_runtime"),
            "mt5_family_or_time_drift": ("P1", "review_family_or_time_drift"),
            "python_signal_not_in_mt5_ledger": ("P2", "review_python_extra_signal_lifecycle"),
        }
    priority, action = mapping.get(cause_bucket, ("P2", "review_unclassified_signal_drift"))
    if high and priority == "P2":
        priority = "P1"
    note = (
        "MT5-only profit is missing from Python-MT5, so gap_effect is negative MT5 net profit."
        if side == "mt5_unmatched"
        else "Python-only profit is included in Python-MT5 but absent from MT5, so gap_effect equals Python runtime-adjusted PnL."
    )
    return priority, action, note


def load_policy_matches() -> pd.DataFrame:
    matches = read_csv(POLICY_MATCHES)
    return matches[matches["source"] == "python_mt5"].copy()


def load_policy_mt5_unmatched(policy_matches: pd.DataFrame) -> pd.DataFrame:
    mt5 = read_csv(MT5_UNIQUE).copy()
    mt5["mt5_trade_id"] = [f"mt5_{idx + 1:04d}" for idx in range(len(mt5))]
    mt5["signal_anchor_time"] = pd.to_datetime(mt5["signal_anchor_time"], errors="coerce")
    mt5["aligned_time"] = mt5["signal_anchor_time"] + pd.Timedelta(minutes=90)
    mt5["dir_norm"] = mt5["dir"].map(normalize_dir)
    matched_mt5 = set(policy_matches["mt5_trade_id"].astype(str))
    return mt5[~mt5["mt5_trade_id"].astype(str).isin(matched_mt5)].copy()


def build_signal_set_drift_cases(runtime_trades: pd.DataFrame, policy_matches: pd.DataFrame) -> pd.DataFrame:
    matched_py = set(policy_matches["py_trade_id"].astype(str))
    py_unmatched = runtime_trades[~runtime_trades["py_trade_id"].astype(str).isin(matched_py)].copy()
    mt5_unmatched = load_policy_mt5_unmatched(policy_matches)
    py_cause = read_csv(PY_CAUSE) if PY_CAUSE.exists() else pd.DataFrame()
    mt5_cause = read_csv(MT5_CAUSE) if MT5_CAUSE.exists() else pd.DataFrame()

    py = py_unmatched.copy()
    if not py_cause.empty:
        cause_cols = [
            "trade_id",
            "cause_bucket",
            "mt5_status",
            "mt5_abs_minutes",
            "mt5_date",
            "mt5_trigger_family",
            "mt5_mode_family",
            "mt5_signed_minutes",
            "mt5_mode",
            "mt5_variant",
        ]
        py = py.merge(py_cause[[c for c in cause_cols if c in py_cause.columns]], left_on="py_trade_id", right_on="trade_id", how="left")

    py_rows = pd.DataFrame(
        {
            "side": "python_unmatched",
            "trade_id": py["py_trade_id"],
            "target_time": py["date"],
            "dir_norm": py["dir"].map(normalize_dir),
            "trigger_family": py["trigger_family"],
            "mode_family": py["mode_family"],
            "mode_or_signal_src": py["mode"],
            "source_profit_$": py["runtime_adjusted_total_$"].map(safe_float),
            "gap_effect_$": py["runtime_adjusted_total_$"].map(safe_float),
            "cause_bucket": py.get("cause_bucket", ""),
            "nearby_status": py.get("mt5_status", ""),
            "nearby_abs_minutes": py.get("mt5_abs_minutes", ""),
            "nearby_time": py.get("mt5_date", ""),
            "nearby_trigger_family": py.get("mt5_trigger_family", ""),
            "nearby_mode_family": py.get("mt5_mode_family", ""),
            "runtime_adjustment_decision": py["runtime_adjustment_decision"],
        }
    )

    mt5 = mt5_unmatched.copy()
    if not mt5_cause.empty:
        cause_cols = [
            "trade_id",
            "cause_bucket",
            "parent_status",
            "parent_time",
            "parent_mode_family",
            "parent_abs_minutes",
            "accepted_status",
            "accepted_abs_minutes",
            "accepted_date",
            "accepted_trigger_family",
            "accepted_mode_family",
            "accepted_mode",
            "picked_status",
            "picked_abs_minutes",
            "picked_date",
            "picked_trigger_family",
            "picked_mode_family",
            "picked_mode",
            "executed_status",
            "executed_abs_minutes",
            "executed_date",
            "executed_trigger_family",
            "executed_mode_family",
            "executed_mode",
        ]
        mt5 = mt5.merge(mt5_cause[[c for c in cause_cols if c in mt5_cause.columns]], left_on="mt5_trade_id", right_on="trade_id", how="left")

    mt5_rows = pd.DataFrame(
        {
            "side": "mt5_unmatched",
            "trade_id": mt5["mt5_trade_id"],
            "target_time": mt5["aligned_time"],
            "dir_norm": mt5["dir_norm"],
            "trigger_family": mt5["trigger_family"],
            "mode_family": mt5["mode_family"],
            "mode_or_signal_src": mt5["signal_src"],
            "source_profit_$": mt5["net_profit"].map(safe_float),
            "gap_effect_$": -mt5["net_profit"].map(safe_float),
            "cause_bucket": mt5.get("cause_bucket", ""),
            "nearby_status": mt5.get("accepted_status", ""),
            "nearby_abs_minutes": mt5.get("accepted_abs_minutes", ""),
            "nearby_time": mt5.get("accepted_date", ""),
            "nearby_trigger_family": mt5.get("accepted_trigger_family", ""),
            "nearby_mode_family": mt5.get("accepted_mode_family", ""),
            "runtime_adjustment_decision": "",
            "parent_status": mt5.get("parent_status", ""),
            "parent_abs_minutes": mt5.get("parent_abs_minutes", ""),
            "picked_status": mt5.get("picked_status", ""),
            "picked_abs_minutes": mt5.get("picked_abs_minutes", ""),
            "executed_status": mt5.get("executed_status", ""),
            "executed_abs_minutes": mt5.get("executed_abs_minutes", ""),
        }
    )

    combined = pd.concat([py_rows, mt5_rows], ignore_index=True, sort=False)
    combined["source_profit_$"] = combined["source_profit_$"].round(6)
    combined["gap_effect_$"] = combined["gap_effect_$"].round(6)
    combined["abs_gap_effect_$"] = combined["gap_effect_$"].abs().round(6)
    combined["cause_bucket"] = combined["cause_bucket"].fillna("unclassified")

    classifications = [
        action_for_signal_case(as_text(row["side"]), as_text(row["cause_bucket"]), safe_float(row["abs_gap_effect_$"]))
        for _, row in combined.iterrows()
    ]
    combined["action_priority"] = [item[0] for item in classifications]
    combined["action_bucket"] = [item[1] for item in classifications]
    combined["action_note"] = [item[2] for item in classifications]
    combined = combined.sort_values(["action_priority", "abs_gap_effect_$"], ascending=[True, False]).reset_index(drop=True)
    return combined


def signal_summary(signal_cases: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        signal_cases.groupby(["side", "cause_bucket", "action_priority", "action_bucket"], dropna=False)
        .agg(
            rows=("trade_id", "count"),
            source_profit_sum=("source_profit_$", "sum"),
            gap_effect_sum=("gap_effect_$", "sum"),
            abs_gap_effect_sum=("abs_gap_effect_$", "sum"),
            max_abs_gap_effect=("abs_gap_effect_$", "max"),
        )
        .reset_index()
    )
    for col in ["source_profit_sum", "gap_effect_sum", "abs_gap_effect_sum", "max_abs_gap_effect"]:
        grouped[col] = grouped[col].round(6)
    return grouped.sort_values(["action_priority", "abs_gap_effect_sum"], ascending=[True, False])


def trigger_mode_summary(signal_cases: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        signal_cases.groupby(["side", "trigger_family", "mode_family"], dropna=False)
        .agg(
            rows=("trade_id", "count"),
            source_profit_sum=("source_profit_$", "sum"),
            gap_effect_sum=("gap_effect_$", "sum"),
            abs_gap_effect_sum=("abs_gap_effect_$", "sum"),
        )
        .reset_index()
    )
    for col in ["source_profit_sum", "gap_effect_sum", "abs_gap_effect_sum"]:
        grouped[col] = grouped[col].round(6)
    return grouped.sort_values("abs_gap_effect_sum", ascending=False)


def overall_summary(
    runtime_trades: pd.DataFrame,
    matched_cases: pd.DataFrame,
    signal_cases: pd.DataFrame,
    policy_matches: pd.DataFrame,
) -> pd.DataFrame:
    py_total = float(runtime_trades["runtime_adjusted_total_$"].sum())
    mt5_matched_profit = float(policy_matches["mt5_profit"].map(safe_float).sum()) if not policy_matches.empty else 0.0
    mt5_unmatched_profit = float(signal_cases.loc[signal_cases["side"] == "mt5_unmatched", "source_profit_$"].sum())
    mt5_ref_profit = mt5_matched_profit + mt5_unmatched_profit

    matched_residual_sum = float(matched_cases["runtime_residual_$"].sum()) if not matched_cases.empty else 0.0
    python_unmatched_gap = float(signal_cases.loc[signal_cases["side"] == "python_unmatched", "gap_effect_$"].sum())
    mt5_unmatched_gap = float(signal_cases.loc[signal_cases["side"] == "mt5_unmatched", "gap_effect_$"].sum())
    signal_gap = python_unmatched_gap + mt5_unmatched_gap
    reconstructed_gap = matched_residual_sum + signal_gap
    direct_gap = py_total - mt5_ref_profit

    return pd.DataFrame(
        [
            {
                "metric": "runtime_python_mt5_total_profit",
                "value": round(py_total, 6),
                "note": "Sum of runtime_adjusted_total_$ over all Python-MT5 trades.",
            },
            {
                "metric": "mt5_reference_profit_from_mapping",
                "value": round(mt5_ref_profit, 6),
                "note": "Selected-policy matched MT5 profit plus selected-policy MT5-unmatched ledger profit.",
            },
            {
                "metric": "selected_policy_matched_mt5_profit",
                "value": round(mt5_matched_profit, 6),
                "note": "MT5 profit over bidirectional_m30_m15_90_profit20 selected matches.",
            },
            {
                "metric": "direct_runtime_gap_python_minus_mt5",
                "value": round(direct_gap, 6),
                "note": "Runtime Python-MT5 total profit minus reconstructed MT5 reference profit.",
            },
            {
                "metric": "remaining_matched_residual_sum",
                "value": round(matched_residual_sum, 6),
                "note": "Runtime adjusted matched PnL minus matched MT5 PnL for non-zero residual cases.",
            },
            {
                "metric": "python_unmatched_gap_effect",
                "value": round(python_unmatched_gap, 6),
                "note": "Python-MT5 unmatched profit included only on Python side.",
            },
            {
                "metric": "mt5_unmatched_gap_effect",
                "value": round(mt5_unmatched_gap, 6),
                "note": "Negative of MT5-only ledger profit.",
            },
            {
                "metric": "signal_set_gap_effect_sum",
                "value": round(signal_gap, 6),
                "note": "Python unmatched plus MT5 unmatched gap effect.",
            },
            {
                "metric": "reconstructed_gap_from_components",
                "value": round(reconstructed_gap, 6),
                "note": "Matched residual plus signal-set gap effect.",
            },
        ]
    )


def build_report(
    overall: pd.DataFrame,
    matched_summary_df: pd.DataFrame,
    signal_summary_df: pd.DataFrame,
    trigger_summary_df: pd.DataFrame,
    matched_cases: pd.DataFrame,
    signal_cases: pd.DataFrame,
    primary_summary: pd.DataFrame,
) -> str:
    lines = [
        "# Runtime Style Remaining Diff Review 20260714",
        "",
        "## Scope",
        "",
        "- Starts after `runtime_style_dynamic_risk_alignment_20260714`.",
        "- Separates residual into matched non-Stage-exit PnL residual and signal-set drift.",
        "- Uses the same `bidirectional_m30_m15_90_profit20` selected-match policy as matched profit/exit diff.",
        "- Runtime-adjusted Python PnL is used for Python-unmatched impact.",
        "",
        "## Overall Components",
        "",
        markdown_table(overall, ["metric", "value", "note"]),
        "",
        "## Runtime Primary Diff Summary",
        "",
        markdown_table(
            primary_summary,
            [
                "primary_diff_class",
                "rows",
                "adjusted_rows",
                "runtime_residual_sum",
                "runtime_abs_residual_sum",
                "runtime_abs_residual_mean",
            ],
        ),
        "",
        "## Remaining Matched Residual Summary",
        "",
        markdown_table(
            matched_summary_df,
            [
                "primary_diff_class",
                "action_priority",
                "action_bucket",
                "rows",
                "residual_sum",
                "abs_residual_sum",
                "max_abs_residual",
            ],
        ),
        "",
        "## Signal-Set Drift Summary",
        "",
        markdown_table(
            signal_summary_df,
            [
                "side",
                "cause_bucket",
                "action_priority",
                "action_bucket",
                "rows",
                "gap_effect_sum",
                "abs_gap_effect_sum",
                "max_abs_gap_effect",
            ],
        ),
        "",
        "## Trigger/Mode Impact",
        "",
        markdown_table(
            trigger_summary_df,
            ["side", "trigger_family", "mode_family", "rows", "gap_effect_sum", "abs_gap_effect_sum"],
        ),
        "",
        "## Top Matched Residual Cases",
        "",
        markdown_table(
            matched_cases,
            [
                "action_priority",
                "action_bucket",
                "py_trade_id",
                "mt5_trade_id",
                "date",
                "primary_diff_class",
                "runtime_residual_$",
                "runtime_abs_residual_$",
            ],
            max_rows=12,
        ),
        "",
        "## Top Signal-Set Drift Cases",
        "",
        markdown_table(
            signal_cases,
            [
                "action_priority",
                "action_bucket",
                "side",
                "trade_id",
                "target_time",
                "trigger_family",
                "mode_family",
                "cause_bucket",
                "source_profit_$",
                "gap_effect_$",
                "abs_gap_effect_$",
            ],
            max_rows=15,
        ),
        "",
        "## Action Plan",
        "",
        "1. Treat the remaining matched residual as small but actionable diagnostics: review `exit_reason_diff` and `stop_distance_diff` first, then split `minor_or_mixed_diff`; keep `pnl_aligned` as tolerance unless later reruns expand it.",
        "2. For signal-set drift, prioritize high-impact MT5-only positive-profit misses and Python-only high-impact extra signals; these dominate the post-runtime global gap.",
        "3. The cause labels in this report are regenerated from the close-retry mapping snapshot; rerun this review after any mapping-policy change.",
        "4. Keep EA price-side behavior unchanged until a new smoke directly proves a Stage1/2 price-side error.",
    ]
    return "\n".join(lines)


def write_readme() -> None:
    lines = [
        "# Runtime Style Remaining Diff Review 20260714",
        "",
        "Generated by `review_runtime_style_remaining_diff_20260714.py`.",
        "",
        "## Files",
        "",
        "- `remaining_matched_residual_cases.csv`: matched trades still carrying runtime residual after Stage-exit adjustment.",
        "- `remaining_matched_residual_summary.csv`: matched residual grouped by class/action.",
        "- `remaining_signal_set_drift_cases.csv`: Python-unmatched and MT5-unmatched cases with gap effect and action bucket.",
        "- `remaining_signal_set_drift_summary.csv`: unmatched drift grouped by side/cause/action.",
        "- `remaining_signal_trigger_mode_summary.csv`: unmatched drift grouped by side/trigger/mode.",
        "- `remaining_diff_overall_summary.csv`: reconstructed gap components.",
        "- `remaining_diff_action_plan.md`: human-readable review and next actions.",
        "",
        "## Boundary",
        "",
        "This is a review layer. It does not modify EA, Python signal generation, or prior dynamic-risk outputs.",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    runtime_trades = read_csv(RUNTIME_TRADES)
    primary_summary = read_csv(PRIMARY_SUMMARY)
    policy_matches = load_policy_matches()

    matched_cases = build_matched_residual_cases(runtime_trades)
    matched_summary_df = matched_summary(matched_cases)
    signal_cases = build_signal_set_drift_cases(runtime_trades, policy_matches)
    signal_summary_df = signal_summary(signal_cases)
    trigger_summary_df = trigger_mode_summary(signal_cases)
    overall = overall_summary(runtime_trades, matched_cases, signal_cases, policy_matches)

    export_csv(matched_cases, OUT_DIR / "remaining_matched_residual_cases.csv")
    export_csv(matched_summary_df, OUT_DIR / "remaining_matched_residual_summary.csv")
    export_csv(signal_cases, OUT_DIR / "remaining_signal_set_drift_cases.csv")
    export_csv(signal_summary_df, OUT_DIR / "remaining_signal_set_drift_summary.csv")
    export_csv(trigger_summary_df, OUT_DIR / "remaining_signal_trigger_mode_summary.csv")
    export_csv(overall, OUT_DIR / "remaining_diff_overall_summary.csv")
    write_text(
        OUT_DIR / "remaining_diff_action_plan.md",
        build_report(overall, matched_summary_df, signal_summary_df, trigger_summary_df, matched_cases, signal_cases, primary_summary),
    )
    write_readme()

    print(overall.to_string(index=False))
    print()
    print(matched_summary_df.to_string(index=False))
    print()
    print(signal_summary_df.head(12).to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
