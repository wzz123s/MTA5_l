# -*- coding: utf-8 -*-
"""Review whether +90/+120 time-axis normalization is mergeable.

This gate runs after the MT5 reference baseline was reset to the stage-state
full tester ledger. It is diagnostic only: no Python signal, dynamic-risk, or
EA behavior is changed here.
"""
from __future__ import annotations


import bisect
from pathlib import Path

import numpy as np
import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = STRATEGY_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
VALIDATION_DIR = DATA_DIR / "validation"

SIGNAL_ROOT = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714"
H2_CONTEXT = SIGNAL_ROOT / "h2_mt5_barlevel_shift90_context.csv"
M30_METADATAFIX = SIGNAL_ROOT / "m30_prepared_with_mt5_shift90.csv"
M30_PROCESSED = PROCESSED_DIR / "m30_mt5.csv"
M15_CONTEXT = PROCESSED_DIR / "m15_context_bars.csv"

BASELINE_DIR = VALIDATION_DIR / "stage_state_new_baseline_decision_20260716"
STAGE_REMAP_DIR = VALIDATION_DIR / "stage_state_full_remap_residual_review_20260716"
STAGE_LEDGER_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"
BRIDGE_DIR = VALIDATION_DIR / "m15_slot1_time_axis_bridge_20260714"
MT5_0068_DIR = VALIDATION_DIR / "mt5_0068_layer3_time_axis_boundary_20260715"
OUT_DIR = VALIDATION_DIR / "python_mt5_time_axis_normalization_stage_state_20260716"

TOP_PCT = 34.0
H2_LOOKBACK = 500
BIAS55_THRESHOLD = 3.0


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def parse_time(value: object) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.notna(parsed):
        return parsed
    return pd.to_datetime(str(value).replace(".", "-"), errors="coerce")


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"L", "LONG", "BUY", "B", "1"}:
        return "BUY"
    if text in {"S", "SHORT", "SELL", "-1"}:
        return "SELL"
    return text


def mode_family(value: object) -> str:
    text = str(value).strip()
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return text


def safe_float(value: object, default: float = np.nan) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def safe_int(value: object, default: int = 0) -> int:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return int(parsed)


def load_date_set(path: Path) -> set[pd.Timestamp]:
    frame = read_csv(path)
    if "date" not in frame.columns:
        raise RuntimeError(f"{path} has no date column")
    return set(pd.to_datetime(frame["date"], errors="coerce").dropna())


def load_h2() -> pd.DataFrame:
    h2 = read_csv(H2_CONTEXT).copy()
    h2["date_dt"] = pd.to_datetime(h2["date"], errors="coerce")
    h2["source_bar_time_dt"] = pd.to_datetime(h2.get("source_bar_time", pd.NaT), errors="coerce")
    for col in ["close", "SMA_5", "SMA_13", "SMA_55"]:
        h2[col] = pd.to_numeric(h2[col], errors="coerce")
    h2 = h2.dropna(subset=["date_dt", "close", "SMA_5", "SMA_13", "SMA_55"])
    h2 = h2[(h2["SMA_5"] != 0) & (h2["SMA_13"] != 0) & (h2["SMA_55"] != 0)].copy()
    h2["Bias_5"] = (h2["close"] - h2["SMA_5"]).abs() / h2["SMA_5"] * 100.0
    h2["Bias_13"] = (h2["close"] - h2["SMA_13"]).abs() / h2["SMA_13"] * 100.0
    h2["Bias_55"] = (h2["close"] - h2["SMA_55"]).abs() / h2["SMA_55"] * 100.0
    return h2.sort_values("date_dt").reset_index(drop=True)


def rolling_threshold(values: list[float]) -> float:
    if len(values) < 10:
        return np.nan
    arr = np.sort(np.asarray(values, dtype=float))
    idx = int(np.floor(len(arr) * (1.0 - TOP_PCT / 100.0)))
    idx = max(0, min(idx, len(arr) - 1))
    return float(arr[idx])


