# -*- coding: utf-8 -*-
"""Lifecycle-aware max-pos probe for Layer3 rescue candidates.

This is a non-destructive prototype. It keeps baseline signals, EA behavior,
dynamic-risk code, and mapping rules unchanged while testing whether replacing
the fixed 24-hour Layer3 max-pos occupancy with a Stage-derived active-until
estimate changes the admitted rescue candidates and full-chain alignment.
"""
from __future__ import annotations


import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import prototype_stage_state_layer3_m15_slot1_postn_rescue_full_chain_20260717 as proto  # noqa: E402


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

GENERALIZATION_DIR = VALIDATION_DIR / "stage_state_layer3_target_only_replacement_generalization_20260717"
SOURCE_AUDIT_DIR = VALIDATION_DIR / "stage_state_layer3_displacement_source_mt5_0076_20260717"

OUT_DIR = VALIDATION_DIR / "stage_state_lifecycle_aware_maxpos_probe_20260717"
SIGNALS_ROOT = OUT_DIR / "signals"
INPUTS_ROOT = OUT_DIR / "dynamic_inputs"
DYNAMIC_ROOT = OUT_DIR / "dynamic_alignment"
MAPPING_ROOT = OUT_DIR / "mapping"

TARGET_TIME = pd.Timestamp("2026-03-24 12:00:00")


@dataclass(frozen=True)
class ProbeVariant:
    name: str
    description: str
    selector: str
    remove_nearest_opposite: bool


VARIANTS = [
    ProbeVariant(
        "lifecycle_add_all29_stage3time",
        "Append all 29 rescue candidates and use Stage-derived stage3_time as active-until.",
        "all29",
        False,
    ),
    ProbeVariant(
        "lifecycle_replace_nearest_all29_stage3time",
        "Remove nearest opposite rows for all 29 rescue candidates, then use Stage-derived stage3_time as active-until.",
        "all29",
        True,
    ),
    ProbeVariant(
        "lifecycle_replace_same_family8_stage3time",
        "Remove nearest opposite rows only for the 8 same-family-opposite candidates, then use Stage-derived stage3_time as active-until.",
        "same_family_opposite",
        True,
    ),
]


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


def parse_dt_series(series: pd.Series) -> pd.Series:
    return series.map(parse_dt)


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


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL", "SHORT", "-1"}:
        return "SELL"
    if text in {"L", "B", "BUY", "LONG", "1"}:
        return "BUY"
    return text


def mode_family(value: object) -> str:
    text = str(value)
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return text.strip()


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None, max_rows: int = 80) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.copy()
    if columns is not None:
        display = display[[col for col in columns if col in display.columns]]
    return display.head(max_rows).to_markdown(index=False)


def patch_proto_output_roots() -> None:
    proto.OUT_DIR = OUT_DIR
    proto.SIGNALS_ROOT = SIGNALS_ROOT
    proto.INPUTS_ROOT = INPUTS_ROOT
    proto.DYNAMIC_ROOT = DYNAMIC_ROOT
    proto.MAPPING_ROOT = MAPPING_ROOT


def load_features() -> pd.DataFrame:
    features = read_csv(GENERALIZATION_DIR / "layer3_target_only_generalization_candidate_features.csv")
    features["row_time_dt"] = parse_dt_series(features["row_time"])
    features["nearest_opposite_layer3_time_dt"] = parse_dt_series(features["nearest_opposite_layer3_time"])
    features["dir_norm"] = features["dir_norm"].map(normalize_dir)
    features["mode_family"] = features["mode_family"].map(mode_family)
    features["same_family_opposite"] = features["same_family_opposite"].map(as_bool)
    features["target_like_strict"] = features["target_like_strict"].map(as_bool)
    return features.sort_values("row_time_dt").reset_index(drop=True)


def select_features(features: pd.DataFrame, variant: ProbeVariant) -> pd.DataFrame:
    if variant.selector == "all29":
        return features.copy()
    if variant.selector == "same_family_opposite":
        return features[features["same_family_opposite"]].copy()
    raise ValueError(variant.selector)


