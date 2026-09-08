# -*- coding: utf-8 -*-
"""Source/provenance audit for the mt5_0076 Layer3 displacement.

The audit is diagnostic-only. It explains why the Python chain has a raw and
Layer1/2 candidate at the aligned mt5_0076 target time, while the current
Python Layer3/dynamic chain keeps an earlier opposite signal instead.
"""
from __future__ import annotations


import sys
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import prototype_stage_state_layer3_m15_slot1_postn_rescue_full_chain_20260717 as proto  # noqa: E402
import review_stage_state_targeted_raw_signal_replay_20260717 as raw_replay  # noqa: E402


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

GENERALIZATION_DIR = VALIDATION_DIR / "stage_state_layer3_target_only_replacement_generalization_20260717"
RAW_REPLAY_DIR = VALIDATION_DIR / "stage_state_targeted_raw_signal_replay_20260717"
PROTOTYPE_DIR = VALIDATION_DIR / "stage_state_layer3_m15_slot1_postn_rescue_full_chain_20260717"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
MT5_STAGE_STATE_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"

OUT_DIR = VALIDATION_DIR / "stage_state_layer3_displacement_source_mt5_0076_20260717"

TARGET_ID = "mt5_0076"
TARGET_TIME = pd.Timestamp("2026-03-24 12:00:00")
REMOVED_OPPOSITE_TIME = pd.Timestamp("2026-03-24 05:00:00")
WINDOW_START = pd.Timestamp("2026-03-24 02:00:00")
WINDOW_END = pd.Timestamp("2026-03-24 16:00:00")


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def parse_dt(value: object) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    if not text:
        return pd.NaT
    return pd.to_datetime(text.replace(".", "-"), errors="coerce")