def h2_eval(h2: pd.DataFrame, eval_time: pd.Timestamp) -> dict[str, object]:
    if pd.isna(eval_time):
        return {
            "eval_time": pd.NaT,
            "h2_lookup_time": pd.NaT,
            "h2_source_bar_time": pd.NaT,
            "Bias_5": np.nan,
            "Bias_13": np.nan,
            "Bias_55": np.nan,
            "layer1_pass": False,
            "layer3_threshold": np.nan,
            "layer3_pass": False,
            "hist_count": 0,
        }
    h2_times = h2["date_dt"].tolist()
    idx = bisect.bisect_right(h2_times, eval_time) - 1
    if idx < 0:
        return {
            "eval_time": eval_time,
            "h2_lookup_time": pd.NaT,
            "h2_source_bar_time": pd.NaT,
            "Bias_5": np.nan,
            "Bias_13": np.nan,
            "Bias_55": np.nan,
            "layer1_pass": False,
            "layer3_threshold": np.nan,
            "layer3_pass": False,
            "hist_count": 0,
        }
    row = h2.iloc[idx]
    start = max(0, idx - H2_LOOKBACK + 1)
    hist = h2["Bias_5"].iloc[start : idx + 1].dropna().astype(float).tolist()
    threshold = rolling_threshold(hist)
    bias5 = float(row["Bias_5"])
    return {
        "eval_time": eval_time,
        "h2_lookup_time": row["date_dt"],
        "h2_source_bar_time": row["source_bar_time_dt"],
        "Bias_5": bias5,
        "Bias_13": float(row["Bias_13"]),
        "Bias_55": float(row["Bias_55"]),
        "layer1_pass": bool(float(row["Bias_55"]) > BIAS55_THRESHOLD),
        "layer3_threshold": threshold,
        "layer3_pass": bool(True if pd.isna(threshold) else bias5 >= threshold),
        "hist_count": int(len(hist)),
    }


def load_stage_state_ledger_lookup() -> dict[tuple[str, str, str], dict[str, object]]:
    ledger = read_csv(STAGE_LEDGER_DIR / "30m2H_strategy_trade_ledger.csv").copy()
    ledger = ledger[ledger["trigger_tag"].astype(str).str.contains("M15 SLOT1", regex=False)].copy()
    ledger["anchor_dt"] = ledger["signal_anchor_time"].map(parse_time)
    ledger["anchor_key"] = ledger["anchor_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")
    ledger["dir_norm"] = ledger["dir"].map(normalize_dir)
    ledger["mode_family"] = ledger["signal_src"].map(mode_family)
    rows: dict[tuple[str, str, str], dict[str, object]] = {}
    for key, group in ledger.groupby(["anchor_key", "dir_norm", "mode_family"], dropna=False):
        first = group.iloc[0]
        rows[key] = {
            "stage_state_ledger_stage_rows": int(len(group)),
            "stage_state_ledger_net_profit": safe_float(pd.to_numeric(group["net_profit"], errors="coerce").sum()),
            "stage_state_ledger_entry": safe_float(first.get("signal_entry")),
            "stage_state_ledger_stop": safe_float(first.get("signal_stop")),
            "stage_state_local_exit_reasons": ";".join(sorted(set(group["local_exit_reason"].dropna().astype(str)))),
            "stage_state_deal_reasons": ";".join(sorted(set(group["deal_reason"].dropna().astype(str)))),
        }
    return rows


