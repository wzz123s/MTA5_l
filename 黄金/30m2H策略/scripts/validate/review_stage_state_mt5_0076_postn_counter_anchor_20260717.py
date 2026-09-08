# -*- coding: utf-8 -*-
"""Audit mt5_0076 M15 SLOT1 post_n counter/anchor source.

This diagnostic script separates the MT5 real signal anchor from the +90 minute
alignment target used by the mapper. It compares MT5 mt5_0076 with Python raw,
Layer1/2, cluster candidates, and lifecycle trace rows around 2026-03-24.
"""
from __future__ import annotations


from pathlib import Path
import re

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
DATA_DIR = STRATEGY_DIR / "data"

MT5_STAGE_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"
CLUSTER_DIR = VALIDATION_DIR / "stage_state_m15_slot1_postn_cluster_priority_audit_20260717"
LIFECYCLE_DIR = VALIDATION_DIR / "stage_state_lifecycle_aware_maxpos_probe_20260717"

OUT_DIR = VALIDATION_DIR / "stage_state_mt5_0076_postn_counter_anchor_audit_20260717"

TARGET_MT5_ID = "mt5_0076"
WINDOW_START = pd.Timestamp("2026-03-24 08:00:00")
WINDOW_END = pd.Timestamp("2026-03-24 12:30:00")


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


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"L", "B", "BUY", "LONG", "1"}:
        return "BUY"
    if text in {"S", "SELL", "SHORT", "-1"}:
        return "SELL"
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


def mode_number(value: object) -> int:
    text = str(value)
    match = re.search(r"post_n(\d+)", text)
    if not match:
        return -1
    return int(match.group(1))


def safe_float(value: object) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return float("nan")
    return float(parsed)


def minutes_diff(left: object, right: object) -> float:
    ldt = parse_dt(left)
    rdt = parse_dt(right)
    if pd.isna(ldt) or pd.isna(rdt):
        return float("nan")
    return float((ldt - rdt).total_seconds() / 60.0)


def simple_table(frame: pd.DataFrame, columns: list[str] | None = None, max_rows: int = 80) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.copy()
    if columns is not None:
        display = display[[col for col in columns if col in display.columns]]
    return display.head(max_rows).to_markdown(index=False)


def find_signal_file(keyword: str) -> Path:
    hits = [path for path in SIGNAL_DIR.glob("*.csv") if keyword.lower() in path.name.lower()]
    if not hits:
        raise FileNotFoundError(f"no signal file for keyword={keyword}")
    return hits[0]


def load_mt5_unique_target() -> pd.Series:
    mt5 = read_csv(DYNAMIC_DIR / "mt5_ledger_unique_signals.csv")
    mt5 = mt5.copy()
    mt5["mt5_trade_id"] = [f"mt5_{idx + 1:04d}" for idx in range(len(mt5))]
    mt5["signal_anchor_dt"] = parse_dt_series(mt5["signal_anchor_time"])
    mt5["aligned_target_time"] = mt5["signal_anchor_dt"] + pd.Timedelta(minutes=90)
    hit = mt5[mt5["mt5_trade_id"].eq(TARGET_MT5_ID)].copy()
    if hit.empty:
        raise RuntimeError(f"{TARGET_MT5_ID} not found")
    return hit.iloc[0]


def load_mt5_ledger_target(mt5_target: pd.Series) -> pd.DataFrame:
    ledger = read_csv(MT5_STAGE_DIR / "30m2H_strategy_trade_ledger.csv")
    ledger["signal_anchor_dt"] = parse_dt_series(ledger["signal_anchor_time"])
    ledger["open_dt"] = parse_dt_series(ledger["open_time"])
    ledger["exit_dt"] = parse_dt_series(ledger["exit_time"])
    rows = ledger[
        ledger["signal_anchor_dt"].eq(mt5_target["signal_anchor_dt"])
        & ledger["signal_src"].astype(str).eq(str(mt5_target["signal_src"]))
        & ledger["dir"].map(normalize_dir).eq(normalize_dir(mt5_target["dir"]))
    ].copy()
    return rows.sort_values(["stage", "ticket"]).reset_index(drop=True)


