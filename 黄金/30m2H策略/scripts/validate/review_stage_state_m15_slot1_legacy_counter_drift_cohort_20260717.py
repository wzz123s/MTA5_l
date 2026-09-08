# -*- coding: utf-8 -*-
"""Audit all M15 SLOT1 post_n legacy merged-counter drift cases.

Diagnostic-only:
- no EA edits
- no signal snapshot edits
- no mapping-rule edits
- no dynamic-risk edits
"""

from __future__ import annotations


from dataclasses import dataclass
from pathlib import Path
import math
import re

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
STRATEGY_DIR = ROOT / "黄金" / "30m2H策略"
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

OUT_DIR = VALIDATION_DIR / "stage_state_m15_slot1_legacy_counter_drift_cohort_20260717"

MT5_STAGE_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"
SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"

TESTER_LOG = MT5_STAGE_DIR / "tester_agent_20260716.log"
MT5_UNIQUE = DYNAMIC_DIR / "mt5_ledger_unique_signals.csv"
PY_DYNAMIC = DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"
PY_MAPPING = MAPPING_DIR / "python_mt5_mt5_unique_matches.csv"
PY_UNMATCHED_MT5 = MAPPING_DIR / "python_mt5_unmatched_mt5_trades.csv"

PYTHON_M15_COVERAGE_START = pd.Timestamp("2022-04-08 14:30:00")
EA_ALIGN_DELTA_MINUTES = 90
NEARBY_MINUTES = 180


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


def signed_expected_counter(mode_n: int | None, direction: str) -> int | None:
    if mode_n is None:
        return None
    return mode_n if normalize_dir(direction) == "BUY" else -mode_n


def semijoin(values: list[object]) -> str:
    out = []
    for value in values:
        if pd.isna(value):
            continue
        text = str(value)
        if text and text not in out:
            out.append(text)
    return ";".join(out)


def minutes(left: object, right: object) -> float:
    ldt = parse_dt(left)
    rdt = parse_dt(right)
    if pd.isna(ldt) or pd.isna(rdt):
        return float("nan")
    return float((ldt - rdt).total_seconds() / 60.0)


def read_lines(path: Path):
    for enc in ("utf-8-sig", "utf-16", "utf-16-le", "gb18030", "cp936"):
        try:
            with path.open("r", encoding=enc) as handle:
                for line in handle:
                    yield line.rstrip("\n")
            return
        except UnicodeError:
            continue
    with path.open("r", errors="ignore") as handle:
        for line in handle:
            yield line.rstrip("\n")


def parse_key_value(line: str, key: str) -> str:
    if key == "anchor":
        match = re.search(r"anchor=(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2})", line)
        return match.group(1) if match else ""
    match = re.search(rf"{re.escape(key)}=([^\s,]+)", line)
    return match.group(1) if match else ""


def parse_event_kind(line: str) -> str:
    if "[SIGNAL]" in line:
        return "SIGNAL"
    for kind in ["Candidate", "Execute", "Stop"]:
        if f"[DIAG] {kind}" in line:
            return kind
    return ""


def parse_signal_direction(line: str) -> str:
    match = re.search(r"\[SIGNAL\]\s+(BUY|SELL)!", line)
    if match:
        return match.group(1)
    return parse_key_value(line, "dir")