def build_candidate_matrix() -> pd.DataFrame:
    candidates = read_csv(BRIDGE_DIR / "m15_slot1_time_axis_bridge_candidates.csv").copy()
    for col in ["shifted_anchor", "raw_anchor", "log_time", "log_time_plus90"]:
        candidates[col] = candidates[col].map(parse_time)
    candidates["dir_norm"] = candidates["dir_norm"].map(normalize_dir)
    candidates["mode_family"] = candidates["mode_family"].map(mode_family)
    candidates["candidate_id"] = [
        str(value) if str(value) not in {"", "nan", "NaN"} else f"m15_slot1_{idx + 1:04d}"
        for idx, value in enumerate(candidates.get("remaining_trade_id", pd.Series(dtype=object)))
    ]

    m30_processed_dates = load_date_set(M30_PROCESSED)
    m30_metadata_dates = load_date_set(M30_METADATAFIX)
    m15_dates = load_date_set(M15_CONTEXT)
    ledger_lookup = load_stage_state_ledger_lookup()

    rows: list[dict[str, object]] = []
    for _, row in candidates.iterrows():
        raw_anchor = row["raw_anchor"]
        shifted_anchor = row["shifted_anchor"]
        log_time = row["log_time"]
        m30_plus90 = raw_anchor + pd.Timedelta(minutes=90)
        m30_plus120 = raw_anchor + pd.Timedelta(minutes=120)
        date_plus30 = shifted_anchor + pd.Timedelta(minutes=30)
        log_plus90 = log_time + pd.Timedelta(minutes=90)
        log_plus120 = log_time + pd.Timedelta(minutes=120)
        key = (
            raw_anchor.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(raw_anchor) else "",
            row["dir_norm"],
            row["mode_family"],
        )
        ledger = ledger_lookup.get(key, {})
        out = row.to_dict()
        out.update(
            {
                "m30_plus90_target": m30_plus90,
                "m30_plus120_target": m30_plus120,
                "date_plus30_target": date_plus30,
                "log_plus90_target": log_plus90,
                "log_plus120_target": log_plus120,
                "m30_processed_plus90_exists": pd.notna(m30_plus90) and m30_plus90 in m30_processed_dates,
                "m30_processed_plus120_exists": pd.notna(m30_plus120) and m30_plus120 in m30_processed_dates,
                "m30_metadatafix_plus90_exists": pd.notna(m30_plus90) and m30_plus90 in m30_metadata_dates,
                "m30_metadatafix_plus120_exists": pd.notna(m30_plus120) and m30_plus120 in m30_metadata_dates,
                "m15_log_plus90_exists_recomputed": pd.notna(log_plus90) and log_plus90 in m15_dates,
                "m15_log_plus120_exists": pd.notna(log_plus120) and log_plus120 in m15_dates,
                "date_plus30_equals_raw_plus120": bool(pd.notna(date_plus30) and date_plus30 == m30_plus120),
                **ledger,
            }
        )
        out["current_plus90_available_metadatafix"] = bool(
            out["m30_metadatafix_plus90_exists"] and out["m15_log_plus90_exists_recomputed"]
        )
        out["plus120_available_metadatafix"] = bool(
            out["m30_metadatafix_plus120_exists"] and out["m15_log_plus120_exists"]
        )
        out["stage_state_ledger_has_same_anchor"] = bool(ledger)
        rows.append(out)
    return pd.DataFrame(rows).sort_values(["shifted_anchor", "dir_norm", "mode_family"]).reset_index(drop=True)


def build_layer3_matrix(candidates: pd.DataFrame) -> pd.DataFrame:
    h2 = load_h2()
    rows: list[dict[str, object]] = []
    for _, row in candidates.iterrows():
        variants = [
            ("current_raw_plus90", row["raw_anchor"] + pd.Timedelta(minutes=90)),
            ("raw_plus120", row["raw_anchor"] + pd.Timedelta(minutes=120)),
            ("date_plus30", row["shifted_anchor"] + pd.Timedelta(minutes=30)),
            ("log_plus90", row["log_time"] + pd.Timedelta(minutes=90)),
            ("log_plus120", row["log_time"] + pd.Timedelta(minutes=120)),
        ]
        for variant, eval_time in variants:
            out = {
                "candidate_id": row["candidate_id"],
                "remaining_trade_id": row.get("remaining_trade_id", ""),
                "shifted_anchor": row["shifted_anchor"],
                "raw_anchor": row["raw_anchor"],
                "log_time": row["log_time"],
                "dir_norm": row["dir_norm"],
                "mode_family": row["mode_family"],
                "bridge_class": row.get("bridge_class", ""),
                "in_current_remaining_drift": row.get("in_current_remaining_drift", ""),
                "variant": variant,
            }
            out.update(h2_eval(h2, eval_time))
            out["threshold_margin"] = out["Bias_5"] - out["layer3_threshold"]
            rows.append(out)
    return pd.DataFrame(rows)