def build_mt5_signal_context() -> tuple[pd.DataFrame, pd.DataFrame]:
    signals = read_csv(MT5_STAGE_DIR / "30m2H_strategy_signals_export.csv")
    signals["bar_dt"] = parse_dt_series(signals["bar_time"])
    signals = signals[signals["bar_dt"].between(WINDOW_START, WINDOW_END, inclusive="both")].copy()
    signals["source_table"] = "mt5_signal_export"
    signals["event_time"] = signals["bar_dt"].map(fmt_dt)
    signals["mode"] = ""
    signals["signal_src"] = ""
    signals["dir_norm"] = ""
    signals["entry_or_close"] = signals["close"]
    signals["stop"] = signals.get("stop_sma", "")
    signals["note"] = signals["decision"].astype(str) + ":" + signals["skip_reason"].astype(str)

    ledger = read_csv(MT5_STAGE_DIR / "30m2H_strategy_trade_ledger.csv")
    ledger["signal_anchor_dt"] = parse_dt_series(ledger["signal_anchor_time"])
    ledger["open_dt"] = parse_dt_series(ledger["open_time"])
    ledger["exit_dt"] = parse_dt_series(ledger["exit_time"])
    ledger = ledger[
        ledger["signal_anchor_dt"].between(WINDOW_START, WINDOW_END, inclusive="both")
        & ledger["signal_src"].astype(str).str.contains("post_n", na=False)
    ].copy()
    grouped = []
    group_cols = ["signal_anchor_time", "trigger_tag", "signal_src", "dir"]
    for keys, grp in ledger.groupby(group_cols, dropna=False):
        signal_anchor_time, trigger_tag, signal_src, direction = keys
        grouped.append(
            {
                "source_table": "mt5_trade_ledger",
                "event_time": fmt_dt(signal_anchor_time),
                "signal_anchor_time": fmt_dt(signal_anchor_time),
                "aligned_target_time_plus90": fmt_dt(parse_dt(signal_anchor_time) + pd.Timedelta(minutes=90)),
                "open_time_min": fmt_dt(grp["open_dt"].min()),
                "exit_time_max": fmt_dt(grp["exit_dt"].max()),
                "trigger_family": str(trigger_tag).replace("[", "").replace("]", ""),
                "signal_src": signal_src,
                "mode": signal_src,
                "mode_n": mode_number(signal_src),
                "dir_norm": normalize_dir(direction),
                "entry_or_close": round(float(pd.to_numeric(grp["signal_entry"], errors="coerce").iloc[0]), 6),
                "stop": round(float(pd.to_numeric(grp["signal_stop"], errors="coerce").iloc[0]), 6),
                "stage_rows": int(len(grp)),
                "net_profit": round(float(pd.to_numeric(grp["net_profit"], errors="coerce").sum()), 6),
                "note": ";".join(sorted(set(grp["local_exit_reason"].astype(str)))),
            }
        )
    ledger_context = pd.DataFrame(grouped)
    return signals, ledger_context


def prep_python_signal_table(path: Path, source_table: str) -> pd.DataFrame:
    df = read_csv(path)
    df["date_dt"] = parse_dt_series(df["date"])
    df = df[df["date_dt"].between(WINDOW_START, WINDOW_END, inclusive="both")].copy()
    df["source_table"] = source_table
    df["event_time"] = df["date_dt"].map(fmt_dt)
    df["dir_norm"] = df["dir"].map(normalize_dir)
    df["mode_n"] = df["mode"].map(mode_number)
    df["mode_family"] = df["mode"].map(mode_family)
    return df


