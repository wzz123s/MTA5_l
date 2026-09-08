# -*- coding: utf-8 -*-
"""Generalization audit for the target-only Layer3 replacement prototype.

This script checks whether the successful mt5_0076 target-only replacement can
be expressed as a low-blast-radius rule. It runs a few narrow, non-destructive
full-chain variants and keeps the main signal/EA/mapping gates closed unless a
multi-case rule survives the checks.
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

PRIOR_DIR = VALIDATION_DIR / "stage_state_layer3_m15_slot1_postn_rescue_full_chain_20260717"
OUT_DIR = VALIDATION_DIR / "stage_state_layer3_target_only_replacement_generalization_20260717"
SIGNALS_ROOT = OUT_DIR / "signals"
INPUTS_ROOT = OUT_DIR / "dynamic_inputs"
DYNAMIC_ROOT = OUT_DIR / "dynamic_alignment"
MAPPING_ROOT = OUT_DIR / "mapping"

TARGET_TIME = pd.Timestamp("2026-03-24 12:00:00")


@dataclass(frozen=True)
class RuleVariant:
    name: str
    description: str
    selector: str


RULES = [
    RuleVariant(
        "gen_same_family_opposite_all8",
        "All candidates whose nearest opposite Layer3 row is also M15 SLOT1/post_n.",
        "same_family_opposite",
    ),
    RuleVariant(
        "gen_same_family_buy_negative_all5",
        "BUY candidates in the same-family-opposite bucket with negative Layer1/2 pnl.",
        "same_family_buy_negative",
    ),
    RuleVariant(
        "gen_same_family_cluster_latest2",
        "Only the latest candidate in each same-family-opposite cluster.",
        "same_family_cluster_latest",
    ),
    RuleVariant(
        "gen_target_like_strict1",
        "Strict non-id target-like condition: same-family opposite, BUY, post_n6, negative pnl, <=480 minutes.",
        "target_like_strict",
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


def mode_number(value: object) -> int:
    text = str(value)
    if "post_n" not in text:
        return -1
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else -1


def build_candidate_features(details: pd.DataFrame, rescue_rows: pd.DataFrame) -> pd.DataFrame:
    out = details.copy()
    out["row_time_dt"] = pd.to_datetime(out["row_time"], errors="coerce")
    out["nearest_opposite_layer3_time_dt"] = pd.to_datetime(out["nearest_opposite_layer3_time"], errors="coerce")
    out["source_profit_num"] = pd.to_numeric(out["source_profit"], errors="coerce")
    out["mode_n"] = out["mode"].map(mode_number)
    out["opposite_signed_minutes"] = (
        out["nearest_opposite_layer3_time_dt"] - out["row_time_dt"]
    ).dt.total_seconds() / 60.0
    out["same_family_opposite"] = (
        out["nearest_opposite_layer3_trigger"].astype(str).eq("M15 SLOT1")
        & out["nearest_opposite_layer3_mode"].astype(str).eq("post_n")
    )
    out["target_like_strict"] = (
        out["same_family_opposite"]
        & out["dir_norm"].astype(str).eq("BUY")
        & out["mode"].astype(str).eq("post_n6")
        & out["variant"].astype(str).eq("ea_slot1_replace")
        & (out["source_profit_num"] < 0)
        & (pd.to_numeric(out["nearest_opposite_abs_minutes"], errors="coerce") <= 480)
    )
    out["candidate_cluster_key"] = (
        out["nearest_opposite_layer3_time_dt"].astype(str)
        + "|"
        + out["nearest_opposite_layer3_trigger"].astype(str)
        + "|"
        + out["nearest_opposite_layer3_mode"].astype(str)
        + "|"
        + out["dir_norm"].astype(str)
    )

    cluster = out.groupby("candidate_cluster_key", dropna=False).agg(
        cluster_rows=("row_time", "count"),
        cluster_min_time=("row_time_dt", "min"),
        cluster_max_time=("row_time_dt", "max"),
        cluster_max_mode_n=("mode_n", "max"),
        cluster_min_profit=("source_profit_num", "min"),
        cluster_max_profit=("source_profit_num", "max"),
        cluster_negative_rows=("source_profit_num", lambda s: int((s < 0).sum())),
    )
    out = out.merge(cluster, on="candidate_cluster_key", how="left")
    out["cluster_all_negative"] = out["cluster_negative_rows"].eq(out["cluster_rows"])
    out["is_cluster_latest_time"] = out["row_time_dt"].eq(out["cluster_max_time"])
    out["is_cluster_max_mode"] = out["mode_n"].eq(out["cluster_max_mode_n"])
    out["is_target_time"] = out["row_time_dt"].eq(TARGET_TIME)

    rescue_lookup = rescue_rows.copy()
    rescue_lookup["row_time_dt"] = pd.to_datetime(rescue_lookup["date"], errors="coerce")
    rescue_lookup = rescue_lookup.rename(
        columns={
            "entry": "candidate_entry",
            "stop": "candidate_stop",
            "sd": "candidate_sd",
            "Bias_5": "candidate_Bias_5",
            "Bias_13": "candidate_Bias_13",
            "Bias_55": "candidate_Bias_55",
            "spec_pass": "candidate_spec_pass",
            "spec_reason": "candidate_spec_reason",
        }
    )
    keep_cols = [
        "row_time_dt",
        "candidate_entry",
        "candidate_stop",
        "candidate_sd",
        "candidate_Bias_5",
        "candidate_Bias_13",
        "candidate_Bias_55",
        "candidate_spec_pass",
        "candidate_spec_reason",
    ]
    out = out.merge(rescue_lookup[keep_cols].drop_duplicates("row_time_dt"), on="row_time_dt", how="left")
    return out


def select_rule_features(features: pd.DataFrame, rule: RuleVariant) -> pd.DataFrame:
    if rule.selector == "same_family_opposite":
        return features[features["same_family_opposite"]].copy()
    if rule.selector == "same_family_buy_negative":
        return features[
            features["same_family_opposite"]
            & features["dir_norm"].astype(str).eq("BUY")
            & (features["source_profit_num"] < 0)
        ].copy()
    if rule.selector == "same_family_cluster_latest":
        return features[features["same_family_opposite"] & features["is_cluster_latest_time"]].copy()
    if rule.selector == "target_like_strict":
        return features[features["target_like_strict"]].copy()
    raise ValueError(rule.selector)


def subset_rescue_rows(rescue_rows: pd.DataFrame, selected_features: pd.DataFrame) -> pd.DataFrame:
    selected_times = set(pd.to_datetime(selected_features["row_time_dt"], errors="coerce"))
    rows = rescue_rows.copy()
    rows["date_dt"] = pd.to_datetime(rows["date"], errors="coerce")
    return rows[rows["date_dt"].isin(selected_times)].copy()


def build_custom_variant(
    rule: RuleVariant,
    layer3: pd.DataFrame,
    rescue_rows: pd.DataFrame,
    selected_features: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = proto.mark_base_layer3(layer3)
    selected_details = selected_features.copy()
    selected_details["row_time_dt"] = pd.to_datetime(selected_details["row_time_dt"], errors="coerce")
    selected_details["nearest_opposite_layer3_time_dt"] = pd.to_datetime(
        selected_details["nearest_opposite_layer3_time_dt"], errors="coerce"
    )
    selected_rescue = subset_rescue_rows(rescue_rows, selected_details)
    selected_rescue["prototype_original_layer3"] = False
    selected_rescue["prototype_added_candidate"] = True
    selected_rescue["prototype_candidate_rule"] = rule.name
    selected_rescue["prototype_priority"] = -1

    base_after_removal, removed = proto.remove_nearest_opposites(base, selected_details)
    combined = pd.concat([base_after_removal, selected_rescue], ignore_index=True, sort=False)
    combined = combined.drop_duplicates(subset=["date_dt", "dir_norm", "mode", "variant"], keep="first")
    before_maxpos = combined.sort_values("date_dt").reset_index(drop=True)
    after_maxpos = proto.apply_max_pos_3(before_maxpos).sort_values("date_dt").reset_index(drop=True)
    return after_maxpos, before_maxpos, removed


def variant_signal_summary(
    rule: RuleVariant,
    selected_features: pd.DataFrame,
    before_maxpos: pd.DataFrame,
    after_maxpos: pd.DataFrame,
    removed: pd.DataFrame,
) -> dict[str, object]:
    added_before = before_maxpos[before_maxpos.get("prototype_added_candidate", False).astype(bool)].copy()
    added_after = after_maxpos[after_maxpos.get("prototype_added_candidate", False).astype(bool)].copy()
    target_after = added_after[pd.to_datetime(added_after["date_dt"], errors="coerce").eq(TARGET_TIME)].copy()
    return {
        "variant": rule.name,
        "description": rule.description,
        "selected_candidates": int(len(selected_features)),
        "selected_clusters": int(selected_features["candidate_cluster_key"].nunique()) if not selected_features.empty else 0,
        "before_maxpos_rows": int(len(before_maxpos)),
        "after_maxpos_rows": int(len(after_maxpos)),
        "candidate_rows_before_maxpos": int(len(added_before)),
        "candidate_rows_after_maxpos": int(len(added_after)),
        "removed_nearest_opposite_rows": int(len(removed)),
        "target_candidate_after_maxpos": int(len(target_after)),
        "target_candidate_profit_sum": round(
            float(pd.to_numeric(target_after.get("pnl", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum()),
            6,
        )
        if not target_after.empty
        else 0.0,
    }


def source_row(frame: pd.DataFrame, source: str) -> pd.Series:
    hit = frame[frame["source"].astype(str).eq(source)]
    if hit.empty:
        raise ValueError(f"missing source={source}")
    return hit.iloc[0]


def build_rule_result_summary(
    signal_summary: pd.DataFrame,
    before_after: pd.DataFrame,
    target_review: pd.DataFrame,
) -> pd.DataFrame:
    base = before_after[before_after["scenario"].eq("current_stage_state_metadatafix")].iloc[0]
    rows: list[dict[str, object]] = []
    for _, sig in signal_summary.iterrows():
        name = sig["variant"]
        after = before_after[before_after["scenario"].eq(name)].iloc[0]
        target = target_review[target_review["scenario"].eq(name)].iloc[0]
        matched_delta = int(after["matched_unique"]) - int(base["matched_unique"])
        reliable_delta = int(after["reliable_tier_matched"]) - int(base["reliable_tier_matched"])
        direct_delta = float(after["direct_gap_py_minus_mt5"]) - float(base["direct_gap_py_minus_mt5"])
        signal_delta = float(after["signal_set_gap_py_minus_mt5"]) - float(base["signal_set_gap_py_minus_mt5"])
        multi_support = int(sig["selected_candidates"]) > 1
        target_exact = str(target.get("mt5_0076_match_tier", "")) == "exact_align90_all"
        not_worse = matched_delta >= 0 and reliable_delta >= 0 and direct_delta <= 0 and signal_delta <= 0
        generalization_gate = bool(multi_support and target_exact and not_worse)
        if generalization_gate:
            decision = "generalized_rule_candidate_needs_manual_review"
        elif target_exact and not multi_support and not_worse:
            decision = "single_support_only_not_mergeable"
        else:
            decision = "diagnostic_only_reject"
        rows.append(
            {
                "variant": name,
                "selected_candidates": int(sig["selected_candidates"]),
                "selected_clusters": int(sig["selected_clusters"]),
                "candidate_rows_after_maxpos": int(sig["candidate_rows_after_maxpos"]),
                "target_candidate_after_maxpos": int(sig["target_candidate_after_maxpos"]),
                "mt5_0076_match_tier": target.get("mt5_0076_match_tier", ""),
                "mt5_0076_matched": bool(target.get("mt5_0076_matched", False)),
                "target_python_time_matched": bool(target.get("target_python_time_matched", False)),
                "matched_unique_delta": matched_delta,
                "reliable_tier_delta": reliable_delta,
                "python_unmatched_delta": int(after["python_unmatched"]) - int(base["python_unmatched"]),
                "mt5_unmatched_delta": int(after["mt5_unmatched"]) - int(base["mt5_unmatched"]),
                "direct_gap_delta": round(direct_delta, 6),
                "signal_set_gap_delta": round(signal_delta, 6),
                "multi_case_support": multi_support,
                "target_exact": target_exact,
                "metrics_not_worse": not_worse,
                "generalization_gate_pass": generalization_gate,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "decision": decision,
            }
        )
    return pd.DataFrame(rows)


def build_final_decision(result_summary: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    passed = result_summary[result_summary["generalization_gate_pass"]].copy()
    single = result_summary[result_summary["decision"].eq("single_support_only_not_mergeable")].copy()
    target_like_count = int(features["target_like_strict"].sum())
    if not passed.empty:
        decision = "generalized_rule_candidate_found_but_main_gate_still_closed"
        next_action = "manual_review_generalized_rule_then_full_regression"
    elif not single.empty:
        decision = "target_only_single_support_not_mergeable"
        next_action = "audit_layer3_displacement_source_for_mt5_0076_before_signal_change"
    else:
        decision = "no_viable_generalized_replacement_rule"
        next_action = "return_to_raw_source_audit_for_remaining_mt5_only_cases"
    return pd.DataFrame(
        [
            {
                "reviewed_candidates": int(len(features)),
                "same_family_opposite_candidates": int(features["same_family_opposite"].sum()),
                "target_like_strict_candidates": target_like_count,
                "rules_tested": int(len(result_summary)),
                "generalization_gate_pass_count": int(len(passed)),
                "single_support_pass_count": int(len(single)),
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "decision": decision,
                "recommended_next_action": next_action,
            }
        ]
    )


def write_report(
    features: pd.DataFrame,
    signal_summary: pd.DataFrame,
    before_after: pd.DataFrame,
    target_review: pd.DataFrame,
    result_summary: pd.DataFrame,
    final_decision: pd.DataFrame,
) -> None:
    fd = final_decision.iloc[0]
    lines = [
        "# Stage-State Layer3 Target-Only Replacement Generalization Audit",
        "",
        "## Scope",
        "",
        "- Reviews whether the successful target-only `mt5_0076` replacement can generalize.",
        "- Runs narrow full-chain variants only; no baseline signal, EA, or mapping rule is changed.",
        "",
        "## Candidate Shape",
        "",
        f"- Reviewed candidates: `{int(fd['reviewed_candidates'])}`.",
        f"- Same-family-opposite candidates: `{int(fd['same_family_opposite_candidates'])}`.",
        f"- Strict target-like candidates: `{int(fd['target_like_strict_candidates'])}`.",
        "",
        "## Rule Signal Summary",
        "",
        markdown_table(signal_summary),
        "",
        "## Rule Full-Chain Summary",
        "",
        markdown_table(before_after),
        "",
        "## Target mt5_0076 Summary",
        "",
        markdown_table(target_review),
        "",
        "## Rule Decisions",
        "",
        markdown_table(result_summary),
        "",
        "## Final Decision",
        "",
        markdown_table(final_decision),
        "",
        "## Interpretation",
        "",
        "- Wider same-family replacements still either miss the exact target or worsen the direct gap.",
        "- The strict target-like condition reproduces the `mt5_0076` improvement, but it has only one historical supporting candidate.",
        "- Single-support target-only behavior is not a safe main-signal rule.",
        "",
        "## Output Files",
        "",
        "- `layer3_target_only_generalization_candidate_features.csv`",
        "- `layer3_target_only_generalization_signal_summary.csv`",
        "- `layer3_target_only_generalization_before_after.csv`",
        "- `layer3_target_only_generalization_target_review.csv`",
        "- `layer3_target_only_generalization_rule_decisions.csv`",
        "- `layer3_target_only_generalization_final_decision.csv`",
    ]
    write_text(OUT_DIR / "layer3_target_only_replacement_generalization_review.md", "\n".join(lines))
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# stage_state_layer3_target_only_replacement_generalization_20260717",
                "",
                "Non-destructive generalization audit for the mt5_0076 target-only Layer3 replacement prototype.",
            ]
        ),
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    patch_proto_output_roots()
    for directory in [SIGNALS_ROOT, INPUTS_ROOT, DYNAMIC_ROOT, MAPPING_ROOT]:
        if directory.exists():
            shutil.rmtree(directory)

    raw, layer12, layer3, m30 = proto.load_base_tables()
    details = proto.load_rescue_details()
    rescue_rows = proto.select_rescue_rows(layer12, details)
    features = build_candidate_features(details, rescue_rows)
    export_csv(features, OUT_DIR / "layer3_target_only_generalization_candidate_features.csv")

    signal_rows: list[dict[str, object]] = []
    before_after_rows = [
        proto.scenario_stats(
            "current_stage_state_metadatafix",
            proto.BASE_DYNAMIC_DIR,
            proto.BASE_MAPPING_DIR,
            "current accepted stage-state metadatafix baseline",
        )
    ]
    target_rows = [proto.target_status("current_stage_state_metadatafix", proto.BASE_DYNAMIC_DIR, proto.BASE_MAPPING_DIR)]

    for rule in RULES:
        selected = select_rule_features(features, rule)
        layer3_proto, before_maxpos, removed = build_custom_variant(rule, layer3, rescue_rows, selected)
        stage = proto.build_stage_results(m30, layer3_proto)
        signal_dir = proto.write_signal_snapshot(
            proto.Variant(rule.name, rule.description),
            raw,
            layer12,
            layer3_proto,
            stage,
        )
        export_csv(selected, OUT_DIR / f"{rule.name}_selected_features.csv")
        export_csv(before_maxpos, OUT_DIR / f"{rule.name}_layer3_before_maxpos.csv")
        export_csv(removed, OUT_DIR / f"{rule.name}_removed_nearest_opposite_rows.csv")

        input_dir = proto.run_prepare_inputs(proto.Variant(rule.name, rule.description), signal_dir)
        dynamic_dir, mapping_dir = proto.run_dynamic_and_mapping(proto.Variant(rule.name, rule.description), input_dir)

        signal_rows.append(variant_signal_summary(rule, selected, before_maxpos, layer3_proto, removed))
        before_after_rows.append(proto.scenario_stats(rule.name, dynamic_dir, mapping_dir, rule.description))
        target_rows.append(proto.target_status(rule.name, dynamic_dir, mapping_dir))

    signal_summary = pd.DataFrame(signal_rows)
    before_after = pd.DataFrame(before_after_rows)
    target_review = pd.DataFrame(target_rows)
    result_summary = build_rule_result_summary(signal_summary, before_after, target_review)
    final_decision = build_final_decision(result_summary, features)

    export_csv(signal_summary, OUT_DIR / "layer3_target_only_generalization_signal_summary.csv")
    export_csv(before_after, OUT_DIR / "layer3_target_only_generalization_before_after.csv")
    export_csv(target_review, OUT_DIR / "layer3_target_only_generalization_target_review.csv")
    export_csv(result_summary, OUT_DIR / "layer3_target_only_generalization_rule_decisions.csv")
    export_csv(final_decision, OUT_DIR / "layer3_target_only_generalization_final_decision.csv")
    write_report(features, signal_summary, before_after, target_review, result_summary, final_decision)
    print((OUT_DIR / "layer3_target_only_replacement_generalization_review.md").read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