def pivot_layer3(candidates: pd.DataFrame, layer3: pd.DataFrame) -> pd.DataFrame:
    pass_pivot = layer3.pivot_table(
        index="candidate_id",
        columns="variant",
        values="layer3_pass",
        aggfunc="first",
    )
    margin_pivot = layer3.pivot_table(
        index="candidate_id",
        columns="variant",
        values="threshold_margin",
        aggfunc="first",
    )
    pass_pivot = pass_pivot.rename(columns={c: f"{c}_layer3_pass" for c in pass_pivot.columns})
    margin_pivot = margin_pivot.rename(columns={c: f"{c}_threshold_margin" for c in margin_pivot.columns})
    out = candidates.merge(pass_pivot.reset_index(), on="candidate_id", how="left")
    out = out.merge(margin_pivot.reset_index(), on="candidate_id", how="left")
    out["plus120_flips_current_layer3_fail_to_pass"] = (
        (out["current_raw_plus90_layer3_pass"] == False) & (out["raw_plus120_layer3_pass"] == True)  # noqa: E712
    )
    out["plus120_flips_current_layer3_pass_to_fail"] = (
        (out["current_raw_plus90_layer3_pass"] == True) & (out["raw_plus120_layer3_pass"] == False)  # noqa: E712
    )
    return out


def summarize_bool(frame: pd.DataFrame, column: str) -> int:
    if column not in frame.columns:
        return 0
    return int(frame[column].fillna(False).astype(bool).sum())


def build_summary(cases: pd.DataFrame) -> pd.DataFrame:
    bridge_gap_summary = read_csv(BRIDGE_DIR / "m15_slot1_time_axis_gap_summary.csv")
    bridge_metrics = {
        str(row["metric"]): safe_int(row["value"])
        for _, row in bridge_gap_summary.iterrows()
    }
    gap = cases[cases["has_time_axis_gap"].fillna(False).astype(bool)].copy()
    remaining_bridge = cases[cases["bridge_class"].astype(str) == "time_axis_bridge_candidate"].copy()
    changed = read_csv(BRIDGE_DIR / "bridge_reclass_changed_cases.csv")
    changed_gap_sum = safe_float(pd.to_numeric(changed.get("gap_effect_$"), errors="coerce").sum(), 0.0)
    stage_state_same_anchor = summarize_bool(cases, "stage_state_ledger_has_same_anchor")
    rows = [
        {"metric": "stage_state_m15_slot1_candidates_reused_from_bridge_view", "value": int(len(cases))},
        {"metric": "bridge_summary_m15_slot1_signals", "value": bridge_metrics.get("m15_slot1_signals", 0)},
        {"metric": "bridge_summary_any_time_axis_gap", "value": bridge_metrics.get("any_time_axis_gap", 0)},
        {"metric": "bridge_summary_current_remaining_m15_slot1_with_gap", "value": bridge_metrics.get("current_remaining_m15_slot1_with_gap", 0)},
        {"metric": "bridge_summary_reclass_changed_cases", "value": bridge_metrics.get("remaining_reclass_changed_cases", 0)},
        {"metric": "stage_state_ledger_same_anchor_matches", "value": stage_state_same_anchor},
        {"metric": "plus90_available_all_candidates", "value": summarize_bool(cases, "current_plus90_available_metadatafix")},
        {"metric": "plus120_available_all_candidates", "value": summarize_bool(cases, "plus120_available_metadatafix")},
        {"metric": "plus120_available_among_time_axis_gaps", "value": summarize_bool(gap, "plus120_available_metadatafix")},
        {"metric": "plus120_available_among_remaining_bridge_candidates", "value": summarize_bool(remaining_bridge, "plus120_available_metadatafix")},
        {"metric": "current_plus90_layer3_pass_all_candidates", "value": summarize_bool(cases, "current_raw_plus90_layer3_pass")},
        {"metric": "raw_plus120_layer3_pass_all_candidates", "value": summarize_bool(cases, "raw_plus120_layer3_pass")},
        {"metric": "date_plus30_layer3_pass_all_candidates", "value": summarize_bool(cases, "date_plus30_layer3_pass")},
        {"metric": "plus120_fail_to_pass_flips_all_candidates", "value": summarize_bool(cases, "plus120_flips_current_layer3_fail_to_pass")},
        {"metric": "plus120_pass_to_fail_flips_all_candidates", "value": summarize_bool(cases, "plus120_flips_current_layer3_pass_to_fail")},
        {"metric": "changed_cases_gap_effect_sum_old_bridge_view", "value": round(changed_gap_sum, 6)},
    ]
    return pd.DataFrame(rows)