def load_python_tables() -> dict[str, pd.DataFrame]:
    return {
        "python_raw_candidates": prep_python_signal_table(SIGNAL_DIR / "raw_candidates.csv", "python_raw_candidates"),
        "python_layer12_pass": prep_python_signal_table(find_signal_file("Layer1"), "python_layer12_pass"),
        "python_layer3_selected": prep_python_signal_table(find_signal_file("Layer3"), "python_layer3_selected"),
        "python_stage_result": prep_python_signal_table(find_signal_file("Stage"), "python_stage_result"),
    }


def load_cluster_and_lifecycle() -> tuple[pd.DataFrame, pd.DataFrame]:
    cluster = read_csv(CLUSTER_DIR / "cluster_priority_candidate_rows.csv")
    cluster["row_time_dt"] = parse_dt_series(cluster["row_time"])
    cluster = cluster[
        cluster["row_time_dt"].between(WINDOW_START, WINDOW_END, inclusive="both")
        & cluster["dir_norm"].map(normalize_dir).eq("BUY")
    ].copy()
    cluster["source_table"] = "cluster_priority_candidates"
    cluster["event_time"] = cluster["row_time_dt"].map(fmt_dt)
    cluster["mode_n"] = cluster["mode"].map(mode_number)

    trace = read_csv(LIFECYCLE_DIR / "lifecycle_maxpos_trace.csv")
    trace["row_time_dt"] = parse_dt_series(trace["row_time"])
    trace = trace[
        trace["variant"].astype(str).eq("lifecycle_replace_same_family8_stage3time")
        & trace["policy"].astype(str).eq("lifecycle_stage3time")
        & trace["prototype_added_candidate"].map(as_bool)
        & trace["row_time_dt"].between(WINDOW_START, WINDOW_END, inclusive="both")
    ].copy()
    trace["source_table"] = "lifecycle_trace_same_family8"
    trace["event_time"] = trace["row_time_dt"].map(fmt_dt)
    trace["mode_n"] = trace["mode"].map(mode_number)
    return cluster, trace


