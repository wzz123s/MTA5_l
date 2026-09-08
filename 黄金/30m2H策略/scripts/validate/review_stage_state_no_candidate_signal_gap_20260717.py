# -*- coding: utf-8 -*-
"""Triage true no-candidate signal-set gaps for stage-state MT5 alignment.

This gate reviews only rows already classified as no-candidate in the current
stage-state signal-set triage. It widens the search window around each case to
separate boundary/accounting cases from likely signal-construction gaps.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

TRIAGE_DIR = VALIDATION_DIR / "stage_state_signal_set_residual_triage_20260716"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"

OUT_DIR = VALIDATION_DIR / "stage_state_no_candidate_signal_gap_triage_20260717"

EA_ALIGN_DELTA_MINUTES = 90
DAY_MINUTES = 24 * 60
WINDOW_7D = 7 * DAY_MINUTES
WINDOW_30D = 30 * DAY_MINUTES
WINDOW_90D = 90 * DAY_MINUTES

NO_CANDIDATE_BUCKETS = {
    "python_only_signal_gap_no_mt5_candidate",
    "mt5_only_signal_gap_no_python_candidate",
}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL", "SHORT", "-1"}:
        return "SELL"
    if text in {"L", "B", "BUY", "LONG", "1"}:
        return "BUY"
    return text


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def safe_float(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def parse_time(value: object) -> pd.Timestamp:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.notna(parsed):
        return parsed
    return pd.to_datetime(str(value).replace(".", "-"), errors="coerce")


def priority(abs_gap: float) -> str:
    if abs_gap >= 150:
        return "P1"
    if abs_gap >= 75:
        return "P2"
    if abs_gap >= 25:
        return "P3"
    return "P4"


def mode_family(value: object) -> str:
    text = str(value).strip()
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return text


def load_python_trades() -> pd.DataFrame:
    df = read_csv(DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv").copy()
    df["py_trade_id"] = [f"python_mt5_{i + 1:04d}" for i in range(len(df))]
    df["target_time"] = pd.to_datetime(df["date"], errors="coerce")
    df["dir_norm"] = df["dir"].map(normalize_dir)
    df["mode_family"] = df["mode_family"].map(mode_family)
    df["profit"] = pd.to_numeric(df["dynamic_total_$"], errors="coerce")
    return df


def load_mt5_trades() -> pd.DataFrame:
    df = read_csv(DYNAMIC_DIR / "mt5_ledger_unique_signals.csv").copy()
    df["mt5_trade_id"] = [f"mt5_{i + 1:04d}" for i in range(len(df))]
    df["signal_anchor_time"] = pd.to_datetime(df["signal_anchor_time"], errors="coerce")
    df["target_time"] = df["signal_anchor_time"] + pd.Timedelta(minutes=EA_ALIGN_DELTA_MINUTES)
    df["dir_norm"] = df["dir"].map(normalize_dir)
    df["mode_family"] = df["mode_family"].map(mode_family)
    df["profit"] = pd.to_numeric(df["net_profit"], errors="coerce")
    return df


def compact_row(row: pd.Series, side: str) -> dict[str, object]:
    if row is None or row.empty:
        return {}
    if side == "python_unmatched":
        return {
            "nearest_trade_id": row.get("mt5_trade_id", ""),
            "nearest_time": row.get("target_time", ""),
            "nearest_raw_anchor": row.get("signal_anchor_time", ""),
            "nearest_dir_norm": row.get("dir_norm", ""),
            "nearest_trigger_family": row.get("trigger_family", ""),
            "nearest_mode_family": row.get("mode_family", ""),
            "nearest_signal_or_mode": row.get("signal_src", ""),
            "nearest_profit": safe_float(row.get("profit")),
            "nearest_stop_pts_spec": safe_float(row.get("stop_pts_spec")),
            "nearest_balance_after": safe_float(row.get("balance_after")),
        }
    return {
        "nearest_trade_id": row.get("py_trade_id", ""),
        "nearest_time": row.get("target_time", ""),
        "nearest_raw_anchor": "",
        "nearest_dir_norm": row.get("dir_norm", ""),
        "nearest_trigger_family": row.get("trigger_family", ""),
        "nearest_mode_family": row.get("mode_family", ""),
        "nearest_signal_or_mode": row.get("mode", ""),
        "nearest_profit": safe_float(row.get("profit")),
        "nearest_stop_pts_spec": safe_float(row.get("stop_pts_spec")),
        "nearest_balance_after": safe_float(row.get("balance_after")),
    }


def nearest_with_context(
    target_time: pd.Timestamp,
    case_dir: str,
    trigger: str,
    mode: str,
    other: pd.DataFrame,
    side: str,
) -> dict[str, object]:
    if pd.isna(target_time) or other.empty:
        return {
            "same_dir_7d_count": 0,
            "same_dir_30d_count": 0,
            "same_dir_90d_count": 0,
            "same_trigger_mode_30d_count": 0,
            "same_trigger_30d_count": 0,
            "same_mode_30d_count": 0,
            "opposite_dir_1d_count": 0,
            "opposite_dir_7d_count": 0,
            "nearest_same_dir_minutes": "",
            "nearest_any_dir_minutes": "",
        }

    work = other.copy()
    work["time_diff_minutes"] = (work["target_time"] - target_time).dt.total_seconds() / 60.0
    work["abs_time_diff_minutes"] = work["time_diff_minutes"].abs()
    work = work[pd.notna(work["abs_time_diff_minutes"])]

    same_dir = work[work["dir_norm"] == case_dir].copy()
    opposite_dir = work[work["dir_norm"] != case_dir].copy()

    same_dir_30d = same_dir[same_dir["abs_time_diff_minutes"] <= WINDOW_30D].copy()
    nearest_same = same_dir.sort_values("abs_time_diff_minutes").iloc[0] if not same_dir.empty else pd.Series(dtype=object)
    nearest_any = work.sort_values("abs_time_diff_minutes").iloc[0] if not work.empty else pd.Series(dtype=object)

    same_trigger_mode_30d = same_dir_30d[
        (same_dir_30d["trigger_family"].astype(str) == str(trigger))
        & (same_dir_30d["mode_family"].astype(str) == str(mode))
    ]
    same_trigger_30d = same_dir_30d[same_dir_30d["trigger_family"].astype(str) == str(trigger)]
    same_mode_30d = same_dir_30d[same_dir_30d["mode_family"].astype(str) == str(mode)]

    same_context = compact_row(nearest_same, side)
    any_context = compact_row(nearest_any, side)
    out = {
        "same_dir_7d_count": int((same_dir["abs_time_diff_minutes"] <= WINDOW_7D).sum()),
        "same_dir_30d_count": int((same_dir["abs_time_diff_minutes"] <= WINDOW_30D).sum()),
        "same_dir_90d_count": int((same_dir["abs_time_diff_minutes"] <= WINDOW_90D).sum()),
        "same_trigger_mode_30d_count": int(len(same_trigger_mode_30d)),
        "same_trigger_30d_count": int(len(same_trigger_30d)),
        "same_mode_30d_count": int(len(same_mode_30d)),
        "opposite_dir_1d_count": int((opposite_dir["abs_time_diff_minutes"] <= DAY_MINUTES).sum()),
        "opposite_dir_7d_count": int((opposite_dir["abs_time_diff_minutes"] <= WINDOW_7D).sum()),
        "nearest_same_dir_minutes": round(float(nearest_same.get("abs_time_diff_minutes")), 6)
        if not nearest_same.empty
        else "",
        "nearest_same_dir_signed_minutes": round(float(nearest_same.get("time_diff_minutes")), 6)
        if not nearest_same.empty
        else "",
        "nearest_any_dir_minutes": round(float(nearest_any.get("abs_time_diff_minutes")), 6)
        if not nearest_any.empty
        else "",
        "nearest_any_dir_signed_minutes": round(float(nearest_any.get("time_diff_minutes")), 6)
        if not nearest_any.empty
        else "",
    }
    out.update({f"same_dir_{k}": v for k, v in same_context.items()})
    out.update({f"any_dir_{k}": v for k, v in any_context.items()})
    return out


def classify_case(row: dict[str, object], py: pd.DataFrame, mt5: pd.DataFrame) -> tuple[str, str, str]:
    side = str(row["side"])
    target_time = parse_time(row["target_time"])
    trigger = str(row["trigger_family"])
    mode = str(row["mode_family"])
    mode_or_signal = str(row.get("mode_or_signal_src", ""))
    variant = str(row.get("variant", ""))
    nearest_same = safe_float(row.get("nearest_same_dir_minutes"), default=10**12)
    same_30d = int(row.get("same_dir_30d_count", 0))
    same_trigger_mode_30d = int(row.get("same_trigger_mode_30d_count", 0))
    opposite_1d = int(row.get("opposite_dir_1d_count", 0))
    opposite_7d = int(row.get("opposite_dir_7d_count", 0))

    first_py = py["target_time"].min()
    last_py = py["target_time"].max()
    first_mt5 = mt5["target_time"].min()
    last_mt5 = mt5["target_time"].max()

    if side == "python_unmatched" and pd.notna(target_time) and target_time < first_mt5:
        return (
            "python_before_first_mt5_trade_gap",
            "diagnostic_or_data_window_review",
            "Python-MT5 signal occurs before the first MT5 ledger trade; review warmup/history/EA-start boundary before strategy changes.",
        )
    if side == "python_unmatched" and pd.notna(target_time) and target_time > last_mt5:
        return (
            "python_after_last_mt5_trade_gap",
            "diagnostic_or_data_window_review",
            "Python-MT5 signal occurs after the last MT5 ledger trade; review end-window handling before strategy changes.",
        )
    if side == "mt5_unmatched" and pd.notna(target_time) and target_time < first_py:
        return (
            "mt5_before_first_python_trade_gap",
            "diagnostic_or_data_window_review",
            "MT5 signal occurs before the first Python-MT5 trade; review warmup/history boundary.",
        )
    if side == "mt5_unmatched" and pd.notna(target_time) and target_time > last_py:
        return (
            "mt5_after_last_python_trade_gap",
            "diagnostic_or_data_window_review",
            "MT5 signal occurs after the last Python-MT5 trade; review end-window handling.",
        )
    if same_30d > 0 and nearest_same > WINDOW_7D and same_trigger_mode_30d > 0:
        return (
            "outside_7d_same_family_mapping_window_review",
            "mapping_accounting_review",
            "Same direction/trigger/mode appears outside the 7-day candidate window; keep as accounting/window review, not EA behavior proof.",
        )
    if same_30d > 0 and nearest_same > WINDOW_7D:
        return (
            "outside_7d_same_direction_mapping_window_review",
            "mapping_accounting_review",
            "Same direction appears outside the 7-day candidate window but not same family; review mapping window only as diagnostic.",
        )
    if opposite_1d > 0 or opposite_7d > 0:
        return (
            "nearby_opposite_direction_signal_divergence",
            "signal_construction_review",
            "A nearby opposite-direction signal exists while same-direction candidate is absent; inspect trend/trigger parity before EA changes.",
        )
    if trigger == "M15 SLOT1" and ("replace" in mode_or_signal or "rescue" in mode_or_signal or "rescue" in variant):
        return (
            "m15_slot1_replace_rescue_no_candidate",
            "signal_level_prototype_candidate",
            "M15 SLOT1 replace/rescue signal has no counterpart; build a signal-level replay before changing EA or Python main logic.",
        )
    if trigger == "M15 SLOT1":
        return (
            "m15_slot1_true_no_candidate_signal_gap",
            "signal_level_prototype_candidate",
            "M15 SLOT1 no-candidate gap remains after wider candidate search; inspect raw M15/M30 parent rules.",
        )
    if trigger == "M30 CLOSE" and mode == "post_n":
        return (
            "m30_post_n_true_no_candidate_signal_gap",
            "signal_level_prototype_candidate",
            "M30 CLOSE post_n no-candidate gap remains; inspect post_n continuation/raw-parent rules.",
        )
    return (
        "true_no_candidate_signal_gap_requires_diag",
        "signal_or_ea_diag_required",
        "No nearby counterpart was found; add signal/EA diagnostic evidence before behavior changes.",
    )


def build_case_review() -> pd.DataFrame:
    cases = read_csv(TRIAGE_DIR / "stage_state_signal_set_case_triage.csv").copy()
    cases = cases[cases["action_bucket"].astype(str).isin(NO_CANDIDATE_BUCKETS)].copy()
    cases["target_time"] = pd.to_datetime(cases["target_time"], errors="coerce")
    cases["gap_effect_$"] = pd.to_numeric(cases["gap_effect_$"], errors="coerce").fillna(0.0)
    cases["abs_gap_effect_$"] = cases["gap_effect_$"].abs()
    cases["dir_norm"] = cases["dir_norm"].map(normalize_dir)
    cases["mode_family"] = cases["mode_family"].map(mode_family)

    py = load_python_trades()
    mt5 = load_mt5_trades()
    py_by_id = {str(row["py_trade_id"]): row for _, row in py.iterrows()}
    mt5_by_id = {str(row["mt5_trade_id"]): row for _, row in mt5.iterrows()}

    rows: list[dict[str, object]] = []
    for _, case in cases.iterrows():
        side = str(case["side"])
        target_time = parse_time(case["target_time"])
        base = case.to_dict()

        if side == "python_unmatched":
            other = mt5
            own = py_by_id.get(str(case["trade_id"]), pd.Series(dtype=object))
            context = nearest_with_context(
                target_time,
                str(case["dir_norm"]),
                str(case["trigger_family"]),
                str(case["mode_family"]),
                other,
                side,
            )
            base.update(
                {
                    "variant": own.get("variant", ""),
                    "entry": safe_float(own.get("entry")),
                    "stop": safe_float(own.get("stop")),
                    "stop_pts_spec": safe_float(own.get("stop_pts_spec")),
                    "dynamic_total_lot": safe_float(own.get("dynamic_total_lot")),
                    "stage1_exit": own.get("stage1_exit", ""),
                    "stage2_exit": own.get("stage2_exit", ""),
                    "stage3_exit": own.get("stage3_exit", ""),
                    "local_exit_reasons": "",
                    "deal_reasons": "",
                }
            )
        else:
            other = py
            own = mt5_by_id.get(str(case["trade_id"]), pd.Series(dtype=object))
            context = nearest_with_context(
                target_time,
                str(case["dir_norm"]),
                str(case["trigger_family"]),
                str(case["mode_family"]),
                other,
                side,
            )
            base.update(
                {
                    "variant": "",
                    "entry": "",
                    "stop": "",
                    "stop_pts_spec": safe_float(own.get("stop_pts_spec")),
                    "dynamic_total_lot": "",
                    "stage1_exit": "",
                    "stage2_exit": "",
                    "stage3_exit": "",
                    "local_exit_reasons": own.get("local_exit_reasons", ""),
                    "deal_reasons": own.get("deal_reasons", ""),
                    "raw_anchor": own.get("signal_anchor_time", case.get("raw_anchor", "")),
                }
            )

        base.update(context)
        action_bucket, next_action, note = classify_case(base, py, mt5)
        base["no_candidate_action_bucket"] = action_bucket
        base["next_action_group"] = next_action
        base["review_note"] = note
        base["review_priority"] = priority(float(base["abs_gap_effect_$"]))
        rows.append(base)

    out = pd.DataFrame(rows).sort_values(
        ["abs_gap_effect_$", "side", "trade_id"], ascending=[False, True, True]
    )
    return out.reset_index(drop=True)


def summarize_cases(cases: pd.DataFrame) -> pd.DataFrame:
    grouped = cases.groupby(["no_candidate_action_bucket", "side"], dropna=False)
    rows = []
    for (bucket, side), grp in grouped:
        rows.append(
            {
                "no_candidate_action_bucket": bucket,
                "side": side,
                "rows": int(len(grp)),
                "gap_effect_sum": round(float(grp["gap_effect_$"].sum()), 6),
                "abs_gap_effect_sum": round(float(grp["abs_gap_effect_$"].sum()), 6),
                "max_abs_gap_effect": round(float(grp["abs_gap_effect_$"].max()), 6),
                "p1_rows": int((grp["review_priority"] == "P1").sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["abs_gap_effect_sum", "rows", "no_candidate_action_bucket"],
        ascending=[False, False, True],
    )


def summarize_trigger_mode(cases: pd.DataFrame) -> pd.DataFrame:
    grouped = cases.groupby(["side", "trigger_family", "mode_family"], dropna=False)
    rows = []
    for (side, trigger, mode), grp in grouped:
        rows.append(
            {
                "side": side,
                "trigger_family": trigger,
                "mode_family": mode,
                "rows": int(len(grp)),
                "gap_effect_sum": round(float(grp["gap_effect_$"].sum()), 6),
                "abs_gap_effect_sum": round(float(grp["abs_gap_effect_$"].sum()), 6),
                "top_trade_id": str(grp.sort_values("abs_gap_effect_$", ascending=False).iloc[0]["trade_id"]),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["abs_gap_effect_sum", "rows"], ascending=[False, False]
    )


def build_decision(cases: pd.DataFrame, bucket_summary: pd.DataFrame) -> pd.DataFrame:
    expected = read_csv(TRIAGE_DIR / "stage_state_signal_set_bucket_summary.csv")
    expected = expected[expected["action_bucket"].astype(str).isin(NO_CANDIDATE_BUCKETS)].copy()
    expected["gap_effect_sum"] = pd.to_numeric(expected["gap_effect_sum"], errors="coerce").fillna(0.0)
    expected["abs_gap_effect_sum"] = pd.to_numeric(expected["abs_gap_effect_sum"], errors="coerce").fillna(0.0)

    recomputed_gap = float(cases["gap_effect_$"].sum())
    recomputed_abs = float(cases["abs_gap_effect_$"].sum())
    expected_gap = float(expected["gap_effect_sum"].sum())
    expected_abs = float(expected["abs_gap_effect_sum"].sum())
    top_bucket = bucket_summary.iloc[0]["no_candidate_action_bucket"] if not bucket_summary.empty else ""
    signal_level_abs = float(
        bucket_summary[
            bucket_summary["no_candidate_action_bucket"].astype(str).str.contains(
                "true_no_candidate|replace_rescue", regex=True
            )
        ]["abs_gap_effect_sum"].sum()
    )
    boundary_abs = float(
        bucket_summary[
            bucket_summary["no_candidate_action_bucket"].astype(str).str.contains(
                "before_first|after_last", regex=True
            )
        ]["abs_gap_effect_sum"].sum()
    )
    mapping_window_abs = float(
        bucket_summary[
            bucket_summary["no_candidate_action_bucket"].astype(str).str.contains(
                "outside_7d", regex=True
            )
        ]["abs_gap_effect_sum"].sum()
    )

    recommended = "build_no_candidate_signal_level_replay_before_any_main_logic_change"
    if boundary_abs >= signal_level_abs and boundary_abs >= mapping_window_abs:
        recommended = "audit_reference_window_and_warmup_then_replay_no_candidate_signals"
    elif mapping_window_abs >= signal_level_abs:
        recommended = "audit_mapping_window_accounting_then_signal_replay"

    return pd.DataFrame(
        [
            {
                "gate": "stage_state_no_candidate_signal_gap_triage",
                "reviewed_rows": int(len(cases)),
                "python_only_rows": int((cases["side"] == "python_unmatched").sum()),
                "mt5_only_rows": int((cases["side"] == "mt5_unmatched").sum()),
                "expected_gap_effect_sum": round(expected_gap, 6),
                "recomputed_gap_effect_sum": round(recomputed_gap, 6),
                "gap_recompute_error": round(recomputed_gap - expected_gap, 9),
                "expected_abs_gap_effect_sum": round(expected_abs, 6),
                "recomputed_abs_gap_effect_sum": round(recomputed_abs, 6),
                "abs_gap_recompute_error": round(recomputed_abs - expected_abs, 9),
                "top_action_bucket": top_bucket,
                "boundary_abs_gap": round(boundary_abs, 6),
                "mapping_window_abs_gap": round(mapping_window_abs, 6),
                "signal_level_candidate_abs_gap": round(signal_level_abs, 6),
                "ea_behavior_gate_open": False,
                "main_signal_change_gate_open": False,
                "signal_level_prototype_required": True,
                "merge_gate_pass": False,
                "recommended_next_action": recommended,
                "decision": "triage_complete_no_direct_merge",
                "reason": (
                    "No-candidate rows are real signal-set residual, but they still require boundary/window "
                    "and signal-level replay evidence before any Python or EA behavior change."
                ),
            }
        ]
    )


def simple_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows_"
    return frame.to_markdown(index=False)


def write_report(cases: pd.DataFrame, bucket_summary: pd.DataFrame, trigger_summary: pd.DataFrame, decision: pd.DataFrame) -> None:
    d = decision.iloc[0]
    top_cases = cases.head(10)[
        [
            "side",
            "trade_id",
            "target_time",
            "dir_norm",
            "trigger_family",
            "mode_family",
            "gap_effect_$",
            "abs_gap_effect_$",
            "no_candidate_action_bucket",
            "nearest_same_dir_minutes",
            "opposite_dir_7d_count",
        ]
    ]
    report = [
        "# Stage-State No-Candidate Signal Gap Triage",
        "",
        "## Scope",
        "",
        "- Reviews only rows classified as `python_only_signal_gap_no_mt5_candidate` or `mt5_only_signal_gap_no_python_candidate`.",
        "- Widens candidate context to 30/90 days for diagnostic classification.",
        "- Does not change mapping, Python signals, dynamic risk, or EA behavior.",
        "",
        "## Closure",
        "",
        f"- Reviewed rows: `{int(d['reviewed_rows'])}`.",
        f"- Python-only rows: `{int(d['python_only_rows'])}`.",
        f"- MT5-only rows: `{int(d['mt5_only_rows'])}`.",
        f"- Recomputed gap effect: `{float(d['recomputed_gap_effect_sum']):+.6f}`.",
        f"- Expected gap effect: `{float(d['expected_gap_effect_sum']):+.6f}`.",
        f"- Recompute error: `{float(d['gap_recompute_error']):+.9f}`.",
        f"- Recomputed abs gap: `{float(d['recomputed_abs_gap_effect_sum']):.6f}`.",
        "",
        "## Action Bucket Summary",
        "",
        simple_table(bucket_summary),
        "",
        "## Trigger/Mode Summary",
        "",
        simple_table(trigger_summary),
        "",
        "## Top Cases",
        "",
        simple_table(top_cases),
        "",
        "## Decision",
        "",
        f"- `ea_behavior_gate_open`: `{bool_value(d['ea_behavior_gate_open'])}`.",
        f"- `main_signal_change_gate_open`: `{bool_value(d['main_signal_change_gate_open'])}`.",
        f"- `signal_level_prototype_required`: `{bool_value(d['signal_level_prototype_required'])}`.",
        f"- `merge_gate_pass`: `{bool_value(d['merge_gate_pass'])}`.",
        f"- Recommended next action: `{d['recommended_next_action']}`.",
        "",
        "No-candidate rows are now separated from mapping unique-conflict and duplicate-continuation diagnostics. The next executable step should replay these raw signal moments at signal level before modifying main strategy logic.",
        "",
        "## Output Files",
        "",
        "- `stage_state_no_candidate_signal_gap_cases.csv`",
        "- `stage_state_no_candidate_signal_gap_bucket_summary.csv`",
        "- `stage_state_no_candidate_trigger_mode_summary.csv`",
        "- `stage_state_no_candidate_signal_gap_decision.csv`",
    ]
    write_text(OUT_DIR / "stage_state_no_candidate_signal_gap_review.md", "\n".join(report))

    readme = [
        "# stage_state_no_candidate_signal_gap_triage_20260717",
        "",
        "Diagnostic triage for current stage-state Python-only / MT5-only no-candidate signal-set residuals.",
        "",
        "This directory is read-only diagnostic output. It does not change strategy logic.",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(readme))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = build_case_review()
    bucket_summary = summarize_cases(cases)
    trigger_summary = summarize_trigger_mode(cases)
    decision = build_decision(cases, bucket_summary)

    export_csv(cases, OUT_DIR / "stage_state_no_candidate_signal_gap_cases.csv")
    export_csv(bucket_summary, OUT_DIR / "stage_state_no_candidate_signal_gap_bucket_summary.csv")
    export_csv(trigger_summary, OUT_DIR / "stage_state_no_candidate_trigger_mode_summary.csv")
    export_csv(decision, OUT_DIR / "stage_state_no_candidate_signal_gap_decision.csv")
    write_report(cases, bucket_summary, trigger_summary, decision)


if __name__ == "__main__":
    main()