def build_changed_case_review(cases: pd.DataFrame) -> pd.DataFrame:
    changed = read_csv(BRIDGE_DIR / "bridge_reclass_changed_cases.csv").copy()
    changed_ids = set(changed["trade_id"].dropna().astype(str))
    subset = cases[cases["remaining_trade_id"].astype(str).isin(changed_ids)].copy()
    merged = changed.merge(
        subset[
            [
                "remaining_trade_id",
                "raw_anchor",
                "shifted_anchor",
                "log_time",
                "dir_norm",
                "mode_family",
                "current_plus90_available_metadatafix",
                "plus120_available_metadatafix",
                "stage_state_ledger_has_same_anchor",
                "stage_state_ledger_stage_rows",
                "stage_state_ledger_net_profit",
                "current_raw_plus90_layer3_pass",
                "raw_plus120_layer3_pass",
                "date_plus30_layer3_pass",
                "log_plus90_layer3_pass",
                "log_plus120_layer3_pass",
                "plus120_flips_current_layer3_fail_to_pass",
                "plus120_flips_current_layer3_pass_to_fail",
            ]
        ],
        left_on="trade_id",
        right_on="remaining_trade_id",
        how="left",
        suffixes=("", "_candidate"),
    )
    return merged


def load_mt5_0068_decision() -> pd.DataFrame:
    decision = read_csv(MT5_0068_DIR / "mt5_0068_boundary_decision.csv").copy()
    eval_matrix = read_csv(MT5_0068_DIR / "mt5_0068_layer3_eval_matrix.csv").copy()
    compact_rows = []
    for _, row in eval_matrix.iterrows():
        compact_rows.append(
            {
                "variant": row.get("variant"),
                "eval_time": row.get("eval_time"),
                "h2_lookup_time": row.get("h2_lookup_time"),
                "Bias_5": row.get("Bias_5"),
                "layer3_threshold": row.get("layer3_threshold"),
                "threshold_margin": row.get("threshold_margin"),
                "layer3_pass": row.get("layer3_pass"),
            }
        )
    compact = pd.DataFrame(compact_rows)
    export_csv(compact, OUT_DIR / "mt5_0068_prior_boundary_layer3_compact.csv")
    return decision


