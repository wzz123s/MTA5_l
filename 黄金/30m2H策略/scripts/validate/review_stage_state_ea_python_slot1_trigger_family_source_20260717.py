# -*- coding: utf-8 -*-
"""Source audit for EA/Python M15 SLOT1 trigger-family drift.

Diagnostic-only:
- no EA edits
- no Python signal edits
- no dynamic-risk edits
- no mapping-rule edits
"""

from __future__ import annotations


from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

NEAR_TRIGGER_DIR = VALIDATION_DIR / "stage_state_m15_slot1_near_trigger_family_drift_audit_20260717"
NO_CANDIDATE_DIR = VALIDATION_DIR / "stage_state_m15_slot1_no_candidate_source_gap_audit_20260717"
OUT_DIR = VALIDATION_DIR / "stage_state_ea_python_slot1_trigger_family_source_audit_20260717"

CASE_VERDICT = NEAR_TRIGGER_DIR / "m15_slot1_near_trigger_case_verdict.csv"
TIMELINE = NEAR_TRIGGER_DIR / "m15_slot1_near_trigger_timeline_pm120.csv"
CANDIDATE_SAMPLES = NO_CANDIDATE_DIR / "m15_slot1_no_candidate_candidate_samples.csv"

EA_SOURCE = ROOT / "auto_trade" / "30m2H_Strategy_EA.mq5"
PY_M15 = ROOT / "scripts" / "_m15_early_entry_test.py"
PY_COMBO = ROOT / "scripts" / "_m15_h2_combo_test.py"
PY_REBUILD = STRATEGY_DIR / "scripts" / "signals" / "rebuild_python_mt5_shift90.py"
PY_DIRECTION = ROOT / "processing" / "direction.py"

TARGET_IDS = ["mt5_0052", "mt5_0054", "mt5_0067", "mt5_0068", "mt5_0069"]


@dataclass(frozen=True)
class SourceHit:
    hit_id: str
    side: str
    component: str
    path: Path
    start_line: int
    end_line: int
    evidence_summary: str
    role: str


