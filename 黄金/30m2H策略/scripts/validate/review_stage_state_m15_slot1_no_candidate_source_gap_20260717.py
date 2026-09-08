# -*- coding: utf-8 -*-
"""Audit M15 SLOT1 post_n no-candidate/source-gap cases.

Diagnostic-only:
- no EA edits
- no signal snapshot edits
- no mapping-rule edits
- no dynamic-risk edits
"""

from __future__ import annotations


from pathlib import Path
import re

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = ROOT / "黄金" / "30m2H策略"
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

PREV_DIR = VALIDATION_DIR / "stage_state_m15_slot1_legacy_counter_drift_cohort_20260717"
OUT_DIR = VALIDATION_DIR / "stage_state_m15_slot1_no_candidate_source_gap_audit_20260717"

DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"
SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"

COHORT_ALIGNMENT = PREV_DIR / "m15_slot1_postn_cohort_alignment.csv"
PY_DYNAMIC = DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"
PY_MAPPING = MAPPING_DIR / "python_mt5_mt5_unique_matches.csv"
PY_UNMATCHED_MT5 = MAPPING_DIR / "python_mt5_unmatched_mt5_trades.csv"

PYTHON_M15_COVERAGE_START = pd.Timestamp("2022-04-08 14:30:00")
TARGET_CLASSIFICATION = "python_no_postn_candidate_nearby"
TARGET_WINDOWS: list[tuple[str, int]] = [
    ("pm60", 60),
    ("pm24h", 24 * 60),
    ("pm7d", 7 * 24 * 60),
]
EXACT_TARGETS = ["actual", "aligned_plus90"]


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


def mode_family(value: object) -> str:
    text = str(value).lower()
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return str(value).strip()


def mode_number(value: object) -> int | None:
    match = re.search(r"post_n(\d+)", str(value))
    if not match:
        return None
    return int(match.group(1))


def safe_float(value: object) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return float("nan")
    return float(parsed)


def safe_int(value: object) -> int | None:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return int(parsed)