def build_gate_decision(summary: pd.DataFrame, cases: pd.DataFrame) -> pd.DataFrame:
    baseline = read_csv(BASELINE_DIR / "stage_state_new_baseline_decision.csv").iloc[0]
    remap = read_csv(STAGE_REMAP_DIR / "stage_state_full_remap_summary.csv")
    metadatafix = remap[remap["scenario"].astype(str) == "metadatafix"].iloc[0]

    all_gap = cases[cases["has_time_axis_gap"].fillna(False).astype(bool)].copy()
    remaining_bridge = cases[cases["bridge_class"].astype(str) == "time_axis_bridge_candidate"].copy()
    plus120_available_for_all_gaps = len(all_gap) > 0 and summarize_bool(all_gap, "plus120_available_metadatafix") == len(all_gap)
    plus120_available_for_remaining_bridge = len(remaining_bridge) > 0 and summarize_bool(
        remaining_bridge, "plus120_available_metadatafix"
    ) == len(remaining_bridge)
    no_pass_to_fail = summarize_bool(cases, "plus120_flips_current_layer3_pass_to_fail") == 0
    full_chain_recomputed = False
    stable_subset_proven = bool(plus120_available_for_remaining_bridge and no_pass_to_fail and full_chain_recomputed)
    global_rule_pass = bool(plus120_available_for_all_gaps and no_pass_to_fail and full_chain_recomputed)

    return pd.DataFrame(
        [
            {
                "gate": "python_mt5_time_axis_normalization_stage_state",
                "current_mt5_baseline_id": baseline["current_mt5_baseline_id"],
                "current_mt5_final_balance": baseline["current_mt5_final_balance"],
                "current_mt5_trade_count": baseline["current_mt5_trade_count"],
                "metadatafix_direct_gap_vs_current_mt5": baseline["metadatafix_direct_gap_vs_current_mt5"],
                "stage_state_metadatafix_matched_unique": metadatafix["matched_unique"],
                "stage_state_metadatafix_python_unmatched": metadatafix["python_unmatched"],
                "stage_state_metadatafix_mt5_unmatched": metadatafix["mt5_unmatched"],
                "stage_state_metadatafix_signal_set_gap": metadatafix["signal_set_gap_py_minus_mt5"],
                "m15_slot1_candidates": len(cases),
                "time_axis_gap_candidates": len(all_gap),
                "remaining_bridge_candidates_old_view": len(remaining_bridge),
                "plus120_available_for_all_time_axis_gaps": plus120_available_for_all_gaps,
                "plus120_available_for_remaining_bridge_old_view": plus120_available_for_remaining_bridge,
                "plus120_pass_to_fail_count": summarize_bool(cases, "plus120_flips_current_layer3_pass_to_fail"),
                "plus120_fail_to_pass_count": summarize_bool(cases, "plus120_flips_current_layer3_fail_to_pass"),
                "full_chain_shared_only_gap_recomputed": full_chain_recomputed,
                "stable_subset_rule_proven": stable_subset_proven,
                "global_plus120_rule_merge_gate_pass": global_rule_pass,
                "date_plus30_rule_merge_gate_pass": global_rule_pass,
                "mt5_0068_status": "accounting_only_time_axis_diagnostic",
                "decision": "do_not_merge_time_axis_rule",
                "reason": (
                    "+120/date+30 changes Layer3 outcomes, but it is not data-available for all gap candidates "
                    "and no stage-state full-chain shared/only/fund-curve rerun exists."
                ),
                "next_action": "resume_stage_state_signal_set_residual_triage_or_run_explicit_full_chain_time_axis_prototype",
            }
        ]
    )


def markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.head(max_rows).copy()
    try:
        return display.to_markdown(index=False)
    except Exception:
        columns = list(display.columns)
        rows = [[str(value) for value in row] for row in display.to_numpy()]
        widths = [len(col) for col in columns]
        for row in rows:
            for idx, value in enumerate(row):
                widths[idx] = max(widths[idx], len(value))

        def render(row: list[str]) -> str:
            return "| " + " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(row)) + " |"

        return "\n".join([render(columns), "| " + " | ".join("-" * width for width in widths) + " |", *[render(r) for r in rows]])