def parse_m15_slot1_postn_log_events() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    for line_no, line in enumerate(read_lines(TESTER_LOG), start=1):
        if "[M15 SLOT1]" not in line or "post_n" not in line:
            continue
        kind = parse_event_kind(line)
        if kind not in {"Candidate", "Execute", "SIGNAL", "Stop"}:
            continue
        event_match = re.search(r"(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})", line)
        if not event_match:
            continue
        mode = parse_key_value(line, "mode")
        mode_n = mode_number(mode)
        if mode_n is None:
            continue
        direction = normalize_dir(parse_signal_direction(line))
        anchor = parse_key_value(line, "anchor")
        rows.append(
            {
                "line_number": line_no,
                "event_kind": kind,
                "event_time": fmt_dt(event_match.group(1)),
                "anchor_time": fmt_dt(anchor),
                "dir_norm": direction,
                "mode": mode,
                "mode_n": mode_n,
                "post_n_counter": safe_int(parse_key_value(line, "post_n_counter")),
                "merged_post_n_counter": safe_int(parse_key_value(line, "merged_post_n_counter")),
                "m15_close": safe_float(parse_key_value(line, "m15_close")),
                "m15_smma13": safe_float(parse_key_value(line, "m15_smma13")),
                "real_entry": safe_float(parse_key_value(line, "real_entry")),
                "stop_price": safe_float(parse_key_value(line, "stop_price")),
                "stop_pts": safe_float(parse_key_value(line, "stop_pts")),
                "line": line.strip(),
            }
        )

    raw = pd.DataFrame(rows)
    if raw.empty:
        return raw, raw

    group_cols = [
        "event_kind",
        "event_time",
        "anchor_time",
        "dir_norm",
        "mode",
        "mode_n",
        "post_n_counter",
        "merged_post_n_counter",
    ]
    dedup = (
        raw.sort_values("line_number")
        .groupby(group_cols, dropna=False)
        .agg(
            first_line_number=("line_number", "min"),
            last_line_number=("line_number", "max"),
            session_hit_count=("line_number", "count"),
            m15_close=("m15_close", "first"),
            m15_smma13=("m15_smma13", "first"),
            real_entry=("real_entry", "first"),
            stop_price=("stop_price", "first"),
            stop_pts=("stop_pts", "first"),
            sample_line=("line", "last"),
        )
        .reset_index()
    )
    return raw, dedup


def load_mt5_postn_cohort() -> pd.DataFrame:
    mt5 = read_csv(MT5_UNIQUE).copy()
    mt5["mt5_trade_id"] = [f"mt5_{idx + 1:04d}" for idx in range(len(mt5))]
    mt5["signal_anchor_dt"] = mt5["signal_anchor_time"].map(parse_dt)
    mt5["aligned_dt"] = mt5["signal_anchor_dt"] + pd.Timedelta(minutes=EA_ALIGN_DELTA_MINUTES)
    mt5["dir_norm"] = mt5["dir"].map(normalize_dir)
    mt5["mt5_mode_n"] = mt5["signal_src"].map(mode_number)
    mt5["mt5_expected_signed_counter"] = [
        signed_expected_counter(mode_n, direction) for mode_n, direction in zip(mt5["mt5_mode_n"], mt5["dir_norm"])
    ]
    cohort = mt5[
        mt5["trigger_family"].astype(str).eq("M15 SLOT1")
        & mt5["mode_family"].astype(str).eq("post_n")
    ].copy()
    return cohort.reset_index(drop=True)


def find_signal_file(keyword: str) -> Path:
    hits = [path for path in SIGNAL_DIR.glob("*.csv") if keyword.lower() in path.name.lower()]
    if not hits:
        raise FileNotFoundError(f"no signal file for {keyword}")
    return hits[0]


def load_python_signal_table(path: Path, source_table: str) -> pd.DataFrame:
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
    else:
        frame["trigger_family"] = ""
    frame["source_table"] = source_table
    return frame


def load_python_tables() -> dict[str, pd.DataFrame]:
    dynamic = read_csv(PY_DYNAMIC).copy()
    dynamic["date_dt"] = dynamic["date"].map(parse_dt)
    dynamic["entry_time_dt"] = pd.NaT
    dynamic["dir_norm"] = dynamic["dir"].map(normalize_dir)
    dynamic["mode_family"] = dynamic["mode"].map(mode_family)
    dynamic["mode_n"] = dynamic["mode"].map(mode_number)
    dynamic["source_table"] = "python_dynamic_risk"

    return {
        "raw": load_python_signal_table(SIGNAL_DIR / "raw_candidates.csv", "python_raw_candidates"),
        "layer12": load_python_signal_table(find_signal_file("Layer1"), "python_layer12_pass"),
        "layer3": load_python_signal_table(find_signal_file("Layer3"), "python_layer3_selected"),
        "stage": load_python_signal_table(find_signal_file("Stage"), "python_stage_result"),
        "dynamic": dynamic,
    }


