# -*- coding: utf-8 -*-
"""Full-chain prototype for Layer3 M15 SLOT1 post_n same-family rescue.

This is a non-destructive prototype. It creates versioned signal snapshots,
rebuilds Stage results, prepares dynamic-risk inputs, reruns the current
stage-state execution-model dynamic risk, reruns the existing mapper, and then
compares the result with the accepted stage-state metadatafix baseline.
"""
from __future__ import annotations


import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = Path(r"F:\use_code\MTA5_l")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(SCRIPT_DIR))

import _stage12_combo_test as s12  # noqa: E402
import map_python_mt5_ledger_trades as mapper  # noqa: E402
import prepare_dynamic_risk_inputs_shift90 as prep_inputs  # noqa: E402
import review_execution_model_normalization_20260715 as exec_norm  # noqa: E402


STRATEGY_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

BASE_SIGNAL_ROOT = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714"
BASE_SIGNAL_DIR = BASE_SIGNAL_ROOT / "python_h2_context_q2early"
BASE_M30 = BASE_SIGNAL_ROOT / "m30_prepared_with_mt5_shift90.csv"

FEASIBILITY_DIR = VALIDATION_DIR / "stage_state_targeted_signal_prototype_feasibility_20260717"
BASE_INPUT_DIR = VALIDATION_DIR / "dynamic_risk_inputs_shift90_metadatafix_20260714"
BASE_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
BASE_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"
STAGE_STATE_LEDGER_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"

OUT_DIR = VALIDATION_DIR / "stage_state_layer3_m15_slot1_postn_rescue_full_chain_20260717"
SIGNALS_ROOT = OUT_DIR / "signals"
INPUTS_ROOT = OUT_DIR / "dynamic_inputs"
DYNAMIC_ROOT = OUT_DIR / "dynamic_alignment"
MAPPING_ROOT = OUT_DIR / "mapping"

RAW_FILE = "raw_candidates.csv"
LAYER12_FILE = "候选信号_Layer1_Layer2通过.csv"
LAYER3_FILE = "最终信号_Layer3入选.csv"
STAGE_FILE = "执行交易_Stage结果.csv"

STAGE1_R = 2.0
STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0
TARGET_MT5_ID = "mt5_0076"
TARGET_TIME = pd.Timestamp("2026-03-24 12:00:00")


@dataclass(frozen=True)
class Variant:
    name: str
    description: str


