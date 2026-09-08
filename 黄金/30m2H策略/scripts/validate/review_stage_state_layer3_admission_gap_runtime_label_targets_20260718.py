# -*- coding: utf-8 -*-
"""Layer3 admission-gap audit for runtime-label targets.

Diagnostic-only:
- does not edit signal builders
- does not edit EA
- does not edit dynamic-risk or mapping outputs
"""

from __future__ import annotations


import bisect
from pathlib import Path
import sys

import numpy as np
import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(r"F:\use_code\MTA5_l")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import _current_baseline as cb  # noqa: E402
from _h2_context import load_h2_context  # noqa: E402


STRATEGY_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"
BASE_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"

RESIDUAL_DIR = VALIDATION_DIR / "stage_state_relaxed_postn_mismatch_residual_audit_20260718"
RUNTIME_LABEL_DIR = VALIDATION_DIR / "stage_state_python_slot1_runtime_label_feasibility_20260717"
SOURCE_AUDIT_DIR = VALIDATION_DIR / "stage_state_ea_python_slot1_trigger_family_source_audit_20260717"
OUT_DIR = VALIDATION_DIR / "stage_state_layer3_admission_gap_runtime_label_targets_20260718"

TARGET_RETENTION = RESIDUAL_DIR / "strict_plus_exclusion_target_retention.csv"
RUNTIME_TARGET_REVIEW = RUNTIME_LABEL_DIR / "runtime_label_target_review.csv"
RUNTIME_ASSIGNMENTS = RUNTIME_LABEL_DIR / "runtime_label_dynamic_assignments.csv"
SOURCE_CASE_REVIEW = SOURCE_AUDIT_DIR / "slot1_trigger_family_source_case_review.csv"
PY_DYNAMIC = BASE_DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"

TARGET_IDS = ["mt5_0052", "mt5_0054", "mt5_0068", "mt5_0069"]
MISSING_LAYER3_TARGETS = {"mt5_0052", "mt5_0054"}
CONTROL_TARGETS = {"mt5_0068", "mt5_0069"}
TOP_PCT = 34
LOOKBACK = 500


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_md(lines: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8-sig")


def signal_file(pattern: str) -> Path:
    hits = sorted(SIGNAL_DIR.glob(pattern))
    if not hits:
        raise FileNotFoundError(pattern)
    return hits[0]


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


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"BUY", "B", "L", "LONG", "1"}:
        return "BUY"
    if text in {"SELL", "S", "SHORT", "-1"}:
        return "SELL"
    return text


def short_dir(value: str) -> str:
    text = normalize_dir(value)
    if text == "BUY":
        return "L"
    if text == "SELL":
        return "S"
    return str(value)


def mode_family(value: object) -> str:
    text = str(value).lower()
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return str(value).strip()


