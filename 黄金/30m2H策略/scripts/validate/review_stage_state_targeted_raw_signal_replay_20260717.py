# -*- coding: utf-8 -*-
"""Targeted raw-signal replay for directional/MT5-only residual cases.

This script reviews the four remaining cases from the targeted signal replay:
mt5_0076, mt5_0067, mt5_0044, and mt5_0026. It links MT5-only signals to the
available Python raw -> Layer1/2 -> Layer3 -> executed chain and classifies the
loss point without changing strategy or mapping logic.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
DATA_DIR = STRATEGY_DIR / "data"

TARGETED_REPLAY_DIR = VALIDATION_DIR / "stage_state_targeted_signal_replay_20260717"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
DYNAMIC_INPUT_DIR = VALIDATION_DIR / "dynamic_risk_inputs_shift90_metadatafix_20260714"
SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"

OUT_DIR = VALIDATION_DIR / "stage_state_targeted_raw_signal_replay_20260717"

TARGET_IDS = {"mt5_0076", "mt5_0067", "mt5_0044", "mt5_0026"}
WINDOWS_MINUTES = [0, 60, 180, 1440]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def safe_float(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


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


def infer_trigger(row: pd.Series) -> str:
    trigger = str(row.get("trigger", row.get("trigger_family", ""))).strip()
    if trigger:
        return trigger
    text = " ".join(str(row.get(col, "")) for col in ["variant", "mode", "signal_src"]).lower()
    if "slot1" in text or "m15" in text:
        return "M15 SLOT1"
    return "M30 CLOSE"


def prep_signal_table(frame: pd.DataFrame, source_table: str) -> pd.DataFrame:
    out = frame.copy()
    out["source_table"] = source_table
    out["target_time"] = out["date"].map(parse_dt)
    out["dir_norm"] = out["dir"].map(normalize_dir)
    out["trigger_family"] = out.apply(infer_trigger, axis=1)
    out["mode_family"] = out["mode"].map(mode_family)
    out["mode_or_signal_src"] = out.get("mode", "")
    out["variant"] = out.get("variant", "")
    out["spec_pass_bool"] = out.get("spec_pass", False).map(bool_value) if "spec_pass" in out.columns else False
    out["profit"] = pd.to_numeric(
        out.get("total_$", out.get("pnl", pd.Series(0.0, index=out.index))),
        errors="coerce",
    )
    return out


def load_signal_chain() -> dict[str, pd.DataFrame]:
    raw = prep_signal_table(read_csv(SIGNAL_DIR / "raw_candidates.csv"), "python_raw_candidates")
    layer12 = prep_signal_table(read_csv(SIGNAL_DIR / "候选信号_Layer1_Layer2通过.csv"), "python_layer12_pass")
    layer3 = prep_signal_table(read_csv(SIGNAL_DIR / "最终信号_Layer3入选.csv"), "python_layer3_selected")

    stage = read_csv(SIGNAL_DIR / "执行交易_Stage结果.csv").copy()
    layer3_key = layer3[
        ["date", "mode", "dir", "trigger_family", "variant", "spec_pass", "spec_reason"]
    ].drop_duplicates(["date", "mode", "dir"])
    stage = stage.merge(layer3_key, on=["date", "mode", "dir"], how="left")
    stage = prep_signal_table(stage, "python_stage_result_export")

    dynamic = read_csv(DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv").copy()
    dynamic["py_trade_id"] = [f"python_mt5_{i + 1:04d}" for i in range(len(dynamic))]
    dynamic["source_table"] = "python_dynamic_executed"
    dynamic["target_time"] = dynamic["date"].map(parse_dt)
    dynamic["dir_norm"] = dynamic["dir"].map(normalize_dir)
    dynamic["mode_family"] = dynamic["mode_family"].map(mode_family)
    dynamic["trigger_family"] = dynamic["trigger_family"].astype(str)
    dynamic["mode_or_signal_src"] = dynamic["mode"]
    dynamic["variant"] = dynamic["variant"].astype(str)
    dynamic["profit"] = pd.to_numeric(dynamic["dynamic_total_$"], errors="coerce")

    inputs = read_csv(DYNAMIC_INPUT_DIR / "python_mt5_dynamic_risk_inputs.csv").copy()
    inputs["target_time"] = inputs["date"].map(parse_dt)
    inputs["dir_norm"] = inputs["dir"].map(normalize_dir)
    inputs["mode_family"] = inputs["mode"].map(mode_family)
    inputs["stage3_time_input"] = inputs["stage3_time"].map(parse_dt) if "stage3_time" in inputs.columns else pd.NaT
    dynamic = dynamic.merge(
        inputs[["target_time", "dir_norm", "mode", "stage3_time_input"]].drop_duplicates(
            ["target_time", "dir_norm", "mode"]
        ),
        on=["target_time", "dir_norm", "mode"],
        how="left",
    )

    return {
        "python_raw_candidates": raw,
        "python_layer12_pass": layer12,
        "python_layer3_selected": layer3,
        "python_stage_result_export": stage,
        "python_dynamic_executed": dynamic,
    }


def load_mt5_unique() -> pd.DataFrame:
    mt5 = read_csv(DYNAMIC_DIR / "mt5_ledger_unique_signals.csv").copy()
    mt5["source_table"] = "mt5_unique_ledger"
    mt5["mt5_trade_id"] = [f"mt5_{i + 1:04d}" for i in range(len(mt5))]
    mt5["signal_anchor_dt"] = mt5["signal_anchor_time"].map(parse_dt)
    mt5["target_time"] = mt5["signal_anchor_dt"] + pd.Timedelta(minutes=90)
    mt5["dir_norm"] = mt5["dir"].map(normalize_dir)
    mt5["mode_family"] = mt5["mode_family"].map(mode_family)
    mt5["trigger_family"] = mt5["trigger_family"].astype(str)
    mt5["mode_or_signal_src"] = mt5["signal_src"]
    mt5["profit"] = pd.to_numeric(mt5["net_profit"], errors="coerce")
    return mt5


def load_targets() -> pd.DataFrame:
    review = read_csv(TARGETED_REPLAY_DIR / "targeted_signal_replay_case_review.csv").copy()
    targets = review[review["trade_id"].astype(str).isin(TARGET_IDS)].copy()
    targets["target_time"] = targets["target_time"].map(parse_dt)
    targets["dir_norm"] = targets["dir_norm"].map(normalize_dir)
    targets["mode_family"] = targets["mode_family"].map(mode_family)
    targets["abs_gap_effect_$"] = pd.to_numeric(targets["abs_gap_effect_$"], errors="coerce").fillna(0.0)
    return targets.sort_values("abs_gap_effect_$", ascending=False).reset_index(drop=True)


def with_time_diff(table: pd.DataFrame, target_time: pd.Timestamp) -> pd.DataFrame:
    out = table.copy()
    out["time_diff_minutes"] = (out["target_time"] - target_time).dt.total_seconds() / 60.0
    out["abs_time_diff_minutes"] = out["time_diff_minutes"].abs()
    return out[pd.notna(out["abs_time_diff_minutes"])].copy()


def equivalent_rows(table: pd.DataFrame, target: pd.Series, window_minutes: int) -> pd.DataFrame:
    rows = with_time_diff(table, target["target_time"])
    rows = rows[rows["abs_time_diff_minutes"] <= window_minutes].copy()
    if rows.empty:
        return rows
    same_dir = rows["dir_norm"].astype(str) == str(target["dir_norm"])
    same_mode = rows["mode_family"].astype(str) == str(target["mode_family"])
    same_trigger = rows["trigger_family"].astype(str) == str(target["trigger_family"])
    table_name = str(table["source_table"].iloc[0]) if "source_table" in table.columns and not table.empty else ""
    if str(target["trigger_family"]) == "M15 SLOT1" and table_name == "python_raw_candidates":
        return rows[same_dir & same_mode].copy()
    return rows[same_dir & same_trigger & same_mode].copy()


def count_rows(table: pd.DataFrame, target: pd.Series, window_minutes: int, relation: str) -> int:
    rows = with_time_diff(table, target["target_time"])
    rows = rows[rows["abs_time_diff_minutes"] <= window_minutes].copy()
    if rows.empty:
        return 0
    same_dir = rows["dir_norm"].astype(str) == str(target["dir_norm"])
    same_trigger = rows["trigger_family"].astype(str) == str(target["trigger_family"])
    same_mode = rows["mode_family"].astype(str) == str(target["mode_family"])
    if relation == "same_family":
        return int((same_dir & same_trigger & same_mode).sum())
    if relation == "raw_equivalent":
        if str(target["trigger_family"]) == "M15 SLOT1":
            return int((same_dir & same_mode).sum())
        return int((same_dir & same_trigger & same_mode).sum())
    if relation == "same_dir":
        return int(same_dir.sum())
    if relation == "opposite_dir":
        return int((~same_dir).sum())
    if relation == "opposite_dir_same_mode":
        return int(((~same_dir) & same_mode).sum())
    return int(len(rows))


def nearest_row(table: pd.DataFrame, target: pd.Series, relation: str) -> pd.Series:
    rows = with_time_diff(table, target["target_time"])
    if rows.empty:
        return pd.Series(dtype=object)
    if relation == "equivalent":
        rows = equivalent_rows(table, target, 1440)
    elif relation == "same_dir":
        rows = rows[rows["dir_norm"].astype(str) == str(target["dir_norm"])].copy()
    elif relation == "opposite_dir":
        rows = rows[rows["dir_norm"].astype(str) != str(target["dir_norm"])].copy()
    if rows.empty:
        return pd.Series(dtype=object)
    return rows.sort_values("abs_time_diff_minutes").iloc[0]


def build_window_counts(targets: pd.DataFrame, tables: dict[str, pd.DataFrame], mt5: pd.DataFrame) -> pd.DataFrame:
    rows = []
    all_tables = dict(tables)
    all_tables["mt5_unique_ledger"] = mt5
    for _, target in targets.iterrows():
        for table_name, table in all_tables.items():
            for window in WINDOWS_MINUTES:
                rows.append(
                    {
                        "target_case_id": target["target_case_id"],
                        "trade_id": target["trade_id"],
                        "source_table": table_name,
                        "window_minutes": window,
                        "raw_equivalent_count": count_rows(table, target, window, "raw_equivalent"),
                        "same_family_count": count_rows(table, target, window, "same_family"),
                        "same_dir_count": count_rows(table, target, window, "same_dir"),
                        "opposite_dir_count": count_rows(table, target, window, "opposite_dir"),
                        "opposite_dir_same_mode_count": count_rows(table, target, window, "opposite_dir_same_mode"),
                    }
                )
    return pd.DataFrame(rows)


def context_rows(targets: pd.DataFrame, tables: dict[str, pd.DataFrame], mt5: pd.DataFrame) -> pd.DataFrame:
    rows = []
    all_tables = dict(tables)
    all_tables["mt5_unique_ledger"] = mt5
    for _, target in targets.iterrows():
        for table_name, table in all_tables.items():
            nearby = with_time_diff(table, target["target_time"])
            nearby = nearby[nearby["abs_time_diff_minutes"] <= 1440].copy()
            if nearby.empty:
                continue
            nearby = nearby.sort_values(["abs_time_diff_minutes", "target_time"]).head(12)
            for _, src in nearby.iterrows():
                rows.append(
                    {
                        "target_case_id": target["target_case_id"],
                        "target_trade_id": target["trade_id"],
                        "source_table": table_name,
                        "row_id": src.get("py_trade_id", src.get("mt5_trade_id", "")),
                        "row_time": fmt_dt(src.get("target_time")),
                        "time_diff_minutes": round(safe_float(src.get("time_diff_minutes")), 6),
                        "abs_time_diff_minutes": round(safe_float(src.get("abs_time_diff_minutes")), 6),
                        "dir_norm": src.get("dir_norm", ""),
                        "trigger_family": src.get("trigger_family", ""),
                        "mode_family": src.get("mode_family", ""),
                        "mode_or_signal_src": src.get("mode_or_signal_src", src.get("mode", src.get("signal_src", ""))),
                        "variant": src.get("variant", ""),
                        "same_dir": str(src.get("dir_norm", "")) == str(target["dir_norm"]),
                        "same_family": (
                            str(src.get("dir_norm", "")) == str(target["dir_norm"])
                            and str(src.get("trigger_family", "")) == str(target["trigger_family"])
                            and str(src.get("mode_family", "")) == str(target["mode_family"])
                        ),
                        "raw_equivalent": (
                            str(src.get("dir_norm", "")) == str(target["dir_norm"])
                            and str(src.get("mode_family", "")) == str(target["mode_family"])
                        )
                        if table_name == "python_raw_candidates" and str(target["trigger_family"]) == "M15 SLOT1"
                        else (
                            str(src.get("dir_norm", "")) == str(target["dir_norm"])
                            and str(src.get("trigger_family", "")) == str(target["trigger_family"])
                            and str(src.get("mode_family", "")) == str(target["mode_family"])
                        ),
                        "spec_pass": src.get("spec_pass", ""),
                        "spec_reason": src.get("spec_reason", ""),
                        "profit": round(safe_float(src.get("profit", src.get("net_profit", ""))), 6),
                        "stage1_exit": src.get("stage1_exit", ""),
                        "stage2_exit": src.get("stage2_exit", ""),
                        "stage3_exit": src.get("stage3_exit", ""),
                    }
                )
    return pd.DataFrame(rows)


def row_to_hint(row: pd.Series) -> str:
    if row.empty:
        return ""
    return (
        f"{fmt_dt(row.get('target_time'))} "
        f"{row.get('dir_norm', '')} {row.get('trigger_family', '')}/{row.get('mode_family', '')} "
        f"dt={safe_float(row.get('time_diff_minutes')):.0f}m"
    )


def classify_target(target: pd.Series, tables: dict[str, pd.DataFrame]) -> tuple[str, str, str]:
    raw = tables["python_raw_candidates"]
    layer12 = tables["python_layer12_pass"]
    layer3 = tables["python_layer3_selected"]
    dynamic = tables["python_dynamic_executed"]

    raw_exact = len(equivalent_rows(raw, target, 0))
    raw_60 = len(equivalent_rows(raw, target, 60))
    layer12_exact = len(equivalent_rows(layer12, target, 0))
    layer3_exact = len(equivalent_rows(layer3, target, 0))
    dynamic_exact = len(equivalent_rows(dynamic, target, 0))
    layer3_1d_opp = count_rows(layer3, target, 1440, "opposite_dir")
    dynamic_1d_opp = count_rows(dynamic, target, 1440, "opposite_dir")
    layer12_same_dir_60 = count_rows(layer12, target, 60, "same_dir")

    if raw_exact == 0 and raw_60 == 0:
        if layer3_1d_opp > 0 or dynamic_1d_opp > 0:
            return (
                "raw_absent_nearby_opposite_selected",
                "raw_signal_replay_no_main_change",
                "No same-direction raw equivalent appears near target, while opposite-direction Python selections exist nearby.",
            )
        return (
            "raw_absent_for_mt5_signal",
            "python_raw_generation_audit",
            "No Python raw equivalent appears near the MT5 signal target.",
        )
    if str(target["trigger_family"]) == "M30 CLOSE" and layer12_same_dir_60 > 0 and layer12_exact == 0:
        return (
            "layer12_trigger_family_drift_after_raw_parent",
            "trigger_family_transform_audit",
            "Python raw equivalent exists, but Layer1/2 promotes nearby same-direction rows under a different trigger family.",
        )
    if layer12_exact == 0:
        return (
            "layer12_absent_after_raw_equivalent",
            "layer12_filter_audit",
            "Python raw equivalent exists but does not pass into same-family Layer1/2 at the target.",
        )
    if layer3_exact == 0:
        if layer3_1d_opp > 0 or dynamic_1d_opp > 0:
            return (
                "layer3_displaced_by_nearby_opposite_selection",
                "layer3_gate_raw_replay",
                "Same-family Layer1/2 exists, but Layer3/executed selected nearby opposite-direction signals.",
            )
        return (
            "layer3_reject_after_layer12",
            "layer3_gate_raw_replay",
            "Same-family Layer1/2 exists but no same-family Layer3 target was selected.",
        )
    if dynamic_exact == 0:
        return (
            "not_executed_after_layer3",
            "execution_lifecycle_replay",
            "Python Layer3 selected the target but it did not appear in executed dynamic trades.",
        )
    return (
        "python_counterpart_exists_mapping_only",
        "mapping_accounting_review",
        "Python executed counterpart exists; remaining issue is mapping/accounting.",
    )


def build_case_review(targets: pd.DataFrame, tables: dict[str, pd.DataFrame], mt5: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, target in targets.iterrows():
        classification, action, note = classify_target(target, tables)
        raw_near = nearest_row(tables["python_raw_candidates"], target, "equivalent")
        layer12_near = nearest_row(tables["python_layer12_pass"], target, "equivalent")
        layer3_near = nearest_row(tables["python_layer3_selected"], target, "equivalent")
        opposite_near = nearest_row(tables["python_layer3_selected"], target, "opposite_dir")
        dyn_opposite = nearest_row(tables["python_dynamic_executed"], target, "opposite_dir")

        rows.append(
            {
                "target_case_id": target["target_case_id"],
                "trade_id": target["trade_id"],
                "target_time": fmt_dt(target["target_time"]),
                "dir_norm": target["dir_norm"],
                "trigger_family": target["trigger_family"],
                "mode_family": target["mode_family"],
                "abs_gap_effect_$": round(safe_float(target["abs_gap_effect_$"]), 6),
                "prior_replay_classification": target.get("replay_classification", ""),
                "raw_exact_equivalent_count": len(equivalent_rows(tables["python_raw_candidates"], target, 0)),
                "raw_60m_equivalent_count": len(equivalent_rows(tables["python_raw_candidates"], target, 60)),
                "layer12_exact_same_family_count": len(equivalent_rows(tables["python_layer12_pass"], target, 0)),
                "layer12_60m_same_family_count": len(equivalent_rows(tables["python_layer12_pass"], target, 60)),
                "layer3_exact_same_family_count": len(equivalent_rows(tables["python_layer3_selected"], target, 0)),
                "layer3_1440m_opposite_count": count_rows(tables["python_layer3_selected"], target, 1440, "opposite_dir"),
                "dynamic_exact_same_family_count": len(equivalent_rows(tables["python_dynamic_executed"], target, 0)),
                "dynamic_1440m_opposite_count": count_rows(tables["python_dynamic_executed"], target, 1440, "opposite_dir"),
                "mt5_exact_same_family_count": len(equivalent_rows(mt5, target, 0)),
                "nearest_raw_equivalent": row_to_hint(raw_near),
                "nearest_layer12_equivalent": row_to_hint(layer12_near),
                "nearest_layer3_equivalent": row_to_hint(layer3_near),
                "nearest_layer3_opposite": row_to_hint(opposite_near),
                "nearest_dynamic_opposite": row_to_hint(dyn_opposite),
                "raw_chain_loss_point": classification,
                "recommended_next_action": action,
                "raw_replay_note": note,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "merge_gate_pass": False,
            }
        )
    return pd.DataFrame(rows)


def summarize(review: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for loss_point, grp in review.groupby("raw_chain_loss_point", dropna=False):
        rows.append(
            {
                "raw_chain_loss_point": loss_point,
                "rows": int(len(grp)),
                "abs_gap_effect_sum": round(float(pd.to_numeric(grp["abs_gap_effect_$"], errors="coerce").sum()), 6),
                "targets": ";".join(grp["trade_id"].astype(str)),
                "recommended_next_action": ";".join(sorted(set(grp["recommended_next_action"].astype(str)))),
            }
        )
    return pd.DataFrame(rows).sort_values("abs_gap_effect_sum", ascending=False)


def build_decision(review: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    raw_absent_abs = float(
        summary[summary["raw_chain_loss_point"].astype(str).str.contains("raw_absent", regex=False)][
            "abs_gap_effect_sum"
        ].sum()
    )
    layer3_abs = float(
        summary[summary["raw_chain_loss_point"].astype(str).str.contains("layer3", regex=False)][
            "abs_gap_effect_sum"
        ].sum()
    )
    layer12_abs = float(
        summary[summary["raw_chain_loss_point"].astype(str).str.contains("layer12", regex=False)][
            "abs_gap_effect_sum"
        ].sum()
    )
    execution_abs = float(
        summary[summary["raw_chain_loss_point"].astype(str).str.contains("not_executed", regex=False)][
            "abs_gap_effect_sum"
        ].sum()
    )
    recommended = "prototype_targeted_layer3_or_raw_parent_rules"
    if raw_absent_abs >= max(layer3_abs, layer12_abs, execution_abs):
        recommended = "audit_python_raw_generation_vs_mt5_signal_source"
    elif layer3_abs > 0:
        recommended = "prototype_targeted_layer3_gate_rules_before_full_chain"
    elif layer12_abs > 0:
        recommended = "audit_layer12_trigger_family_transform"
    return pd.DataFrame(
        [
            {
                "gate": "stage_state_targeted_raw_signal_replay",
                "reviewed_rows": int(len(review)),
                "reviewed_abs_gap_effect_sum": round(float(review["abs_gap_effect_$"].sum()), 6),
                "raw_absent_abs_gap": round(raw_absent_abs, 6),
                "layer12_abs_gap": round(layer12_abs, 6),
                "layer3_abs_gap": round(layer3_abs, 6),
                "execution_abs_gap": round(execution_abs, 6),
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "targeted_signal_prototype_required": True,
                "merge_gate_pass": False,
                "recommended_next_action": recommended,
                "decision": "raw_replay_complete_no_main_change",
                "reason": (
                    "All four MT5-only/directional targets have a Python raw-chain loss point, but this is "
                    "still diagnostic evidence only. Any signal change requires a non-destructive prototype "
                    "and full-chain rerun."
                ),
            }
        ]
    )


def simple_table(frame: pd.DataFrame, max_rows: int = 40) -> str:
    if frame.empty:
        return "_No rows_"
    return frame.head(max_rows).to_markdown(index=False)


def write_report(review: pd.DataFrame, summary: pd.DataFrame, decision: pd.DataFrame) -> None:
    d = decision.iloc[0]
    cols = [
        "trade_id",
        "target_time",
        "dir_norm",
        "trigger_family",
        "mode_family",
        "abs_gap_effect_$",
        "raw_exact_equivalent_count",
        "layer12_exact_same_family_count",
        "layer3_exact_same_family_count",
        "dynamic_exact_same_family_count",
        "raw_chain_loss_point",
        "recommended_next_action",
    ]
    report = [
        "# Stage-State Targeted Raw Signal Replay",
        "",
        "## Scope",
        "",
        "- Reviews only `mt5_0076`, `mt5_0067`, `mt5_0044`, and `mt5_0026`.",
        "- Links MT5-only targets to Python raw, Layer1/2, Layer3, stage export, and dynamic executed records.",
        "- Does not change Python signals, mapping rules, dynamic risk, or EA behavior.",
        "",
        "## Summary",
        "",
        f"- Reviewed rows: `{int(d['reviewed_rows'])}`.",
        f"- Reviewed abs gap: `{float(d['reviewed_abs_gap_effect_sum']):.6f}`.",
        f"- Raw-absent abs gap: `{float(d['raw_absent_abs_gap']):.6f}`.",
        f"- Layer1/2 abs gap: `{float(d['layer12_abs_gap']):.6f}`.",
        f"- Layer3 abs gap: `{float(d['layer3_abs_gap']):.6f}`.",
        f"- Execution abs gap: `{float(d['execution_abs_gap']):.6f}`.",
        "",
        "## Loss Point Summary",
        "",
        simple_table(summary),
        "",
        "## Case Review",
        "",
        simple_table(review[cols]),
        "",
        "## Decision",
        "",
        f"- `main_signal_change_gate_open`: `{bool_value(d['main_signal_change_gate_open'])}`.",
        f"- `ea_behavior_gate_open`: `{bool_value(d['ea_behavior_gate_open'])}`.",
        f"- `targeted_signal_prototype_required`: `{bool_value(d['targeted_signal_prototype_required'])}`.",
        f"- `merge_gate_pass`: `{bool_value(d['merge_gate_pass'])}`.",
        f"- Recommended next action: `{d['recommended_next_action']}`.",
        "",
        "The raw replay identifies where each target drops from the Python chain, but it is not a merge signal. A prototype must be run before main logic changes.",
        "",
        "## Output Files",
        "",
        "- `targeted_raw_signal_replay_case_review.csv`",
        "- `targeted_raw_signal_replay_window_counts.csv`",
        "- `targeted_raw_signal_replay_context_rows.csv`",
        "- `targeted_raw_signal_replay_summary.csv`",
        "- `targeted_raw_signal_replay_decision.csv`",
    ]
    write_text(OUT_DIR / "targeted_raw_signal_replay_review.md", "\n".join(report))
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# stage_state_targeted_raw_signal_replay_20260717",
                "",
                "Raw-chain diagnostic output for four MT5-only/directional residual cases.",
                "",
                "This is diagnostic-only and does not modify strategy logic.",
            ]
        ),
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tables = load_signal_chain()
    mt5 = load_mt5_unique()
    targets = load_targets()
    window_counts = build_window_counts(targets, tables, mt5)
    ctx = context_rows(targets, tables, mt5)
    review = build_case_review(targets, tables, mt5)
    summary = summarize(review)
    decision = build_decision(review, summary)

    export_csv(targets, OUT_DIR / "targeted_raw_signal_replay_targets.csv")
    export_csv(window_counts, OUT_DIR / "targeted_raw_signal_replay_window_counts.csv")
    export_csv(ctx, OUT_DIR / "targeted_raw_signal_replay_context_rows.csv")
    export_csv(review, OUT_DIR / "targeted_raw_signal_replay_case_review.csv")
    export_csv(summary, OUT_DIR / "targeted_raw_signal_replay_summary.csv")
    export_csv(decision, OUT_DIR / "targeted_raw_signal_replay_decision.csv")
    write_report(review, summary, decision)


if __name__ == "__main__":
    main()
