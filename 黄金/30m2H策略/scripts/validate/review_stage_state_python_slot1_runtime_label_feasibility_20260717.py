# -*- coding: utf-8 -*-
"""Diagnostic-only feasibility test for Python SLOT1 runtime labels.

This script does not edit EA code, the main signal builder, dynamic-risk logic,
or the canonical mapping rules. It creates a label-only copy of the current
Python-MT5 dynamic trades and remaps that copy against the accepted MT5
stage-state ledger.
"""

from __future__ import annotations


from itertools import product
from pathlib import Path
import shutil
import sys

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SCRIPT_DIR))

import map_python_mt5_ledger_trades as mapper  # noqa: E402


STRATEGY_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

SOURCE_AUDIT_DIR = VALIDATION_DIR / "stage_state_ea_python_slot1_trigger_family_source_audit_20260717"
NEAR_TRIGGER_DIR = VALIDATION_DIR / "stage_state_m15_slot1_near_trigger_family_drift_audit_20260717"
BASE_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
BASE_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"

OUT_DIR = VALIDATION_DIR / "stage_state_python_slot1_runtime_label_feasibility_20260717"
MAPPING_INPUT_DIR = OUT_DIR / "diagnostic_mapping_input"
MAPPING_OUT_DIR = OUT_DIR / "diagnostic_mapping"

CASE_REVIEW = SOURCE_AUDIT_DIR / "slot1_trigger_family_source_case_review.csv"
TIMELINE = NEAR_TRIGGER_DIR / "m15_slot1_near_trigger_timeline_pm120.csv"
PY_DYNAMIC = BASE_DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"

TARGET_IDS = ["mt5_0052", "mt5_0054", "mt5_0067", "mt5_0068", "mt5_0069"]
RELABEL_TARGET_CLASS = "python_relabel_gap"
SEQUENCE_RESET_CLASS = "base_sequence_reset_gap"
RUNTIME_WINDOW_MINUTES = 120


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_md(lines: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8-sig")


def parse_dt(value: object) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    if not text:
        return pd.NaT
    return pd.to_datetime(text.replace(".", "-"), errors="coerce")


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"BUY", "B", "L", "LONG", "1"}:
        return "BUY"
    if text in {"SELL", "S", "SHORT", "-1"}:
        return "SELL"
    return text


def mode_family(value: object) -> str:
    text = str(value).lower()
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return str(value).strip()


def runtime_mode_from_ea_mode(value: object) -> str:
    text = str(value)
    marker = "post_n"
    pos = text.find(marker)
    if pos < 0:
        return ""
    end = pos + len(marker)
    while end < len(text) and text[end].isdigit():
        end += 1
    return text[pos:end]