SOURCE_HITS: tuple[SourceHit, ...] = (
    SourceHit(
        "ea_detect_pre_cross",
        "EA",
        "DetectPreCross",
        EA_SOURCE,
        2309,
        2333,
        "EA pre_cross excludes true SMA5/SMA13 crosses and only returns pre_cross when close crosses SMA13 while SMA5 stays on the old side.",
        "Defines the EA pre_cross branch that can outrank post_n inside TryM15EarlyEntry.",
    ),
    SourceHit(
        "ea_update_raw_postn_state",
        "EA",
        "UpdatePostNState",
        EA_SOURCE,
        2339,
        2390,
        "EA keeps a raw PythonSMMA post_n counter, but this is only logged in the M15 candidate line for this branch.",
        "Separates raw post_n state from the merged counter actually used by M15 SLOT1 post_n classification.",
    ),
    SourceHit(
        "ea_update_merged_postn_state",
        "EA",
        "UpdateMergedPostNState",
        EA_SOURCE,
        2396,
        2453,
        "EA updates g_merged_post_n_counter from M30MergedDirectionCodeLastCompleted; same merged direction increments, merged flip resets to +/-1.",
        "Primary EA counter source for M15 SLOT1 post_n labels.",
    ),
    SourceHit(
        "ea_try_m15_classification",
        "EA",
        "TryM15EarlyEntry classification",
        EA_SOURCE,
        2903,
        2933,
        "EA classifies M15 SLOT1 in priority order: pre_cross, cross, then post_n from g_merged_post_n_counter.",
        "Explains why EA can emit post_n at the exact SLOT1 anchor when pre_cross/cross conditions are false at EA runtime.",
    ),
    SourceHit(
        "ea_try_m15_candidate_log",
        "EA",
        "TryM15EarlyEntry candidate logging",
        EA_SOURCE,
        2944,
        2951,
        "EA logs mode, anchor, raw post_n counter, and merged post_n counter in M15 Candidate events.",
        "Connects source logic to the extracted EA log evidence.",
    ),
    SourceHit(
        "ea_try_m15_stop_spec_tag",
        "EA",
        "TryM15EarlyEntry stop/spec/tag",
        EA_SOURCE,
        2976,
        3047,
        "EA chooses stop logic by the already selected trigger family, checks StopSpec, then only appends _replace_or_rescue.",
        "Rules out StopSpec/tagging as the creator of a post_n label.",
    ),
    SourceHit(
        "ea_m30_strict_postn_veto",
        "EA",
        "M30 close strict post_n veto",
        EA_SOURCE,
        3514,
        3529,
        "EA strict merged-post veto is in M30 CLOSE candidate handling, not the M15 SLOT1 branch audited here.",
        "Prevents over-attributing the M30-only strict veto to SLOT1 label drift.",
    ),
    SourceHit(
        "py_combo_candidate_frames",
        "Python",
        "build_candidate_frames",
        PY_COMBO,
        77,
        85,
        "Python raw candidates are collected separately as pre_cross, cross, and post_n, then accepted candidates are filtered by spec_pass.",
        "Defines the raw/Layer1/2 trigger-family input set before SLOT1 replacement/rescue.",
    ),
    SourceHit(
        "py_collect_pre_cross",
        "Python",
        "collect_pre_cross_candidates",
        PY_M15,
        118,
        159,
        "Python pre_cross skips direction good/bad, then labels accepted rows with mode pre_cross.",
        "Defines Python pre_cross family labels.",
    ),
    SourceHit(
        "py_collect_cross",
        "Python",
        "collect_cross_candidates",
        PY_M15,
        162,
        194,
        "Python cross requires direction good/bad and labels accepted rows with mode cross.",
        "Defines Python cross family labels.",
    ),
    SourceHit(
        "py_collect_postn",
        "Python",
        "collect_post_candidates",
        PY_M15,
        197,
        228,
        "Python post_n uses merged_post_cross_n and labels rows as post_nN.",
        "Defines Python post_n family labels and its dependence on the merged counter column.",
    ),
    SourceHit(
        "py_dedupe_priority",
        "Python",
        "dedupe_anchor priority",
        PY_M15,
        231,
        246,
        "Python dedupe priority is pre_cross first, cross second, post_n last for the same anchor and direction.",
        "Explains why a same-anchor cross/pre_cross can suppress a Python post_n candidate.",
    ),
    SourceHit(
        "py_recalc_preserves_mode",
        "Python",
        "recalc_trade",
        PY_M15,
        341,
        353,
        "Python recalc_trade changes entry/stop/spec/variant but leaves the original mode untouched.",
        "Shows SLOT1 replacement/rescue does not relabel cross/pre_cross to post_n.",
    ),
    SourceHit(
        "py_replace_preserves_mode",
        "Python",
        "apply_replace_variant",
        PY_M15,
        380,
        410,
        "Python SLOT1 replacement copies the original trade row and calls recalc_trade without changing mode.",
        "Primary Python source for the relabel gap.",
    ),
    SourceHit(
        "py_rescue_preserves_mode",
        "Python",
        "build_rescued_trades",
        PY_M15,
        413,
        434,
        "Python runtime rescue copies the rejected raw trade and calls recalc_trade without changing mode.",
        "Shows runtime rescue also preserves raw trigger-family labels.",
    ),
    SourceHit(
        "py_rebuild_slot1_pipeline",
        "Python",
        "rebuild_python_mt5_shift90 SLOT1 pipeline",
        PY_REBUILD,
        222,
        249,
        "Python-MT5 pipeline applies ea_slot1_replace to accepted rows and ea_slot1_runtime_rescue to rejected raw rows, then dedupes.",
        "Connects helper behavior to the current Python-MT5 signal build.",
    ),
    SourceHit(
        "py_direction_counter_semantics",
        "Python",
        "add_pre_cross_and_counter",
        PY_DIRECTION,
        110,
        148,
        "Python base direction/counter logic separates cross/pre_cross and post-cross counter semantics.",
        "Supports the mt5_0067 base sequence reset classification.",
    ),
)


