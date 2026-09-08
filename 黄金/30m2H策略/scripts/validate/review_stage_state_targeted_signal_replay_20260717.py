# -*- coding: utf-8 -*-
"""Targeted signal-chain replay for outside/no-candidate stage-state moments.

This gate links selected no-candidate moments to available Python signal-chain
exports and MT5 stage-state ledger evidence. It is diagnostic-only: it does not
rerun the strategy, change mapping rules, or modify EA/Python behavior.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
DATA_DIR = STRATEGY_DIR / "data"

NO_CANDIDATE_DIR = VALIDATION_DIR / "stage_state_no_candidate_signal_gap_triage_20260717"
OUTSIDE_DIR = VALIDATION_DIR / "stage_state_outside_7d_mapping_window_audit_20260717"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
DYNAMIC_INPUT_DIR = VALIDATION_DIR / "dynamic_risk_inputs_shift90_metadatafix_20260714"
SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"
MT5_STAGE_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"

OUT_DIR = VALIDATION_DIR / "stage_state_targeted_signal_replay_20260717"

EA_ALIGN_DELTA_MINUTES = 90
DAY_MINUTES = 24 * 60
SELECT_ABS_GAP_MIN = 75.0


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


def clean_trigger_tag(value: object) -> str:
    return str(value).replace("[", "").replace("]", "").strip()


def signal_src_family(value: object) -> str:
    return mode_family(value)


def prepare_python_signal_table(frame: pd.DataFrame, source_table: str) -> pd.DataFrame:
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
        out.get("dynamic_total_$", out.get("total_$", out.get("pnl", pd.Series(0.0, index=out.index)))),
        errors="coerce",
    )
    out["stage3_time"] = out["stage3_time"].map(parse_dt) if "stage3_time" in out.columns else pd.NaT
    return out


def load_python_signal_tables() -> dict[str, pd.DataFrame]:
    raw = prepare_python_signal_table(read_csv(SIGNAL_DIR / "raw_candidates.csv"), "python_raw_candidates")
    layer12 = prepare_python_signal_table(
        read_csv(SIGNAL_DIR / "候选信号_Layer1_Layer2通过.csv"),
        "python_layer12_pass",
    )
    layer3 = prepare_python_signal_table(
        read_csv(SIGNAL_DIR / "最终信号_Layer3入选.csv"),
        "python_layer3_selected",
    )
    stage = read_csv(SIGNAL_DIR / "执行交易_Stage结果.csv").copy()
    layer3_key = layer3[
        ["target_time", "date", "mode", "dir", "trigger_family", "variant", "spec_pass", "spec_reason"]
    ].drop_duplicates(["date", "mode", "dir"])
    stage = stage.merge(layer3_key, on=["date", "mode", "dir"], how="left")
    stage = prepare_python_signal_table(stage, "python_stage_result_export")
    return {
        "python_raw_candidates": raw,
        "python_layer12_pass": layer12,
        "python_layer3_selected": layer3,
        "python_stage_result_export": stage,
    }


def load_python_dynamic() -> pd.DataFrame:
    dyn = read_csv(DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv").copy()
    dyn["py_trade_id"] = [f"python_mt5_{i + 1:04d}" for i in range(len(dyn))]
    dyn["target_time"] = dyn["date"].map(parse_dt)
    dyn["dir_norm"] = dyn["dir"].map(normalize_dir)
    dyn["mode_family"] = dyn["mode_family"].map(mode_family)
    dyn["trigger_family"] = dyn["trigger_family"].astype(str)
    dyn["profit"] = pd.to_numeric(dyn["dynamic_total_$"], errors="coerce")

    inputs = read_csv(DYNAMIC_INPUT_DIR / "python_mt5_dynamic_risk_inputs.csv").copy()
    inputs["target_time"] = inputs["date"].map(parse_dt)
    inputs["dir_norm"] = inputs["dir"].map(normalize_dir)
    inputs["mode_family"] = inputs["mode"].map(mode_family)
    inputs["stage3_time_input"] = inputs["stage3_time"].map(parse_dt) if "stage3_time" in inputs.columns else pd.NaT
    join_cols = ["target_time", "dir_norm", "mode"]
    input_cols = join_cols + ["stage3_time_input", "stage3_exit", "trigger", "variant"]
    dyn = dyn.merge(inputs[input_cols].drop_duplicates(join_cols), on=join_cols, how="left", suffixes=("", "_input"))
    dyn["stage3_time"] = dyn["stage3_time_input"]
    dyn["source_table"] = "python_dynamic_executed"
    dyn["mode_or_signal_src"] = dyn["mode"]
    dyn["spec_pass_bool"] = True
    return dyn


def load_mt5_unique() -> pd.DataFrame:
    mt5 = read_csv(DYNAMIC_DIR / "mt5_ledger_unique_signals.csv").copy()
    mt5["mt5_trade_id"] = [f"mt5_{i + 1:04d}" for i in range(len(mt5))]
    mt5["signal_anchor_dt"] = mt5["signal_anchor_time"].map(parse_dt)
    mt5["target_time"] = mt5["signal_anchor_dt"] + pd.Timedelta(minutes=EA_ALIGN_DELTA_MINUTES)
    mt5["dir_norm"] = mt5["dir"].map(normalize_dir)
    mt5["mode_family"] = mt5["mode_family"].map(mode_family)
    mt5["trigger_family"] = mt5["trigger_family"].astype(str)
    mt5["profit"] = pd.to_numeric(mt5["net_profit"], errors="coerce")
    mt5["source_table"] = "mt5_unique_ledger"
    mt5["mode_or_signal_src"] = mt5["signal_src"]
    return mt5


def join_unique_values(series: pd.Series) -> str:
    vals = [str(v) for v in series.dropna().astype(str).unique() if str(v).strip()]
    return ";".join(vals)


def load_mt5_stage_group(mt5_unique: pd.DataFrame) -> pd.DataFrame:
    stage = read_csv(MT5_STAGE_DIR / "30m2H_strategy_trade_ledger.csv").copy()
    stage["signal_anchor_dt"] = stage["signal_anchor_time"].map(parse_dt)
    stage["open_dt"] = stage["open_time"].map(parse_dt)
    stage["exit_dt"] = stage["exit_time"].map(parse_dt)
    stage["dir_norm"] = stage["dir"].map(normalize_dir)
    stage["trigger_family"] = stage["trigger_tag"].map(clean_trigger_tag)
    stage["mode_family"] = stage["signal_src"].map(signal_src_family)
    stage["profit"] = pd.to_numeric(stage["net_profit"], errors="coerce")
    grouped = (
        stage.groupby(["signal_anchor_dt", "trigger_family", "mode_family", "signal_src", "dir_norm"], dropna=False)
        .agg(
            stage_rows=("stage", "count"),
            stage_list=("stage", join_unique_values),
            lots_list=("lots", join_unique_values),
            first_open=("open_dt", "min"),
            last_exit=("exit_dt", "max"),
            net_profit=("profit", "sum"),
            local_exit_reasons=("local_exit_reason", join_unique_values),
            deal_reasons=("deal_reason", join_unique_values),
        )
        .reset_index()
    )
    grouped["target_time"] = grouped["signal_anchor_dt"] + pd.Timedelta(minutes=EA_ALIGN_DELTA_MINUTES)
    id_map = mt5_unique[
        ["mt5_trade_id", "signal_anchor_dt", "trigger_family", "mode_family", "signal_src", "dir_norm"]
    ].copy()
    grouped = grouped.merge(
        id_map,
        on=["signal_anchor_dt", "trigger_family", "mode_family", "signal_src", "dir_norm"],
        how="left",
    )
    grouped["source_table"] = "mt5_stage_state_ledger_group"
    grouped["mode_or_signal_src"] = grouped["signal_src"]
    grouped["profit"] = grouped["net_profit"]
    return grouped


def load_selected_cases() -> pd.DataFrame:
    outside = read_csv(OUTSIDE_DIR / "outside_7d_mapping_window_case_review.csv").copy()
    outside["case_source"] = "outside_7d_window_audit"
    no_candidate = read_csv(NO_CANDIDATE_DIR / "stage_state_no_candidate_signal_gap_cases.csv").copy()
    no_candidate["case_source"] = "no_candidate_triage"

    for frame in [outside, no_candidate]:
        frame["target_time"] = frame["target_time"].map(parse_dt)
        frame["gap_effect_$"] = pd.to_numeric(frame["gap_effect_$"], errors="coerce").fillna(0.0)
        frame["abs_gap_effect_$"] = frame["gap_effect_$"].abs()
        frame["dir_norm"] = frame["dir_norm"].map(normalize_dir)
        frame["mode_family"] = frame["mode_family"].map(mode_family)

    outside["selection_reason"] = "all_outside_7d_cases"
    selected = [outside]
    no_candidate_high = no_candidate[no_candidate["abs_gap_effect_$"] >= SELECT_ABS_GAP_MIN].copy()
    no_candidate_high["selection_reason"] = "no_candidate_abs_gap_ge_75"
    selected.append(no_candidate_high)

    merged = pd.concat(selected, ignore_index=True, sort=False)
    merged = merged.sort_values(["abs_gap_effect_$", "trade_id"], ascending=[False, True])
    merged = merged.drop_duplicates(["side", "trade_id"], keep="first").reset_index(drop=True)
    merged["target_case_id"] = [f"target_{i + 1:03d}" for i in range(len(merged))]
    return merged


def rows_within(table: pd.DataFrame, target_time: pd.Timestamp, minutes: int) -> pd.DataFrame:
    if table.empty or pd.isna(target_time):
        return table.iloc[0:0].copy()
    out = table.copy()
    out["time_diff_minutes"] = (out["target_time"] - target_time).dt.total_seconds() / 60.0
    out["abs_time_diff_minutes"] = out["time_diff_minutes"].abs()
    return out[pd.notna(out["abs_time_diff_minutes"]) & (out["abs_time_diff_minutes"] <= minutes)].copy()


def count_same_family(table: pd.DataFrame, target_time: pd.Timestamp, direction: str, trigger: str, mode: str, minutes: int) -> int:
    rows = rows_within(table, target_time, minutes)
    if rows.empty:
        return 0
    rows = rows[
        (rows["dir_norm"] == direction)
        & (rows["trigger_family"].astype(str) == str(trigger))
        & (rows["mode_family"].astype(str) == str(mode))
    ]
    return int(len(rows))


def count_same_dir(table: pd.DataFrame, target_time: pd.Timestamp, direction: str, minutes: int) -> int:
    rows = rows_within(table, target_time, minutes)
    if rows.empty:
        return 0
    return int((rows["dir_norm"] == direction).sum())


def nearest_summary(table: pd.DataFrame, target_time: pd.Timestamp, direction: str) -> dict[str, object]:
    rows = table.copy()
    rows["time_diff_minutes"] = (rows["target_time"] - target_time).dt.total_seconds() / 60.0
    rows["abs_time_diff_minutes"] = rows["time_diff_minutes"].abs()
    rows = rows[pd.notna(rows["abs_time_diff_minutes"]) & (rows["dir_norm"] == direction)].copy()
    if rows.empty:
        return {"nearest_id": "", "nearest_minutes": "", "nearest_trigger": "", "nearest_mode": "", "nearest_profit": ""}
    row = rows.sort_values("abs_time_diff_minutes").iloc[0]
    row_id = row.get("py_trade_id", row.get("mt5_trade_id", ""))
    return {
        "nearest_id": row_id,
        "nearest_minutes": round(safe_float(row.get("abs_time_diff_minutes")), 6),
        "nearest_trigger": row.get("trigger_family", ""),
        "nearest_mode": row.get("mode_family", ""),
        "nearest_profit": round(safe_float(row.get("profit")), 6),
    }


def active_python_at(dynamic: pd.DataFrame, target_time: pd.Timestamp, exclude_py_id: str = "") -> pd.DataFrame:
    if pd.isna(target_time):
        return dynamic.iloc[0:0].copy()
    rows = dynamic[pd.notna(dynamic["stage3_time"])].copy()
    active = rows[(rows["target_time"] <= target_time) & (rows["stage3_time"] > target_time)].copy()
    if exclude_py_id:
        active = active[active["py_trade_id"].astype(str) != str(exclude_py_id)]
    return active


def active_mt5_at(stage_group: pd.DataFrame, target_time: pd.Timestamp, exclude_mt5_id: str = "") -> pd.DataFrame:
    if pd.isna(target_time):
        return stage_group.iloc[0:0].copy()
    active = stage_group[(stage_group["first_open"] <= target_time) & (stage_group["last_exit"] > target_time)].copy()
    if exclude_mt5_id:
        active = active[active["mt5_trade_id"].astype(str) != str(exclude_mt5_id)]
    return active


def classify_case(row: dict[str, object]) -> tuple[str, str, str]:
    outside_bucket = str(row.get("case_review_bucket", ""))
    action_bucket = str(row.get("no_candidate_action_bucket", row.get("action_bucket", "")))
    side = str(row.get("side", ""))
    counterpart_active = int(row.get("counterpart_active_count", 0))
    py_layer3_exact = int(row.get("python_layer3_exact_same_family", 0))
    py_exec_exact = int(row.get("python_dynamic_exact_same_family", 0))
    mt5_exact = int(row.get("mt5_unique_exact_same_family", 0))
    opposite_1d = int(row.get("opposite_dir_1d_count", 0) or 0)

    if outside_bucket == "outside_candidate_already_occupied_accounting_only":
        return (
            "accounting_only_occupied_outside_candidate",
            "keep_accounting_only",
            "Outside-window nearest candidate is already consumed by current unique matching.",
        )
    if outside_bucket == "outside_relaxed_family_window_risk":
        return (
            "accounting_only_relaxed_window_risk",
            "keep_accounting_only",
            "Outside-window candidate is trigger/mode relaxed and should not be promoted without replay.",
        )
    if "before_first_mt5" in action_bucket or "after_last" in action_bucket:
        return (
            "boundary_window_gap",
            "audit_data_window_or_warmup",
            "Case falls on reference coverage boundary; do not change strategy logic from this alone.",
        )
    if counterpart_active > 0:
        return (
            "lifecycle_suppressed_counterpart_candidate",
            "prototype_lifecycle_suppression",
            "Counterpart side has an active trade at the target time; lifecycle/position mutual exclusion must be replayed.",
        )
    if "nearby_opposite_direction" in action_bucket or opposite_1d > 0:
        return (
            "directional_signal_divergence_needs_raw_replay",
            "targeted_signal_raw_replay",
            "Nearby opposite-direction context exists; inspect trend/trigger construction before behavior changes.",
        )
    if side == "python_unmatched" and py_layer3_exact > 0 and py_exec_exact > 0 and mt5_exact == 0:
        return (
            "python_only_true_signal_needs_ea_diag",
            "add_or_extract_ea_signal_diag",
            "Python signal chain reaches Layer3/executed, but no same-family MT5 ledger counterpart is present.",
        )
    if side == "mt5_unmatched" and mt5_exact > 0 and py_layer3_exact == 0 and py_exec_exact == 0:
        return (
            "mt5_only_true_signal_needs_python_replay",
            "targeted_python_signal_replay",
            "MT5 ledger signal exists, but Python Layer3/executed counterpart is absent at the same family/time.",
        )
    return (
        "needs_deeper_raw_replay",
        "targeted_signal_raw_replay",
        "Available ledger/signal exports do not fully explain the case; replay raw signal construction.",
    )


def build_context_rows(
    case: pd.Series,
    python_tables: dict[str, pd.DataFrame],
    python_dynamic: pd.DataFrame,
    mt5_unique: pd.DataFrame,
    mt5_stage_group: pd.DataFrame,
) -> pd.DataFrame:
    target_time = case["target_time"]
    direction = str(case["dir_norm"])
    trigger = str(case["trigger_family"])
    mode = str(case["mode_family"])
    context_tables = dict(python_tables)
    context_tables["python_dynamic_executed"] = python_dynamic
    context_tables["mt5_unique_ledger"] = mt5_unique
    context_tables["mt5_stage_state_ledger_group"] = mt5_stage_group
    rows: list[dict[str, object]] = []
    for table_name, table in context_tables.items():
        nearby = rows_within(table, target_time, DAY_MINUTES)
        if nearby.empty:
            nearby = rows_within(table, target_time, 7 * DAY_MINUTES).sort_values("abs_time_diff_minutes").head(3)
        else:
            nearby = nearby.sort_values("abs_time_diff_minutes").head(8)
        for _, src in nearby.iterrows():
            row_id = src.get("py_trade_id", src.get("mt5_trade_id", ""))
            rows.append(
                {
                    "target_case_id": case["target_case_id"],
                    "target_trade_id": case["trade_id"],
                    "source_table": table_name,
                    "row_id": row_id,
                    "row_time": fmt_dt(src.get("target_time")),
                    "time_diff_minutes": round(safe_float(src.get("time_diff_minutes")), 6),
                    "abs_time_diff_minutes": round(safe_float(src.get("abs_time_diff_minutes")), 6),
                    "dir_norm": src.get("dir_norm", ""),
                    "trigger_family": src.get("trigger_family", ""),
                    "mode_family": src.get("mode_family", ""),
                    "mode_or_signal_src": src.get("mode_or_signal_src", src.get("mode", src.get("signal_src", ""))),
                    "variant": src.get("variant", ""),
                    "same_dir": str(src.get("dir_norm", "")) == direction,
                    "same_family": (
                        str(src.get("dir_norm", "")) == direction
                        and str(src.get("trigger_family", "")) == trigger
                        and str(src.get("mode_family", "")) == mode
                    ),
                    "profit": round(safe_float(src.get("profit", src.get("net_profit", ""))), 6),
                    "stage3_time": fmt_dt(src.get("stage3_time", "")),
                    "first_open": fmt_dt(src.get("first_open", "")),
                    "last_exit": fmt_dt(src.get("last_exit", "")),
                    "local_exit_reasons": src.get("local_exit_reasons", ""),
                    "deal_reasons": src.get("deal_reasons", ""),
                    "stage1_exit": src.get("stage1_exit", ""),
                    "stage2_exit": src.get("stage2_exit", ""),
                    "stage3_exit": src.get("stage3_exit", ""),
                    "spec_pass": src.get("spec_pass", ""),
                    "spec_reason": src.get("spec_reason", ""),
                }
            )
    return pd.DataFrame(rows)


def build_case_review(
    cases: pd.DataFrame,
    python_tables: dict[str, pd.DataFrame],
    python_dynamic: pd.DataFrame,
    mt5_unique: pd.DataFrame,
    mt5_stage_group: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    context_frames: list[pd.DataFrame] = []
    for _, case in cases.iterrows():
        target_time = case["target_time"]
        direction = str(case["dir_norm"])
        trigger = str(case["trigger_family"])
        mode = str(case["mode_family"])
        side = str(case["side"])
        trade_id = str(case["trade_id"])

        exclude_py = trade_id if side == "python_unmatched" else ""
        exclude_mt5 = trade_id if side == "mt5_unmatched" else ""
        py_active = active_python_at(python_dynamic, target_time, exclude_py)
        mt5_active = active_mt5_at(mt5_stage_group, target_time, exclude_mt5)
        counterpart_active = mt5_active if side == "python_unmatched" else py_active

        layer3 = python_tables["python_layer3_selected"]
        raw = python_tables["python_raw_candidates"]
        layer12 = python_tables["python_layer12_pass"]

        row = case.to_dict()
        row.update(
            {
                "target_time": fmt_dt(target_time),
                "python_raw_exact_same_family": count_same_family(raw, target_time, direction, trigger, mode, 0),
                "python_raw_60m_same_family": count_same_family(raw, target_time, direction, trigger, mode, 60),
                "python_layer12_exact_same_family": count_same_family(layer12, target_time, direction, trigger, mode, 0),
                "python_layer3_exact_same_family": count_same_family(layer3, target_time, direction, trigger, mode, 0),
                "python_layer3_60m_same_family": count_same_family(layer3, target_time, direction, trigger, mode, 60),
                "python_dynamic_exact_same_family": count_same_family(python_dynamic, target_time, direction, trigger, mode, 0),
                "python_dynamic_60m_same_family": count_same_family(python_dynamic, target_time, direction, trigger, mode, 60),
                "mt5_unique_exact_same_family": count_same_family(mt5_unique, target_time, direction, trigger, mode, 0),
                "mt5_unique_60m_same_family": count_same_family(mt5_unique, target_time, direction, trigger, mode, 60),
                "mt5_stage_exact_same_family": count_same_family(mt5_stage_group, target_time, direction, trigger, mode, 0),
                "python_same_dir_1d_count": count_same_dir(python_dynamic, target_time, direction, DAY_MINUTES),
                "mt5_same_dir_1d_count": count_same_dir(mt5_unique, target_time, direction, DAY_MINUTES),
                "python_active_count": int(len(py_active)),
                "mt5_active_count": int(len(mt5_active)),
                "counterpart_active_count": int(len(counterpart_active)),
                "python_active_trade_ids": ";".join(py_active["py_trade_id"].astype(str).head(6)),
                "mt5_active_trade_ids": ";".join(mt5_active["mt5_trade_id"].dropna().astype(str).head(6)),
            }
        )
        py_nearest = nearest_summary(python_dynamic, target_time, direction)
        mt5_nearest = nearest_summary(mt5_unique, target_time, direction)
        row.update({f"nearest_python_{k}": v for k, v in py_nearest.items()})
        row.update({f"nearest_mt5_{k}": v for k, v in mt5_nearest.items()})
        classification, next_action, note = classify_case(row)
        row["replay_classification"] = classification
        row["recommended_next_action"] = next_action
        row["replay_note"] = note
        rows.append(row)
        context_frames.append(build_context_rows(case, python_tables, python_dynamic, mt5_unique, mt5_stage_group))

    review = pd.DataFrame(rows).sort_values(["abs_gap_effect_$", "trade_id"], ascending=[False, True]).reset_index(drop=True)
    context = pd.concat(context_frames, ignore_index=True) if context_frames else pd.DataFrame()
    return review, context


def summarize_review(review: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (classification, side), grp in review.groupby(["replay_classification", "side"], dropna=False):
        rows.append(
            {
                "replay_classification": classification,
                "side": side,
                "rows": int(len(grp)),
                "gap_effect_sum": round(float(pd.to_numeric(grp["gap_effect_$"], errors="coerce").sum()), 6),
                "abs_gap_effect_sum": round(float(pd.to_numeric(grp["abs_gap_effect_$"], errors="coerce").sum()), 6),
                "p1_rows": int((pd.to_numeric(grp["abs_gap_effect_$"], errors="coerce") >= 150).sum()),
                "counterpart_active_rows": int((pd.to_numeric(grp["counterpart_active_count"], errors="coerce") > 0).sum()),
            }
        )
    return pd.DataFrame(rows).sort_values("abs_gap_effect_sum", ascending=False)


def build_decision(review: pd.DataFrame, summary: pd.DataFrame) -> pd.DataFrame:
    total_abs = float(pd.to_numeric(review["abs_gap_effect_$"], errors="coerce").sum())
    p1_p2_rows = int((pd.to_numeric(review["abs_gap_effect_$"], errors="coerce") >= SELECT_ABS_GAP_MIN).sum())
    accounting_abs = float(
        summary[
            summary["replay_classification"].astype(str).str.contains("accounting_only", regex=False)
        ]["abs_gap_effect_sum"].sum()
    )
    lifecycle_abs = float(
        summary[
            summary["replay_classification"].astype(str).eq("lifecycle_suppressed_counterpart_candidate")
        ]["abs_gap_effect_sum"].sum()
    )
    true_signal_abs = float(
        summary[
            summary["replay_classification"].astype(str).str.contains("true_signal", regex=False)
        ]["abs_gap_effect_sum"].sum()
    )
    directional_abs = float(
        summary[
            summary["replay_classification"].astype(str).eq("directional_signal_divergence_needs_raw_replay")
        ]["abs_gap_effect_sum"].sum()
    )

    recommended = "keep_accounting_only_then_target_lifecycle_or_directional_replay"
    if lifecycle_abs >= max(true_signal_abs, directional_abs):
        recommended = "prototype_lifecycle_suppression_before_signal_changes"
    elif true_signal_abs > 0 or directional_abs > 0:
        recommended = "targeted_raw_signal_replay_before_main_logic_change"

    return pd.DataFrame(
        [
            {
                "gate": "stage_state_targeted_signal_level_replay",
                "reviewed_rows": int(len(review)),
                "p1_p2_rows": p1_p2_rows,
                "reviewed_abs_gap_effect_sum": round(total_abs, 6),
                "accounting_only_abs_gap": round(accounting_abs, 6),
                "lifecycle_candidate_abs_gap": round(lifecycle_abs, 6),
                "true_signal_candidate_abs_gap": round(true_signal_abs, 6),
                "directional_signal_divergence_abs_gap": round(directional_abs, 6),
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "lifecycle_prototype_required": lifecycle_abs > 0,
                "raw_signal_replay_required": true_signal_abs > 0 or directional_abs > 0,
                "merge_gate_pass": False,
                "recommended_next_action": recommended,
                "decision": "diagnostic_replay_complete_no_main_change",
                "reason": (
                    "Targeted replay links top no-candidate moments to available signal/ledger evidence, "
                    "but does not provide enough proof to change Python signals, EA behavior, or mapping rules directly."
                ),
            }
        ]
    )


def simple_table(frame: pd.DataFrame, max_rows: int = 30) -> str:
    if frame.empty:
        return "_No rows_"
    return frame.head(max_rows).to_markdown(index=False)


def write_report(review: pd.DataFrame, context: pd.DataFrame, summary: pd.DataFrame, decision: pd.DataFrame) -> None:
    d = decision.iloc[0]
    top_cases = review.head(12)[
        [
            "target_case_id",
            "side",
            "trade_id",
            "target_time",
            "dir_norm",
            "trigger_family",
            "mode_family",
            "abs_gap_effect_$",
            "counterpart_active_count",
            "python_layer3_exact_same_family",
            "python_dynamic_exact_same_family",
            "mt5_unique_exact_same_family",
            "replay_classification",
            "recommended_next_action",
        ]
    ]
    report = [
        "# Stage-State Targeted Signal-Level Replay",
        "",
        "## Scope",
        "",
        "- Reviews all outside-7d cases plus no-candidate P1/P2 moments.",
        "- Uses the current Python-MT5 dynamic trades, MT5 stage-state ledger, and the closest available Python signal-chain export.",
        "- Does not rerun the strategy, change signal logic, change mapping rules, or modify EA behavior.",
        "",
        "## Coverage",
        "",
        f"- Reviewed rows: `{int(d['reviewed_rows'])}`.",
        f"- P1/P2 rows: `{int(d['p1_p2_rows'])}`.",
        f"- Reviewed abs gap: `{float(d['reviewed_abs_gap_effect_sum']):.6f}`.",
        f"- Accounting-only abs gap: `{float(d['accounting_only_abs_gap']):.6f}`.",
        f"- Lifecycle candidate abs gap: `{float(d['lifecycle_candidate_abs_gap']):.6f}`.",
        f"- True-signal candidate abs gap: `{float(d['true_signal_candidate_abs_gap']):.6f}`.",
        f"- Directional divergence abs gap: `{float(d['directional_signal_divergence_abs_gap']):.6f}`.",
        "",
        "## Classification Summary",
        "",
        simple_table(summary),
        "",
        "## Top Cases",
        "",
        simple_table(top_cases, 20),
        "",
        "## Decision",
        "",
        f"- `main_signal_change_gate_open`: `{bool_value(d['main_signal_change_gate_open'])}`.",
        f"- `ea_behavior_gate_open`: `{bool_value(d['ea_behavior_gate_open'])}`.",
        f"- `lifecycle_prototype_required`: `{bool_value(d['lifecycle_prototype_required'])}`.",
        f"- `raw_signal_replay_required`: `{bool_value(d['raw_signal_replay_required'])}`.",
        f"- `merge_gate_pass`: `{bool_value(d['merge_gate_pass'])}`.",
        f"- Recommended next action: `{d['recommended_next_action']}`.",
        "",
        "The replay evidence keeps the current main logic closed. Any behavior change still needs a targeted non-destructive prototype and full-chain rerun.",
        "",
        "## Output Files",
        "",
        "- `targeted_signal_replay_case_review.csv`",
        "- `targeted_signal_replay_context_rows.csv`",
        "- `targeted_signal_replay_classification_summary.csv`",
        "- `targeted_signal_replay_decision.csv`",
    ]
    write_text(OUT_DIR / "targeted_signal_replay_review.md", "\n".join(report))

    readme = [
        "# stage_state_targeted_signal_replay_20260717",
        "",
        "Diagnostic targeted replay for outside/no-candidate stage-state moments.",
        "",
        "Uses available signal/ledger exports only. This is not a strategy rerun and does not modify main logic.",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(readme))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    python_tables = load_python_signal_tables()
    python_dynamic = load_python_dynamic()
    mt5_unique = load_mt5_unique()
    mt5_stage_group = load_mt5_stage_group(mt5_unique)
    cases = load_selected_cases()

    review, context = build_case_review(cases, python_tables, python_dynamic, mt5_unique, mt5_stage_group)
    summary = summarize_review(review)
    decision = build_decision(review, summary)

    export_csv(cases, OUT_DIR / "targeted_signal_replay_selected_cases.csv")
    export_csv(review, OUT_DIR / "targeted_signal_replay_case_review.csv")
    export_csv(context, OUT_DIR / "targeted_signal_replay_context_rows.csv")
    export_csv(summary, OUT_DIR / "targeted_signal_replay_classification_summary.csv")
    export_csv(decision, OUT_DIR / "targeted_signal_replay_decision.csv")
    write_report(review, context, summary, decision)


if __name__ == "__main__":
    main()