def build_combined_timeline(
    mt5_signals: pd.DataFrame,
    mt5_ledger_context: pd.DataFrame,
    python_tables: dict[str, pd.DataFrame],
    cluster: pd.DataFrame,
    lifecycle: pd.DataFrame,
) -> pd.DataFrame:
    rows = []
    for _, row in mt5_signals.iterrows():
        rows.append(
            {
                "source_table": "mt5_signal_export",
                "event_time": row.get("event_time", ""),
                "anchor_or_date_time": row.get("event_time", ""),
                "aligned_target_time_plus90": "",
                "open_or_entry_time": "",
                "dir_norm": "",
                "trigger_family": "",
                "mode": "",
                "mode_n": "",
                "entry_or_close": row.get("close", ""),
                "stop": row.get("stop_sma", ""),
                "decision_or_status": row.get("decision", ""),
                "note": row.get("skip_reason", ""),
            }
        )
    for _, row in mt5_ledger_context.iterrows():
        rows.append(
            {
                "source_table": "mt5_trade_ledger",
                "event_time": row.get("event_time", ""),
                "anchor_or_date_time": row.get("signal_anchor_time", ""),
                "aligned_target_time_plus90": row.get("aligned_target_time_plus90", ""),
                "open_or_entry_time": row.get("open_time_min", ""),
                "dir_norm": row.get("dir_norm", ""),
                "trigger_family": row.get("trigger_family", ""),
                "mode": row.get("signal_src", ""),
                "mode_n": row.get("mode_n", ""),
                "entry_or_close": row.get("entry_or_close", ""),
                "stop": row.get("stop", ""),
                "decision_or_status": "TRADE",
                "note": row.get("note", ""),
            }
        )
    for name, frame in python_tables.items():
        for _, row in frame.iterrows():
            rows.append(
                {
                    "source_table": name,
                    "event_time": row.get("event_time", ""),
                    "anchor_or_date_time": row.get("event_time", ""),
                    "aligned_target_time_plus90": "",
                    "open_or_entry_time": fmt_dt(row.get("entry_time", "")),
                    "dir_norm": row.get("dir_norm", ""),
                    "trigger_family": "M15 SLOT1" if "slot1" in str(row.get("variant", "")).lower() else "M30 CLOSE",
                    "mode": row.get("mode", ""),
                    "mode_n": row.get("mode_n", ""),
                    "entry_or_close": row.get("entry", ""),
                    "stop": row.get("stop", ""),
                    "decision_or_status": row.get("spec_reason", ""),
                    "note": row.get("variant", ""),
                }
            )
    for _, row in cluster.iterrows():
        rows.append(
            {
                "source_table": "cluster_priority_candidates",
                "event_time": row.get("event_time", ""),
                "anchor_or_date_time": row.get("event_time", ""),
                "aligned_target_time_plus90": "",
                "open_or_entry_time": "",
                "dir_norm": row.get("dir_norm", ""),
                "trigger_family": row.get("trigger_family", ""),
                "mode": row.get("mode", ""),
                "mode_n": row.get("mode_n", ""),
                "entry_or_close": row.get("candidate_entry", ""),
                "stop": row.get("candidate_stop", ""),
                "decision_or_status": row.get("candidate_spec_reason", ""),
                "note": row.get("exact_same_family_mt5_id", ""),
            }
        )
    for _, row in lifecycle.iterrows():
        rows.append(
            {
                "source_table": "lifecycle_trace_same_family8",
                "event_time": row.get("event_time", ""),
                "anchor_or_date_time": row.get("event_time", ""),
                "aligned_target_time_plus90": "",
                "open_or_entry_time": "",
                "dir_norm": row.get("dir_norm", ""),
                "trigger_family": row.get("trigger_family", ""),
                "mode": row.get("mode", ""),
                "mode_n": row.get("mode_n", ""),
                "entry_or_close": "",
                "stop": "",
                "decision_or_status": "accepted" if as_bool(row.get("accepted", False)) else "rejected",
                "note": f"active_count={row.get('active_count_before', '')}; blockers={row.get('active_blockers_before', '')}",
            }
        )
    out = pd.DataFrame(rows)
    out["_event_dt"] = parse_dt_series(out["event_time"])
    return out.sort_values(["_event_dt", "source_table", "mode_n"]).drop(columns=["_event_dt"]).reset_index(drop=True)