CASE_SOURCE_MAP: dict[str, tuple[str, ...]] = {
    "python_relabel_gap": (
        "ea_try_m15_classification",
        "ea_try_m15_candidate_log",
        "ea_try_m15_stop_spec_tag",
        "py_combo_candidate_frames",
        "py_collect_cross",
        "py_collect_pre_cross",
        "py_replace_preserves_mode",
        "py_rescue_preserves_mode",
        "py_rebuild_slot1_pipeline",
    ),
    "base_sequence_reset_gap": (
        "ea_update_merged_postn_state",
        "ea_try_m15_classification",
        "ea_try_m15_candidate_log",
        "py_collect_cross",
        "py_collect_postn",
        "py_direction_counter_semantics",
    ),
    "stopspec_rescue_path_gap": (
        "ea_try_m15_stop_spec_tag",
        "py_recalc_preserves_mode",
        "py_replace_preserves_mode",
        "py_rescue_preserves_mode",
    ),
    "insufficient_code_evidence": (
        "ea_try_m15_classification",
        "py_combo_candidate_frames",
    ),
}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_md(lines: Iterable[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8-sig")


def read_text_lines(path: Path) -> list[str]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding).splitlines()
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace").splitlines()


def code_snippet(path: Path, start_line: int, end_line: int) -> str:
    lines = read_text_lines(path)
    start = max(start_line - 1, 0)
    end = min(end_line, len(lines))
    return "\n".join(f"{idx + 1}: {lines[idx].rstrip()}" for idx in range(start, end))


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def safe_float(value: object) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return float("nan")
    return float(parsed)


def safe_int(value: object) -> int:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return 0
    return int(parsed)


def semijoin(values: Iterable[object], limit: int = 16) -> str:
    out: list[str] = []
    for value in values:
        if pd.isna(value):
            continue
        text = str(value).strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return ";".join(out)


def build_code_hits() -> pd.DataFrame:
    rows = []
    for hit in SOURCE_HITS:
        rows.append(
            {
                "hit_id": hit.hit_id,
                "side": hit.side,
                "component": hit.component,
                "file": str(hit.path.relative_to(ROOT)),
                "start_line": hit.start_line,
                "end_line": hit.end_line,
                "evidence_summary": hit.evidence_summary,
                "role": hit.role,
                "snippet": code_snippet(hit.path, hit.start_line, hit.end_line),
            }
        )
    return pd.DataFrame(rows)


def classify_case(row: pd.Series) -> tuple[str, str, str]:
    previous = str(row.get("primary_classification", ""))
    layer12_nonpostn = safe_int(row.get("layer12_near_same_dir_nonpostn_count"))
    layer12_postn = safe_int(row.get("layer12_near_same_dir_postn_count"))
    raw_nonpostn = safe_int(row.get("raw_near_same_dir_nonpostn_count"))
    raw_postn = safe_int(row.get("raw_near_same_dir_postn_count"))
    raw_day_postn = safe_int(row.get("raw_day_same_dir_postn_count"))
    ea_exact = safe_int(row.get("ea_exact_event_count"))

    if previous == "trigger_family_label_gap" and ea_exact > 0 and layer12_nonpostn > 0 and layer12_postn == 0:
        return (
            "python_relabel_gap",
            "ea_label_drift;python_relabel_gap",
            "EA exact SLOT1 runtime classifies post_n from g_merged_post_n_counter; Python SLOT1 replace/rescue preserves the nearby raw/Layer1/2 cross/pre_cross mode and does not relabel it to EA runtime post_n.",
        )
    if previous == "raw_sequence_gap" and ea_exact > 0 and raw_nonpostn > 0 and raw_postn == 0 and raw_day_postn > 0:
        return (
            "base_sequence_reset_gap",
            "ea_label_drift;base_sequence_reset_gap",
            "EA exact SLOT1 sees merged post_n at the anchor, while Python raw near window is still cross/pre_cross and same-direction post_n appears only later in the base sequence.",
        )
    if "rescue" in str(row.get("mt5_signal_src", "")).lower():
        return (
            "insufficient_code_evidence",
            "stopspec_rescue_path_gap_not_supported",
            "The EA rescue suffix is appended after trigger-family selection, and Python rescue preserves original mode; StopSpec/tagging does not explain post_n creation for this sample.",
        )
    return (
        "insufficient_code_evidence",
        "insufficient_code_evidence",
        "Available timeline and source hits do not isolate a repeated trigger-family source.",
    )


def timeline_summary(timeline: pd.DataFrame, mt5_trade_id: str) -> dict[str, object]:
    rows = timeline[timeline["mt5_trade_id"].eq(mt5_trade_id)].copy()
    ea_rows = rows[rows["source"].eq("ea_log")]
    py_rows = rows[rows["source"].eq("python")]
    target_ea_rows = rows[rows.get("is_target_ea_signal", False).map(boolish)] if "is_target_ea_signal" in rows.columns else rows.iloc[0:0]
    py_near_nonpostn = py_rows[
        py_rows["same_dir"].map(boolish)
        & ~py_rows["mode_family"].astype(str).eq("post_n")
    ]
    py_near_postn = py_rows[
        py_rows["same_dir"].map(boolish)
        & py_rows["mode_family"].astype(str).eq("post_n")
    ]
    return {
        "timeline_evidence_rows": int(len(rows)),
        "timeline_target_ea_rows": int(len(target_ea_rows)),
        "timeline_python_near_nonpostn_rows": int(len(py_near_nonpostn)),
        "timeline_python_near_postn_rows": int(len(py_near_postn)),
        "timeline_ea_modes": semijoin(ea_rows.get("mode", pd.Series(dtype=str)).tolist()),
        "timeline_python_modes": semijoin(py_rows.get("mode", pd.Series(dtype=str)).tolist()),
    }


def candidate_sample_summary(candidate_samples: pd.DataFrame, mt5_trade_id: str) -> dict[str, object]:
    rows = candidate_samples[candidate_samples["mt5_trade_id"].eq(mt5_trade_id)].copy()
    if rows.empty:
        return {
            "candidate_sample_rows": 0,
            "candidate_sample_modes": "",
            "candidate_sample_layers": "",
        }
    return {
        "candidate_sample_rows": int(len(rows)),
        "candidate_sample_modes": semijoin(rows.get("mode", pd.Series(dtype=str)).tolist()),
        "candidate_sample_layers": semijoin(rows.get("layer", pd.Series(dtype=str)).tolist()),
    }


def build_case_review(
    case_verdict: pd.DataFrame,
    timeline: pd.DataFrame,
    candidate_samples: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    hits_by_id = {hit.hit_id: hit for hit in SOURCE_HITS}
    for _, row in case_verdict[case_verdict["mt5_trade_id"].isin(TARGET_IDS)].iterrows():
        primary, secondary, reason = classify_case(row)
        source_hit_ids = CASE_SOURCE_MAP.get(primary, CASE_SOURCE_MAP["insufficient_code_evidence"])
        ea_hit_ids = [hit_id for hit_id in source_hit_ids if hits_by_id[hit_id].side == "EA"]
        py_hit_ids = [hit_id for hit_id in source_hit_ids if hits_by_id[hit_id].side == "Python"]

        out = {
            "mt5_trade_id": row.get("mt5_trade_id", ""),
            "signal_anchor_time": row.get("signal_anchor_time", ""),
            "aligned_time_plus90": row.get("aligned_time_plus90", ""),
            "dir_norm": row.get("dir_norm", ""),
            "mt5_signal_src": row.get("mt5_signal_src", ""),
            "mt5_mode_n": row.get("mt5_mode_n", ""),
            "mt5_net_profit": safe_float(row.get("mt5_net_profit")),
            "previous_primary_classification": row.get("primary_classification", ""),
            "source_primary_classification": primary,
            "source_secondary_classifications": secondary,
            "source_classification_reason": reason,
            "ea_source_hits": semijoin(ea_hit_ids),
            "python_source_hits": semijoin(py_hit_ids),
            "ea_exact_event_count": safe_int(row.get("ea_exact_event_count")),
            "ea_exact_event_kinds": row.get("ea_exact_event_kinds", ""),
            "ea_exact_post_n_counter": row.get("ea_exact_post_n_counter", ""),
            "ea_exact_merged_post_n_counter": row.get("ea_exact_merged_post_n_counter", ""),
            "raw_near_same_dir_nonpostn_count": safe_int(row.get("raw_near_same_dir_nonpostn_count")),
            "raw_near_same_dir_postn_count": safe_int(row.get("raw_near_same_dir_postn_count")),
            "raw_day_same_dir_postn_count": safe_int(row.get("raw_day_same_dir_postn_count")),
            "layer12_near_same_dir_nonpostn_count": safe_int(row.get("layer12_near_same_dir_nonpostn_count")),
            "layer12_near_same_dir_postn_count": safe_int(row.get("layer12_near_same_dir_postn_count")),
            "layer12_nearest_near_nonpostn_time": row.get("layer12_nearest_near_nonpostn_time", ""),
            "layer12_nearest_near_nonpostn_mode": row.get("layer12_nearest_near_nonpostn_mode", ""),
            "raw_nearest_near_nonpostn_time": row.get("raw_nearest_near_nonpostn_time", ""),
            "raw_nearest_near_nonpostn_mode": row.get("raw_nearest_near_nonpostn_mode", ""),
            "raw_nearest_day_postn_time": row.get("raw_nearest_day_postn_time", ""),
            "raw_nearest_day_postn_mode": row.get("raw_nearest_day_postn_mode", ""),
            "mapping_status": row.get("mapping_status", ""),
            "mapping_match_tier": row.get("mapping_match_tier", ""),
            "mapping_is_reliable_tier": row.get("mapping_is_reliable_tier", ""),
            "mapping_py_date": row.get("mapping_py_date", ""),
            "mapping_py_mode": row.get("mapping_py_mode", ""),
            "stopspec_rescue_path_supported": False,
            "prototype_gate_open": False,
            "main_signal_change_gate_open": False,
            "ea_behavior_gate_open": False,
            "mapping_change_gate_open": False,
            "merge_gate_pass": False,
        }
        out.update(timeline_summary(timeline, str(row.get("mt5_trade_id", ""))))
        out.update(candidate_sample_summary(candidate_samples, str(row.get("mt5_trade_id", ""))))
        rows.append(out)

    return pd.DataFrame(rows)


def build_case_code_map(case_review: pd.DataFrame, code_hits: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, case in case_review.iterrows():
        hit_ids = []
        hit_ids.extend(str(case.get("ea_source_hits", "")).split(";"))
        hit_ids.extend(str(case.get("python_source_hits", "")).split(";"))
        for hit_id in [hit_id for hit_id in hit_ids if hit_id]:
            hit = code_hits[code_hits["hit_id"].eq(hit_id)]
            if hit.empty:
                continue
            h = hit.iloc[0]
            rows.append(
                {
                    "mt5_trade_id": case["mt5_trade_id"],
                    "source_primary_classification": case["source_primary_classification"],
                    "hit_id": hit_id,
                    "side": h["side"],
                    "component": h["component"],
                    "file": h["file"],
                    "start_line": h["start_line"],
                    "end_line": h["end_line"],
                    "case_relevance": h["role"],
                }
            )
    return pd.DataFrame(rows)


def build_summaries(case_review: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    class_summary = (
        case_review.groupby("source_primary_classification", dropna=False)
        .agg(
            count=("mt5_trade_id", "count"),
            mt5_net_profit_sum=("mt5_net_profit", "sum"),
            reliable_mapped_count=("mapping_is_reliable_tier", lambda s: int(s.map(boolish).sum())),
            mt5_ids=("mt5_trade_id", lambda s: ";".join(s)),
        )
        .reset_index()
        .sort_values(["count", "mt5_net_profit_sum"], ascending=[False, False])
    )

    target_count = int(len(case_review))
    python_relabel_gap_count = int((case_review["source_primary_classification"] == "python_relabel_gap").sum())
    base_sequence_reset_gap_count = int((case_review["source_primary_classification"] == "base_sequence_reset_gap").sum())
    stopspec_rescue_path_gap_count = int((case_review["source_primary_classification"] == "stopspec_rescue_path_gap").sum())
    insufficient_code_evidence_count = int((case_review["source_primary_classification"] == "insufficient_code_evidence").sum())
    ea_label_drift_secondary_count = int(
        case_review["source_secondary_classifications"].astype(str).str.contains("ea_label_drift", regex=False).sum()
    )
    reliable = int(case_review["mapping_is_reliable_tier"].map(boolish).sum())
    all_have_ea_source = bool(case_review["ea_source_hits"].astype(str).str.len().gt(0).all())
    all_have_python_source = bool(case_review["python_source_hits"].astype(str).str.len().gt(0).all())
    all_have_timeline = bool(case_review["timeline_evidence_rows"].gt(0).all())

    final = pd.DataFrame(
        [
            {
                "target_count": target_count,
                "mt5_net_profit_sum": case_review["mt5_net_profit"].sum(),
                "source_primary_class_count": int(case_review["source_primary_classification"].nunique()),
                "python_relabel_gap_count": python_relabel_gap_count,
                "base_sequence_reset_gap_count": base_sequence_reset_gap_count,
                "stopspec_rescue_path_gap_count": stopspec_rescue_path_gap_count,
                "insufficient_code_evidence_count": insufficient_code_evidence_count,
                "ea_label_drift_secondary_count": ea_label_drift_secondary_count,
                "reliable_mapped_count": reliable,
                "all_targets_have_ea_source_hit": all_have_ea_source,
                "all_targets_have_python_source_hit": all_have_python_source,
                "all_targets_have_timeline_evidence": all_have_timeline,
                "diagnostic_source_rule_found": python_relabel_gap_count >= 4 and base_sequence_reset_gap_count >= 1,
                "prototype_gate_open": False,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "recommended_next_action": "diagnostic_only_python_slot1_runtime_label_variant_feasibility_no_main_merge",
            }
        ]
    )
    return class_summary, final


def simple_table(frame: pd.DataFrame, max_rows: int = 30) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def build_report(
    case_review: pd.DataFrame,
    class_summary: pd.DataFrame,
    final: pd.DataFrame,
    case_code_map: pd.DataFrame,
) -> list[str]:
    f = final.iloc[0].to_dict()
    show_cols = [
        "mt5_trade_id",
        "signal_anchor_time",
        "dir_norm",
        "mt5_signal_src",
        "mt5_net_profit",
        "source_primary_classification",
        "source_secondary_classifications",
        "ea_exact_event_kinds",
        "layer12_nearest_near_nonpostn_time",
        "layer12_nearest_near_nonpostn_mode",
        "raw_nearest_day_postn_time",
        "raw_nearest_day_postn_mode",
        "timeline_python_modes",
    ]
    show_cols = [col for col in show_cols if col in case_review.columns]
    map_cols = [
        "mt5_trade_id",
        "source_primary_classification",
        "side",
        "component",
        "file",
        "start_line",
        "end_line",
    ]
    return [
        "# Stage-State EA vs Python SLOT1 Trigger-Family Source Audit",
        "",
        "## Final Decision",
        "",
        f"- Target count: `{f['target_count']}`.",
        f"- Python relabel gap count: `{f['python_relabel_gap_count']}`.",
        f"- Base sequence reset gap count: `{f['base_sequence_reset_gap_count']}`.",
        f"- StopSpec rescue path gap count: `{f['stopspec_rescue_path_gap_count']}`.",
        f"- Insufficient code evidence count: `{f['insufficient_code_evidence_count']}`.",
        f"- EA label drift secondary count: `{f['ea_label_drift_secondary_count']}`.",
        f"- All targets have EA source hit: `{f['all_targets_have_ea_source_hit']}`.",
        f"- All targets have Python source hit: `{f['all_targets_have_python_source_hit']}`.",
        f"- All targets have timeline evidence: `{f['all_targets_have_timeline_evidence']}`.",
        f"- Diagnostic source rule found: `{f['diagnostic_source_rule_found']}`.",
        f"- Prototype gate: `{f['prototype_gate_open']}`.",
        f"- Main signal gate: `{f['main_signal_change_gate_open']}`.",
        f"- EA behavior gate: `{f['ea_behavior_gate_open']}`.",
        f"- Mapping gate: `{f['mapping_change_gate_open']}`.",
        f"- Merge gate: `{f['merge_gate_pass']}`.",
        "",
        "## Classification Summary",
        "",
        simple_table(class_summary),
        "",
        "## Case Review",
        "",
        simple_table(case_review[show_cols], max_rows=20),
        "",
        "## Case Code Map",
        "",
        simple_table(case_code_map[map_cols], max_rows=80),
        "",
        "## Interpretation",
        "",
        "- The 4-row cluster is best treated as `python_relabel_gap`: EA determines the SLOT1 trigger family at runtime from the current M30 context and merged counter, while Python SLOT1 replacement/rescue keeps the raw M30 `cross/pre_cross` mode.",
        "- `mt5_0067` remains a separate `base_sequence_reset_gap`: Python raw has a same-direction `cross` near the EA anchor and only reaches same-mode `post_n` later.",
        "- StopSpec/rescue tagging is not supported as the post_n creator. EA appends `_replace_or_rescue` after selecting the mode, and Python rescue/replacement preserves the existing mode.",
        "- This audit is diagnostic-only. It opens no EA, Python main-signal, mapping, dynamic-risk, or merge gate.",
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    case_verdict = read_csv(CASE_VERDICT)
    timeline = read_csv(TIMELINE)
    candidate_samples = read_csv(CANDIDATE_SAMPLES) if CANDIDATE_SAMPLES.exists() else pd.DataFrame()

    code_hits = build_code_hits()
    case_review = build_case_review(case_verdict, timeline, candidate_samples)
    case_code_map = build_case_code_map(case_review, code_hits)
    class_summary, final = build_summaries(case_review)

    write_csv(code_hits, OUT_DIR / "slot1_trigger_family_source_code_hits.csv")
    write_csv(case_review, OUT_DIR / "slot1_trigger_family_source_case_review.csv")
    write_csv(case_code_map, OUT_DIR / "slot1_trigger_family_source_case_code_map.csv")
    write_csv(class_summary, OUT_DIR / "slot1_trigger_family_source_classification_summary.csv")
    write_csv(final, OUT_DIR / "slot1_trigger_family_source_final_decision.csv")
    write_md(build_report(case_review, class_summary, final, case_code_map), OUT_DIR / "slot1_trigger_family_source_audit.md")
    write_md(
        [
            "# SLOT1 Trigger-Family Source Audit",
            "",
            f"- Target count: `{int(final.loc[0, 'target_count'])}`.",
            f"- Python relabel gap count: `{int(final.loc[0, 'python_relabel_gap_count'])}`.",
            f"- Base sequence reset gap count: `{int(final.loc[0, 'base_sequence_reset_gap_count'])}`.",
            f"- Merge gate: `{bool(final.loc[0, 'merge_gate_pass'])}`.",
        ],
        OUT_DIR / "README.md",
    )
    print(f"Wrote {OUT_DIR}")
    print(final.to_string(index=False))


if __name__ == "__main__":
    main()