def build_report(
    summary: pd.DataFrame,
    gate: pd.DataFrame,
    changed: pd.DataFrame,
    mt5_0068_decision: pd.DataFrame,
) -> str:
    gate_row = gate.iloc[0]
    changed_display_cols = [
        "trade_id",
        "target_time",
        "dir_norm",
        "mode_family",
        "gap_effect_$",
        "current_plus90_available_metadatafix",
        "plus120_available_metadatafix",
        "stage_state_ledger_has_same_anchor",
        "stage_state_ledger_net_profit",
        "current_raw_plus90_layer3_pass",
        "raw_plus120_layer3_pass",
        "date_plus30_layer3_pass",
        "plus120_flips_current_layer3_fail_to_pass",
    ]
    lines = [
        "# Python-MT5 +90/+120 time-axis normalization gate (stage-state baseline)",
        "",
        "## Scope",
        "",
        "- Baseline: accepted stage-state MT5 full tester ledger.",
        "- Candidate source: prior M15 SLOT1 time-axis bridge view, rechecked against current stage-state ledger anchors.",
        "- This is a diagnostic gate only; it does not change signal generation, Stage execution, dynamic risk, or EA code.",
        "",
        "## Decision",
        "",
        f"- Global +120/date+30 merge gate pass: `{gate_row['global_plus120_rule_merge_gate_pass']}`.",
        f"- Stable subset rule proven: `{gate_row['stable_subset_rule_proven']}`.",
        f"- `mt5_0068` status: `{gate_row['mt5_0068_status']}`.",
        f"- Decision: `{gate_row['decision']}`.",
        f"- Reason: {gate_row['reason']}",
        "",
        "## Current Stage-State Baseline",
        "",
        markdown_table(
            gate[
                [
                    "current_mt5_baseline_id",
                    "current_mt5_final_balance",
                    "current_mt5_trade_count",
                    "metadatafix_direct_gap_vs_current_mt5",
                    "stage_state_metadatafix_matched_unique",
                    "stage_state_metadatafix_python_unmatched",
                    "stage_state_metadatafix_mt5_unmatched",
                    "stage_state_metadatafix_signal_set_gap",
                ]
            ]
        ),
        "",
        "## Candidate Summary",
        "",
        markdown_table(summary, 40),
        "",
        "## Rechecked Bridge-Changed Cases",
        "",
        markdown_table(changed[[c for c in changed_display_cols if c in changed.columns]], 20),
        "",
        "## mt5_0068 Prior Boundary Decision",
        "",
        markdown_table(mt5_0068_decision, 5),
        "",
        "## Interpretation",
        "",
        "- `+120` and `date+30min` are equivalent for the raw-anchor candidates where `shifted_anchor = raw_anchor + 90min`, but this equivalence is not enough for a merge.",
        "- Some candidates improve Layer3 under `+120`, while some currently passing `+90` candidates can fail under `+120`; therefore it is not a safe global replacement.",
        "- The old bridge changed cases remain useful as time-axis diagnostics, but after the stage-state baseline reset their old trade IDs and unmatched status must not be copied into current funding tables without a full-chain rerun.",
        "- The current action is to keep the time-axis rule read-only and continue with stage-state signal-set residual triage, or explicitly run a separate full-chain prototype before any merge.",
        "",
        "## Output Files",
        "",
        "- `time_axis_candidate_recheck_stage_state.csv`",
        "- `time_axis_layer3_eval_matrix_stage_state.csv`",
        "- `time_axis_changed_case_review_stage_state.csv`",
        "- `time_axis_normalization_summary_stage_state.csv`",
        "- `time_axis_normalization_gate_decision_stage_state.csv`",
        "- `mt5_0068_prior_boundary_layer3_compact.csv`",
    ]
    return "\n".join(lines)


def write_readme() -> None:
    lines = [
        "# Python-MT5 time-axis normalization gate, stage-state baseline",
        "",
        "Generated by `review_python_mt5_time_axis_normalization_stage_state_20260716.py`.",
        "",
        "This folder decides whether M15 SLOT1 `+90`, `+120`, or `date+30min` time-axis handling can be merged after the MT5 reference baseline was reset to the stage-state full tester ledger.",
        "",
        "Result: diagnostic only; no mergeable global time-axis rule was accepted.",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = build_candidate_matrix()
    layer3 = build_layer3_matrix(candidates)
    cases = pivot_layer3(candidates, layer3)
    summary = build_summary(cases)
    changed = build_changed_case_review(cases)
    mt5_0068_decision = load_mt5_0068_decision()
    gate = build_gate_decision(summary, cases)

    export_csv(cases, OUT_DIR / "time_axis_candidate_recheck_stage_state.csv")
    export_csv(layer3, OUT_DIR / "time_axis_layer3_eval_matrix_stage_state.csv")
    export_csv(changed, OUT_DIR / "time_axis_changed_case_review_stage_state.csv")
    export_csv(summary, OUT_DIR / "time_axis_normalization_summary_stage_state.csv")
    export_csv(gate, OUT_DIR / "time_axis_normalization_gate_decision_stage_state.csv")
    write_text(
        OUT_DIR / "python_mt5_time_axis_normalization_stage_state_review.md",
        build_report(summary, gate, changed, mt5_0068_decision),
    )
    write_readme()

    print(gate.to_string(index=False))
    print()
    print(summary.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