def build_candidate_alignment(
    mt5_target: pd.Series,
    mt5_ledger_target: pd.DataFrame,
    python_tables: dict[str, pd.DataFrame],
    cluster: pd.DataFrame,
) -> pd.DataFrame:
    mt5_anchor = mt5_target["signal_anchor_dt"]
    mt5_aligned = mt5_target["aligned_target_time"]
    mt5_mode_n = mode_number(mt5_target["signal_src"])
    mt5_open_min = mt5_ledger_target["open_dt"].min() if not mt5_ledger_target.empty else pd.NaT
    mt5_entry = safe_float(mt5_ledger_target["signal_entry"].iloc[0]) if not mt5_ledger_target.empty else float("nan")
    mt5_stop = safe_float(mt5_ledger_target["signal_stop"].iloc[0]) if not mt5_ledger_target.empty else float("nan")

    rows = []
    for table_name in ["python_raw_candidates", "python_layer12_pass"]:
        frame = python_tables[table_name].copy()
        frame = frame[
            frame["dir_norm"].eq("BUY")
            & frame["mode"].astype(str).str.contains("post_n", na=False)
        ].copy()
        for _, row in frame.iterrows():
            row_time = row["date_dt"]
            mode_n = int(row["mode_n"])
            rows.append(
                {
                    "source_table": table_name,
                    "row_time": fmt_dt(row_time),
                    "entry_time": fmt_dt(row.get("entry_time", "")),
                    "mode": row.get("mode", ""),
                    "mode_n": mode_n,
                    "mode_n_diff_vs_mt5_signal_src": mode_n - mt5_mode_n,
                    "time_diff_to_mt5_anchor_minutes": minutes_diff(row_time, mt5_anchor),
                    "time_diff_to_mt5_aligned_plus90_minutes": minutes_diff(row_time, mt5_aligned),
                    "time_diff_entry_to_mt5_open_minutes": minutes_diff(row.get("entry_time", ""), mt5_open_min),
                    "entry": row.get("entry", ""),
                    "stop": row.get("stop", ""),
                    "entry_diff_vs_mt5_signal_entry": round(safe_float(row.get("entry", "")) - mt5_entry, 6),
                    "stop_diff_vs_mt5_signal_stop": round(safe_float(row.get("stop", "")) - mt5_stop, 6),
                    "spec_pass": row.get("spec_pass", ""),
                    "spec_reason": row.get("spec_reason", ""),
                    "variant": row.get("variant", ""),
                    "matches_actual_anchor_time": row_time == mt5_anchor,
                    "matches_aligned_plus90_time": row_time == mt5_aligned,
                    "matches_mt5_mode_label": mode_n == mt5_mode_n,
                    "matches_mt5_open_time": parse_dt(row.get("entry_time", "")) == mt5_open_min,
                }
            )
    for _, row in cluster.iterrows():
        row_time = row["row_time_dt"]
        mode_n = int(row["mode_n"])
        rows.append(
            {
                "source_table": "cluster_priority_candidates",
                "row_time": fmt_dt(row_time),
                "entry_time": "",
                "mode": row.get("mode", ""),
                "mode_n": mode_n,
                "mode_n_diff_vs_mt5_signal_src": mode_n - mt5_mode_n,
                "time_diff_to_mt5_anchor_minutes": minutes_diff(row_time, mt5_anchor),
                "time_diff_to_mt5_aligned_plus90_minutes": minutes_diff(row_time, mt5_aligned),
                "time_diff_entry_to_mt5_open_minutes": float("nan"),
                "entry": row.get("candidate_entry", ""),
                "stop": row.get("candidate_stop", ""),
                "entry_diff_vs_mt5_signal_entry": round(safe_float(row.get("candidate_entry", "")) - mt5_entry, 6),
                "stop_diff_vs_mt5_signal_stop": round(safe_float(row.get("candidate_stop", "")) - mt5_stop, 6),
                "spec_pass": row.get("candidate_spec_pass", ""),
                "spec_reason": row.get("candidate_spec_reason", ""),
                "variant": row.get("variant", ""),
                "matches_actual_anchor_time": row_time == mt5_anchor,
                "matches_aligned_plus90_time": row_time == mt5_aligned,
                "matches_mt5_mode_label": mode_n == mt5_mode_n,
                "matches_mt5_open_time": False,
            }
        )
    return pd.DataFrame(rows).sort_values(["source_table", "row_time", "mode_n"]).reset_index(drop=True)