VARIANTS = [
    Variant("add_then_maxpos_all29", "append all 29 rescue candidates, then apply current max-pos-3 gate"),
    Variant(
        "replace_nearest_opposite_all29",
        "remove nearest opposite Layer3 rows for all 29 candidates, append all candidates, then apply max-pos-3",
    ),
    Variant(
        "target_mt5_0076_replace_nearest_opposite",
        "only add the exact mt5_0076 target candidate and remove its nearest opposite Layer3 row",
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
    return pd.to_datetime(series.astype(str).str.strip().str.replace(".", "-", regex=False), errors="coerce")


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


def add_norm_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["date_dt"] = out["date"].map(parse_dt)
    out["dir_norm"] = out["dir"].map(normalize_dir)
    out["mode_family_norm"] = out["mode"].map(mode_family)
    if "trigger" in out.columns:
        trigger = out["trigger"].fillna("").astype(str).str.strip()
        inferred = out.get("variant", pd.Series("", index=out.index)).map(trigger_from_variant)
        out["trigger_family_norm"] = trigger.where(trigger.ne(""), inferred)
    else:
        out["trigger_family_norm"] = out.get("variant", pd.Series("", index=out.index)).map(trigger_from_variant)
    return out


def key_cols(frame: pd.DataFrame) -> pd.DataFrame:
    out = add_norm_columns(frame)
    return out[["date_dt", "dir_norm", "mode_family_norm", "trigger_family_norm"]].copy()


def apply_max_pos_3(picked: pd.DataFrame) -> pd.DataFrame:
    if picked.empty:
        return picked.copy()
    rows = []
    active: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for _, row in picked.sort_values(["date_dt", "prototype_priority", "mode"]).iterrows():
        anchor = row["date_dt"]
        if pd.isna(anchor):
            continue
        active = [item for item in active if item[0] > anchor]
        if len(active) < 3:
            rows.append(row)
            active.append((anchor + pd.Timedelta(hours=24), anchor))
    return pd.DataFrame(rows).reset_index(drop=True)


def load_base_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = read_csv(BASE_SIGNAL_DIR / RAW_FILE)
    layer12 = add_norm_columns(read_csv(BASE_SIGNAL_DIR / LAYER12_FILE))
    layer3 = add_norm_columns(read_csv(BASE_SIGNAL_DIR / LAYER3_FILE))
    m30 = read_csv(BASE_M30)
    m30["date"] = parse_dt_series(m30["date"])
    return raw, layer12, layer3, m30


def load_rescue_details() -> pd.DataFrame:
    details = read_csv(FEASIBILITY_DIR / "targeted_signal_prototype_blast_radius_details.csv")
    details = details[details["candidate_rule"].eq("layer3_m15_slot1_postn_same_family_rescue")].copy()
    details["row_time_dt"] = details["row_time"].map(parse_dt)
    details["nearest_opposite_layer3_time_dt"] = details["nearest_opposite_layer3_time"].map(parse_dt)
    details["dir_norm"] = details["dir_norm"].map(normalize_dir)
    details["mode_family"] = details["mode_family"].map(mode_family)
    return details.sort_values("row_time_dt").reset_index(drop=True)


def select_rescue_rows(layer12: pd.DataFrame, details: pd.DataFrame) -> pd.DataFrame:
    rows: list[pd.Series] = []
    for _, detail in details.iterrows():
        hit = layer12[
            layer12["date_dt"].eq(detail["row_time_dt"])
            & layer12["dir_norm"].eq(detail["dir_norm"])
            & layer12["mode_family_norm"].eq(detail["mode_family"])
            & layer12["mode"].astype(str).eq(str(detail["mode"]))
            & layer12["variant"].astype(str).eq(str(detail["variant"]))
        ].copy()
        if hit.empty:
            continue
        rows.append(hit.iloc[0])
    if not rows:
        return layer12.iloc[0:0].copy()
    out = pd.DataFrame(rows).reset_index(drop=True)
    out["prototype_candidate_rule"] = "layer3_m15_slot1_postn_same_family_rescue"
    out["prototype_added_candidate"] = True
    return out


def mark_base_layer3(layer3: pd.DataFrame) -> pd.DataFrame:
    out = layer3.copy()
    out["prototype_candidate_rule"] = ""
    out["prototype_added_candidate"] = False
    out["prototype_original_layer3"] = True
    out["prototype_priority"] = 0
    return out


def remove_nearest_opposites(layer3: pd.DataFrame, details: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = layer3.copy()
    remove_mask = pd.Series(False, index=out.index)
    removal_rows: list[pd.Series] = []
    for _, detail in details.iterrows():
        time = detail["nearest_opposite_layer3_time_dt"]
        if pd.isna(time):
            continue
        hit = out[
            out["date_dt"].eq(time)
            & out["dir_norm"].eq(normalize_dir(detail["nearest_opposite_layer3_dir"]))
            & out["mode_family_norm"].eq(mode_family(detail["nearest_opposite_layer3_mode"]))
        ].copy()
        if hit.empty:
            continue
        idx = hit.index[0]
        if not bool(remove_mask.loc[idx]):
            row = out.loc[idx].copy()
            row["removed_for_candidate_time"] = detail["row_time_dt"]
            removal_rows.append(row)
        remove_mask.loc[idx] = True
    removed = pd.DataFrame(removal_rows).reset_index(drop=True) if removal_rows else out.iloc[0:0].copy()
    return out[~remove_mask].copy(), removed


def build_variant_layer3(
    variant: Variant,
    layer3: pd.DataFrame,
    rescue_rows: pd.DataFrame,
    details: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = mark_base_layer3(layer3)
    candidates = rescue_rows.copy()
    candidates["prototype_original_layer3"] = False
    candidates["prototype_priority"] = -1

    detail_subset = details.copy()
    if variant.name == "target_mt5_0076_replace_nearest_opposite":
        detail_subset = detail_subset[detail_subset["row_time_dt"].eq(TARGET_TIME)].copy()
        candidates = candidates[candidates["date_dt"].eq(TARGET_TIME)].copy()

    removed = base.iloc[0:0].copy()
    if variant.name in {"replace_nearest_opposite_all29", "target_mt5_0076_replace_nearest_opposite"}:
        base, removed = remove_nearest_opposites(base, detail_subset)

    combined = pd.concat([base, candidates], ignore_index=True, sort=False)
    combined = combined.drop_duplicates(subset=["date_dt", "dir_norm", "mode", "variant"], keep="first")
    before_maxpos = combined.copy()
    after_maxpos = apply_max_pos_3(before_maxpos)

    # Keep CSV-compatible original columns plus prototype columns.
    for col in layer3.columns:
        if col not in after_maxpos.columns:
            after_maxpos[col] = ""
    after_maxpos = after_maxpos.sort_values("date_dt").reset_index(drop=True)
    before_maxpos = before_maxpos.sort_values("date_dt").reset_index(drop=True)
    return after_maxpos, before_maxpos, removed


def build_stage_results(m30: pd.DataFrame, layer3_proto: pd.DataFrame) -> pd.DataFrame:
    signals = layer3_proto.copy()
    signals["date"] = signals["date_dt"]
    stage = s12.summarize_variant(m30, signals, STAGE1_R, STAGE2_TRAIL_R, STAGE2_FORCE_R)
    return stage


def write_signal_snapshot(
    variant: Variant,
    raw: pd.DataFrame,
    layer12: pd.DataFrame,
    layer3_proto: pd.DataFrame,
    stage: pd.DataFrame,
) -> Path:
    signal_dir = SIGNALS_ROOT / variant.name
    signal_dir.mkdir(parents=True, exist_ok=True)
    export_csv(raw, signal_dir / RAW_FILE)
    export_csv(layer12.drop(columns=[c for c in ["date_dt", "dir_norm", "mode_family_norm", "trigger_family_norm"] if c in layer12.columns]), signal_dir / LAYER12_FILE)
    drop_norm = [c for c in ["date_dt", "dir_norm", "mode_family_norm", "trigger_family_norm"] if c in layer3_proto.columns]
    export_csv(layer3_proto.drop(columns=drop_norm), signal_dir / LAYER3_FILE)
    export_csv(stage, signal_dir / STAGE_FILE)
    return signal_dir


def run_prepare_inputs(variant: Variant, signal_dir: Path) -> Path:
    out_dir = INPUTS_ROOT / variant.name
    old_out = prep_inputs.OUT_DIR
    old_signal_dir = prep_inputs.SHIFT90_SIGNAL_DIR
    old_m30 = prep_inputs.SHIFT90_M30
    old_sources = prep_inputs.SOURCES
    try:
        prep_inputs.OUT_DIR = out_dir
        prep_inputs.SHIFT90_SIGNAL_DIR = signal_dir
        prep_inputs.SHIFT90_M30 = BASE_M30
        prep_inputs.SOURCES = [
            prep_inputs.SourceConfig("python_only", DATA_DIR / "signals"),
            prep_inputs.SourceConfig("python_mt5", signal_dir, BASE_M30),
        ]
        prep_inputs.main()
    finally:
        prep_inputs.OUT_DIR = old_out
        prep_inputs.SHIFT90_SIGNAL_DIR = old_signal_dir
        prep_inputs.SHIFT90_M30 = old_m30
        prep_inputs.SOURCES = old_sources
    return out_dir


def run_dynamic_and_mapping(variant: Variant, input_dir: Path) -> tuple[Path, Path]:
    dynamic_dir = DYNAMIC_ROOT / variant.name
    mapping_dir = MAPPING_ROOT / variant.name

    old_ledger = exec_norm.LEDGER_DIR
    old_base_ledger = exec_norm.base_dyn.LEDGER_DIR
    old_mapper_input = mapper.INPUT_DIR
    old_mapper_out = mapper.OUT_DIR
    try:
        exec_norm.LEDGER_DIR = STAGE_STATE_LEDGER_DIR
        exec_norm.base_dyn.LEDGER_DIR = STAGE_STATE_LEDGER_DIR
        scenario = exec_norm.Scenario(
            name=variant.name,
            input_dir=input_dir,
            baseline_dynamic_dir=BASE_DYNAMIC_DIR,
            baseline_mapping_dir=BASE_MAPPING_DIR,
            exec_dynamic_dir=dynamic_dir,
            exec_mapping_dir=mapping_dir,
            python_mt5_variant=f"layer3_m15_slot1_postn_rescue_{variant.name}",
        )
        exec_norm.run_dynamic_alignment(scenario)
        # Label the MT5 row as the current accepted stage-state ledger.
        summary_path = dynamic_dir / "dynamic_risk_compare_summary.csv"
        summary = read_csv(summary_path)
        if "source_variant" in summary.columns:
            summary.loc[summary["source"].eq("mt5_ledger"), "source_variant"] = "mt5_stage_state_full_2018_20260707_20260716"
            export_csv(summary, summary_path)
        exec_norm.run_mapping(scenario)
    finally:
        exec_norm.LEDGER_DIR = old_ledger
        exec_norm.base_dyn.LEDGER_DIR = old_base_ledger
        mapper.INPUT_DIR = old_mapper_input
        mapper.OUT_DIR = old_mapper_out
    return dynamic_dir, mapping_dir


def source_row(frame: pd.DataFrame, source: str) -> pd.Series:
    rows = frame[frame["source"].astype(str).eq(source)]
    if rows.empty:
        raise ValueError(f"missing source={source}")
    return rows.iloc[0]


def scenario_stats(name: str, dynamic_dir: Path, mapping_dir: Path, note: str) -> dict[str, object]:
    dyn = read_csv(dynamic_dir / "dynamic_risk_compare_summary.csv")
    mapping = read_csv(mapping_dir / "unique_match_summary.csv")
    py = source_row(dyn, "python_mt5")
    mt5 = source_row(dyn, "mt5_ledger")
    mp = source_row(mapping, "python_mt5")
    direct_gap = float(py["final_balance"]) - float(mt5["final_balance"])
    matched_diff = float(mp["matched_profit_diff"])
    return {
        "scenario": name,
        "python_trade_count": int(py["trade_count"]),
        "mt5_trade_count": int(mt5["trade_count"]),
        "python_final_balance": round(float(py["final_balance"]), 6),
        "mt5_final_balance": round(float(mt5["final_balance"]), 6),
        "direct_gap_py_minus_mt5": round(direct_gap, 6),
        "matched_unique": int(mp["matched_unique"]),
        "reliable_tier_matched": int(mp["reliable_tier_matched"]),
        "relaxed_tier_matched": int(mp["relaxed_tier_matched"]),
        "python_unmatched": int(mp["python_unmatched"]),
        "mt5_unmatched": int(mp["mt5_unmatched"]),
        "matched_profit_diff_py_minus_mt5": round(matched_diff, 6),
        "signal_set_gap_py_minus_mt5": round(direct_gap - matched_diff, 6),
        "note": note,
    }


def target_status(name: str, dynamic_dir: Path, mapping_dir: Path) -> dict[str, object]:
    trades = read_csv(dynamic_dir / "python_mt5_dynamic_risk_trades.csv")
    trades["date_dt"] = parse_dt_series(trades["date"])
    target_trades = trades[trades["date_dt"].eq(TARGET_TIME)].copy()

    matches = read_csv(mapping_dir / "python_mt5_mt5_unique_matches.csv")
    mt5_hit = matches[matches["mt5_trade_id"].astype(str).eq(TARGET_MT5_ID)].copy()
    py_target_hit = pd.DataFrame()
    if "py_date" in matches.columns:
        matches["py_date_dt"] = parse_dt_series(matches["py_date"])
        py_target_hit = matches[matches["py_date_dt"].eq(TARGET_TIME)].copy()

    row: dict[str, object] = {
        "scenario": name,
        "target_time": TARGET_TIME,
        "target_dynamic_rows": int(len(target_trades)),
        "target_dynamic_profit_sum": round(
            float(pd.to_numeric(target_trades.get("dynamic_total_$", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum()),
            6,
        ),
        "target_dynamic_modes": ";".join(target_trades.get("mode", pd.Series(dtype=str)).astype(str).tolist()) if len(target_trades) else "",
        "target_dynamic_variants": ";".join(target_trades.get("variant", pd.Series(dtype=str)).astype(str).tolist()) if len(target_trades) else "",
        "mt5_0076_matched": not mt5_hit.empty,
        "target_python_time_matched": not py_target_hit.empty,
    }
    if not mt5_hit.empty:
        hit = mt5_hit.iloc[0]
        row.update(
            {
                "mt5_0076_match_tier": hit.get("match_tier", ""),
                "mt5_0076_py_trade_id": hit.get("py_trade_id", ""),
                "mt5_0076_py_date": hit.get("py_date", ""),
                "mt5_0076_py_trigger_family": hit.get("py_trigger_family", ""),
                "mt5_0076_py_mode_family": hit.get("py_mode_family", ""),
                "mt5_0076_py_profit": hit.get("py_profit", ""),
                "mt5_0076_mt5_profit": hit.get("mt5_profit", ""),
                "mt5_0076_profit_diff": hit.get("profit_diff", ""),
            }
        )
    else:
        row.update(
            {
                "mt5_0076_match_tier": "",
                "mt5_0076_py_trade_id": "",
                "mt5_0076_py_date": "",
                "mt5_0076_py_trigger_family": "",
                "mt5_0076_py_mode_family": "",
                "mt5_0076_py_profit": "",
                "mt5_0076_mt5_profit": "",
                "mt5_0076_profit_diff": "",
            }
        )
    return row


def build_variant_signal_summary(
    variant: Variant,
    before_maxpos: pd.DataFrame,
    after_maxpos: pd.DataFrame,
    removed: pd.DataFrame,
    rescue_rows: pd.DataFrame,
) -> dict[str, object]:
    after_added = after_maxpos[after_maxpos.get("prototype_added_candidate", False).astype(bool)].copy()
    before_added = before_maxpos[before_maxpos.get("prototype_added_candidate", False).astype(bool)].copy()
    target_after = after_added[after_added["date_dt"].eq(TARGET_TIME)].copy() if not after_added.empty else after_added
    return {
        "variant": variant.name,
        "description": variant.description,
        "base_layer3_rows": int(len(read_csv(BASE_SIGNAL_DIR / LAYER3_FILE))),
        "available_rescue_candidates": int(len(rescue_rows)),
        "before_maxpos_rows": int(len(before_maxpos)),
        "after_maxpos_rows": int(len(after_maxpos)),
        "candidate_rows_before_maxpos": int(len(before_added)),
        "candidate_rows_after_maxpos": int(len(after_added)),
        "removed_nearest_opposite_rows": int(len(removed)),
        "target_candidate_after_maxpos": int(len(target_after)),
        "target_candidate_after_maxpos_profit_sum": round(
            float(pd.to_numeric(target_after.get("pnl", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum()),
            6,
        )
        if len(target_after)
        else 0.0,
    }


def build_decision(before_after: pd.DataFrame, target_review: pd.DataFrame, signal_summary: pd.DataFrame) -> pd.DataFrame:
    base = before_after[before_after["scenario"].eq("current_stage_state_metadatafix")].iloc[0]
    rows: list[dict[str, object]] = []
    for _, row in before_after[~before_after["scenario"].eq("current_stage_state_metadatafix")].iterrows():
        target = target_review[target_review["scenario"].eq(row["scenario"])].iloc[0]
        sig = signal_summary[signal_summary["variant"].eq(row["scenario"])].iloc[0]
        matched_not_worse = int(row["matched_unique"]) >= int(base["matched_unique"])
        reliable_not_worse = int(row["reliable_tier_matched"]) >= int(base["reliable_tier_matched"])
        direct_gap_not_worse = abs(float(row["direct_gap_py_minus_mt5"])) <= abs(float(base["direct_gap_py_minus_mt5"]))
        signal_gap_not_worse = abs(float(row["signal_set_gap_py_minus_mt5"])) <= abs(float(base["signal_set_gap_py_minus_mt5"]))
        target_improved = bool(target["mt5_0076_matched"]) or bool(target["target_python_time_matched"])
        quality_improved = int(row["matched_unique"]) > int(base["matched_unique"]) or int(row["reliable_tier_matched"]) > int(base["reliable_tier_matched"])
        merge_gate = bool(target_improved and quality_improved and matched_not_worse and reliable_not_worse and direct_gap_not_worse and signal_gap_not_worse)
        rows.append(
            {
                "variant": row["scenario"],
                "candidate_rows_after_maxpos": int(sig["candidate_rows_after_maxpos"]),
                "target_candidate_after_maxpos": int(sig["target_candidate_after_maxpos"]),
                "mt5_0076_matched": bool(target["mt5_0076_matched"]),
                "target_python_time_matched": bool(target["target_python_time_matched"]),
                "matched_unique_delta": int(row["matched_unique"]) - int(base["matched_unique"]),
                "reliable_tier_delta": int(row["reliable_tier_matched"]) - int(base["reliable_tier_matched"]),
                "python_unmatched_delta": int(row["python_unmatched"]) - int(base["python_unmatched"]),
                "mt5_unmatched_delta": int(row["mt5_unmatched"]) - int(base["mt5_unmatched"]),
                "direct_gap_delta": round(float(row["direct_gap_py_minus_mt5"]) - float(base["direct_gap_py_minus_mt5"]), 6),
                "signal_set_gap_delta": round(float(row["signal_set_gap_py_minus_mt5"]) - float(base["signal_set_gap_py_minus_mt5"]), 6),
                "matched_not_worse": matched_not_worse,
                "reliable_not_worse": reliable_not_worse,
                "direct_gap_not_worse": direct_gap_not_worse,
                "signal_gap_not_worse": signal_gap_not_worse,
                "quality_improved": quality_improved,
                "target_improved": target_improved,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": merge_gate,
                "decision": "diagnostic_only" if not merge_gate else "prototype_candidate_needs_manual_review",
            }
        )
    return pd.DataFrame(rows)


def markdown_table(frame: pd.DataFrame, columns: list[str] | None = None, max_rows: int = 80) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.copy()
    if columns is not None:
        display = display[[col for col in columns if col in display.columns]]
    return display.head(max_rows).to_markdown(index=False)


def write_report(
    signal_summary: pd.DataFrame,
    before_after: pd.DataFrame,
    target_review: pd.DataFrame,
    decision: pd.DataFrame,
) -> None:
    lines = [
        "# Stage-State Layer3 M15 SLOT1 post_n Rescue Full-Chain Prototype",
        "",
        "## Scope",
        "",
        "- Non-destructive prototype only.",
        "- Builds versioned signal snapshots and reruns Stage, dynamic risk, and mapping.",
        "- Does not modify baseline Python signals, EA behavior, or mapping rules.",
        "",
        "## Signal Variants",
        "",
        markdown_table(signal_summary),
        "",
        "## Before / After",
        "",
        markdown_table(before_after),
        "",
        "## Target mt5_0076",
        "",
        markdown_table(target_review),
        "",
        "## Decision",
        "",
        markdown_table(decision),
        "",
        "## Interpretation",
        "",
        "- `add_then_maxpos_all29` tests whether the current max-pos gate naturally admits the rescue candidates.",
        "- `replace_nearest_opposite_all29` tests whether the nearby opposite Layer3 selections are blocking the same-family candidates.",
        "- `target_mt5_0076_replace_nearest_opposite` is the narrowest target proof for the selected residual case.",
        "- A merge candidate requires improved target matching plus no deterioration in matched/reliable counts and gap components.",
        "",
        "## Output Files",
        "",
        "- `prototype_signal_variant_summary.csv`",
        "- `prototype_full_chain_before_after.csv`",
        "- `prototype_target_mt5_0076_review.csv`",
        "- `prototype_layer3_rescue_decision.csv`",
        "- `signals/<variant>/`",
        "- `dynamic_inputs/<variant>/`",
        "- `dynamic_alignment/<variant>/`",
        "- `mapping/<variant>/`",
    ]
    write_text(OUT_DIR / "stage_state_layer3_m15_slot1_postn_rescue_full_chain_review.md", "\n".join(lines))
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# stage_state_layer3_m15_slot1_postn_rescue_full_chain_20260717",
                "",
                "Full-chain, non-destructive prototype for Layer3 M15 SLOT1 post_n same-family rescue.",
                "",
                "All outputs are diagnostic snapshots. They are not a final strategy version.",
            ]
        ),
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if SIGNALS_ROOT.exists():
        shutil.rmtree(SIGNALS_ROOT)
    if INPUTS_ROOT.exists():
        shutil.rmtree(INPUTS_ROOT)
    if DYNAMIC_ROOT.exists():
        shutil.rmtree(DYNAMIC_ROOT)
    if MAPPING_ROOT.exists():
        shutil.rmtree(MAPPING_ROOT)

    raw, layer12, layer3, m30 = load_base_tables()
    details = load_rescue_details()
    rescue_rows = select_rescue_rows(layer12, details)
    export_csv(details, OUT_DIR / "prototype_layer3_rescue_candidates_source.csv")
    export_csv(rescue_rows, OUT_DIR / "prototype_layer3_rescue_candidates_matched_layer12.csv")

    signal_rows: list[dict[str, object]] = []
    full_chain_rows = [
        scenario_stats(
            "current_stage_state_metadatafix",
            BASE_DYNAMIC_DIR,
            BASE_MAPPING_DIR,
            "current accepted stage-state metadatafix baseline",
        )
    ]
    target_rows = [target_status("current_stage_state_metadatafix", BASE_DYNAMIC_DIR, BASE_MAPPING_DIR)]

    for variant in VARIANTS:
        layer3_proto, before_maxpos, removed = build_variant_layer3(variant, layer3, rescue_rows, details)
        stage = build_stage_results(m30, layer3_proto)
        signal_dir = write_signal_snapshot(variant, raw, layer12, layer3_proto, stage)
        export_csv(before_maxpos, OUT_DIR / f"{variant.name}_layer3_before_maxpos.csv")
        export_csv(removed, OUT_DIR / f"{variant.name}_removed_nearest_opposite_rows.csv")

        input_dir = run_prepare_inputs(variant, signal_dir)
        dynamic_dir, mapping_dir = run_dynamic_and_mapping(variant, input_dir)

        signal_rows.append(build_variant_signal_summary(variant, before_maxpos, layer3_proto, removed, rescue_rows))
        full_chain_rows.append(scenario_stats(variant.name, dynamic_dir, mapping_dir, variant.description))
        target_rows.append(target_status(variant.name, dynamic_dir, mapping_dir))

    signal_summary = pd.DataFrame(signal_rows)
    before_after = pd.DataFrame(full_chain_rows)
    target_review = pd.DataFrame(target_rows)
    decision = build_decision(before_after, target_review, signal_summary)

    export_csv(signal_summary, OUT_DIR / "prototype_signal_variant_summary.csv")
    export_csv(before_after, OUT_DIR / "prototype_full_chain_before_after.csv")
    export_csv(target_review, OUT_DIR / "prototype_target_mt5_0076_review.csv")
    export_csv(decision, OUT_DIR / "prototype_layer3_rescue_decision.csv")
    write_report(signal_summary, before_after, target_review, decision)
    print((OUT_DIR / "stage_state_layer3_m15_slot1_postn_rescue_full_chain_review.md").read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    main()
