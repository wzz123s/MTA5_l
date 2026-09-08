# -*- coding: utf-8 -*-
"""Feasibility audit for targeted signal prototypes.

This is a diagnostic-only gate after targeted raw signal replay. It ranks the
minimal prototype surfaces for the four remaining MT5-only/directional cases
without changing Python signals, MT5/EA behavior, dynamic risk, or mapping.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"
SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
RAW_REPLAY_DIR = VALIDATION_DIR / "stage_state_targeted_raw_signal_replay_20260717"
OUT_DIR = VALIDATION_DIR / "stage_state_targeted_signal_prototype_feasibility_20260717"


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


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL", "SHORT", "-1"}:
        return "SELL"
    if text in {"L", "B", "BUY", "LONG", "1"}:
        return "BUY"
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


def trigger_from_variant(value: object) -> str:
    text = str(value).strip().lower()
    if "slot1" in text or "replace" in text or "rescue" in text:
        return "M15 SLOT1"
    return "M30 CLOSE"


def prep_signal_table(frame: pd.DataFrame, source_table: str) -> pd.DataFrame:
    out = frame.copy()
    out["source_table"] = source_table
    out["dt"] = out["date"].map(parse_dt)
    out["dir_norm"] = out["dir"].map(normalize_dir)
    out["mode_family"] = out["mode"].map(mode_family)
    if "trigger" in out.columns:
        trigger = out["trigger"].fillna("").astype(str).str.strip()
        inferred = out.get("variant", pd.Series("", index=out.index)).map(trigger_from_variant)
        out["trigger_family"] = trigger.where(trigger.ne(""), inferred)
    else:
        out["trigger_family"] = out.get("variant", pd.Series("", index=out.index)).map(trigger_from_variant)
    out["profit"] = pd.to_numeric(out.get("pnl", pd.Series(0.0, index=out.index)), errors="coerce")
    if "spec_pass" in out.columns:
        out["spec_pass_bool"] = out["spec_pass"].astype(str).str.lower().isin({"true", "1", "yes"})
    else:
        out["spec_pass_bool"] = False
    return out


def load_signal_chain() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = prep_signal_table(read_csv(SIGNAL_DIR / "raw_candidates.csv"), "python_raw_candidates")
    raw["trigger_family"] = "M30 CLOSE"
    layer12 = prep_signal_table(read_csv(SIGNAL_DIR / "候选信号_Layer1_Layer2通过.csv"), "python_layer12_pass")
    layer3 = prep_signal_table(read_csv(SIGNAL_DIR / "最终信号_Layer3入选.csv"), "python_layer3_selected")
    return raw, layer12, layer3


def load_mt5_unique() -> pd.DataFrame:
    mt5 = read_csv(DYNAMIC_DIR / "mt5_ledger_unique_signals.csv").copy()
    mt5["mt5_trade_id"] = [f"mt5_{i + 1:04d}" for i in range(len(mt5))]
    mt5["dt"] = mt5["signal_anchor_time"].map(parse_dt) + pd.Timedelta(minutes=90)
    mt5["dir_norm"] = mt5["dir"].map(normalize_dir)
    mt5["mode_family"] = mt5["mode_family"].map(mode_family)
    mt5["trigger_family"] = mt5["trigger_family"].astype(str)
    mt5["profit"] = pd.to_numeric(mt5["net_profit"], errors="coerce")
    return mt5


def key_set(frame: pd.DataFrame) -> set[tuple[pd.Timestamp, str, str, str]]:
    return set(zip(frame["dt"], frame["dir_norm"], frame["mode_family"], frame["trigger_family"]))


def same_key_exists(keys: set[tuple[pd.Timestamp, str, str, str]], row: pd.Series, trigger: str | None = None) -> bool:
    return (
        row["dt"],
        row["dir_norm"],
        row["mode_family"],
        trigger or row["trigger_family"],
    ) in keys


def build_layer3_displacement_details(layer12: pd.DataFrame, layer3: pd.DataFrame) -> pd.DataFrame:
    layer3_keys = key_set(layer3)
    rows: list[dict[str, object]] = []
    source = layer12[
        (layer12["trigger_family"] == "M15 SLOT1")
        & (layer12["mode_family"] == "post_n")
    ].copy()
    for _, row in source.iterrows():
        if same_key_exists(layer3_keys, row):
            continue
        nearby = layer3[
            (layer3["dt"].sub(row["dt"]).abs() <= pd.Timedelta(minutes=1440))
            & (layer3["dir_norm"] != row["dir_norm"])
        ].copy()
        if nearby.empty:
            continue
        nearby["abs_minutes"] = nearby["dt"].sub(row["dt"]).dt.total_seconds().abs() / 60.0
        nearest = nearby.sort_values(["abs_minutes", "dt"]).iloc[0]
        rows.append(
            {
                "candidate_rule": "layer3_m15_slot1_postn_same_family_rescue",
                "row_time": row["dt"],
                "dir_norm": row["dir_norm"],
                "trigger_family": row["trigger_family"],
                "mode_family": row["mode_family"],
                "mode": row.get("mode", ""),
                "variant": row.get("variant", ""),
                "source_profit": row.get("profit", ""),
                "nearest_opposite_layer3_time": nearest["dt"],
                "nearest_opposite_layer3_dir": nearest["dir_norm"],
                "nearest_opposite_layer3_trigger": nearest["trigger_family"],
                "nearest_opposite_layer3_mode": nearest["mode_family"],
                "nearest_opposite_abs_minutes": nearest["abs_minutes"],
                "blast_risk_bucket": "medium",
            }
        )
    return pd.DataFrame(rows)


def build_m30_parent_transform_details(raw: pd.DataFrame, layer12: pd.DataFrame) -> pd.DataFrame:
    layer12_keys = key_set(layer12)
    source = raw[
        (raw["spec_pass_bool"])
        & (raw["mode_family"] == "post_n")
        & (raw["trigger_family"] == "M30 CLOSE")
    ].copy()
    rows: list[dict[str, object]] = []
    for _, row in source.iterrows():
        has_m15 = same_key_exists(layer12_keys, row, "M15 SLOT1")
        has_m30 = same_key_exists(layer12_keys, row, "M30 CLOSE")
        if not has_m15 or has_m30:
            continue
        rows.append(
            {
                "candidate_rule": "preserve_m30_parent_before_slot1_replace",
                "row_time": row["dt"],
                "dir_norm": row["dir_norm"],
                "trigger_family": "M30 CLOSE",
                "mode_family": row["mode_family"],
                "mode": row.get("mode", ""),
                "variant": row.get("variant", ""),
                "source_profit": row.get("profit", ""),
                "spec_pass": row.get("spec_pass", ""),
                "spec_reason": row.get("spec_reason", ""),
                "blast_risk_bucket": "high",
            }
        )
    return pd.DataFrame(rows)


def raw_equivalent_exists(raw: pd.DataFrame, row: pd.Series, window_minutes: int = 60) -> bool:
    diff = raw["dt"].sub(row["dt"]).abs().dt.total_seconds() / 60.0
    same_dir = raw["dir_norm"] == row["dir_norm"]
    same_mode = raw["mode_family"] == row["mode_family"]
    if row["trigger_family"] == "M15 SLOT1":
        matched = raw[same_dir & same_mode & (diff <= window_minutes)]
    else:
        matched = raw[
            same_dir
            & same_mode
            & (raw["trigger_family"] == row["trigger_family"])
            & (diff <= window_minutes)
        ]
    return not matched.empty


def build_mt5_raw_absent_details(raw: pd.DataFrame, mt5: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, row in mt5.iterrows():
        if raw_equivalent_exists(raw, row, 60):
            continue
        rows.append(
            {
                "candidate_rule": "audit_mt5_signal_without_python_raw_equivalent",
                "row_id": row["mt5_trade_id"],
                "row_time": row["dt"],
                "dir_norm": row["dir_norm"],
                "trigger_family": row["trigger_family"],
                "mode_family": row["mode_family"],
                "mode": row.get("signal_src", ""),
                "variant": "",
                "source_profit": row.get("profit", ""),
                "blast_risk_bucket": "unknown",
            }
        )
    return pd.DataFrame(rows)


def build_rule_summary(
    cases: pd.DataFrame,
    layer3_details: pd.DataFrame,
    parent_details: pd.DataFrame,
    raw_absent_details: pd.DataFrame,
) -> pd.DataFrame:
    target_abs = {
        str(row["trade_id"]): float(row["abs_gap_effect_$"])
        for _, row in cases.iterrows()
    }

    def count_raw_abs(trigger: str, mode: str) -> int:
        if raw_absent_details.empty:
            return 0
        return int(
            (
                (raw_absent_details["trigger_family"] == trigger)
                & (raw_absent_details["mode_family"] == mode)
            ).sum()
        )

    rows = [
        {
            "candidate_rule": "layer3_m15_slot1_postn_same_family_rescue",
            "targets": "mt5_0076",
            "target_abs_gap_sum": target_abs.get("mt5_0076", 0.0),
            "historical_blast_radius_rows": int(len(layer3_details)),
            "data_evidence": "exact raw and Layer1/2 same-family exist; Layer3/executed missing; nearby opposite selected",
            "blast_risk_bucket": "medium",
            "prototype_decision": "select_first_non_destructive_full_chain_prototype",
            "decision_reason": "Smallest data-backed rule surface among viable candidates; no raw generation invention required.",
            "recommended_next_step": "prototype_layer3_m15_slot1_postn_same_family_rescue",
            "prototype_rank": 1,
        },
        {
            "candidate_rule": "preserve_m30_parent_before_slot1_replace",
            "targets": "mt5_0044",
            "target_abs_gap_sum": target_abs.get("mt5_0044", 0.0),
            "historical_blast_radius_rows": int(len(parent_details)),
            "data_evidence": "M30 CLOSE raw parent exists but Layer1/2 exact same time is transformed to M15 SLOT1",
            "blast_risk_bucket": "high",
            "prototype_decision": "defer_high_blast_radius",
            "decision_reason": "The transform surface is broad; run after the smaller Layer3 prototype or narrow it further.",
            "recommended_next_step": "narrow_trigger_family_transform_audit",
            "prototype_rank": 2,
        },
        {
            "candidate_rule": "audit_m15_slot1_postn_raw_absent",
            "targets": "mt5_0067",
            "target_abs_gap_sum": target_abs.get("mt5_0067", 0.0),
            "historical_blast_radius_rows": count_raw_abs("M15 SLOT1", "post_n"),
            "data_evidence": "MT5 has M15 SLOT1 post_n, but Python raw equivalent is absent within 60 minutes",
            "blast_risk_bucket": "unknown",
            "prototype_decision": "source_audit_before_prototype",
            "decision_reason": "A prototype would need to create raw signals not present in Python; inspect raw-generation source first.",
            "recommended_next_step": "audit_python_raw_generation_vs_mt5_m15_source",
            "prototype_rank": 3,
        },
        {
            "candidate_rule": "audit_m30_close_postn_raw_absent",
            "targets": "mt5_0026",
            "target_abs_gap_sum": target_abs.get("mt5_0026", 0.0),
            "historical_blast_radius_rows": count_raw_abs("M30 CLOSE", "post_n"),
            "data_evidence": "MT5 has M30 CLOSE post_n, but Python has no raw equivalent nearby",
            "blast_risk_bucket": "unknown",
            "prototype_decision": "source_audit_before_prototype",
            "decision_reason": "Only one current MT5 M30 post_n no-raw row is visible, but no Python raw evidence exists to mutate safely.",
            "recommended_next_step": "audit_python_raw_generation_vs_mt5_m30_source",
            "prototype_rank": 4,
        },
    ]
    return pd.DataFrame(rows)


def target_rule_for_loss_point(loss_point: str) -> str:
    mapping = {
        "layer3_displaced_by_nearby_opposite_selection": "layer3_m15_slot1_postn_same_family_rescue",
        "raw_absent_nearby_opposite_selected": "audit_m15_slot1_postn_raw_absent",
        "layer12_trigger_family_drift_after_raw_parent": "preserve_m30_parent_before_slot1_replace",
        "raw_absent_for_mt5_signal": "audit_m30_close_postn_raw_absent",
    }
    return mapping.get(loss_point, "unknown")


def build_case_feasibility(cases: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    by_rule = summary.set_index("candidate_rule").to_dict("index")
    rows: list[dict[str, object]] = []
    for _, row in cases.iterrows():
        rule = target_rule_for_loss_point(str(row["raw_chain_loss_point"]))
        rule_info = by_rule.get(rule, {})
        rows.append(
            {
                "target_case_id": row["target_case_id"],
                "trade_id": row["trade_id"],
                "target_time": row["target_time"],
                "dir_norm": row["dir_norm"],
                "trigger_family": row["trigger_family"],
                "mode_family": row["mode_family"],
                "abs_gap_effect_$": row["abs_gap_effect_$"],
                "raw_chain_loss_point": row["raw_chain_loss_point"],
                "candidate_rule": rule,
                "raw_exact_equivalent_count": row["raw_exact_equivalent_count"],
                "layer12_exact_same_family_count": row["layer12_exact_same_family_count"],
                "layer3_exact_same_family_count": row["layer3_exact_same_family_count"],
                "dynamic_exact_same_family_count": row["dynamic_exact_same_family_count"],
                "historical_blast_radius_rows": rule_info.get("historical_blast_radius_rows", ""),
                "blast_risk_bucket": rule_info.get("blast_risk_bucket", ""),
                "prototype_decision": rule_info.get("prototype_decision", ""),
                "recommended_next_step": rule_info.get("recommended_next_step", ""),
                "case_feasibility_note": rule_info.get("decision_reason", ""),
            }
        )
    return pd.DataFrame(rows)


def simple_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_No rows._"
    use = frame.loc[:, columns].copy()
    return use.to_markdown(index=False)


def build_decision(summary: pd.DataFrame, cases: pd.DataFrame) -> pd.DataFrame:
    selected = summary.sort_values("prototype_rank").iloc[0]
    total_abs = pd.to_numeric(cases["abs_gap_effect_$"], errors="coerce").fillna(0.0).sum()
    selected_abs = float(selected["target_abs_gap_sum"])
    return pd.DataFrame(
        [
            {
                "reviewed_targets": int(len(cases)),
                "reviewed_abs_gap": float(total_abs),
                "selected_next_prototype": selected["recommended_next_step"],
                "selected_candidate_rule": selected["candidate_rule"],
                "selected_targets": selected["targets"],
                "selected_target_abs_gap": selected_abs,
                "selected_abs_gap_share_pct": float(selected_abs / total_abs * 100.0) if total_abs else 0.0,
                "selected_historical_blast_radius_rows": int(selected["historical_blast_radius_rows"]),
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "targeted_full_chain_prototype_required": True,
                "merge_gate_pass": False,
                "decision": "run_selected_layer3_prototype_next",
            }
        ]
    )


def build_report(
    cases: pd.DataFrame,
    summary: pd.DataFrame,
    decision: pd.DataFrame,
    layer3_details: pd.DataFrame,
    parent_details: pd.DataFrame,
    raw_absent_details: pd.DataFrame,
) -> str:
    d = decision.iloc[0]
    lines = [
        "# Stage-State Targeted Signal Prototype Feasibility Audit",
        "",
        "## Scope",
        "",
        "- Reviews only the 4 targets from targeted raw signal replay.",
        "- Ranks prototype surfaces by evidence and blast radius.",
        "- Does not change Python signals, EA behavior, mapping, dynamic lots, or fund curves.",
        "",
        "## Decision",
        "",
        f"- Reviewed targets: `{int(d['reviewed_targets'])}`.",
        f"- Reviewed abs gap: `{float(d['reviewed_abs_gap']):.6f}`.",
        f"- Selected next prototype: `{d['selected_next_prototype']}`.",
        f"- Selected target: `{d['selected_targets']}`.",
        f"- Selected target abs gap: `{float(d['selected_target_abs_gap']):.6f}` "
        f"({float(d['selected_abs_gap_share_pct']):.2f}% of reviewed abs gap).",
        f"- Selected historical blast radius rows: `{int(d['selected_historical_blast_radius_rows'])}`.",
        "- `main_signal_change_gate_open`: `False`.",
        "- `ea_behavior_gate_open`: `False`.",
        "- `mapping_change_gate_open`: `False`.",
        "- `merge_gate_pass`: `False`.",
        "",
        "## Candidate Rule Ranking",
        "",
        simple_table(
            summary,
            [
                "prototype_rank",
                "candidate_rule",
                "targets",
                "target_abs_gap_sum",
                "historical_blast_radius_rows",
                "blast_risk_bucket",
                "prototype_decision",
            ],
        ),
        "",
        "## Target Feasibility",
        "",
        simple_table(
            cases,
            [
                "trade_id",
                "raw_chain_loss_point",
                "candidate_rule",
                "abs_gap_effect_$",
                "historical_blast_radius_rows",
                "prototype_decision",
            ],
        ),
        "",
        "## Blast-Radius Checks",
        "",
        f"- Layer3 M15 SLOT1 post_n displacement rows: `{len(layer3_details)}`.",
        f"- M30 parent transformed to M15 SLOT1 rows: `{len(parent_details)}`.",
        f"- MT5 unique rows without Python raw equivalent within 60 minutes: `{len(raw_absent_details)}`.",
        "",
        "## Interpretation",
        "",
        "- The selected Layer3 prototype is the smallest data-backed candidate because Python already has exact raw and Layer1/2 evidence for `mt5_0076`.",
        "- The M30 parent-preserve idea explains `mt5_0044`, but its current blast radius is high and should be narrowed before a full-chain test.",
        "- The raw-absent cases (`mt5_0067`, `mt5_0026`) are not safe signal prototypes yet because Python has no raw row to mutate at the target time.",
        "",
        "## Output Files",
        "",
        "- `targeted_signal_prototype_feasibility_case_review.csv`",
        "- `targeted_signal_prototype_candidate_summary.csv`",
        "- `targeted_signal_prototype_blast_radius_details.csv`",
        "- `targeted_signal_prototype_decision.csv`",
    ]
    return "\n".join(lines)


def write_readme() -> None:
    lines = [
        "# Stage-State Targeted Signal Prototype Feasibility 20260717",
        "",
        "Generated by `review_stage_state_targeted_signal_prototype_feasibility_20260717.py`.",
        "",
        "## Files",
        "",
        "- `targeted_signal_prototype_feasibility_review.md`",
        "- `targeted_signal_prototype_feasibility_case_review.csv`",
        "- `targeted_signal_prototype_candidate_summary.csv`",
        "- `targeted_signal_prototype_blast_radius_details.csv`",
        "- `targeted_signal_prototype_decision.csv`",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = read_csv(RAW_REPLAY_DIR / "targeted_raw_signal_replay_case_review.csv")
    raw, layer12, layer3 = load_signal_chain()
    mt5 = load_mt5_unique()

    layer3_details = build_layer3_displacement_details(layer12, layer3)
    parent_details = build_m30_parent_transform_details(raw, layer12)
    raw_absent_details = build_mt5_raw_absent_details(raw, mt5)
    blast_details = pd.concat(
        [layer3_details, parent_details, raw_absent_details],
        ignore_index=True,
        sort=False,
    )

    summary = build_rule_summary(cases, layer3_details, parent_details, raw_absent_details)
    case_review = build_case_feasibility(cases, summary)
    decision = build_decision(summary, cases)

    export_csv(case_review, OUT_DIR / "targeted_signal_prototype_feasibility_case_review.csv")
    export_csv(summary, OUT_DIR / "targeted_signal_prototype_candidate_summary.csv")
    export_csv(blast_details, OUT_DIR / "targeted_signal_prototype_blast_radius_details.csv")
    export_csv(decision, OUT_DIR / "targeted_signal_prototype_decision.csv")

    report = build_report(case_review, summary, decision, layer3_details, parent_details, raw_absent_details)
    write_text(OUT_DIR / "targeted_signal_prototype_feasibility_review.md", report)
    write_readme()
    print(report)


if __name__ == "__main__":
    main()