@dataclass
class MatchSummary:
    count: int
    exact_count: int
    modes: str
    mode_ns: str
    trigger_families: str
    variants: str
    first_mode_n: int | None
    first_time: str
    first_time_diff: float
    first_profit: float


def summarize_rows(rows: pd.DataFrame, target_time: pd.Timestamp, mt5_mode_n: int | None) -> MatchSummary:
    if rows.empty:
        return MatchSummary(0, 0, "", "", "", "", None, "", float("nan"), float("nan"))
    ordered = rows.copy()
    ordered["_abs_mode_diff"] = [
        abs(int(mode_n) - int(mt5_mode_n)) if mt5_mode_n is not None and pd.notna(mode_n) else 999
        for mode_n in ordered["mode_n"]
    ]
    ordered["_abs_time_diff"] = (ordered["date_dt"] - target_time).abs().dt.total_seconds() / 60.0
    ordered = ordered.sort_values(["_abs_mode_diff", "_abs_time_diff", "date_dt"])
    first = ordered.iloc[0]
    profit_col = "dynamic_total_$" if "dynamic_total_$" in ordered.columns else ("total_$" if "total_$" in ordered.columns else "")
    first_profit = safe_float(first.get(profit_col, "")) if profit_col else float("nan")
    return MatchSummary(
        count=int(len(rows)),
        exact_count=int((rows["mode_n"] == mt5_mode_n).sum()) if mt5_mode_n is not None else 0,
        modes=semijoin(rows["mode"].tolist()),
        mode_ns=semijoin(rows["mode_n"].tolist()),
        trigger_families=semijoin(rows.get("trigger_family", pd.Series(dtype=str)).tolist()),
        variants=semijoin(rows.get("variant", pd.Series(dtype=str)).tolist()),
        first_mode_n=safe_int(first.get("mode_n")),
        first_time=fmt_dt(first.get("date_dt")),
        first_time_diff=minutes(first.get("date_dt"), target_time),
        first_profit=first_profit,
    )


def match_python_table(
    table: pd.DataFrame,
    anchor: pd.Timestamp,
    aligned: pd.Timestamp,
    direction: str,
    mt5_mode_n: int | None,
) -> dict[str, object]:
    base = table[
        table["dir_norm"].eq(direction)
        & table["mode_family"].eq("post_n")
    ].copy()

    actual = base[base["date_dt"].eq(anchor)]
    aligned_rows = base[base["date_dt"].eq(aligned)]
    if not base.empty:
        base["_time_diff_abs"] = (base["date_dt"] - anchor).abs().dt.total_seconds() / 60.0
        nearby = base[base["_time_diff_abs"] <= NEARBY_MINUTES].sort_values(["_time_diff_abs", "date_dt"]).copy()
        same_mode = nearby[nearby["mode_n"].eq(mt5_mode_n)] if mt5_mode_n is not None else nearby.iloc[0:0].copy()
    else:
        nearby = base
        same_mode = base

    actual_s = summarize_rows(actual, anchor, mt5_mode_n)
    aligned_s = summarize_rows(aligned_rows, aligned, mt5_mode_n)
    nearby_s = summarize_rows(nearby, anchor, mt5_mode_n)
    same_mode_s = summarize_rows(same_mode, anchor, mt5_mode_n)

    return {
        "actual_count": actual_s.count,
        "actual_exact_count": actual_s.exact_count,
        "actual_modes": actual_s.modes,
        "actual_mode_ns": actual_s.mode_ns,
        "actual_first_mode_n": actual_s.first_mode_n,
        "actual_first_mode_n_diff": (
            actual_s.first_mode_n - mt5_mode_n if actual_s.first_mode_n is not None and mt5_mode_n is not None else ""
        ),
        "actual_trigger_families": actual_s.trigger_families,
        "actual_variants": actual_s.variants,
        "actual_profit": actual_s.first_profit,
        "aligned_count": aligned_s.count,
        "aligned_exact_count": aligned_s.exact_count,
        "aligned_modes": aligned_s.modes,
        "aligned_mode_ns": aligned_s.mode_ns,
        "aligned_first_mode_n": aligned_s.first_mode_n,
        "aligned_first_mode_n_diff": (
            aligned_s.first_mode_n - mt5_mode_n if aligned_s.first_mode_n is not None and mt5_mode_n is not None else ""
        ),
        "aligned_trigger_families": aligned_s.trigger_families,
        "aligned_variants": aligned_s.variants,
        "aligned_profit": aligned_s.first_profit,
        "nearby_count": nearby_s.count,
        "nearby_first_time": nearby_s.first_time,
        "nearby_first_time_diff_minutes": nearby_s.first_time_diff,
        "nearby_modes": nearby_s.modes,
        "nearby_mode_ns": nearby_s.mode_ns,
        "same_mode_nearby_count": same_mode_s.count,
        "same_mode_nearby_first_time": same_mode_s.first_time,
        "same_mode_nearby_first_time_diff_minutes": same_mode_s.first_time_diff,
    }