def build_before_maxpos(
    variant: ProbeVariant,
    layer3: pd.DataFrame,
    layer12: pd.DataFrame,
    selected: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = proto.mark_base_layer3(layer3)
    if variant.remove_nearest_opposite:
        base, removed = proto.remove_nearest_opposites(base, selected)
    else:
        removed = base.iloc[0:0].copy()

    selected_rescue = proto.select_rescue_rows(layer12, selected)
    selected_rescue["prototype_original_layer3"] = False
    selected_rescue["prototype_added_candidate"] = True
    selected_rescue["prototype_candidate_rule"] = variant.name
    selected_rescue["prototype_priority"] = -1

    combined = pd.concat([base, selected_rescue], ignore_index=True, sort=False)
    combined = combined.drop_duplicates(subset=["date_dt", "dir_norm", "mode", "variant"], keep="first")
    combined = combined.sort_values(["date_dt", "prototype_priority", "mode"]).reset_index(drop=True)
    return combined, selected_rescue, removed


def attach_lifecycle_active_until(m30: pd.DataFrame, before_maxpos: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    stage_all = proto.build_stage_results(m30, before_maxpos)
    stage_all["date_dt"] = parse_dt_series(stage_all["date"])
    stage_all["dir_norm"] = stage_all["dir"].map(normalize_dir)
    stage_all["active_until_lifecycle"] = parse_dt_series(stage_all["stage3_time"])
    stage_all["mode"] = stage_all["mode"].astype(str)
    stage_key = stage_all[
        [
            "date_dt",
            "dir_norm",
            "mode",
            "active_until_lifecycle",
            "stage1_exit",
            "stage2_exit",
            "stage3_exit",
            "stage3_time",
            "total_$",
        ]
    ].drop_duplicates(["date_dt", "dir_norm", "mode"], keep="first")

    out = before_maxpos.copy()
    out["date_dt"] = parse_dt_series(out["date_dt"])
    out["dir_norm"] = out["dir_norm"].map(normalize_dir)
    out["mode"] = out["mode"].astype(str)
    out = out.merge(stage_key, on=["date_dt", "dir_norm", "mode"], how="left")
    out["active_until_fixed24"] = out["date_dt"] + pd.Timedelta(hours=24)
    out["active_until_lifecycle"] = out["active_until_lifecycle"].fillna(out["active_until_fixed24"])
    out.loc[out["active_until_lifecycle"] < out["date_dt"], "active_until_lifecycle"] = out["date_dt"]
    return out, stage_all


def row_label(row: pd.Series) -> str:
    return (
        f"{fmt_dt(row.get('date_dt'))} "
        f"{normalize_dir(row.get('dir_norm', row.get('dir', '')))} "
        f"{row.get('trigger_family_norm', row.get('trigger', ''))}/"
        f"{mode_family(row.get('mode_family_norm', row.get('mode', '')))}"
    )


def trace_admission(frame: pd.DataFrame, variant_name: str, policy: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    accepted_ids: list[int] = []
    active: list[tuple[pd.Timestamp, str]] = []
    work = frame.copy().reset_index(drop=True)
    work["_row_id"] = range(len(work))

    for _, row in work.sort_values(["date_dt", "prototype_priority", "mode"]).iterrows():
        anchor = parse_dt(row["date_dt"])
        if pd.isna(anchor):
            continue
        active = [item for item in active if item[0] > anchor]
        blockers = ";".join(item[1] for item in active)
        accepted = len(active) < 3
        if policy == "fixed24":
            active_until = parse_dt(row.get("active_until_fixed24"))
        elif policy == "lifecycle_stage3time":
            active_until = parse_dt(row.get("active_until_lifecycle"))
        else:
            raise ValueError(policy)
        if pd.isna(active_until):
            active_until = anchor + pd.Timedelta(hours=24)
        if active_until < anchor:
            active_until = anchor

        direction = normalize_dir(row.get("dir_norm", row.get("dir", "")))
        family = mode_family(row.get("mode_family_norm", row.get("mode", "")))
        is_added = as_bool(row.get("prototype_added_candidate", False))
        is_target = anchor == TARGET_TIME and direction == "BUY" and family == "post_n"
        rows.append(
            {
                "variant": variant_name,
                "policy": policy,
                "row_id": int(row["_row_id"]),
                "row_time": fmt_dt(anchor),
                "active_until": fmt_dt(active_until),
                "dir_norm": direction,
                "trigger_family": row.get("trigger_family_norm", row.get("trigger", "")),
                "mode_family": family,
                "mode": row.get("mode", ""),
                "source_variant": row.get("variant", ""),
                "prototype_added_candidate": is_added,
                "prototype_original_layer3": as_bool(row.get("prototype_original_layer3", False)),
                "is_target_candidate": is_target,
                "active_count_before": len(active),
                "active_blockers_before": blockers,
                "accepted": accepted,
                "stage1_exit": row.get("stage1_exit", ""),
                "stage2_exit": row.get("stage2_exit", ""),
                "stage3_exit": row.get("stage3_exit", ""),
                "stage_total_$": row.get("total_$", ""),
            }
        )
        if accepted:
            accepted_ids.append(int(row["_row_id"]))
            active.append((active_until, row_label(row)))

    trace = pd.DataFrame(rows)
    after = work[work["_row_id"].isin(accepted_ids)].drop(columns=["_row_id"]).copy()
    return trace, after.sort_values("date_dt").reset_index(drop=True)


def target_candidate_count(frame: pd.DataFrame) -> int:
    if frame.empty:
        return 0
    rows = frame.copy()
    rows["date_dt"] = parse_dt_series(rows["date_dt"])
    return int(
        (
            rows["date_dt"].eq(TARGET_TIME)
            & rows["dir_norm"].map(normalize_dir).eq("BUY")
            & rows["mode"].astype(str).str.contains("post_n", na=False)
            & rows.get("prototype_added_candidate", False).map(as_bool)
        ).sum()
    )


def candidate_count(frame: pd.DataFrame) -> int:
    if frame.empty or "prototype_added_candidate" not in frame.columns:
        return 0
    return int(frame["prototype_added_candidate"].map(as_bool).sum())


def build_signal_summary(
    variant: ProbeVariant,
    selected: pd.DataFrame,
    removed: pd.DataFrame,
    before_maxpos: pd.DataFrame,
    fixed_trace: pd.DataFrame,
    fixed_after: pd.DataFrame,
    lifecycle_trace: pd.DataFrame,
    lifecycle_after: pd.DataFrame,
) -> dict[str, object]:
    target_rows = lifecycle_trace[lifecycle_trace["is_target_candidate"].map(as_bool)].copy()
    target_row = target_rows.iloc[0] if not target_rows.empty else pd.Series(dtype=object)
    return {
        "variant": variant.name,
        "description": variant.description,
        "selector": variant.selector,
        "remove_nearest_opposite": variant.remove_nearest_opposite,
        "selected_candidates": int(len(selected)),
        "selected_same_family_opposite": int(selected["same_family_opposite"].map(as_bool).sum()) if not selected.empty else 0,
        "removed_nearest_opposite_rows": int(len(removed)),
        "before_maxpos_rows": int(len(before_maxpos)),
        "fixed24_after_rows": int(len(fixed_after)),
        "fixed24_candidate_rows_after": candidate_count(fixed_after),
        "fixed24_target_candidate_after": target_candidate_count(fixed_after),
        "lifecycle_after_rows": int(len(lifecycle_after)),
        "lifecycle_candidate_rows_after": candidate_count(lifecycle_after),
        "lifecycle_target_candidate_after": target_candidate_count(lifecycle_after),
        "lifecycle_target_accepted": bool(target_row.get("accepted", False)) if not target_row.empty else False,
        "lifecycle_target_active_count_before": int(target_row.get("active_count_before", -1)) if not target_row.empty else -1,
        "lifecycle_target_blockers_before": target_row.get("active_blockers_before", "") if not target_row.empty else "",
        "lifecycle_minus_fixed_candidate_rows": candidate_count(lifecycle_after) - candidate_count(fixed_after),
    }


def strip_probe_columns(frame: pd.DataFrame) -> pd.DataFrame:
    probe_cols = [
        "active_until_lifecycle",
        "active_until_fixed24",
        "stage1_exit",
        "stage2_exit",
        "stage3_exit",
        "stage3_time",
        "total_$",
    ]
    return frame.drop(columns=[col for col in probe_cols if col in frame.columns]).copy()


def build_before_after_decision(
    before_after: pd.DataFrame,
    target_review: pd.DataFrame,
    signal_summary: pd.DataFrame,
) -> pd.DataFrame:
    base = before_after[before_after["scenario"].eq("current_stage_state_metadatafix")].iloc[0]
    rows = []
    for _, row in before_after[~before_after["scenario"].eq("current_stage_state_metadatafix")].iterrows():
        name = row["scenario"]
        sig = signal_summary[signal_summary["variant"].eq(name)].iloc[0]
        target = target_review[target_review["scenario"].eq(name)].iloc[0]
        matched_delta = int(row["matched_unique"]) - int(base["matched_unique"])
        reliable_delta = int(row["reliable_tier_matched"]) - int(base["reliable_tier_matched"])
        direct_gap_delta = float(row["direct_gap_py_minus_mt5"]) - float(base["direct_gap_py_minus_mt5"])
        signal_gap_delta = float(row["signal_set_gap_py_minus_mt5"]) - float(base["signal_set_gap_py_minus_mt5"])
        matched_not_worse = matched_delta >= 0
        reliable_not_worse = reliable_delta >= 0
        direct_gap_not_worse = abs(float(row["direct_gap_py_minus_mt5"])) <= abs(float(base["direct_gap_py_minus_mt5"]))
        signal_gap_not_worse = abs(float(row["signal_set_gap_py_minus_mt5"])) <= abs(float(base["signal_set_gap_py_minus_mt5"]))
        target_exact = str(target.get("mt5_0076_match_tier", "")).startswith("exact") and as_bool(
            target.get("target_python_time_matched", False)
        )
        multi_candidate_support = int(sig["lifecycle_candidate_rows_after"]) > 1
        quality_improved = matched_delta > 0 or reliable_delta > 0
        lifecycle_probe_gate_pass = bool(
            target_exact
            and multi_candidate_support
            and matched_not_worse
            and reliable_not_worse
            and direct_gap_not_worse
            and signal_gap_not_worse
            and quality_improved
        )
        if lifecycle_probe_gate_pass:
            decision = "prototype_candidate_needs_manual_review"
        elif target_exact and not multi_candidate_support:
            decision = "target_only_or_single_support_not_mergeable"
        elif target_exact:
            decision = "target_exact_but_overall_quality_or_gap_failed"
        else:
            decision = "diagnostic_only_reject"
        rows.append(
            {
                "variant": name,
                "selected_candidates": int(sig["selected_candidates"]),
                "lifecycle_candidate_rows_after": int(sig["lifecycle_candidate_rows_after"]),
                "lifecycle_target_candidate_after": int(sig["lifecycle_target_candidate_after"]),
                "mt5_0076_match_tier": target.get("mt5_0076_match_tier", ""),
                "target_python_time_matched": as_bool(target.get("target_python_time_matched", False)),
                "matched_unique_delta": matched_delta,
                "reliable_tier_delta": reliable_delta,
                "python_unmatched_delta": int(row["python_unmatched"]) - int(base["python_unmatched"]),
                "mt5_unmatched_delta": int(row["mt5_unmatched"]) - int(base["mt5_unmatched"]),
                "direct_gap_delta": round(direct_gap_delta, 6),
                "signal_set_gap_delta": round(signal_gap_delta, 6),
                "matched_not_worse": matched_not_worse,
                "reliable_not_worse": reliable_not_worse,
                "direct_gap_not_worse": direct_gap_not_worse,
                "signal_gap_not_worse": signal_gap_not_worse,
                "multi_candidate_support": multi_candidate_support,
                "quality_improved": quality_improved,
                "lifecycle_probe_gate_pass": lifecycle_probe_gate_pass,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "decision": decision,
            }
        )
    return pd.DataFrame(rows)


def build_final_decision(decision: pd.DataFrame) -> pd.DataFrame:
    pass_count = int(decision["lifecycle_probe_gate_pass"].map(as_bool).sum()) if not decision.empty else 0
    exact_count = int(decision["mt5_0076_match_tier"].astype(str).str.startswith("exact").sum()) if not decision.empty else 0
    return pd.DataFrame(
        [
            {
                "variants_tested": int(len(decision)),
                "target_exact_variant_count": exact_count,
                "lifecycle_probe_gate_pass_count": pass_count,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "decision": "lifecycle_probe_not_mergeable" if pass_count == 0 else "prototype_candidate_manual_review_only",
                "recommended_next_action": "review_lifecycle_probe_failures_before_any_signal_change"
                if pass_count == 0
                else "manual_review_lifecycle_probe_candidate",
            }
        ]
    )


def write_report(
    signal_summary: pd.DataFrame,
    before_after: pd.DataFrame,
    target_review: pd.DataFrame,
    decision: pd.DataFrame,
    final_decision: pd.DataFrame,
) -> None:
    final = final_decision.iloc[0]
    lines = [
        "# Stage-State Lifecycle-Aware Max-Pos Probe",
        "",
        "## Scope",
        "",
        "- Non-destructive prototype only.",
        "- Tests Stage-derived `stage3_time` as active-until instead of fixed 24-hour max-pos occupancy.",
        "- Rebuilds signal snapshots and reruns Stage, dynamic risk, and mapping for lifecycle variants.",
        "- Does not modify baseline Python signals, EA behavior, dynamic-risk code, or mapping rules.",
        "",
        "## Final Decision",
        "",
        f"- Variants tested: `{int(final['variants_tested'])}`.",
        f"- Target exact variants: `{int(final['target_exact_variant_count'])}`.",
        f"- Lifecycle probe gate pass count: `{int(final['lifecycle_probe_gate_pass_count'])}`.",
        f"- Decision: `{final['decision']}`.",
        f"- Recommended next action: `{final['recommended_next_action']}`.",
        f"- `main_signal_change_gate_open = {as_bool(final['main_signal_change_gate_open'])}`.",
        f"- `ea_behavior_gate_open = {as_bool(final['ea_behavior_gate_open'])}`.",
        f"- `mapping_change_gate_open = {as_bool(final['mapping_change_gate_open'])}`.",
        f"- `merge_gate_pass = {as_bool(final['merge_gate_pass'])}`.",
        "",
        "## Signal Admission Summary",
        "",
        markdown_table(signal_summary),
        "",
        "## Full-Chain Before / After",
        "",
        markdown_table(before_after),
        "",
        "## Target mt5_0076",
        "",
        markdown_table(target_review),
        "",
        "## Variant Decisions",
        "",
        markdown_table(decision),
        "",
        "## Interpretation",
        "",
        "- A lifecycle-aware max-pos candidate must improve target matching without reducing matched/reliable counts or worsening direct/signal-set gaps.",
        "- A target-only improvement remains diagnostic-only.",
        "- Any candidate that passes this probe still requires manual review before a main signal change.",
        "",
        "## Output Files",
        "",
        "- `lifecycle_maxpos_signal_summary.csv`",
        "- `lifecycle_maxpos_full_chain_before_after.csv`",
        "- `lifecycle_maxpos_target_mt5_0076_review.csv`",
        "- `lifecycle_maxpos_variant_decisions.csv`",
        "- `lifecycle_maxpos_final_decision.csv`",
        "- `lifecycle_maxpos_trace.csv`",
        "- `signals/<variant>/`",
        "- `dynamic_inputs/<variant>/`",
        "- `dynamic_alignment/<variant>/`",
        "- `mapping/<variant>/`",
    ]
    write_text(OUT_DIR / "stage_state_lifecycle_aware_maxpos_probe_review.md", "\n".join(lines))
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# stage_state_lifecycle_aware_maxpos_probe_20260717",
                "",
                "Full-chain, non-destructive lifecycle-aware max-pos probe for Layer3 rescue candidates.",
                "",
                "All outputs are diagnostic snapshots. They are not a final strategy version.",
            ]
        ),
    )