def postn_number(value: object) -> int | None:
    mode = runtime_mode_from_ea_mode(value)
    if not mode:
        return None
    digits = mode.replace("post_n", "")
    return int(digits) if digits.isdigit() else None


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def num(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return default
    return float(parsed)


def semijoin(values: list[object], limit: int = 20) -> str:
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


def add_dynamic_norm(dynamic: pd.DataFrame) -> pd.DataFrame:
    out = dynamic.copy()
    out["date_dt"] = out["date"].map(parse_dt)
    out["dir_norm"] = out["dir"].map(normalize_dir)
    out["mode_family_norm"] = out["mode"].map(mode_family)
    return out


def timeline_runtime_row(timeline: pd.DataFrame, mt5_id: str) -> pd.Series | None:
    rows = timeline[
        timeline["mt5_trade_id"].astype(str).eq(mt5_id)
        & timeline["source"].astype(str).eq("ea_log")
        & timeline["mode_family"].astype(str).eq("post_n")
        & timeline.get("is_target_ea_signal", pd.Series(False, index=timeline.index)).map(boolish)
    ].copy()
    if rows.empty:
        rows = timeline[
            timeline["mt5_trade_id"].astype(str).eq(mt5_id)
            & timeline["source"].astype(str).eq("ea_log")
            & timeline["mode_family"].astype(str).eq("post_n")
        ].copy()
    if rows.empty:
        return None
    rows["abs_time_diff"] = pd.to_numeric(rows["time_diff_minutes"], errors="coerce").abs()
    rows["event_rank"] = rows["event_kind"].map({"SIGNAL": 0, "Execute": 1, "Candidate": 2}).fillna(9)
    return rows.sort_values(["abs_time_diff", "event_rank"]).iloc[0]


def python_evidence_rows(timeline: pd.DataFrame, mt5_id: str, direction: str) -> pd.DataFrame:
    rows = timeline[
        timeline["mt5_trade_id"].astype(str).eq(mt5_id)
        & timeline["source"].astype(str).eq("python")
        & timeline["dir_norm"].astype(str).eq(direction)
        & ~timeline["mode_family"].astype(str).eq("post_n")
    ].copy()
    if rows.empty:
        return rows
    priority = {"dynamic": 0, "stage": 1, "layer3": 2, "layer12": 3, "raw": 4}
    rows["layer_rank"] = rows["layer"].map(priority).fillna(9)
    rows["abs_time_diff"] = pd.to_numeric(rows["time_diff_minutes"], errors="coerce").abs()
    return rows.sort_values(["layer_rank", "abs_time_diff", "signal_time"])


def build_target_review(case_review: pd.DataFrame, timeline: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, case in case_review[case_review["mt5_trade_id"].isin(TARGET_IDS)].iterrows():
        mt5_id = str(case["mt5_trade_id"])
        source_class = str(case["source_primary_classification"])
        direction = str(case["dir_norm"])
        runtime = timeline_runtime_row(timeline, mt5_id)
        py_rows = python_evidence_rows(timeline, mt5_id, direction)
        py = py_rows.iloc[0] if not py_rows.empty else None
        runtime_mode = runtime_mode_from_ea_mode(runtime["mode"]) if runtime is not None else ""
        runtime_source = ""
        if runtime is not None:
            runtime_source = "ea_log_exact" if abs(num(runtime.get("time_diff_minutes"))) < 1e-9 else "ea_log_near"

        is_relabel_target = source_class == RELABEL_TARGET_CLASS
        is_sequence_reset = source_class == SEQUENCE_RESET_CLASS
        explained = bool(
            is_relabel_target
            and runtime_mode
            and py is not None
            and mode_family(py.get("mode", "")) != "post_n"
        )
        rows.append(
            {
                "mt5_trade_id": mt5_id,
                "signal_anchor_time": case.get("signal_anchor_time", ""),
                "dir_norm": direction,
                "mt5_signal_src": case.get("mt5_signal_src", ""),
                "source_primary_classification": source_class,
                "is_relabel_target": is_relabel_target,
                "is_sequence_reset_case": is_sequence_reset,
                "ea_runtime_mode": runtime_mode,
                "ea_runtime_full_mode": runtime.get("mode", "") if runtime is not None else "",
                "runtime_label_source": runtime_source,
                "ea_runtime_time_diff_minutes": runtime.get("time_diff_minutes", "") if runtime is not None else "",
                "py_evidence_layer": py.get("layer", "") if py is not None else "",
                "py_signal_time": py.get("signal_time", "") if py is not None else "",
                "py_original_mode": py.get("mode", "") if py is not None else "",
                "py_original_mode_family": py.get("mode_family", "") if py is not None else "",
                "py_variant": py.get("variant", "") if py is not None else "",
                "py_trigger_family": py.get("trigger_family", "") if py is not None else "",
                "py_time_diff_minutes": py.get("time_diff_minutes", "") if py is not None else "",
                "target_explained_by_runtime_label": explained,
                "excluded_from_relabel": is_sequence_reset,
                "target_review_reason": (
                    "runtime label explains non-post_n Python SLOT1 evidence"
                    if explained
                    else "kept out of relabel path because it is base sequence reset"
                    if is_sequence_reset
                    else "runtime label evidence incomplete"
                ),
            }
        )
    return pd.DataFrame(rows)


def build_assignment_candidates(target_review: pd.DataFrame, dynamic: pd.DataFrame) -> pd.DataFrame:
    dyn = add_dynamic_norm(dynamic)
    rows: list[dict[str, object]] = []
    for _, target in target_review[target_review["is_relabel_target"]].iterrows():
        anchor = parse_dt(target["signal_anchor_time"])
        if pd.isna(anchor):
            continue
        runtime_mode = str(target["ea_runtime_mode"])
        if not runtime_mode:
            continue
        subset = dyn[
            dyn["dir_norm"].eq(str(target["dir_norm"]))
            & dyn["trigger_family"].astype(str).eq("M15 SLOT1")
            & ~dyn["mode_family_norm"].eq("post_n")
        ].copy()
        if subset.empty:
            continue
        subset["time_diff_minutes"] = (subset["date_dt"] - anchor).dt.total_seconds() / 60.0
        subset["abs_time_diff_minutes"] = subset["time_diff_minutes"].abs()
        subset = subset[subset["abs_time_diff_minutes"] <= RUNTIME_WINDOW_MINUTES]
        for idx, dyn_row in subset.iterrows():
            rows.append(
                {
                    "mt5_trade_id": target["mt5_trade_id"],
                    "signal_anchor_time": target["signal_anchor_time"],
                    "dir_norm": target["dir_norm"],
                    "runtime_mode": runtime_mode,
                    "runtime_mode_family": "post_n",
                    "runtime_label_source": target["runtime_label_source"],
                    "dynamic_row_index": int(idx),
                    "dynamic_date": dyn_row["date"],
                    "dynamic_original_mode": dyn_row["mode"],
                    "dynamic_original_mode_family": dyn_row["mode_family"],
                    "dynamic_variant": dyn_row["variant"],
                    "dynamic_trigger_family": dyn_row["trigger_family"],
                    "dynamic_total_profit": dyn_row.get("dynamic_total_$", ""),
                    "time_diff_minutes_to_signal_anchor": round(float(dyn_row["time_diff_minutes"]), 6),
                    "abs_time_diff_minutes_to_signal_anchor": round(float(dyn_row["abs_time_diff_minutes"]), 6),
                }
            )
    return pd.DataFrame(rows)


def choose_unique_assignments(candidates: pd.DataFrame, relabel_targets: list[str]) -> pd.DataFrame:
    if candidates.empty:
        return candidates.copy()
    choices: list[list[int | None]] = []
    for mt5_id in relabel_targets:
        idxs = candidates[candidates["mt5_trade_id"].eq(mt5_id)].index.tolist()
        choices.append(idxs + [None])

    best: tuple[int, float, tuple[int | None, ...]] | None = None
    for combo in product(*choices):
        used_dynamic: set[int] = set()
        valid = True
        assigned_count = 0
        total_abs = 0.0
        for idx in combo:
            if idx is None:
                continue
            dynamic_idx = int(candidates.loc[idx, "dynamic_row_index"])
            if dynamic_idx in used_dynamic:
                valid = False
                break
            used_dynamic.add(dynamic_idx)
            assigned_count += 1
            total_abs += float(candidates.loc[idx, "abs_time_diff_minutes_to_signal_anchor"])
        if not valid:
            continue
        score = (assigned_count, -total_abs, combo)
        if best is None or score > best:
            best = score

    if best is None:
        return candidates.iloc[0:0].copy()
    chosen = [idx for idx in best[2] if idx is not None]
    out = candidates.loc[chosen].copy().reset_index(drop=True)
    out["assignment_rule"] = "max_target_count_then_min_total_abs_time_diff_unique_dynamic_row"
    return out


def prepare_mapping_input(dynamic: pd.DataFrame, assignments: pd.DataFrame) -> pd.DataFrame:
    MAPPING_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in [
        "python_only_dynamic_risk_trades.csv",
        "python_mt5_dynamic_risk_trades.csv",
        "mt5_ledger_unique_signals.csv",
    ]:
        shutil.copy2(BASE_DYNAMIC_DIR / name, MAPPING_INPUT_DIR / name)

    variant = dynamic.copy()
    for col in [
        "diagnostic_original_mode",
        "diagnostic_original_mode_family",
        "diagnostic_runtime_mode",
        "diagnostic_runtime_mode_family",
        "diagnostic_runtime_label_source",
        "diagnostic_runtime_label_mt5_trade_id",
        "diagnostic_runtime_label_time_diff_minutes",
    ]:
        variant[col] = ""

    for _, assignment in assignments.iterrows():
        idx = int(assignment["dynamic_row_index"])
        variant.loc[idx, "diagnostic_original_mode"] = variant.loc[idx, "mode"]
        variant.loc[idx, "diagnostic_original_mode_family"] = variant.loc[idx, "mode_family"]
        variant.loc[idx, "diagnostic_runtime_mode"] = assignment["runtime_mode"]
        variant.loc[idx, "diagnostic_runtime_mode_family"] = assignment["runtime_mode_family"]
        variant.loc[idx, "diagnostic_runtime_label_source"] = assignment["runtime_label_source"]
        variant.loc[idx, "diagnostic_runtime_label_mt5_trade_id"] = assignment["mt5_trade_id"]
        variant.loc[idx, "diagnostic_runtime_label_time_diff_minutes"] = assignment[
            "time_diff_minutes_to_signal_anchor"
        ]
        variant.loc[idx, "mode"] = assignment["runtime_mode"]
        variant.loc[idx, "mode_family"] = assignment["runtime_mode_family"]
        if "source_variant" in variant.columns:
            variant.loc[idx, "source_variant"] = (
                str(variant.loc[idx, "source_variant"]) + "_diagnostic_runtime_label"
            )

    write_csv(variant, MAPPING_INPUT_DIR / "python_mt5_dynamic_risk_trades.csv")
    write_csv(variant, OUT_DIR / "diagnostic_python_mt5_dynamic_label_variant_trades.csv")
    return variant


def run_mapping() -> None:
    mapper.INPUT_DIR = MAPPING_INPUT_DIR
    mapper.OUT_DIR = MAPPING_OUT_DIR
    mapper.main()


def source_row(frame: pd.DataFrame, source: str) -> pd.Series:
    hit = frame[frame["source"].astype(str).eq(source)]
    if hit.empty:
        raise ValueError(f"missing source={source}")
    return hit.iloc[0]


def compare_mapping() -> pd.DataFrame:
    base = read_csv(BASE_MAPPING_DIR / "unique_match_summary.csv")
    diag = read_csv(MAPPING_OUT_DIR / "unique_match_summary.csv")
    rows: list[dict[str, object]] = []
    for source in ["python_only", "python_mt5"]:
        b = source_row(base, source)
        d = source_row(diag, source)
        row = {"source": source}
        for col in [
            "python_trades",
            "mt5_trades",
            "matched_unique",
            "reliable_tier_matched",
            "relaxed_tier_matched",
            "python_unmatched",
            "mt5_unmatched",
            "matched_profit_diff",
        ]:
            row[f"baseline_{col}"] = b[col]
            row[f"diagnostic_{col}"] = d[col]
            row[f"delta_{col}"] = num(d[col]) - num(b[col])
        rows.append(row)
    return pd.DataFrame(rows)


def target_mapping_before_after() -> pd.DataFrame:
    base = read_csv(BASE_MAPPING_DIR / "python_mt5_mt5_unique_matches.csv")
    diag = read_csv(MAPPING_OUT_DIR / "python_mt5_mt5_unique_matches.csv")
    rows: list[dict[str, object]] = []
    for mt5_id in TARGET_IDS:
        b = base[base["mt5_trade_id"].astype(str).eq(mt5_id)].copy()
        d = diag[diag["mt5_trade_id"].astype(str).eq(mt5_id)].copy()
        b_row = b.iloc[0] if not b.empty else None
        d_row = d.iloc[0] if not d.empty else None
        rows.append(
            {
                "mt5_trade_id": mt5_id,
                "baseline_matched": b_row is not None,
                "baseline_match_tier": b_row.get("match_tier", "") if b_row is not None else "",
                "baseline_mt5_signal_src": b_row.get("mt5_signal_src", "") if b_row is not None else "",
                "baseline_py_trade_id": b_row.get("py_trade_id", "") if b_row is not None else "",
                "baseline_py_date": b_row.get("py_date", "") if b_row is not None else "",
                "baseline_py_mode": b_row.get("py_mode", "") if b_row is not None else "",
                "baseline_py_mode_family": b_row.get("py_mode_family", "") if b_row is not None else "",
                "baseline_is_reliable_tier": b_row.get("is_reliable_tier", "") if b_row is not None else "",
                "diagnostic_matched": d_row is not None,
                "diagnostic_match_tier": d_row.get("match_tier", "") if d_row is not None else "",
                "diagnostic_mt5_signal_src": d_row.get("mt5_signal_src", "") if d_row is not None else "",
                "diagnostic_py_trade_id": d_row.get("py_trade_id", "") if d_row is not None else "",
                "diagnostic_py_date": d_row.get("py_date", "") if d_row is not None else "",
                "diagnostic_py_mode": d_row.get("py_mode", "") if d_row is not None else "",
                "diagnostic_py_mode_family": d_row.get("py_mode_family", "") if d_row is not None else "",
                "diagnostic_is_reliable_tier": d_row.get("is_reliable_tier", "") if d_row is not None else "",
                "match_tier_changed": (b_row.get("match_tier", "") if b_row is not None else "")
                != (d_row.get("match_tier", "") if d_row is not None else ""),
                "baseline_postn_number_same": (
                    postn_number(b_row.get("py_mode", "")) == postn_number(b_row.get("mt5_signal_src", ""))
                    if b_row is not None
                    and str(b_row.get("py_mode_family", "")) == "post_n"
                    and "post_n" in str(b_row.get("mt5_signal_src", ""))
                    else ""
                ),
                "diagnostic_postn_number_same": (
                    postn_number(d_row.get("py_mode", "")) == postn_number(d_row.get("mt5_signal_src", ""))
                    if d_row is not None
                    and str(d_row.get("py_mode_family", "")) == "post_n"
                    and "post_n" in str(d_row.get("mt5_signal_src", ""))
                    else ""
                ),
                "diagnostic_postn_number_mismatch": (
                    postn_number(d_row.get("py_mode", "")) != postn_number(d_row.get("mt5_signal_src", ""))
                    if d_row is not None
                    and str(d_row.get("py_mode_family", "")) == "post_n"
                    and "post_n" in str(d_row.get("mt5_signal_src", ""))
                    else False
                ),
            }
        )
    return pd.DataFrame(rows)


def dynamic_summary(dynamic: pd.DataFrame, variant: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label, frame in [("baseline", dynamic), ("diagnostic_label_variant", variant)]:
        rows.append(
            {
                "variant": label,
                "trade_count": int(len(frame)),
                "final_balance": round(num(frame["balance_after"].iloc[-1]), 6) if not frame.empty else 0.0,
                "dynamic_total_profit": round(float(pd.to_numeric(frame["dynamic_total_$"], errors="coerce").sum()), 6),
                "postn_mode_family_count": int(frame["mode_family"].astype(str).eq("post_n").sum()),
                "m15_slot1_postn_count": int(
                    (
                        frame["trigger_family"].astype(str).eq("M15 SLOT1")
                        & frame["mode_family"].astype(str).eq("post_n")
                    ).sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def build_final_decision(
    target_review: pd.DataFrame,
    assignment_candidates: pd.DataFrame,
    assignments: pd.DataFrame,
    mapping_delta: pd.DataFrame,
    target_map: pd.DataFrame,
) -> pd.DataFrame:
    py_delta = source_row(mapping_delta, "python_mt5")
    relabel_targets = target_review[target_review["is_relabel_target"]]
    sequence_reset = target_review[target_review["is_sequence_reset_case"]]
    target_explained_count = int(relabel_targets["target_explained_by_runtime_label"].sum())
    target_relabel_count = int(len(relabel_targets))
    dynamic_relabelable_count = int(assignments["mt5_trade_id"].nunique()) if not assignments.empty else 0
    sequence_excluded_count = int(sequence_reset["excluded_from_relabel"].sum()) if not sequence_reset.empty else 0
    python_unmatched_delta = num(py_delta["delta_python_unmatched"])
    mt5_unmatched_delta = num(py_delta["delta_mt5_unmatched"])
    reliable_delta = num(py_delta["delta_reliable_tier_matched"])
    matched_unique_delta = num(py_delta["delta_matched_unique"])
    full_chain_not_widened = python_unmatched_delta <= 0 and mt5_unmatched_delta <= 0
    improved_reliability = reliable_delta > 0
    target_only_pass = target_explained_count == target_relabel_count and sequence_excluded_count == len(sequence_reset)
    changed_targets = int(target_map["match_tier_changed"].map(boolish).sum()) if not target_map.empty else 0
    postn_number_mismatch_count = (
        int(target_map["diagnostic_postn_number_mismatch"].map(boolish).sum()) if not target_map.empty else 0
    )

    return pd.DataFrame(
        [
            {
                "target_total": int(len(target_review)),
                "runtime_relabel_target_count": target_relabel_count,
                "target_explained_count": target_explained_count,
                "base_sequence_reset_excluded_count": sequence_excluded_count,
                "assignment_candidate_rows": int(len(assignment_candidates)),
                "dynamic_relabelable_target_count": dynamic_relabelable_count,
                "dynamic_relabel_assignment_rows": int(len(assignments)),
                "target_mapping_changed_count": changed_targets,
                "diagnostic_target_postn_number_mismatch_count": postn_number_mismatch_count,
                "baseline_matched_unique": py_delta["baseline_matched_unique"],
                "diagnostic_matched_unique": py_delta["diagnostic_matched_unique"],
                "delta_matched_unique": matched_unique_delta,
                "baseline_reliable_tier_matched": py_delta["baseline_reliable_tier_matched"],
                "diagnostic_reliable_tier_matched": py_delta["diagnostic_reliable_tier_matched"],
                "delta_reliable_tier_matched": reliable_delta,
                "baseline_python_unmatched": py_delta["baseline_python_unmatched"],
                "diagnostic_python_unmatched": py_delta["diagnostic_python_unmatched"],
                "delta_python_unmatched": python_unmatched_delta,
                "baseline_mt5_unmatched": py_delta["baseline_mt5_unmatched"],
                "diagnostic_mt5_unmatched": py_delta["diagnostic_mt5_unmatched"],
                "delta_mt5_unmatched": mt5_unmatched_delta,
                "full_chain_not_widened": full_chain_not_widened,
                "improved_reliability": improved_reliability,
                "mode_number_safe": postn_number_mismatch_count == 0,
                "target_only_pass": target_only_pass,
                "stage_exit_logic_changed": False,
                "unresolved_p1_blocker_delta": 0,
                "unresolved_p1_blocker_delta_basis": "label_only_no_stage_exit_recompute",
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "recommended_next_action": "mode_number_aware_runtime_label_mapping_audit_before_layer3_admission",
            }
        ]
    )


def simple_table(frame: pd.DataFrame, max_rows: int = 40) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def build_report(
    target_review: pd.DataFrame,
    assignment_candidates: pd.DataFrame,
    assignments: pd.DataFrame,
    dynamic_stats: pd.DataFrame,
    mapping_delta: pd.DataFrame,
    target_map: pd.DataFrame,
    final: pd.DataFrame,
) -> list[str]:
    f = final.iloc[0].to_dict()
    return [
        "# Stage-State Python SLOT1 Runtime-Label Feasibility",
        "",
        "## Final Decision",
        "",
        f"- Runtime relabel targets: `{f['runtime_relabel_target_count']}`.",
        f"- Target explained count: `{f['target_explained_count']}`.",
        f"- Base-sequence reset excluded count: `{f['base_sequence_reset_excluded_count']}`.",
        f"- Dynamic relabelable target count: `{f['dynamic_relabelable_target_count']}`.",
        f"- Diagnostic post_n number mismatch count: `{f['diagnostic_target_postn_number_mismatch_count']}`.",
        f"- Diagnostic matched unique delta: `{f['delta_matched_unique']}`.",
        f"- Diagnostic reliable-tier delta: `{f['delta_reliable_tier_matched']}`.",
        f"- Diagnostic Python-unmatched delta: `{f['delta_python_unmatched']}`.",
        f"- Diagnostic MT5-unmatched delta: `{f['delta_mt5_unmatched']}`.",
        f"- Full-chain not widened: `{f['full_chain_not_widened']}`.",
        f"- Mode-number safe: `{f['mode_number_safe']}`.",
        f"- Target-only pass: `{f['target_only_pass']}`.",
        f"- Main signal gate: `{f['main_signal_change_gate_open']}`.",
        f"- EA behavior gate: `{f['ea_behavior_gate_open']}`.",
        f"- Mapping gate: `{f['mapping_change_gate_open']}`.",
        f"- Merge gate: `{f['merge_gate_pass']}`.",
        "",
        "## Target Review",
        "",
        simple_table(target_review),
        "",
        "## Assignment Candidates",
        "",
        simple_table(assignment_candidates),
        "",
        "## Unique Dynamic Assignments",
        "",
        simple_table(assignments),
        "",
        "## Dynamic Summary",
        "",
        simple_table(dynamic_stats),
        "",
        "## Mapping Delta",
        "",
        simple_table(mapping_delta),
        "",
        "## Target Mapping Before/After",
        "",
        simple_table(target_map),
        "",
        "## Interpretation",
        "",
        "- The target-only source explanation covers all four `python_relabel_gap` cases and keeps `mt5_0067` out of the relabel path.",
        "- Only two of the four relabel targets already exist in the current dynamic trade table, so a label-only full-chain copy can improve mapping reliability but cannot recover targets absent from Layer3/dynamic.",
        "- The current mapper compares post_n at mode-family level. This diagnostic explicitly flags post_n number swaps so an apparent reliable-tier gain is not treated as true parity.",
        "- The diagnostic copy does not change entries, stops, exits, lots, or PnL. Final balance is therefore unchanged by construction.",
        "- No main signal, EA behavior, mapping, or merge gate is opened here.",
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    case_review = read_csv(CASE_REVIEW)
    timeline = read_csv(TIMELINE)
    dynamic = read_csv(PY_DYNAMIC)

    target_review = build_target_review(case_review, timeline)
    assignment_candidates = build_assignment_candidates(target_review, dynamic)
    relabel_targets = target_review[target_review["is_relabel_target"]]["mt5_trade_id"].astype(str).tolist()
    assignments = choose_unique_assignments(assignment_candidates, relabel_targets)
    variant = prepare_mapping_input(dynamic, assignments)
    run_mapping()

    dynamic_stats = dynamic_summary(dynamic, variant)
    mapping_delta = compare_mapping()
    target_map = target_mapping_before_after()
    final = build_final_decision(target_review, assignment_candidates, assignments, mapping_delta, target_map)

    write_csv(target_review, OUT_DIR / "runtime_label_target_review.csv")
    write_csv(assignment_candidates, OUT_DIR / "runtime_label_assignment_candidates.csv")
    write_csv(assignments, OUT_DIR / "runtime_label_dynamic_assignments.csv")
    write_csv(dynamic_stats, OUT_DIR / "runtime_label_dynamic_summary.csv")
    write_csv(mapping_delta, OUT_DIR / "runtime_label_mapping_delta.csv")
    write_csv(target_map, OUT_DIR / "runtime_label_target_mapping_before_after.csv")
    write_csv(final, OUT_DIR / "runtime_label_final_decision.csv")
    write_md(
        build_report(target_review, assignment_candidates, assignments, dynamic_stats, mapping_delta, target_map, final),
        OUT_DIR / "runtime_label_feasibility_audit.md",
    )
    write_md(
        [
            "# Python SLOT1 Runtime-Label Feasibility",
            "",
            f"- Target explained count: `{int(final.loc[0, 'target_explained_count'])}`.",
            f"- Dynamic relabelable target count: `{int(final.loc[0, 'dynamic_relabelable_target_count'])}`.",
            f"- Post_n number mismatch count: `{int(final.loc[0, 'diagnostic_target_postn_number_mismatch_count'])}`.",
            f"- Reliable-tier delta: `{num(final.loc[0, 'delta_reliable_tier_matched'])}`.",
            f"- Merge gate: `{bool(final.loc[0, 'merge_gate_pass'])}`.",
        ],
        OUT_DIR / "README.md",
    )

    print(f"Wrote {OUT_DIR}")
    print(final.to_string(index=False))


if __name__ == "__main__":
    main()