def load_mapping_status() -> pd.DataFrame:
    matches = read_csv(PY_MAPPING).copy()
    unmatched = read_csv(PY_UNMATCHED_MT5).copy()

    match_cols = [
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
    matches = matches[[col for col in match_cols if col in matches.columns]].copy()
    matches["mapping_status"] = "matched"

    unmatched = unmatched[["mt5_trade_id"]].copy()
    unmatched["mapping_status"] = "unmatched"
    return pd.concat([matches, unmatched], ignore_index=True)


def latest_event_for(
    events: pd.DataFrame,
    anchor: pd.Timestamp,
    direction: str,
    mode_n: int | None,
    event_kind: str,
) -> pd.Series | None:
    if events.empty or mode_n is None:
        return None
    rows = events[
        events["event_kind"].eq(event_kind)
        & events["anchor_time"].map(parse_dt).eq(anchor)
        & events["dir_norm"].eq(direction)
        & events["mode_n"].eq(mode_n)
    ].copy()
    if rows.empty:
        return None
    return rows.sort_values("last_line_number").iloc[-1]


def classify_row(row: dict[str, object]) -> str:
    if not row["within_python_m15_coverage"]:
        return "pre_python_m15_coverage"
    if int(row.get("layer12_actual_exact_count") or 0) > 0:
        return "actual_anchor_exact_counter_match"
    if int(row.get("layer12_actual_count") or 0) > 0:
        return "actual_anchor_counter_offset"
    if int(row.get("layer12_aligned_exact_count") or 0) > 0:
        return "aligned_plus90_exact_only"
    if int(row.get("layer12_aligned_count") or 0) > 0:
        return "aligned_plus90_counter_offset"
    if int(row.get("layer12_same_mode_nearby_count") or 0) > 0:
        return "nearby_same_mode_only"
    if int(row.get("layer12_nearby_count") or 0) > 0:
        return "nearby_same_family_counter_offset"
    return "python_no_postn_candidate_nearby"


def build_cohort_alignment(
    cohort: pd.DataFrame,
    events: pd.DataFrame,
    py_tables: dict[str, pd.DataFrame],
    mapping_status: pd.DataFrame,
) -> pd.DataFrame:
    mapping_by_id = mapping_status.drop_duplicates("mt5_trade_id", keep="first").set_index("mt5_trade_id")
    rows: list[dict[str, object]] = []
    for _, mt5 in cohort.iterrows():
        anchor = mt5["signal_anchor_dt"]
        aligned = mt5["aligned_dt"]
        direction = mt5["dir_norm"]
        mt5_mode_n = safe_int(mt5["mt5_mode_n"])
        expected_counter = signed_expected_counter(mt5_mode_n, direction)

        candidate = latest_event_for(events, anchor, direction, mt5_mode_n, "Candidate")
        execute = latest_event_for(events, anchor, direction, mt5_mode_n, "Execute")
        signal = latest_event_for(events, anchor, direction, mt5_mode_n, "SIGNAL")

        row: dict[str, object] = {
            "mt5_trade_id": mt5["mt5_trade_id"],
            "signal_anchor_time": fmt_dt(anchor),
            "aligned_time_plus90": fmt_dt(aligned),
            "within_python_m15_coverage": bool(anchor >= PYTHON_M15_COVERAGE_START),
            "dir_norm": direction,
            "mt5_signal_src": mt5["signal_src"],
            "mt5_mode_n": mt5_mode_n,
            "mt5_expected_signed_counter": expected_counter,
            "mt5_net_profit": safe_float(mt5["net_profit"]),
            "mt5_any_sl": mt5.get("any_sl", ""),
            "mt5_all_sl": mt5.get("all_sl", ""),
            "log_candidate_found": candidate is not None,
            "log_execute_found": execute is not None,
            "log_signal_found": signal is not None,
            "log_candidate_session_hits": int(candidate.get("session_hit_count", 0)) if candidate is not None else 0,
            "log_candidate_event_time": candidate.get("event_time", "") if candidate is not None else "",
            "log_post_n_counter": candidate.get("post_n_counter", "") if candidate is not None else "",
            "log_merged_post_n_counter": candidate.get("merged_post_n_counter", "") if candidate is not None else "",
            "log_post_n_counter_abs": abs(int(candidate["post_n_counter"])) if candidate is not None and pd.notna(candidate.get("post_n_counter")) else "",
            "log_merged_post_n_counter_abs": abs(int(candidate["merged_post_n_counter"])) if candidate is not None and pd.notna(candidate.get("merged_post_n_counter")) else "",
            "log_raw_counter_signed_matches_signal": (
                candidate is not None
                and expected_counter is not None
                and safe_int(candidate.get("post_n_counter")) == expected_counter
            ),
            "log_merged_counter_signed_matches_signal": (
                candidate is not None
                and expected_counter is not None
                and safe_int(candidate.get("merged_post_n_counter")) == expected_counter
            ),
            "log_raw_vs_merged_signed_equal": (
                candidate is not None
                and safe_int(candidate.get("post_n_counter")) == safe_int(candidate.get("merged_post_n_counter"))
            ),
            "log_m15_close": candidate.get("m15_close", "") if candidate is not None else "",
            "log_m15_smma13": candidate.get("m15_smma13", "") if candidate is not None else "",
            "log_execute_real_entry": execute.get("real_entry", "") if execute is not None else "",
            "log_execute_stop_price": execute.get("stop_price", "") if execute is not None else "",
            "log_execute_stop_pts": execute.get("stop_pts", "") if execute is not None else "",
        }

        for table_key in ["raw", "layer12", "layer3", "stage", "dynamic"]:
            summary = match_python_table(py_tables[table_key], anchor, aligned, direction, mt5_mode_n)
            for key, value in summary.items():
                row[f"{table_key}_{key}"] = value

        if mt5["mt5_trade_id"] in mapping_by_id.index:
            mapped = mapping_by_id.loc[mt5["mt5_trade_id"]]
            for col in mapping_by_id.columns:
                row[f"mapping_{col}"] = mapped[col]
        else:
            row["mapping_mapping_status"] = "unknown"

        row["cohort_classification"] = classify_row(row)
        rows.append(row)

    return pd.DataFrame(rows)


def build_summary(cohort_alignment: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    class_summary = (
        cohort_alignment.groupby("cohort_classification", dropna=False)
        .agg(
            count=("mt5_trade_id", "count"),
            mt5_net_profit_sum=("mt5_net_profit", "sum"),
            matched_count=("mapping_mapping_status", lambda s: int((s == "matched").sum())),
            reliable_count=("mapping_is_reliable_tier", lambda s: int(s.astype(str).str.lower().eq("true").sum())),
        )
        .reset_index()
        .sort_values(["count", "mt5_net_profit_sum"], ascending=[False, False])
    )

    counter_summary = (
        cohort_alignment.groupby(
            [
                "within_python_m15_coverage",
                "mt5_mode_n",
                "log_post_n_counter_abs",
                "log_merged_post_n_counter_abs",
                "layer12_actual_first_mode_n_diff",
            ],
            dropna=False,
        )
        .agg(count=("mt5_trade_id", "count"), mt5_net_profit_sum=("mt5_net_profit", "sum"))
        .reset_index()
        .sort_values(["within_python_m15_coverage", "count"], ascending=[False, False])
    )

    mapping_summary = (
        cohort_alignment.groupby(["mapping_mapping_status", "mapping_match_tier"], dropna=False)
        .agg(
            count=("mt5_trade_id", "count"),
            reliable_count=("mapping_is_reliable_tier", lambda s: int(s.astype(str).str.lower().eq("true").sum())),
            mt5_net_profit_sum=("mt5_net_profit", "sum"),
            profit_diff_sum=("mapping_profit_diff", lambda s: float(pd.to_numeric(s, errors="coerce").sum())),
        )
        .reset_index()
        .sort_values(["mapping_mapping_status", "count"], ascending=[True, False])
    )

    total = len(cohort_alignment)
    comparable = int(cohort_alignment["within_python_m15_coverage"].sum())
    actual_offset = int((cohort_alignment["cohort_classification"] == "actual_anchor_counter_offset").sum())
    actual_exact = int((cohort_alignment["cohort_classification"] == "actual_anchor_exact_counter_match").sum())
    pre_coverage = int((cohort_alignment["cohort_classification"] == "pre_python_m15_coverage").sum())
    matched = int((cohort_alignment["mapping_mapping_status"] == "matched").sum())
    reliable = int(cohort_alignment["mapping_is_reliable_tier"].astype(str).str.lower().eq("true").sum())
    log_covered = int(cohort_alignment["log_candidate_found"].sum())
    raw_merged_counter_equal = int(cohort_alignment["log_raw_vs_merged_signed_equal"].sum())

    low_blast_prototype_gate = bool(
        comparable >= 8
        and log_covered == total
        and actual_offset >= 2
        and len(class_summary[class_summary["cohort_classification"].ne("pre_python_m15_coverage")]) > 1
    )

    final = pd.DataFrame(
        [
            {
                "cohort_total": total,
                "comparable_after_python_m15_start": comparable,
                "pre_python_m15_coverage": pre_coverage,
                "log_candidate_covered": log_covered,
                "log_raw_vs_merged_counter_equal": raw_merged_counter_equal,
                "actual_anchor_exact_counter_match": actual_exact,
                "actual_anchor_counter_offset": actual_offset,
                "mapped_count": matched,
                "reliable_mapped_count": reliable,
                "low_blast_prototype_gate_open": low_blast_prototype_gate,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "recommended_next_action": "design_diagnostic_only_m15_slot1_counter_source_variants_if_needed_no_main_merge",
            }
        ]
    )
    return class_summary, counter_summary, mapping_summary, final


def simple_table(frame: pd.DataFrame, max_rows: int = 30) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def build_report(
    class_summary: pd.DataFrame,
    counter_summary: pd.DataFrame,
    mapping_summary: pd.DataFrame,
    final: pd.DataFrame,
    cohort_alignment: pd.DataFrame,
) -> list[str]:
    f = final.iloc[0].to_dict()
    lines = [
        "# Stage-State M15 SLOT1 post_n Legacy Counter Drift Cohort Audit",
        "",
        "## Final Decision",
        "",
        f"- Cohort total: `{f['cohort_total']}`.",
        f"- Comparable after Python M15 start: `{f['comparable_after_python_m15_start']}`.",
        f"- Pre Python M15 coverage: `{f['pre_python_m15_coverage']}`.",
        f"- Log candidate covered: `{f['log_candidate_covered']}`.",
        f"- Actual-anchor exact counter match: `{f['actual_anchor_exact_counter_match']}`.",
        f"- Actual-anchor counter offset: `{f['actual_anchor_counter_offset']}`.",
        f"- Mapped count: `{f['mapped_count']}`.",
        f"- Reliable mapped count: `{f['reliable_mapped_count']}`.",
        f"- Low-blast prototype gate: `{f['low_blast_prototype_gate_open']}`.",
        f"- Main signal gate: `{f['main_signal_change_gate_open']}`.",
        f"- EA behavior gate: `{f['ea_behavior_gate_open']}`.",
        f"- Mapping gate: `{f['mapping_change_gate_open']}`.",
        f"- Merge gate: `{f['merge_gate_pass']}`.",
        "",
        "## Classification Summary",
        "",
        simple_table(class_summary),
        "",
        "## Counter Diff Summary",
        "",
        simple_table(counter_summary, max_rows=40),
        "",
        "## Mapping Summary",
        "",
        simple_table(mapping_summary),
        "",
        "## Cohort Rows",
        "",
        simple_table(
            cohort_alignment[
                [
                    "mt5_trade_id",
                    "signal_anchor_time",
                    "dir_norm",
                    "mt5_signal_src",
                    "mt5_net_profit",
                    "cohort_classification",
                    "log_post_n_counter",
                    "log_merged_post_n_counter",
                    "layer12_actual_modes",
                    "layer12_actual_first_mode_n_diff",
                    "layer12_aligned_modes",
                    "layer12_same_mode_nearby_first_time",
                    "mapping_mapping_status",
                    "mapping_match_tier",
                    "mapping_profit_diff",
                ]
            ],
            max_rows=80,
        ),
        "",
        "## Interpretation",
        "",
        "- The cohort is not a single clean correction target: early rows are outside Python M15 comparable coverage, while comparable rows split across actual-anchor offsets, nearby-only cases, and no-nearby cases.",
        "- The EA log counter evidence is complete enough for cohort accounting, but it does not by itself justify a main-logic counter change.",
        "- Any next prototype should stay diagnostic-only until a variant proves signal-set and profit gaps do not deteriorate.",
    ]
    return lines


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_events, events = parse_m15_slot1_postn_log_events()
    cohort = load_mt5_postn_cohort()
    py_tables = load_python_tables()
    mapping_status = load_mapping_status()
    cohort_alignment = build_cohort_alignment(cohort, events, py_tables, mapping_status)
    class_summary, counter_summary, mapping_summary, final = build_summary(cohort_alignment)

    write_csv(raw_events, OUT_DIR / "ea_m15_slot1_postn_log_events_raw.csv")
    write_csv(events, OUT_DIR / "ea_m15_slot1_postn_log_events_dedup.csv")
    write_csv(cohort_alignment, OUT_DIR / "m15_slot1_postn_cohort_alignment.csv")
    write_csv(class_summary, OUT_DIR / "m15_slot1_postn_classification_summary.csv")
    write_csv(counter_summary, OUT_DIR / "m15_slot1_postn_counter_diff_summary.csv")
    write_csv(mapping_summary, OUT_DIR / "m15_slot1_postn_mapping_summary.csv")
    write_csv(final, OUT_DIR / "m15_slot1_postn_final_decision.csv")
    write_md(build_report(class_summary, counter_summary, mapping_summary, final, cohort_alignment), OUT_DIR / "m15_slot1_postn_legacy_counter_drift_cohort_audit.md")
    write_md(
        [
            "# M15 SLOT1 post_n Legacy Counter Drift Cohort Audit",
            "",
            f"- Cohort total: `{int(final.loc[0, 'cohort_total'])}`.",
            f"- Low-blast prototype gate: `{bool(final.loc[0, 'low_blast_prototype_gate_open'])}`.",
            f"- Merge gate: `{bool(final.loc[0, 'merge_gate_pass'])}`.",
        ],
        OUT_DIR / "README.md",
    )
    print(f"Wrote {OUT_DIR}")
    print(final.to_string(index=False))


if __name__ == "__main__":
    main()