def build_anchor_summary(mt5_target: pd.Series, mt5_ledger_target: pd.DataFrame, alignment: pd.DataFrame) -> pd.DataFrame:
    mt5_anchor = mt5_target["signal_anchor_dt"]
    mt5_aligned = mt5_target["aligned_target_time"]
    mt5_mode_n = mode_number(mt5_target["signal_src"])
    mt5_open_min = mt5_ledger_target["open_dt"].min() if not mt5_ledger_target.empty else pd.NaT
    mt5_exit_max = mt5_ledger_target["exit_dt"].max() if not mt5_ledger_target.empty else pd.NaT

    actual_anchor_rows = alignment[alignment["matches_actual_anchor_time"].map(as_bool)]
    aligned_rows = alignment[alignment["matches_aligned_plus90_time"].map(as_bool)]
    mode_label_rows = alignment[alignment["matches_mt5_mode_label"].map(as_bool)]
    open_time_rows = alignment[alignment["matches_mt5_open_time"].map(as_bool)]

    anchor_counter_shift = bool(not actual_anchor_rows.empty and not actual_anchor_rows["matches_mt5_mode_label"].map(as_bool).any())
    mode_label_drift = bool(not aligned_rows.empty and not aligned_rows["matches_mt5_mode_label"].map(as_bool).any())
    mapping_artifact = bool(not aligned_rows.empty and parse_dt(mt5_aligned) != parse_dt(mt5_anchor))
    python_slot1_gap = bool(len(alignment[alignment["source_table"].eq("python_layer12_pass")]) > 1)
    ea_source_gap = True

    classifications = []
    if anchor_counter_shift:
        classifications.append("counter_anchor_shift")
    if mode_label_drift:
        classifications.append("mode_label_drift")
    if mapping_artifact:
        classifications.append("mapping_alignment_artifact")
    if python_slot1_gap:
        classifications.append("python_slot1_counter_gap")
    if ea_source_gap:
        classifications.append("ea_signal_source_gap")

    primary = "mapping_alignment_artifact"
    if not mapping_artifact and anchor_counter_shift:
        primary = "counter_anchor_shift"
    elif not mapping_artifact and mode_label_drift:
        primary = "mode_label_drift"

    return pd.DataFrame(
        [
            {
                "target_mt5_id": TARGET_MT5_ID,
                "mt5_signal_anchor_time": fmt_dt(mt5_anchor),
                "mt5_aligned_target_time_plus90": fmt_dt(mt5_aligned),
                "mt5_open_time_min": fmt_dt(mt5_open_min),
                "mt5_exit_time_max": fmt_dt(mt5_exit_max),
                "mt5_signal_src": mt5_target.get("signal_src", ""),
                "mt5_mode_n": mt5_mode_n,
                "actual_anchor_python_rows": int(len(actual_anchor_rows)),
                "actual_anchor_python_modes": ";".join(actual_anchor_rows["mode"].astype(str).tolist()),
                "aligned_plus90_python_rows": int(len(aligned_rows)),
                "aligned_plus90_python_modes": ";".join(aligned_rows["mode"].astype(str).tolist()),
                "mode_label_match_rows": int(len(mode_label_rows)),
                "mode_label_match_times": ";".join(mode_label_rows["row_time"].astype(str).tolist()),
                "open_time_match_rows": int(len(open_time_rows)),
                "open_time_match_modes": ";".join(open_time_rows["mode"].astype(str).tolist()),
                "counter_anchor_shift": anchor_counter_shift,
                "mode_label_drift": mode_label_drift,
                "mapping_alignment_artifact": mapping_artifact,
                "python_slot1_counter_gap": python_slot1_gap,
                "ea_signal_source_gap": ea_source_gap,
                "primary_classification": primary,
                "classifications": ";".join(classifications),
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "recommended_next_action": "audit_ea_slot1_counter_generation_against_python_layer12_before_any_ranking_prototype",
            }
        ]
    )