def trigger_from_variant(value: object, entry_time: object = "", date: object = "") -> str:
    text = str(value).lower()
    if "slot1" in text or "rescue" in text or "replace" in text:
        return "M15 SLOT1"
    et = parse_dt(entry_time)
    dt = parse_dt(date)
    if pd.notna(et) and pd.notna(dt) and et < dt:
        return "M15 SLOT1"
    return "M30 CLOSE"


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def num(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return default
    return float(parsed)


def add_norm_columns(frame: pd.DataFrame, layer: str) -> pd.DataFrame:
    out = frame.copy()
    if "date" in out.columns:
        out["date_dt"] = out["date"].map(parse_dt)
    if "entry_time" in out.columns:
        out["entry_time_dt"] = out["entry_time"].map(parse_dt)
    else:
        out["entry_time_dt"] = pd.NaT
    if "dir" in out.columns:
        out["dir_norm"] = out["dir"].map(normalize_dir)
    else:
        out["dir_norm"] = ""
    if "mode" in out.columns:
        out["mode_family"] = out["mode"].map(mode_family)
    else:
        out["mode_family"] = ""
    if "variant" in out.columns:
        out["trigger_family_inferred"] = [
            trigger_from_variant(variant, entry_time, date)
            for variant, entry_time, date in zip(
                out["variant"],
                out.get("entry_time", pd.Series("", index=out.index)),
                out.get("date", pd.Series("", index=out.index)),
            )
        ]
    elif "trigger_family" in out.columns:
        out["trigger_family_inferred"] = out["trigger_family"]
    else:
        out["trigger_family_inferred"] = ""
    out["layer"] = layer
    return out


def load_signal_tables() -> dict[str, pd.DataFrame]:
    tables = {
        "raw": add_norm_columns(read_csv(SIGNAL_DIR / "raw_candidates.csv"), "raw"),
        "layer12": add_norm_columns(read_csv(signal_file("*Layer1*")), "layer12"),
        "layer3": add_norm_columns(read_csv(signal_file("*Layer3*")), "layer3"),
        "stage": add_norm_columns(read_csv(signal_file("*Stage*")), "stage"),
        "dynamic": add_norm_columns(read_csv(PY_DYNAMIC), "dynamic"),
    }
    return tables


def compute_layer3_all(layer12: pd.DataFrame) -> pd.DataFrame:
    out = layer12.copy().reset_index(drop=True)
    out["layer12_row_id"] = out.index
    h2 = load_h2_context()
    h2_bias = cb._build_h2_bias5_lookup(h2)
    h2_times = pd.to_datetime(h2_bias["date"]).tolist()
    h2_bias_values = h2_bias["Bias_5_calc"].tolist()

    eval_times: list[pd.Timestamp] = []
    trigger_by_entry: list[str] = []
    bias5_values: list[float] = []
    threshold_values: list[float] = []
    pass_flags: list[bool] = []
    hist_ranks: list[float] = []

    for _, row in out.iterrows():
        date = parse_dt(row["date"])
        entry_time = parse_dt(row.get("entry_time", ""))
        trigger = "M15 SLOT1" if pd.notna(entry_time) and pd.notna(date) and entry_time < date else "M30 CLOSE"
        eval_time = date
        if trigger == "M30 CLOSE":
            eval_time = eval_time + pd.Timedelta(minutes=cb.EA_DIAG_M30_LAYER3_SHIFT_MINUTES)
        eval_times.append(eval_time)
        trigger_by_entry.append(trigger)

        idx = bisect.bisect_right(h2_times, eval_time) - 1
        if idx < 0:
            bias5_values.append(np.nan)
            threshold_values.append(np.nan)
            pass_flags.append(False)
            hist_ranks.append(np.nan)
            continue
        start = max(0, idx - LOOKBACK + 1)
        hist = h2_bias_values[start : idx + 1]
        current_bias = float(h2_bias_values[idx])
        threshold = cb._rolling_top_threshold(hist, TOP_PCT)
        bias5_values.append(current_bias)
        threshold_values.append(threshold)
        if pd.isna(threshold):
            pass_flags.append(True)
            hist_ranks.append(np.nan)
        else:
            pass_flags.append(current_bias >= threshold)
            hist_arr = np.asarray(hist, dtype=float)
            hist_ranks.append(float((hist_arr <= current_bias).mean() * 100.0))

    out["trigger_by_entry_time"] = trigger_by_entry
    out["layer3_eval_time"] = eval_times
    out["Bias_5_ea"] = bias5_values
    out["layer3_threshold_ea"] = threshold_values
    out["layer3_bias_gap"] = out["Bias_5_ea"] - out["layer3_threshold_ea"]
    out["layer3_hist_percentile"] = hist_ranks
    out["layer3_pass_ea"] = pass_flags
    return out


def apply_max_pos_3_with_state(layer3_before: pd.DataFrame) -> pd.DataFrame:
    if layer3_before.empty:
        return layer3_before.copy()
    rows = []
    active: list[tuple[pd.Timestamp, pd.Timestamp, int]] = []
    for _, row in layer3_before.sort_values(["date_dt", "mode", "dir_norm", "layer12_row_id"]).iterrows():
        anchor = row["date_dt"]
        active = [item for item in active if item[0] > anchor]
        out = row.copy()
        out["maxpos_active_count_before"] = len(active)
        out["maxpos_active_anchors_before"] = ";".join(item[1].strftime("%Y-%m-%d %H:%M:%S") for item in active[:8])
        out["maxpos_pass"] = len(active) < 3
        rows.append(out)
        if bool(out["maxpos_pass"]):
            active.append((anchor + pd.Timedelta(hours=24), anchor, int(row["layer12_row_id"])))
    return pd.DataFrame(rows).reset_index(drop=True)


def exact_rows(table: pd.DataFrame, time: object, direction: str, mode: str | None = None) -> pd.DataFrame:
    dt = parse_dt(time)
    if pd.isna(dt) or table.empty:
        return table.iloc[0:0].copy()
    rows = table[table["date_dt"].eq(dt) & table["dir_norm"].eq(normalize_dir(direction))].copy()
    if mode:
        rows = rows[rows.get("mode", pd.Series("", index=rows.index)).astype(str).eq(str(mode))]
    return rows


def nearest_row(table: pd.DataFrame, time: object, direction: str, same_dir: bool = True, window_minutes: int = 24 * 60) -> pd.Series | None:
    dt = parse_dt(time)
    if pd.isna(dt) or table.empty:
        return None
    rows = table.copy()
    if same_dir:
        rows = rows[rows["dir_norm"].eq(normalize_dir(direction))]
    else:
        rows = rows[~rows["dir_norm"].eq(normalize_dir(direction))]
    if rows.empty:
        return None
    rows["time_diff_minutes"] = (rows["date_dt"] - dt).dt.total_seconds() / 60.0
    rows["abs_time_diff_minutes"] = rows["time_diff_minutes"].abs()
    rows = rows[rows["abs_time_diff_minutes"] <= window_minutes]
    if rows.empty:
        return None
    return rows.sort_values(["abs_time_diff_minutes", "date_dt"]).iloc[0]


def row_ref(row: pd.Series | None) -> dict[str, object]:
    if row is None:
        return {
            "time": "",
            "diff_minutes": "",
            "dir": "",
            "mode": "",
            "variant": "",
            "pnl": "",
        }
    return {
        "time": fmt_dt(row.get("date_dt")),
        "diff_minutes": round(num(row.get("time_diff_minutes")), 6),
        "dir": row.get("dir_norm", ""),
        "mode": row.get("mode", ""),
        "variant": row.get("variant", ""),
        "pnl": row.get("pnl", row.get("total_$", row.get("dynamic_total_$", ""))),
    }


def target_candidate_specs(
    runtime_review: pd.DataFrame,
    assignments: pd.DataFrame,
    retention: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for _, target in runtime_review[runtime_review["mt5_trade_id"].isin(TARGET_IDS)].iterrows():
        mt5_id = str(target["mt5_trade_id"])
        assignment = assignments[assignments["mt5_trade_id"].astype(str).eq(mt5_id)].copy()
        if not assignment.empty:
            a = assignment.iloc[0]
            candidate_time = a["dynamic_date"]
            candidate_mode = a["dynamic_original_mode"]
            candidate_variant = a["dynamic_variant"]
            candidate_source = "runtime_assignment_dynamic_original"
            runtime_mode = a["runtime_mode"]
        else:
            candidate_time = target["py_signal_time"]
            candidate_mode = target["py_original_mode"]
            candidate_variant = target["py_variant"]
            candidate_source = "runtime_target_review_py_evidence"
            runtime_mode = target["ea_runtime_mode"]
        ret = retention[retention["mt5_trade_id"].astype(str).eq(mt5_id)]
        rows.append(
            {
                "mt5_trade_id": mt5_id,
                "mt5_signal_src": target["mt5_signal_src"],
                "signal_anchor_time": target["signal_anchor_time"],
                "dir_norm": target["dir_norm"],
                "candidate_time": candidate_time,
                "candidate_mode": candidate_mode,
                "candidate_variant": candidate_variant,
                "candidate_source": candidate_source,
                "ea_runtime_mode": runtime_mode,
                "retained_after_exclusion": boolish(ret.iloc[0]["retained_after_exclusion"]) if not ret.empty else False,
                "post_exclusion_tier": ret.iloc[0]["post_exclusion_tier"] if not ret.empty else "",
                "is_missing_layer3_target": mt5_id in MISSING_LAYER3_TARGETS,
                "is_control_target": mt5_id in CONTROL_TARGETS,
            }
        )
    return pd.DataFrame(rows)


def build_stage_presence(specs: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for _, spec in specs.iterrows():
        for layer in ["raw", "layer12", "layer3", "stage", "dynamic"]:
            table = tables[layer]
            exact = exact_rows(table, spec["candidate_time"], spec["dir_norm"], str(spec["candidate_mode"]) if layer in {"raw", "layer12", "layer3", "stage"} else None)
            if exact.empty and layer in {"dynamic"}:
                exact = exact_rows(table, spec["candidate_time"], spec["dir_norm"])
            if exact.empty:
                rows.append(
                    {
                        "mt5_trade_id": spec["mt5_trade_id"],
                        "layer": layer,
                        "present": False,
                        "row_count": 0,
                    }
                )
                continue
            for _, hit in exact.iterrows():
                rows.append(
                    {
                        "mt5_trade_id": spec["mt5_trade_id"],
                        "layer": layer,
                        "present": True,
                        "row_count": len(exact),
                        "date": hit.get("date", ""),
                        "dir": hit.get("dir", ""),
                        "mode": hit.get("mode", ""),
                        "variant": hit.get("variant", ""),
                        "entry_time": hit.get("entry_time", ""),
                        "pnl": hit.get("pnl", ""),
                        "total_$": hit.get("total_$", ""),
                        "dynamic_total_$": hit.get("dynamic_total_$", ""),
                        "Bias_5": hit.get("Bias_5", ""),
                        "Bias_5_ea": hit.get("Bias_5_ea", ""),
                        "layer3_threshold_ea": hit.get("layer3_threshold_ea", ""),
                        "layer3_pass_ea": hit.get("layer3_pass_ea", ""),
                        "spec_pass": hit.get("spec_pass", ""),
                        "spec_reason": hit.get("spec_reason", ""),
                    }
                )
    return pd.DataFrame(rows)


def build_admission_review(
    specs: pd.DataFrame,
    layer12_eval: pd.DataFrame,
    before_state: pd.DataFrame,
    after_maxpos: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    before_by_id = before_state.set_index("layer12_row_id", drop=False) if not before_state.empty else pd.DataFrame()
    after_ids = set(after_maxpos["layer12_row_id"].astype(int)) if "layer12_row_id" in after_maxpos.columns else set()

    for _, spec in specs.iterrows():
        hits = exact_rows(layer12_eval, spec["candidate_time"], spec["dir_norm"], spec["candidate_mode"])
        if "variant" in hits.columns:
            hits = hits[hits["variant"].astype(str).eq(str(spec["candidate_variant"]))]
        if hits.empty:
            rows.append(
                {
                    **spec.to_dict(),
                    "admission_failure_reason": "missing_layer12_candidate",
                    "layer12_present": False,
                    "layer3_before_maxpos": False,
                    "layer3_after_maxpos": False,
                    "low_blast_admission_rule_supported": False,
                }
            )
            continue
        hit = hits.iloc[0]
        row_id = int(hit["layer12_row_id"])
        before_hit = before_by_id.loc[row_id] if not before_by_id.empty and row_id in before_by_id.index else None
        layer3_pass = boolish(hit["layer3_pass_ea"])
        maxpos_pass = bool(before_hit["maxpos_pass"]) if before_hit is not None else False
        after_pass = row_id in after_ids
        if not layer3_pass:
            reason = "layer3_threshold_fail"
        elif not maxpos_pass:
            reason = "max_position_blocked_after_layer3"
        elif not after_pass:
            reason = "after_maxpos_missing_unknown"
        else:
            reason = "admitted_to_layer3_dynamic_path"

        same_before = nearest_row(before_state, hit["date_dt"], hit["dir_norm"], same_dir=True)
        opp_before = nearest_row(before_state, hit["date_dt"], hit["dir_norm"], same_dir=False)
        same_after = nearest_row(after_maxpos, hit["date_dt"], hit["dir_norm"], same_dir=True)
        opp_after = nearest_row(after_maxpos, hit["date_dt"], hit["dir_norm"], same_dir=False)

        bias_gap = num(hit.get("layer3_bias_gap"), np.nan)
        low_blast = bool(layer3_pass and maxpos_pass and after_pass)
        # If Layer3 threshold fails, admitting it would bypass a global H2 top_pct gate.
        if reason == "layer3_threshold_fail":
            low_blast = False

        row = {
            **spec.to_dict(),
            "layer12_present": True,
            "layer12_row_id": row_id,
            "layer12_date": hit.get("date", ""),
            "layer12_entry_time": hit.get("entry_time", ""),
            "layer12_mode": hit.get("mode", ""),
            "layer12_variant": hit.get("variant", ""),
            "layer12_pnl": hit.get("pnl", ""),
            "layer12_sd": hit.get("sd", ""),
            "layer12_spec_pass": hit.get("spec_pass", ""),
            "layer12_spec_reason": hit.get("spec_reason", ""),
            "trigger_by_entry_time": hit.get("trigger_by_entry_time", ""),
            "trigger_by_variant": hit.get("trigger_family_inferred", ""),
            "layer3_eval_time": fmt_dt(hit.get("layer3_eval_time")),
            "Bias_5_original": hit.get("Bias_5", ""),
            "Bias_5_ea": hit.get("Bias_5_ea", ""),
            "layer3_threshold_ea": hit.get("layer3_threshold_ea", ""),
            "layer3_bias_gap": bias_gap,
            "layer3_hist_percentile": hit.get("layer3_hist_percentile", ""),
            "layer3_pass_ea": layer3_pass,
            "layer3_before_maxpos": before_hit is not None,
            "maxpos_active_count_before": before_hit.get("maxpos_active_count_before", "") if before_hit is not None else "",
            "maxpos_active_anchors_before": before_hit.get("maxpos_active_anchors_before", "") if before_hit is not None else "",
            "maxpos_pass": maxpos_pass,
            "layer3_after_maxpos": after_pass,
            "admission_failure_reason": reason,
            "low_blast_admission_rule_supported": low_blast,
            "same_dir_before_maxpos_time": row_ref(same_before)["time"],
            "same_dir_before_maxpos_diff_minutes": row_ref(same_before)["diff_minutes"],
            "same_dir_before_maxpos_mode": row_ref(same_before)["mode"],
            "opp_dir_before_maxpos_time": row_ref(opp_before)["time"],
            "opp_dir_before_maxpos_diff_minutes": row_ref(opp_before)["diff_minutes"],
            "opp_dir_before_maxpos_mode": row_ref(opp_before)["mode"],
            "same_dir_after_maxpos_time": row_ref(same_after)["time"],
            "same_dir_after_maxpos_diff_minutes": row_ref(same_after)["diff_minutes"],
            "same_dir_after_maxpos_mode": row_ref(same_after)["mode"],
            "opp_dir_after_maxpos_time": row_ref(opp_after)["time"],
            "opp_dir_after_maxpos_diff_minutes": row_ref(opp_after)["diff_minutes"],
            "opp_dir_after_maxpos_mode": row_ref(opp_after)["mode"],
        }
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_admission(admission: pd.DataFrame) -> pd.DataFrame:
    return (
        admission.groupby("admission_failure_reason", dropna=False)
        .agg(
            count=("mt5_trade_id", "count"),
            mt5_ids=("mt5_trade_id", lambda s: ";".join(s.astype(str))),
            missing_layer3_targets=("is_missing_layer3_target", lambda s: int(s.map(boolish).sum())),
            control_targets=("is_control_target", lambda s: int(s.map(boolish).sum())),
            avg_layer3_bias_gap=("layer3_bias_gap", lambda s: round(float(pd.to_numeric(s, errors="coerce").mean()), 6)),
        )
        .reset_index()
        .sort_values(["count", "admission_failure_reason"], ascending=[False, True])
    )


def build_final_decision(admission: pd.DataFrame) -> pd.DataFrame:
    missing = admission[admission["is_missing_layer3_target"].map(boolish)].copy()
    controls = admission[admission["is_control_target"].map(boolish)].copy()
    missing_reasons = ";".join(missing["admission_failure_reason"].astype(str).drop_duplicates())
    controls_admitted = bool(controls["layer3_after_maxpos"].map(boolish).all()) if not controls.empty else False
    missing_all_threshold_fail = bool(missing["admission_failure_reason"].astype(str).eq("layer3_threshold_fail").all()) if not missing.empty else False
    low_blast = False
    if not missing.empty and bool(missing["low_blast_admission_rule_supported"].map(boolish).all()):
        low_blast = True
    return pd.DataFrame(
        [
            {
                "target_count": int(len(admission)),
                "missing_layer3_target_count": int(len(missing)),
                "control_target_count": int(len(controls)),
                "missing_layer3_failure_reasons": missing_reasons,
                "missing_all_layer3_threshold_fail": missing_all_threshold_fail,
                "controls_admitted_after_maxpos": controls_admitted,
                "low_blast_admission_rule_supported": low_blast,
                "layer3_admission_prototype_gate_open": False,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "recommended_next_action": "close_runtime_label_layer3_admission_path_return_to_ea_stage_exit_or_independent_signal_gap",
            }
        ]
    )


def simple_table(frame: pd.DataFrame, max_rows: int = 40) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def build_report(
    specs: pd.DataFrame,
    stage_presence: pd.DataFrame,
    admission: pd.DataFrame,
    summary: pd.DataFrame,
    final: pd.DataFrame,
) -> list[str]:
    f = final.iloc[0].to_dict()
    show_cols = [
        "mt5_trade_id",
        "candidate_time",
        "candidate_mode",
        "ea_runtime_mode",
        "layer12_present",
        "Bias_5_ea",
        "layer3_threshold_ea",
        "layer3_bias_gap",
        "layer3_pass_ea",
        "maxpos_active_count_before",
        "maxpos_pass",
        "layer3_after_maxpos",
        "admission_failure_reason",
        "low_blast_admission_rule_supported",
    ]
    show_cols = [col for col in show_cols if col in admission.columns]
    return [
        "# Stage-State Layer3 Admission Gap Audit For Runtime-Label Targets",
        "",
        "## Final Decision",
        "",
        f"- Missing Layer3 target count: `{f['missing_layer3_target_count']}`.",
        f"- Missing target failure reasons: `{f['missing_layer3_failure_reasons']}`.",
        f"- Missing all threshold fail: `{f['missing_all_layer3_threshold_fail']}`.",
        f"- Controls admitted after maxpos: `{f['controls_admitted_after_maxpos']}`.",
        f"- Low-blast admission rule supported: `{f['low_blast_admission_rule_supported']}`.",
        f"- Layer3 admission prototype gate: `{f['layer3_admission_prototype_gate_open']}`.",
        f"- Main signal gate: `{f['main_signal_change_gate_open']}`.",
        f"- EA behavior gate: `{f['ea_behavior_gate_open']}`.",
        f"- Mapping gate: `{f['mapping_change_gate_open']}`.",
        f"- Merge gate: `{f['merge_gate_pass']}`.",
        "",
        "## Target Candidate Specs",
        "",
        simple_table(specs),
        "",
        "## Stage Presence",
        "",
        simple_table(stage_presence, max_rows=80),
        "",
        "## Admission Review",
        "",
        simple_table(admission[show_cols]),
        "",
        "## Admission Summary",
        "",
        simple_table(summary),
        "",
        "## Interpretation",
        "",
        "- `mt5_0052` and `mt5_0054` are present in raw and Layer1/2, but fail the EA-style Layer3 H2 top_pct threshold before max-position is relevant.",
        "- `mt5_0068` and `mt5_0069` have control rows that pass Layer3 and survive max-position, which explains why they reach Stage/dynamic.",
        "- Letting `mt5_0052/0054` in would require bypassing the global Layer3 threshold, not a narrow max-position or displacement correction.",
        "- No main signal, EA behavior, mapping, dynamic-risk, or merge gate is opened here.",
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tables = load_signal_tables()
    retention = read_csv(TARGET_RETENTION)
    runtime_review = read_csv(RUNTIME_TARGET_REVIEW)
    assignments = read_csv(RUNTIME_ASSIGNMENTS) if RUNTIME_ASSIGNMENTS.exists() else pd.DataFrame()
    source_review = read_csv(SOURCE_CASE_REVIEW)

    specs = target_candidate_specs(runtime_review, assignments, retention)
    specs = specs.merge(
        source_review[["mt5_trade_id", "source_primary_classification", "source_secondary_classifications"]],
        on="mt5_trade_id",
        how="left",
    )

    layer12_eval = compute_layer3_all(tables["layer12"])
    before = layer12_eval[layer12_eval["layer3_pass_ea"].map(boolish)].copy()
    before_state = apply_max_pos_3_with_state(before)
    after_maxpos = before_state[before_state["maxpos_pass"].map(boolish)].copy()

    stage_presence = build_stage_presence(specs, tables)
    admission = build_admission_review(specs, layer12_eval, before_state, after_maxpos)
    summary = summarize_admission(admission)
    final = build_final_decision(admission)

    write_csv(specs, OUT_DIR / "layer3_admission_target_specs.csv")
    write_csv(stage_presence, OUT_DIR / "layer3_admission_stage_presence.csv")
    write_csv(layer12_eval, OUT_DIR / "layer12_with_layer3_eval_all.csv")
    write_csv(before_state, OUT_DIR / "layer3_before_maxpos_with_state.csv")
    write_csv(after_maxpos, OUT_DIR / "layer3_after_maxpos_recomputed.csv")
    write_csv(admission, OUT_DIR / "layer3_admission_case_review.csv")
    write_csv(summary, OUT_DIR / "layer3_admission_summary.csv")
    write_csv(final, OUT_DIR / "layer3_admission_final_decision.csv")
    write_md(build_report(specs, stage_presence, admission, summary, final), OUT_DIR / "layer3_admission_gap_audit.md")
    write_md(
        [
            "# Layer3 Admission Gap Runtime-Label Targets",
            "",
            f"- Missing target reasons: `{final.loc[0, 'missing_layer3_failure_reasons']}`.",
            f"- Controls admitted after maxpos: `{bool(final.loc[0, 'controls_admitted_after_maxpos'])}`.",
            f"- Layer3 admission prototype gate: `{bool(final.loc[0, 'layer3_admission_prototype_gate_open'])}`.",
            f"- Merge gate: `{bool(final.loc[0, 'merge_gate_pass'])}`.",
        ],
        OUT_DIR / "README.md",
    )
    print(f"Wrote {OUT_DIR}")
    print(final.to_string(index=False))


if __name__ == "__main__":
    main()