def fmt_dt(value: object) -> str:
    dt = parse_dt(value)
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def safe_float(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def mode_family(value: object) -> str:
    text = str(value)
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return text.strip()


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL", "SHORT", "-1"}:
        return "SELL"
    if text in {"L", "B", "BUY", "LONG", "1"}:
        return "BUY"
    return text


def simple_table(frame: pd.DataFrame, columns: list[str] | None = None, max_rows: int = 80) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.copy()
    if columns is not None:
        display = display[[col for col in columns if col in display.columns]]
    return display.head(max_rows).to_markdown(index=False)


def in_window(frame: pd.DataFrame, time_col: str) -> pd.DataFrame:
    out = frame.copy()
    out["_time"] = out[time_col].map(parse_dt)
    return out[out["_time"].between(WINDOW_START, WINDOW_END, inclusive="both")].copy()


def load_target() -> pd.Series:
    targets = raw_replay.load_targets()
    hit = targets[targets["trade_id"].astype(str).eq(TARGET_ID)].copy()
    if hit.empty:
        raise RuntimeError(f"Target {TARGET_ID} not found")
    return hit.iloc[0]


def build_timeline(tables: dict[str, pd.DataFrame], mt5_unique: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    source_order = {
        "python_raw_candidates": 1,
        "python_layer12_pass": 2,
        "python_layer3_selected": 3,
        "python_stage_result_export": 4,
        "python_dynamic_executed": 5,
        "mt5_unique_ledger": 6,
    }

    for table_name, table in {**tables, "mt5_unique_ledger": mt5_unique}.items():
        nearby = in_window(table, "target_time")
        if nearby.empty:
            continue
        for _, row in nearby.iterrows():
            row_time = parse_dt(row.get("target_time"))
            trigger = str(row.get("trigger_family", row.get("trigger", "")))
            mode = str(row.get("mode_or_signal_src", row.get("mode", row.get("signal_src", ""))))
            family = str(row.get("mode_family", mode_family(mode)))
            direction = normalize_dir(row.get("dir_norm", row.get("dir", "")))
            if family not in {"post_n", "pre_cross", "cross"}:
                continue
            if row_time < WINDOW_START or row_time > WINDOW_END:
                continue
            is_focus = (
                (row_time == TARGET_TIME and direction == "BUY" and family == "post_n")
                or (row_time == REMOVED_OPPOSITE_TIME and direction == "SELL")
                or table_name in {"python_layer3_selected", "python_dynamic_executed", "mt5_unique_ledger"}
            )
            if not is_focus and table_name in {"python_raw_candidates", "python_layer12_pass"}:
                # Keep the raw/Layer1/2 table compact but preserve every target-family candidate.
                is_focus = direction in {"BUY", "SELL"} and family in {"post_n", "pre_cross", "cross"}
            if not is_focus:
                continue
            rows.append(
                {
                    "source_order": source_order.get(table_name, 99),
                    "source_table": table_name,
                    "row_time": fmt_dt(row_time),
                    "mt5_signal_anchor_time": fmt_dt(row.get("signal_anchor_time", "")),
                    "row_id": row.get("py_trade_id", row.get("mt5_trade_id", "")),
                    "dir_norm": direction,
                    "trigger_family": trigger,
                    "mode_family": family,
                    "mode_or_signal_src": mode,
                    "variant": row.get("variant", ""),
                    "entry": row.get("entry", row.get("signal_entry", "")),
                    "stop": row.get("stop", row.get("signal_stop", "")),
                    "sd_or_stop_pts": row.get("sd", row.get("stop_pts_spec", "")),
                    "spec_pass": row.get("spec_pass", ""),
                    "spec_reason": row.get("spec_reason", ""),
                    "profit": round(safe_float(row.get("profit", row.get("dynamic_total_$", row.get("net_profit", "")))), 6),
                    "stage1_exit": row.get("stage1_exit", ""),
                    "stage2_exit": row.get("stage2_exit", ""),
                    "stage3_exit": row.get("stage3_exit", ""),
                    "stage3_time": fmt_dt(row.get("stage3_time_input", row.get("stage3_time", ""))),
                    "balance_before": row.get("balance_before", ""),
                    "balance_after": row.get("balance_after", ""),
                }
            )
    return pd.DataFrame(rows).sort_values(["row_time", "source_order", "source_table"]).reset_index(drop=True)


def build_field_comparison(features: pd.DataFrame, removed: pd.DataFrame) -> pd.DataFrame:
    target = features[features["row_time_dt"].map(parse_dt).eq(TARGET_TIME)].copy()
    if target.empty:
        target = features[features["is_target_time"].map(as_bool)].copy()
    if target.empty:
        raise RuntimeError("Target candidate feature row not found")
    target_row = target.iloc[0]
    removed_row = removed.iloc[0] if not removed.empty else pd.Series(dtype=object)

    fields = [
        ("time", "row_time", "date"),
        ("direction", "dir_norm", "dir_norm"),
        ("trigger_family", "trigger_family", "trigger_family_norm"),
        ("mode", "mode", "mode"),
        ("variant", "variant", "variant"),
        ("entry", "candidate_entry", "entry"),
        ("stop", "candidate_stop", "stop"),
        ("sd", "candidate_sd", "sd"),
        ("source_profit_or_pnl", "source_profit", "pnl"),
        ("Bias_5", "candidate_Bias_5", "Bias_5"),
        ("Bias_13", "candidate_Bias_13", "Bias_13"),
        ("Bias_55", "candidate_Bias_55", "Bias_55"),
        ("Bias_5_ea", "candidate_Bias_5", "Bias_5_ea"),
        ("layer3_threshold_ea", "", "layer3_threshold_ea"),
        ("layer3_pass_ea", "", "layer3_pass_ea"),
        ("spec_pass", "candidate_spec_pass", "spec_pass"),
        ("spec_reason", "candidate_spec_reason", "spec_reason"),
        ("nearest_opposite_time", "nearest_opposite_layer3_time", ""),
        ("nearest_opposite_abs_minutes", "nearest_opposite_abs_minutes", ""),
        ("cluster_rows", "cluster_rows", ""),
        ("cluster_all_negative", "cluster_all_negative", ""),
        ("is_cluster_latest_time", "is_cluster_latest_time", ""),
        ("is_cluster_max_mode", "is_cluster_max_mode", ""),
    ]

    rows = []
    for label, target_col, removed_col in fields:
        rows.append(
            {
                "field": label,
                "added_target_2026_03_24_1200_buy": target_row.get(target_col, "") if target_col else "",
                "removed_opposite_2026_03_24_0500_sell": removed_row.get(removed_col, "") if removed_col else "",
            }
        )
    return pd.DataFrame(rows)


def target_detail_from_features(features: pd.DataFrame) -> pd.DataFrame:
    target = features[features["row_time_dt"].map(parse_dt).eq(TARGET_TIME)].copy()
    if target.empty:
        target = features[features["is_target_time"].map(as_bool)].copy()
    if target.empty:
        raise RuntimeError("Target candidate detail not found")
    out = target.iloc[[0]].copy()
    out["row_time_dt"] = out["row_time_dt"].map(parse_dt)
    out["nearest_opposite_layer3_time_dt"] = out["nearest_opposite_layer3_time_dt"].map(parse_dt)
    return out


def trace_max_pos_3(picked: pd.DataFrame, scenario: str) -> pd.DataFrame:
    if picked.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    active: list[tuple[pd.Timestamp, pd.Timestamp, str, str, str]] = []
    frame = picked.copy()
    frame["date_dt"] = frame["date_dt"].map(parse_dt)
    if "prototype_priority" not in frame.columns:
        frame["prototype_priority"] = 0
    for _, row in frame.sort_values(["date_dt", "prototype_priority", "mode"]).iterrows():
        anchor = parse_dt(row.get("date_dt"))
        if pd.isna(anchor):
            continue
        active = [item for item in active if item[0] > anchor]
        active_before = len(active)
        blockers = ";".join(f"{fmt_dt(item[1])} {item[2]} {item[3]}/{item[4]}" for item in active)
        accepted = active_before < 3
        direction = normalize_dir(row.get("dir_norm", row.get("dir", "")))
        trigger = str(row.get("trigger_family_norm", row.get("trigger", "")))
        family = mode_family(row.get("mode_family_norm", row.get("mode", "")))
        rows.append(
            {
                "scenario": scenario,
                "row_time": fmt_dt(anchor),
                "dir_norm": direction,
                "trigger_family": trigger,
                "mode_family": family,
                "mode": row.get("mode", ""),
                "variant": row.get("variant", ""),
                "prototype_added_candidate": as_bool(row.get("prototype_added_candidate", False)),
                "prototype_original_layer3": as_bool(row.get("prototype_original_layer3", False)),
                "is_target_candidate": anchor == TARGET_TIME and direction == "BUY" and family == "post_n",
                "is_removed_opposite_row": anchor == REMOVED_OPPOSITE_TIME and direction == "SELL",
                "active_count_before": active_before,
                "active_blockers_before": blockers,
                "accepted_by_current_24h_maxpos": accepted,
            }
        )
        if accepted:
            active.append((anchor + pd.Timedelta(hours=24), anchor, direction, trigger, family))
    return pd.DataFrame(rows)


def build_maxpos_probe(features: pd.DataFrame) -> pd.DataFrame:
    _, layer12, layer3, _ = proto.load_base_tables()
    base = proto.mark_base_layer3(layer3)
    detail = target_detail_from_features(features)
    target_rescue = proto.select_rescue_rows(layer12, detail)
    target_rescue["prototype_original_layer3"] = False
    target_rescue["prototype_added_candidate"] = True
    target_rescue["prototype_candidate_rule"] = "source_audit_mt5_0076_target"
    target_rescue["prototype_priority"] = -1

    base_removed, _ = proto.remove_nearest_opposites(base, detail)

    add_no_removal = pd.concat([base, target_rescue], ignore_index=True, sort=False)
    add_no_removal = add_no_removal.drop_duplicates(subset=["date_dt", "dir_norm", "mode", "variant"], keep="first")

    replace_nearest = pd.concat([base_removed, target_rescue], ignore_index=True, sort=False)
    replace_nearest = replace_nearest.drop_duplicates(subset=["date_dt", "dir_norm", "mode", "variant"], keep="first")

    traces = [
        trace_max_pos_3(base, "baseline_current_layer3_reapply"),
        trace_max_pos_3(add_no_removal, "add_target_no_removal"),
        trace_max_pos_3(replace_nearest, "add_target_remove_nearest_opposite"),
    ]
    probe = pd.concat(traces, ignore_index=True, sort=False)
    focus = probe[
        probe["row_time"].isin(
            [
                fmt_dt(REMOVED_OPPOSITE_TIME),
                fmt_dt(TARGET_TIME),
                "2026-03-24 02:00:00",
                "2026-03-24 04:30:00",
            ]
        )
        | probe["is_target_candidate"]
        | probe["is_removed_opposite_row"]
    ].copy()
    return focus.sort_values(["scenario", "row_time"]).reset_index(drop=True)


def summarize_maxpos_probe(probe: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scenario, grp in probe.groupby("scenario", dropna=False):
        target = grp[grp["is_target_candidate"].map(as_bool)].copy()
        opposite = grp[grp["is_removed_opposite_row"].map(as_bool)].copy()
        rows.append(
            {
                "scenario": scenario,
                "target_candidate_present": not target.empty,
                "target_accepted_by_current_24h_maxpos": bool(target["accepted_by_current_24h_maxpos"].iloc[0]) if not target.empty else False,
                "target_active_count_before": int(target["active_count_before"].iloc[0]) if not target.empty else -1,
                "target_active_blockers_before": target["active_blockers_before"].iloc[0] if not target.empty else "",
                "removed_opposite_present": not opposite.empty,
                "removed_opposite_accepted": bool(opposite["accepted_by_current_24h_maxpos"].iloc[0]) if not opposite.empty else False,
            }
        )
    return pd.DataFrame(rows)


def build_mt5_lifecycle() -> pd.DataFrame:
    ledger = read_csv(MT5_STAGE_STATE_DIR / "30m2H_strategy_trade_ledger.csv")
    ledger["signal_anchor_dt"] = ledger["signal_anchor_time"].map(parse_dt)
    ledger["aligned_target_time"] = ledger["signal_anchor_dt"] + pd.Timedelta(minutes=90)
    ledger["open_dt"] = ledger["open_time"].map(parse_dt)
    ledger["exit_dt"] = ledger["exit_time"].map(parse_dt)
    ledger["dir_norm"] = ledger["dir"].map(normalize_dir)
    ledger["trigger_family"] = ledger["trigger_tag"].astype(str).str.replace("[", "", regex=False).str.replace("]", "", regex=False)
    ledger["mode_family"] = ledger["signal_src"].map(mode_family)

    win = ledger[ledger["aligned_target_time"].between(WINDOW_START, WINDOW_END, inclusive="both")].copy()
    rows = []
    group_cols = ["signal_anchor_time", "aligned_target_time", "trigger_family", "signal_src", "mode_family", "dir_norm"]
    for keys, grp in win.groupby(group_cols, dropna=False):
        signal_anchor_time, aligned_target_time, trigger, signal_src, family, direction = keys
        rows.append(
            {
                "signal_anchor_time": signal_anchor_time,
                "aligned_target_time": fmt_dt(aligned_target_time),
                "trigger_family": trigger,
                "signal_src": signal_src,
                "mode_family": family,
                "dir_norm": direction,
                "stage_rows": int(len(grp)),
                "open_min": fmt_dt(grp["open_dt"].min()),
                "exit_max": fmt_dt(grp["exit_dt"].max()),
                "net_profit": round(float(pd.to_numeric(grp["net_profit"], errors="coerce").sum()), 6),
                "local_exit_reasons": ";".join(sorted(set(grp["local_exit_reason"].astype(str)))),
                "deal_reasons": ";".join(sorted(set(grp["deal_reason"].astype(str)))),
                "is_mt5_0076_aligned_target": parse_dt(aligned_target_time) == TARGET_TIME and direction == "BUY" and family == "post_n",
                "open_before_aligned_target": parse_dt(grp["open_dt"].min()) < TARGET_TIME,
                "closed_before_aligned_target": parse_dt(grp["exit_dt"].max()) < TARGET_TIME,
            }
        )
    return pd.DataFrame(rows).sort_values(["aligned_target_time", "signal_anchor_time"]).reset_index(drop=True)


def build_decision(
    target: pd.Series,
    tables: dict[str, pd.DataFrame],
    mt5_unique: pd.DataFrame,
    maxpos_summary: pd.DataFrame,
    mt5_lifecycle: pd.DataFrame,
    target_review: pd.DataFrame,
) -> pd.DataFrame:
    raw_exact = len(raw_replay.equivalent_rows(tables["python_raw_candidates"], target, 0))
    layer12_exact = len(raw_replay.equivalent_rows(tables["python_layer12_pass"], target, 0))
    layer3_exact = len(raw_replay.equivalent_rows(tables["python_layer3_selected"], target, 0))
    dynamic_exact = len(raw_replay.equivalent_rows(tables["python_dynamic_executed"], target, 0))
    mt5_exact = len(raw_replay.equivalent_rows(mt5_unique, target, 0))

    add_no = maxpos_summary[maxpos_summary["scenario"].eq("add_target_no_removal")].copy()
    replace = maxpos_summary[maxpos_summary["scenario"].eq("add_target_remove_nearest_opposite")].copy()
    add_no_accepted = bool(add_no["target_accepted_by_current_24h_maxpos"].iloc[0]) if not add_no.empty else False
    replace_accepted = bool(replace["target_accepted_by_current_24h_maxpos"].iloc[0]) if not replace.empty else False
    blockers = add_no["target_active_blockers_before"].iloc[0] if not add_no.empty else ""

    mt5_target = mt5_lifecycle[mt5_lifecycle["is_mt5_0076_aligned_target"].map(as_bool)].copy()
    mt5_target_closed_before_aligned = bool(mt5_target["closed_before_aligned_target"].iloc[0]) if not mt5_target.empty else False

    exact_variant = target_review[target_review["scenario"].astype(str).eq("target_mt5_0076_replace_nearest_opposite")]
    target_only_exact_pass = False
    if not exact_variant.empty:
        row = exact_variant.iloc[0]
        target_only_exact_pass = bool(row.get("mt5_0076_matched", False)) and bool(row.get("target_python_time_matched", False))

    source_bucket = "maxpos_lifecycle_gap"
    secondary_bucket = "layer3_selection_policy_gap"
    if raw_exact == 0 or layer12_exact == 0:
        source_bucket = "time_axis_or_data_gap"
        secondary_bucket = ""
    elif layer3_exact > 0 and dynamic_exact > 0:
        source_bucket = "accounting_only"
        secondary_bucket = ""
    elif not target_only_exact_pass:
        source_bucket = "layer3_selection_policy_gap"
        secondary_bucket = ""

    return pd.DataFrame(
        [
            {
                "target_trade_id": TARGET_ID,
                "aligned_target_time": fmt_dt(TARGET_TIME),
                "raw_exact_equivalent_count": raw_exact,
                "layer12_exact_same_family_count": layer12_exact,
                "layer3_exact_same_family_count": layer3_exact,
                "dynamic_exact_same_family_count": dynamic_exact,
                "mt5_exact_same_family_count": mt5_exact,
                "add_target_no_removal_accepted": add_no_accepted,
                "add_target_no_removal_active_blockers": blockers,
                "add_target_remove_nearest_opposite_accepted": replace_accepted,
                "target_only_exact_pass": target_only_exact_pass,
                "mt5_target_closed_before_aligned_time": mt5_target_closed_before_aligned,
                "source_bucket": source_bucket,
                "secondary_bucket": secondary_bucket,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "recommended_next_action": "prototype_lifecycle_aware_maxpos_probe_for_layer3_rescue_candidates",
            }
        ]
    )


def write_report(
    timeline: pd.DataFrame,
    field_compare: pd.DataFrame,
    maxpos_summary: pd.DataFrame,
    mt5_lifecycle: pd.DataFrame,
    decision: pd.DataFrame,
) -> None:
    d = decision.iloc[0]
    report = [
        "# Stage-State Layer3 Displacement Source Audit: mt5_0076",
        "",
        "## Scope",
        "",
        "- Diagnostic-only audit for `mt5_0076`.",
        "- Reviews Python raw, Layer1/2, Layer3, dynamic execution, MT5 unique ledger, and MT5 stage-state ledger.",
        "- Does not change Python signals, EA behavior, dynamic risk, or mapping.",
        "",
        "## Decision",
        "",
        f"- Source bucket: `{d['source_bucket']}`.",
        f"- Secondary bucket: `{d['secondary_bucket']}`.",
        f"- Raw exact equivalent count: `{int(d['raw_exact_equivalent_count'])}`.",
        f"- Layer1/2 exact same-family count: `{int(d['layer12_exact_same_family_count'])}`.",
        f"- Layer3 exact same-family count: `{int(d['layer3_exact_same_family_count'])}`.",
        f"- Dynamic exact same-family count: `{int(d['dynamic_exact_same_family_count'])}`.",
        f"- MT5 exact same-family count: `{int(d['mt5_exact_same_family_count'])}`.",
        f"- Add target without removing opposite accepted: `{as_bool(d['add_target_no_removal_accepted'])}`.",
        f"- Add target after removing nearest opposite accepted: `{as_bool(d['add_target_remove_nearest_opposite_accepted'])}`.",
        f"- Current 24h max-pos blockers before target: `{d['add_target_no_removal_active_blockers']}`.",
        f"- Target-only exact prototype pass: `{as_bool(d['target_only_exact_pass'])}`.",
        f"- MT5 target closed before aligned target time: `{as_bool(d['mt5_target_closed_before_aligned_time'])}`.",
        "",
        "Interpretation: Python has a valid raw and Layer1/2 candidate at the aligned target time, but the current Layer3/max-pos path keeps earlier accepted signals under a fixed 24-hour occupancy model. MT5 records the aligned target as an actual same-family ledger signal and its position lifecycle is not represented by that fixed Python occupancy model.",
        "",
        "## Max-Pos Summary",
        "",
        simple_table(maxpos_summary),
        "",
        "## Added Target vs Removed Opposite",
        "",
        simple_table(field_compare),
        "",
        "## MT5 Lifecycle Context",
        "",
        simple_table(mt5_lifecycle),
        "",
        "## Compact Timeline",
        "",
        simple_table(
            timeline,
            [
                "source_table",
                "row_time",
                "mt5_signal_anchor_time",
                "row_id",
                "dir_norm",
                "trigger_family",
                "mode_family",
                "mode_or_signal_src",
                "variant",
                "profit",
                "stage1_exit",
                "stage2_exit",
                "stage3_exit",
                "stage3_time",
            ],
            max_rows=120,
        ),
        "",
        "## Gates",
        "",
        f"- `main_signal_change_gate_open = {as_bool(d['main_signal_change_gate_open'])}`",
        f"- `ea_behavior_gate_open = {as_bool(d['ea_behavior_gate_open'])}`",
        f"- `mapping_change_gate_open = {as_bool(d['mapping_change_gate_open'])}`",
        f"- `merge_gate_pass = {as_bool(d['merge_gate_pass'])}`",
        f"- Recommended next action: `{d['recommended_next_action']}`.",
        "",
        "## Output Files",
        "",
        "- `layer3_displacement_timeline_mt5_0076.csv`",
        "- `layer3_displacement_added_vs_removed_fields.csv`",
        "- `layer3_displacement_maxpos_probe.csv`",
        "- `layer3_displacement_maxpos_summary.csv`",
        "- `layer3_displacement_mt5_lifecycle.csv`",
        "- `layer3_displacement_source_decision.csv`",
    ]
    write_text(OUT_DIR / "layer3_displacement_source_audit_mt5_0076.md", "\n".join(report))
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# stage_state_layer3_displacement_source_mt5_0076_20260717",
                "",
                "Diagnostic-only source/provenance audit for the mt5_0076 Layer3 displacement.",
                "",
                "No strategy, EA, dynamic-risk, or mapping logic is changed by this output.",
            ]
        ),
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    target = load_target()
    tables = raw_replay.load_signal_chain()
    mt5_unique = raw_replay.load_mt5_unique()

    features = read_csv(GENERALIZATION_DIR / "layer3_target_only_generalization_candidate_features.csv")
    removed = read_csv(GENERALIZATION_DIR / "gen_target_like_strict1_removed_nearest_opposite_rows.csv")
    target_review = read_csv(PROTOTYPE_DIR / "prototype_target_mt5_0076_review.csv")

    timeline = build_timeline(tables, mt5_unique)
    field_compare = build_field_comparison(features, removed)
    maxpos_probe = build_maxpos_probe(features)
    maxpos_summary = summarize_maxpos_probe(maxpos_probe)
    mt5_lifecycle = build_mt5_lifecycle()
    decision = build_decision(target, tables, mt5_unique, maxpos_summary, mt5_lifecycle, target_review)

    export_csv(timeline, OUT_DIR / "layer3_displacement_timeline_mt5_0076.csv")
    export_csv(field_compare, OUT_DIR / "layer3_displacement_added_vs_removed_fields.csv")
    export_csv(maxpos_probe, OUT_DIR / "layer3_displacement_maxpos_probe.csv")
    export_csv(maxpos_summary, OUT_DIR / "layer3_displacement_maxpos_summary.csv")
    export_csv(mt5_lifecycle, OUT_DIR / "layer3_displacement_mt5_lifecycle.csv")
    export_csv(decision, OUT_DIR / "layer3_displacement_source_decision.csv")
    write_report(timeline, field_compare, maxpos_summary, mt5_lifecycle, decision)


if __name__ == "__main__":
    main()