def clean_output_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in [SIGNALS_ROOT, INPUTS_ROOT, DYNAMIC_ROOT, MAPPING_ROOT]:
        if path.exists():
            shutil.rmtree(path)


def main() -> None:
    patch_proto_output_roots()
    clean_output_dirs()

    raw, layer12, layer3, m30 = proto.load_base_tables()
    features = load_features()
    source_decision = read_csv(SOURCE_AUDIT_DIR / "layer3_displacement_source_decision.csv")
    export_csv(features, OUT_DIR / "lifecycle_maxpos_candidate_features_source.csv")
    export_csv(source_decision, OUT_DIR / "lifecycle_maxpos_source_audit_decision.csv")

    full_chain_rows = [
        proto.scenario_stats(
            "current_stage_state_metadatafix",
            proto.BASE_DYNAMIC_DIR,
            proto.BASE_MAPPING_DIR,
            "current accepted stage-state metadatafix baseline",
        )
    ]
    target_rows = [proto.target_status("current_stage_state_metadatafix", proto.BASE_DYNAMIC_DIR, proto.BASE_MAPPING_DIR)]
    signal_rows: list[dict[str, object]] = []
    trace_frames: list[pd.DataFrame] = []

    for variant in VARIANTS:
        selected = select_features(features, variant)
        before_maxpos, selected_rescue, removed = build_before_maxpos(variant, layer3, layer12, selected)
        before_with_active, stage_all = attach_lifecycle_active_until(m30, before_maxpos)
        fixed_trace, fixed_after = trace_admission(before_with_active, variant.name, "fixed24")
        lifecycle_trace, lifecycle_after = trace_admission(before_with_active, variant.name, "lifecycle_stage3time")

        lifecycle_signals = strip_probe_columns(lifecycle_after)
        stage = proto.build_stage_results(m30, lifecycle_signals)
        signal_dir = proto.write_signal_snapshot(variant, raw, layer12, lifecycle_signals, stage)
        input_dir = proto.run_prepare_inputs(variant, signal_dir)
        dynamic_dir, mapping_dir = proto.run_dynamic_and_mapping(variant, input_dir)

        export_csv(selected, OUT_DIR / f"{variant.name}_selected_features.csv")
        export_csv(selected_rescue, OUT_DIR / f"{variant.name}_selected_rescue_rows.csv")
        export_csv(removed, OUT_DIR / f"{variant.name}_removed_nearest_opposite_rows.csv")
        export_csv(before_with_active, OUT_DIR / f"{variant.name}_before_maxpos_with_active_until.csv")
        export_csv(fixed_after, OUT_DIR / f"{variant.name}_fixed24_after_maxpos.csv")
        export_csv(lifecycle_after, OUT_DIR / f"{variant.name}_lifecycle_after_maxpos.csv")
        export_csv(stage_all, OUT_DIR / f"{variant.name}_before_maxpos_stage_estimates.csv")

        fixed_trace["trace_scope"] = "current_24h_recomputed"
        lifecycle_trace["trace_scope"] = "lifecycle_probe"
        trace_frames.extend([fixed_trace, lifecycle_trace])

        signal_rows.append(
            build_signal_summary(
                variant,
                selected,
                removed,
                before_with_active,
                fixed_trace,
                fixed_after,
                lifecycle_trace,
                lifecycle_after,
            )
        )
        full_chain_rows.append(proto.scenario_stats(variant.name, dynamic_dir, mapping_dir, variant.description))
        target_rows.append(proto.target_status(variant.name, dynamic_dir, mapping_dir))

    signal_summary = pd.DataFrame(signal_rows)
    before_after = pd.DataFrame(full_chain_rows)
    target_review = pd.DataFrame(target_rows)
    decisions = build_before_after_decision(before_after, target_review, signal_summary)
    final_decision = build_final_decision(decisions)
    trace = pd.concat(trace_frames, ignore_index=True, sort=False) if trace_frames else pd.DataFrame()

    export_csv(signal_summary, OUT_DIR / "lifecycle_maxpos_signal_summary.csv")
    export_csv(before_after, OUT_DIR / "lifecycle_maxpos_full_chain_before_after.csv")
    export_csv(target_review, OUT_DIR / "lifecycle_maxpos_target_mt5_0076_review.csv")
    export_csv(decisions, OUT_DIR / "lifecycle_maxpos_variant_decisions.csv")
    export_csv(final_decision, OUT_DIR / "lifecycle_maxpos_final_decision.csv")
    export_csv(trace, OUT_DIR / "lifecycle_maxpos_trace.csv")
    write_report(signal_summary, before_after, target_review, decisions, final_decision)


if __name__ == "__main__":
    main()