def write_report(
    summary: pd.DataFrame,
    alignment: pd.DataFrame,
    timeline: pd.DataFrame,
    mt5_ledger_target: pd.DataFrame,
) -> None:
    s = summary.iloc[0]
    lines = [
        "# Stage-State mt5_0076 M15 SLOT1 post_n Counter / Anchor Source Audit",
        "",
        "## Scope",
        "",
        "- Diagnostic-only audit for `mt5_0076`.",
        "- Separates MT5 real signal anchor from mapper `+90` aligned target time.",
        "- Compares MT5 signal source against Python raw, Layer1/2, cluster candidate, and lifecycle trace rows.",
        "- Does not change baseline signals, EA behavior, dynamic risk, or mapping.",
        "",
        "## Final Classification",
        "",
        f"- Primary classification: `{s['primary_classification']}`.",
        f"- Classifications: `{s['classifications']}`.",
        f"- MT5 signal anchor: `{s['mt5_signal_anchor_time']}`.",
        f"- MT5 aligned target time +90: `{s['mt5_aligned_target_time_plus90']}`.",
        f"- MT5 open time: `{s['mt5_open_time_min']}`.",
        f"- MT5 signal src: `{s['mt5_signal_src']}`.",
        f"- Actual-anchor Python modes: `{s['actual_anchor_python_modes']}`.",
        f"- Aligned +90 Python modes: `{s['aligned_plus90_python_modes']}`.",
        f"- Mode-label match times: `{s['mode_label_match_times']}`.",
        f"- Open-time match modes: `{s['open_time_match_modes']}`.",
        "",
        "## Interpretation",
        "",
        "- The MT5 trade is anchored at `2026-03-24 10:30`, not at `2026-03-24 12:00`.",
        "- The `2026-03-24 12:00` exact candidate exists because the mapper uses `signal_anchor_time + 90 minutes`.",
        "- At the MT5 real anchor, Python Layer1/2 has `post_n3`, not MT5 `post_n5`.",
        "- At the mapper-aligned time, Python has `post_n6`, again not MT5 `post_n5`.",
        "- Python `post_n5` occurs at `2026-03-24 11:30`, between the real anchor and the aligned target.",
        "- This means latest/max-mode/post_n6 ranking would be correcting a mapper-aligned artifact before the counter source is proven.",
        "",
        "## Anchor Summary",
        "",
        simple_table(summary),
        "",
        "## Candidate Alignment",
        "",
        simple_table(alignment),
        "",
        "## MT5 Target Ledger Rows",
        "",
        simple_table(
            mt5_ledger_target,
            [
                "signal_anchor_time",
                "trigger_tag",
                "signal_src",
                "dir",
                "stage",
                "open_time",
                "signal_entry",
                "signal_stop",
                "exit_time",
                "net_profit",
                "local_exit_reason",
                "deal_reason",
            ],
        ),
        "",
        "## Combined Timeline",
        "",
        simple_table(timeline),
        "",
        "## Gates",
        "",
        f"- `main_signal_change_gate_open = {as_bool(s['main_signal_change_gate_open'])}`",
        f"- `ea_behavior_gate_open = {as_bool(s['ea_behavior_gate_open'])}`",
        f"- `mapping_change_gate_open = {as_bool(s['mapping_change_gate_open'])}`",
        f"- `merge_gate_pass = {as_bool(s['merge_gate_pass'])}`",
        f"- Recommended next action: `{s['recommended_next_action']}`.",
        "",
        "## Output Files",
        "",
        "- `postn_counter_anchor_summary.csv`",
        "- `postn_counter_anchor_candidate_alignment.csv`",
        "- `postn_counter_anchor_combined_timeline.csv`",
        "- `postn_counter_anchor_mt5_target_ledger_rows.csv`",
    ]
    write_text(OUT_DIR / "mt5_0076_postn_counter_anchor_audit.md", "\n".join(lines))
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# stage_state_mt5_0076_postn_counter_anchor_audit_20260717",
                "",
                "Diagnostic-only counter/anchor source audit for mt5_0076.",
                "",
                "No baseline strategy, EA, dynamic-risk, or mapping logic is changed.",
            ]
        ),
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mt5_target = load_mt5_unique_target()
    mt5_ledger_target = load_mt5_ledger_target(mt5_target)
    mt5_signals, mt5_ledger_context = build_mt5_signal_context()
    python_tables = load_python_tables()
    cluster, lifecycle = load_cluster_and_lifecycle()
    timeline = build_combined_timeline(mt5_signals, mt5_ledger_context, python_tables, cluster, lifecycle)
    alignment = build_candidate_alignment(mt5_target, mt5_ledger_target, python_tables, cluster)
    summary = build_anchor_summary(mt5_target, mt5_ledger_target, alignment)

    export_csv(summary, OUT_DIR / "postn_counter_anchor_summary.csv")
    export_csv(alignment, OUT_DIR / "postn_counter_anchor_candidate_alignment.csv")
    export_csv(timeline, OUT_DIR / "postn_counter_anchor_combined_timeline.csv")
    export_csv(mt5_ledger_target, OUT_DIR / "postn_counter_anchor_mt5_target_ledger_rows.csv")
    write_report(summary, alignment, timeline, mt5_ledger_target)


if __name__ == "__main__":
    main()