def boolish(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y"}


def semijoin(values: list[object], limit: int = 12) -> str:
    out: list[str] = []
    for value in values:
        if pd.isna(value):
            continue
        text = str(value)
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return ";".join(out)


def profit_col(frame: pd.DataFrame) -> str:
    for col in ["dynamic_total_$", "total_$", "pnl", "profit", "source_profit"]:
        if col in frame.columns:
            return col
    return ""


def find_signal_file(keyword: str) -> Path:
    hits = [path for path in SIGNAL_DIR.glob("*.csv") if keyword.lower() in path.name.lower()]
    if not hits:
        raise FileNotFoundError(f"no signal file for {keyword}")
    return hits[0]


def load_signal_table(path: Path, layer_name: str) -> pd.DataFrame:
    frame = read_csv(path).copy()
    frame["date_dt"] = frame["date"].map(parse_dt)
    if "entry_time" in frame.columns:
        frame["entry_time_dt"] = frame["entry_time"].map(parse_dt)
    else:
        frame["entry_time_dt"] = pd.NaT
    frame["dir_norm"] = frame["dir"].map(normalize_dir)
    frame["mode_family"] = frame["mode"].map(mode_family)
    frame["mode_n"] = frame["mode"].map(mode_number)
    if "variant" in frame.columns:
        frame["trigger_family"] = [
            "M15 SLOT1" if "slot1" in str(value).lower() or "rescue" in str(value).lower() else "M30 CLOSE"
            for value in frame["variant"]
        ]
    elif "trigger_family" not in frame.columns:
        frame["trigger_family"] = ""
    frame["layer_name"] = layer_name
    return frame


def load_python_tables() -> dict[str, pd.DataFrame]:
    dynamic = read_csv(PY_DYNAMIC).copy()
    dynamic["date_dt"] = dynamic["date"].map(parse_dt)
    dynamic["entry_time_dt"] = pd.NaT
    dynamic["dir_norm"] = dynamic["dir"].map(normalize_dir)
    dynamic["mode_family"] = dynamic["mode"].map(mode_family)
    dynamic["mode_n"] = dynamic["mode"].map(mode_number)
    if "trigger_family" not in dynamic.columns:
        dynamic["trigger_family"] = [
            "M15 SLOT1" if "slot1" in str(value).lower() or "rescue" in str(value).lower() else "M30 CLOSE"
            for value in dynamic.get("variant", pd.Series([""] * len(dynamic)))
        ]
    dynamic["layer_name"] = "dynamic"

    return {
        "raw": load_signal_table(SIGNAL_DIR / "raw_candidates.csv", "raw"),
        "layer12": load_signal_table(find_signal_file("Layer1"), "layer12"),
        "layer3": load_signal_table(find_signal_file("Layer3"), "layer3"),
        "stage": load_signal_table(find_signal_file("Stage"), "stage"),
        "dynamic": dynamic,
    }


def load_mapping_status() -> pd.DataFrame:
    matches = read_csv(PY_MAPPING).copy()
    unmatched = read_csv(PY_UNMATCHED_MT5).copy()
    keep_cols = [
        "mt5_trade_id",
        "match_tier",
        "is_reliable_tier",
        "py_trade_id",
        "py_date",
        "py_trigger_family",
        "py_mode_family",
        "py_mode",
        "py_variant",
        "py_profit",
        "mt5_profit",
        "profit_diff",
        "profit_abs_diff",
    ]
    matches = matches[[col for col in keep_cols if col in matches.columns]].copy()
    matches["mapping_status"] = "matched"
    unmatched = unmatched[["mt5_trade_id"]].copy()
    unmatched["mapping_status"] = "unmatched"
    return pd.concat([matches, unmatched], ignore_index=True).drop_duplicates("mt5_trade_id", keep="first")


def time_diff_minutes(left: object, right: object) -> float:
    ldt = parse_dt(left)
    rdt = parse_dt(right)
    if pd.isna(ldt) or pd.isna(rdt):
        return float("nan")
    return float((ldt - rdt).total_seconds() / 60.0)


def window_rows(table: pd.DataFrame, target_time: pd.Timestamp, window_minutes: int) -> pd.DataFrame:
    if table.empty or pd.isna(target_time):
        return table.iloc[0:0].copy()
    diff = (table["date_dt"] - target_time).dt.total_seconds() / 60.0
    rows = table[diff.abs() <= window_minutes].copy()
    rows["time_diff_minutes"] = diff.loc[rows.index]
    rows["abs_time_diff_minutes"] = rows["time_diff_minutes"].abs()
    return rows


def exact_rows(table: pd.DataFrame, target_time: pd.Timestamp) -> pd.DataFrame:
    if table.empty or pd.isna(target_time):
        return table.iloc[0:0].copy()
    rows = table[table["date_dt"].eq(target_time)].copy()
    rows["time_diff_minutes"] = 0.0
    rows["abs_time_diff_minutes"] = 0.0
    return rows


def count_evidence(rows: pd.DataFrame, direction: str, mt5_mode_n: int | None) -> dict[str, object]:
    if rows.empty:
        return {
            "any_count": 0,
            "same_dir_any_count": 0,
            "same_dir_postn_count": 0,
            "same_dir_postn_same_mode_count": 0,
            "same_dir_nonpostn_count": 0,
            "opposite_dir_postn_count": 0,
            "same_dir_postn_modes": "",
            "same_dir_any_modes": "",
            "same_dir_postn_variants": "",
            "nearest_same_dir_postn_time": "",
            "nearest_same_dir_postn_diff_minutes": "",
            "nearest_same_dir_any_time": "",
            "nearest_same_dir_any_diff_minutes": "",
        }

    same_dir = rows[rows["dir_norm"].eq(direction)].copy()
    same_dir_postn = same_dir[same_dir["mode_family"].eq("post_n")].copy()
    same_dir_same_mode = (
        same_dir_postn[same_dir_postn["mode_n"].eq(mt5_mode_n)].copy()
        if mt5_mode_n is not None
        else same_dir_postn.iloc[0:0].copy()
    )
    same_dir_nonpostn = same_dir[~same_dir["mode_family"].eq("post_n")].copy()
    opposite_postn = rows[~rows["dir_norm"].eq(direction) & rows["mode_family"].eq("post_n")].copy()

    def nearest(frame: pd.DataFrame) -> tuple[str, object]:
        if frame.empty:
            return "", ""
        ordered = frame.sort_values(["abs_time_diff_minutes", "date_dt"])
        row = ordered.iloc[0]
        return fmt_dt(row["date_dt"]), round(float(row["time_diff_minutes"]), 6)

    postn_time, postn_diff = nearest(same_dir_postn)
    any_time, any_diff = nearest(same_dir)

    return {
        "any_count": int(len(rows)),
        "same_dir_any_count": int(len(same_dir)),
        "same_dir_postn_count": int(len(same_dir_postn)),
        "same_dir_postn_same_mode_count": int(len(same_dir_same_mode)),
        "same_dir_nonpostn_count": int(len(same_dir_nonpostn)),
        "opposite_dir_postn_count": int(len(opposite_postn)),
        "same_dir_postn_modes": semijoin(same_dir_postn.get("mode", pd.Series(dtype=str)).tolist()),
        "same_dir_any_modes": semijoin(same_dir.get("mode", pd.Series(dtype=str)).tolist()),
        "same_dir_postn_variants": semijoin(same_dir_postn.get("variant", pd.Series(dtype=str)).tolist()),
        "nearest_same_dir_postn_time": postn_time,
        "nearest_same_dir_postn_diff_minutes": postn_diff,
        "nearest_same_dir_any_time": any_time,
        "nearest_same_dir_any_diff_minutes": any_diff,
    }


def build_window_evidence(targets: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, target in targets.iterrows():
        anchor = parse_dt(target["signal_anchor_time"])
        aligned = parse_dt(target["aligned_time_plus90"])
        direction = normalize_dir(target["dir_norm"])
        mt5_mode_n = safe_int(target["mt5_mode_n"])
        exact_map = {"actual": anchor, "aligned_plus90": aligned}

        for layer, table in tables.items():
            for label, target_time in exact_map.items():
                evidence = count_evidence(exact_rows(table, target_time), direction, mt5_mode_n)
                rows.append(
                    {
                        "mt5_trade_id": target["mt5_trade_id"],
                        "layer": layer,
                        "window_label": label,
                        "window_minutes": 0,
                        "target_time": fmt_dt(target_time),
                        **evidence,
                    }
                )
            for label, window_minutes in TARGET_WINDOWS:
                evidence = count_evidence(window_rows(table, anchor, window_minutes), direction, mt5_mode_n)
                rows.append(
                    {
                        "mt5_trade_id": target["mt5_trade_id"],
                        "layer": layer,
                        "window_label": label,
                        "window_minutes": window_minutes,
                        "target_time": fmt_dt(anchor),
                        **evidence,
                    }
                )
    return pd.DataFrame(rows)


def best_candidates_for_target(
    target: pd.Series,
    tables: dict[str, pd.DataFrame],
    per_layer_limit: int = 8,
) -> pd.DataFrame:
    anchor = parse_dt(target["signal_anchor_time"])
    direction = normalize_dir(target["dir_norm"])
    mt5_mode_n = safe_int(target["mt5_mode_n"])
    rows: list[pd.DataFrame] = []
    for layer in ["raw", "layer12", "layer3", "stage", "dynamic"]:
        table = tables[layer]
        window = window_rows(table, anchor, 7 * 24 * 60)
        if window.empty:
            continue
        sample = window.copy()
        sample["mt5_trade_id"] = target["mt5_trade_id"]
        sample["layer"] = layer
        sample["same_dir"] = sample["dir_norm"].eq(direction)
        sample["is_postn"] = sample["mode_family"].eq("post_n")
        sample["same_mode"] = sample["mode_n"].eq(mt5_mode_n) if mt5_mode_n is not None else False
        sample["_sort_same_dir"] = (~sample["same_dir"]).astype(int)
        sample["_sort_postn"] = (~sample["is_postn"]).astype(int)
        sample["_sort_same_mode"] = (~sample["same_mode"]).astype(int)
        sample = sample.sort_values(
            ["_sort_same_dir", "_sort_postn", "_sort_same_mode", "abs_time_diff_minutes", "date_dt"]
        ).head(per_layer_limit)
        rows.append(sample)

    if not rows:
        return pd.DataFrame()

    combined = pd.concat(rows, ignore_index=True)
    pcol = profit_col(combined)
    out = pd.DataFrame(
        {
            "mt5_trade_id": combined["mt5_trade_id"],
            "layer": combined["layer"],
            "candidate_time": combined["date_dt"].map(fmt_dt),
            "time_diff_minutes": combined["time_diff_minutes"].round(6),
            "dir_norm": combined["dir_norm"],
            "mode": combined["mode"],
            "mode_family": combined["mode_family"],
            "mode_n": combined["mode_n"],
            "trigger_family": combined.get("trigger_family", ""),
            "variant": combined.get("variant", ""),
            "same_dir": combined["same_dir"],
            "is_postn": combined["is_postn"],
            "same_mode": combined["same_mode"],
            "spec_pass": combined.get("spec_pass", ""),
            "spec_reason": combined.get("spec_reason", ""),
            "profit_value": combined[pcol] if pcol else "",
        }
    )
    return out


def get_metric(evidence: pd.DataFrame, mt5_id: str, layer: str, window_label: str, column: str) -> int:
    rows = evidence[
        evidence["mt5_trade_id"].eq(mt5_id)
        & evidence["layer"].eq(layer)
        & evidence["window_label"].eq(window_label)
    ]
    if rows.empty:
        return 0
    value = pd.to_numeric(rows.iloc[0].get(column), errors="coerce")
    if pd.isna(value):
        return 0
    return int(value)


def get_text_metric(evidence: pd.DataFrame, mt5_id: str, layer: str, window_label: str, column: str) -> str:
    rows = evidence[
        evidence["mt5_trade_id"].eq(mt5_id)
        & evidence["layer"].eq(layer)
        & evidence["window_label"].eq(window_label)
    ]
    if rows.empty:
        return ""
    value = rows.iloc[0].get(column, "")
    if pd.isna(value):
        return ""
    return str(value)


def classify_case(target: pd.Series, evidence: pd.DataFrame) -> tuple[str, str, str]:
    mt5_id = str(target["mt5_trade_id"])
    if not boolish(target.get("within_python_m15_coverage", False)) or parse_dt(target["signal_anchor_time"]) < PYTHON_M15_COVERAGE_START:
        return "coverage_edge", "outside Python comparable M15 coverage", "coverage_edge"

    raw_actual_postn = get_metric(evidence, mt5_id, "raw", "actual", "same_dir_postn_count")
    layer12_actual_postn = get_metric(evidence, mt5_id, "layer12", "actual", "same_dir_postn_count")
    raw_60_postn = get_metric(evidence, mt5_id, "raw", "pm60", "same_dir_postn_count")
    raw_60_any = get_metric(evidence, mt5_id, "raw", "pm60", "same_dir_any_count")
    raw_24_postn = get_metric(evidence, mt5_id, "raw", "pm24h", "same_dir_postn_count")
    raw_24_any = get_metric(evidence, mt5_id, "raw", "pm24h", "same_dir_any_count")
    raw_7d_postn = get_metric(evidence, mt5_id, "raw", "pm7d", "same_dir_postn_count")
    raw_7d_any = get_metric(evidence, mt5_id, "raw", "pm7d", "same_dir_any_count")
    raw_7d_opp_postn = get_metric(evidence, mt5_id, "raw", "pm7d", "opposite_dir_postn_count")
    layer12_60_any = get_metric(evidence, mt5_id, "layer12", "pm60", "same_dir_any_count")
    layer12_24_any = get_metric(evidence, mt5_id, "layer12", "pm24h", "same_dir_any_count")
    layer12_7d_postn = get_metric(evidence, mt5_id, "layer12", "pm7d", "same_dir_postn_count")
    layer12_24_postn = get_metric(evidence, mt5_id, "layer12", "pm24h", "same_dir_postn_count")
    layer12_60_postn = get_metric(evidence, mt5_id, "layer12", "pm60", "same_dir_postn_count")
    layer12_7d_any = get_metric(evidence, mt5_id, "layer12", "pm7d", "same_dir_any_count")
    dynamic_7d_postn = get_metric(evidence, mt5_id, "dynamic", "pm7d", "same_dir_postn_count")
    mapping_tier = str(target.get("mapping_match_tier", ""))
    mapping_status = str(target.get("mapping_mapping_status", ""))

    secondary: list[str] = []
    evidence_window = ""

    if raw_actual_postn > 0 and layer12_actual_postn == 0:
        primary = "raw_present_layer12_filtered"
        evidence_window = "actual"
        reason = "raw same-direction post_n exists at actual anchor but no Layer1/2 post_n survives there"
    elif raw_60_postn > 0 and layer12_60_postn == 0:
        primary = "raw_present_layer12_filtered"
        evidence_window = "pm60"
        reason = "raw same-direction post_n exists within +/-60m but no Layer1/2 post_n survives nearby"
    elif layer12_60_any > 0 and layer12_60_postn == 0:
        primary = "layer12_present_not_postn"
        evidence_window = "pm60"
        reason = "Layer1/2 same-direction candidate exists within +/-60m, but it is not post_n"
    elif raw_60_any > 0 and raw_60_postn == 0:
        primary = "trigger_or_direction_drift"
        evidence_window = "pm60"
        reason = "raw same-direction candidate exists within +/-60m, but it is not post_n"
    elif raw_24_postn > 0 and layer12_24_postn == 0:
        primary = "raw_present_layer12_filtered"
        evidence_window = "pm24h"
        reason = "raw same-direction post_n exists within +/-24h but no Layer1/2 post_n survives in that window"
    elif layer12_24_any > 0 and layer12_24_postn == 0:
        primary = "layer12_present_not_postn"
        evidence_window = "pm24h"
        reason = "Layer1/2 same-direction candidate exists within +/-24h, but it is not post_n"
    elif raw_7d_postn == 0:
        if layer12_7d_any > 0 or raw_7d_any > 0 or raw_7d_opp_postn > 0:
            primary = "trigger_or_direction_drift"
            evidence_window = "pm7d"
            reason = "no same-direction raw post_n in +/-7d, but other trigger/direction candidates exist"
        else:
            primary = "raw_absent"
            evidence_window = "pm7d"
            reason = "no same-direction raw post_n candidate within +/-7d"
    elif layer12_7d_postn == 0:
        primary = "raw_present_layer12_filtered"
        evidence_window = "pm7d"
        reason = "raw same-direction post_n exists within +/-7d but no Layer1/2 same-direction post_n survives"
    elif layer12_24_postn == 0:
        primary = "time_axis_drift"
        evidence_window = "pm7d"
        reason = "Layer1/2 same-direction post_n exists only outside +/-24h"
    elif layer12_60_postn == 0:
        primary = "time_axis_drift"
        evidence_window = "pm24h"
        reason = "Layer1/2 same-direction post_n exists within +/-24h but not +/-60m"
    elif layer12_60_any > 0 and layer12_60_postn == 0:
        primary = "layer12_present_not_postn"
        evidence_window = "pm60"
        reason = "Layer1/2 same-direction candidate exists near anchor, but not as post_n"
    else:
        primary = "mapping_policy_artifact"
        evidence_window = "pm60"
        reason = "Layer1/2 near candidate exists; previous no-candidate status is mapping/window artifact"

    if "nearby_7d" in mapping_tier or (mapping_status == "matched" and layer12_24_postn == 0):
        secondary.append("mapping_policy_artifact")
    if dynamic_7d_postn == 0 and layer12_7d_postn > 0:
        secondary.append("post_layer12_execution_filter")
    if layer12_7d_any > 0 and layer12_7d_postn == 0:
        secondary.append("layer12_present_not_postn")
    if layer12_7d_postn > 0 and layer12_24_postn == 0:
        secondary.append("time_axis_drift")
    if raw_24_any > 0 and raw_24_postn == 0:
        secondary.append("trigger_or_direction_drift")
    if not secondary:
        secondary.append(primary)

    return primary, reason, ";".join(dict.fromkeys(secondary)) + f"|evidence_window={evidence_window}"


def build_case_review(targets: pd.DataFrame, evidence: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, target in targets.iterrows():
        mt5_id = str(target["mt5_trade_id"])
        primary, reason, secondary = classify_case(target, evidence)
        rows.append(
            {
                "mt5_trade_id": mt5_id,
                "signal_anchor_time": target["signal_anchor_time"],
                "aligned_time_plus90": target["aligned_time_plus90"],
                "dir_norm": target["dir_norm"],
                "mt5_signal_src": target["mt5_signal_src"],
                "mt5_mode_n": target["mt5_mode_n"],
                "mt5_net_profit": safe_float(target["mt5_net_profit"]),
                "profit_bucket": "positive" if safe_float(target["mt5_net_profit"]) > 0 else "negative_or_flat",
                "mapping_status": target.get("mapping_mapping_status", ""),
                "mapping_match_tier": target.get("mapping_match_tier", ""),
                "mapping_is_reliable_tier": target.get("mapping_is_reliable_tier", ""),
                "mapping_py_trade_id": target.get("mapping_py_trade_id", ""),
                "mapping_py_date": target.get("mapping_py_date", ""),
                "mapping_py_mode": target.get("mapping_py_mode", ""),
                "mapping_profit_diff": target.get("mapping_profit_diff", ""),
                "primary_classification": primary,
                "secondary_classifications": secondary,
                "classification_reason": reason,
                "raw_actual_same_dir_postn_count": get_metric(evidence, mt5_id, "raw", "actual", "same_dir_postn_count"),
                "layer12_actual_same_dir_postn_count": get_metric(evidence, mt5_id, "layer12", "actual", "same_dir_postn_count"),
                "raw_pm60_same_dir_any_count": get_metric(evidence, mt5_id, "raw", "pm60", "same_dir_any_count"),
                "raw_pm60_same_dir_postn_count": get_metric(evidence, mt5_id, "raw", "pm60", "same_dir_postn_count"),
                "layer12_pm60_same_dir_any_count": get_metric(evidence, mt5_id, "layer12", "pm60", "same_dir_any_count"),
                "raw_pm7d_same_dir_postn_count": get_metric(evidence, mt5_id, "raw", "pm7d", "same_dir_postn_count"),
                "raw_pm7d_same_dir_any_count": get_metric(evidence, mt5_id, "raw", "pm7d", "same_dir_any_count"),
                "raw_pm7d_nearest_postn_time": get_text_metric(evidence, mt5_id, "raw", "pm7d", "nearest_same_dir_postn_time"),
                "raw_pm7d_nearest_postn_diff_minutes": get_text_metric(evidence, mt5_id, "raw", "pm7d", "nearest_same_dir_postn_diff_minutes"),
                "layer12_pm60_same_dir_postn_count": get_metric(evidence, mt5_id, "layer12", "pm60", "same_dir_postn_count"),
                "layer12_pm24h_same_dir_postn_count": get_metric(evidence, mt5_id, "layer12", "pm24h", "same_dir_postn_count"),
                "layer12_pm7d_same_dir_postn_count": get_metric(evidence, mt5_id, "layer12", "pm7d", "same_dir_postn_count"),
                "layer12_pm7d_nearest_postn_time": get_text_metric(evidence, mt5_id, "layer12", "pm7d", "nearest_same_dir_postn_time"),
                "layer12_pm7d_nearest_postn_diff_minutes": get_text_metric(evidence, mt5_id, "layer12", "pm7d", "nearest_same_dir_postn_diff_minutes"),
                "layer12_pm7d_modes": get_text_metric(evidence, mt5_id, "layer12", "pm7d", "same_dir_postn_modes"),
                "dynamic_pm7d_same_dir_postn_count": get_metric(evidence, mt5_id, "dynamic", "pm7d", "same_dir_postn_count"),
            }
        )
    return pd.DataFrame(rows)


def build_summaries(case_review: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    class_summary = (
        case_review.groupby("primary_classification", dropna=False)
        .agg(
            count=("mt5_trade_id", "count"),
            mt5_net_profit_sum=("mt5_net_profit", "sum"),
            positive_count=("profit_bucket", lambda s: int((s == "positive").sum())),
            negative_or_flat_count=("profit_bucket", lambda s: int((s == "negative_or_flat").sum())),
            reliable_mapped_count=("mapping_is_reliable_tier", lambda s: int(s.map(boolish).sum())),
            mt5_ids=("mt5_trade_id", lambda s: ";".join(s)),
        )
        .reset_index()
        .sort_values(["count", "mt5_net_profit_sum"], ascending=[False, False])
    )
    profit_summary = (
        case_review.groupby("profit_bucket", dropna=False)
        .agg(
            count=("mt5_trade_id", "count"),
            mt5_net_profit_sum=("mt5_net_profit", "sum"),
            primary_classes=("primary_classification", lambda s: semijoin(s.tolist())),
            mt5_ids=("mt5_trade_id", lambda s: ";".join(s)),
        )
        .reset_index()
    )
    total = int(len(case_review))
    positive = int((case_review["profit_bucket"] == "positive").sum())
    reliable = int(case_review["mapping_is_reliable_tier"].map(boolish).sum())
    top_class_count = int(class_summary["count"].max()) if not class_summary.empty else 0
    raw_absent_count = int((case_review["primary_classification"] == "raw_absent").sum())
    layer12_filtered_count = int((case_review["primary_classification"] == "raw_present_layer12_filtered").sum())
    layer12_present_not_postn_count = int((case_review["primary_classification"] == "layer12_present_not_postn").sum())
    trigger_drift_count = int((case_review["primary_classification"] == "trigger_or_direction_drift").sum())
    time_axis_count = int((case_review["primary_classification"] == "time_axis_drift").sum())
    diagnostic_source_prototype_gate = False
    final = pd.DataFrame(
        [
            {
                "target_count": total,
                "positive_mt5_count": positive,
                "negative_or_flat_mt5_count": total - positive,
                "mt5_net_profit_sum": case_review["mt5_net_profit"].sum(),
                "reliable_mapped_count": reliable,
                "primary_class_count": int(case_review["primary_classification"].nunique()),
                "top_primary_class_count": top_class_count,
                "raw_absent_count": raw_absent_count,
                "raw_present_layer12_filtered_count": layer12_filtered_count,
                "layer12_present_not_postn_count": layer12_present_not_postn_count,
                "trigger_or_direction_drift_count": trigger_drift_count,
                "time_axis_drift_count": time_axis_count,
                "diagnostic_source_prototype_gate_open": diagnostic_source_prototype_gate,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "recommended_next_action": "audit_raw_generator_and_layer12_filters_for_each_source_gap_bucket_no_main_merge",
            }
        ]
    )
    return class_summary, profit_summary, final


def simple_table(frame: pd.DataFrame, max_rows: int = 40) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def build_report(
    case_review: pd.DataFrame,
    class_summary: pd.DataFrame,
    profit_summary: pd.DataFrame,
    final: pd.DataFrame,
) -> list[str]:
    f = final.iloc[0].to_dict()
    return [
        "# Stage-State M15 SLOT1 No-Candidate Source-Gap Audit",
        "",
        "## Final Decision",
        "",
        f"- Target count: `{f['target_count']}`.",
        f"- MT5 net profit sum: `{f['mt5_net_profit_sum']}`.",
        f"- Positive MT5 count: `{f['positive_mt5_count']}`.",
        f"- Reliable mapped count: `{f['reliable_mapped_count']}`.",
        f"- Primary class count: `{f['primary_class_count']}`.",
        f"- Diagnostic source prototype gate: `{f['diagnostic_source_prototype_gate_open']}`.",
        f"- Main signal gate: `{f['main_signal_change_gate_open']}`.",
        f"- EA behavior gate: `{f['ea_behavior_gate_open']}`.",
        f"- Mapping gate: `{f['mapping_change_gate_open']}`.",
        f"- Merge gate: `{f['merge_gate_pass']}`.",
        "",
        "## Classification Summary",
        "",
        simple_table(class_summary),
        "",
        "## Profit Summary",
        "",
        simple_table(profit_summary),
        "",
        "## Case Review",
        "",
        simple_table(
            case_review[
                [
                    "mt5_trade_id",
                    "signal_anchor_time",
                    "dir_norm",
                    "mt5_signal_src",
                    "mt5_net_profit",
                    "mapping_match_tier",
                    "primary_classification",
                    "classification_reason",
                    "raw_actual_same_dir_postn_count",
                    "raw_pm60_same_dir_any_count",
                    "layer12_pm60_same_dir_any_count",
                    "raw_pm7d_same_dir_postn_count",
                    "layer12_pm7d_same_dir_postn_count",
                    "layer12_pm7d_nearest_postn_time",
                    "layer12_pm7d_nearest_postn_diff_minutes",
                    "dynamic_pm7d_same_dir_postn_count",
                ]
            ],
            max_rows=20,
        ),
        "",
        "## Interpretation",
        "",
        "- This audit is diagnostic-only. It does not open the main signal, EA behavior, mapping, or merge gate.",
        "- The no-candidate bucket is reviewed by raw presence, Layer1/2 survival, time-axis distance, mapping status, and MT5 profit sign.",
        "- A source-gap prototype remains closed until one bucket shows a repeatable rule that is not merely a far-window mapping or profit-only selection.",
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cohort = read_csv(COHORT_ALIGNMENT)
    targets = cohort[cohort["cohort_classification"].eq(TARGET_CLASSIFICATION)].copy()
    tables = load_python_tables()
    mapping = load_mapping_status()
    targets = targets.drop(columns=[col for col in targets.columns if col.startswith("mapping_")], errors="ignore")
    targets = targets.merge(mapping.add_prefix("mapping_"), left_on="mt5_trade_id", right_on="mapping_mt5_trade_id", how="left")
    targets = targets.drop(columns=["mapping_mt5_trade_id"], errors="ignore")

    evidence = build_window_evidence(targets, tables)
    sample_frames = [best_candidates_for_target(target, tables) for _, target in targets.iterrows()]
    samples = pd.concat([frame for frame in sample_frames if not frame.empty], ignore_index=True) if sample_frames else pd.DataFrame()
    case_review = build_case_review(targets, evidence)
    class_summary, profit_summary, final = build_summaries(case_review)

    write_csv(case_review, OUT_DIR / "m15_slot1_no_candidate_case_review.csv")
    write_csv(evidence, OUT_DIR / "m15_slot1_no_candidate_window_evidence.csv")
    write_csv(samples, OUT_DIR / "m15_slot1_no_candidate_candidate_samples.csv")
    write_csv(class_summary, OUT_DIR / "m15_slot1_no_candidate_classification_summary.csv")
    write_csv(profit_summary, OUT_DIR / "m15_slot1_no_candidate_profit_summary.csv")
    write_csv(final, OUT_DIR / "m15_slot1_no_candidate_final_decision.csv")
    write_md(build_report(case_review, class_summary, profit_summary, final), OUT_DIR / "m15_slot1_no_candidate_source_gap_audit.md")
    write_md(
        [
            "# M15 SLOT1 No-Candidate Source-Gap Audit",
            "",
            f"- Target count: `{int(final.loc[0, 'target_count'])}`.",
            f"- Diagnostic source prototype gate: `{bool(final.loc[0, 'diagnostic_source_prototype_gate_open'])}`.",
            f"- Merge gate: `{bool(final.loc[0, 'merge_gate_pass'])}`.",
        ],
        OUT_DIR / "README.md",
    )
    print(f"Wrote {OUT_DIR}")
    print(final.to_string(index=False))


if __name__ == "__main__":
    main()
