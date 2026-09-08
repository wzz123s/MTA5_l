# -*- coding: utf-8 -*-
"""Audit M15 SLOT1 near-trigger family drift cases.

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

NO_CANDIDATE_DIR = VALIDATION_DIR / "stage_state_m15_slot1_no_candidate_source_gap_audit_20260717"
COUNTER_COHORT_DIR = VALIDATION_DIR / "stage_state_m15_slot1_legacy_counter_drift_cohort_20260717"
OUT_DIR = VALIDATION_DIR / "stage_state_m15_slot1_near_trigger_family_drift_audit_20260717"

DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716"
SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"

CASE_REVIEW = NO_CANDIDATE_DIR / "m15_slot1_no_candidate_case_review.csv"
EA_POSTN_EVENTS = COUNTER_COHORT_DIR / "ea_m15_slot1_postn_log_events_dedup.csv"
PY_DYNAMIC = DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"

TARGET_IDS = ["mt5_0052", "mt5_0054", "mt5_0067", "mt5_0068", "mt5_0069"]
NEAR_WINDOW_MINUTES = 120
DAY_WINDOW_MINUTES = 24 * 60
WEEK_WINDOW_MINUTES = 7 * 24 * 60


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
    frame["layer"] = layer_name
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
    dynamic["layer"] = "dynamic"

    return {
        "raw": load_signal_table(SIGNAL_DIR / "raw_candidates.csv", "raw"),
        "layer12": load_signal_table(find_signal_file("Layer1"), "layer12"),
        "layer3": load_signal_table(find_signal_file("Layer3"), "layer3"),
        "stage": load_signal_table(find_signal_file("Stage"), "stage"),
        "dynamic": dynamic,
    }


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


def nearest_row(rows: pd.DataFrame, direction: str, mt5_mode_n: int | None, family_filter: str) -> pd.Series | None:
    if rows.empty:
        return None
    subset = rows[rows["dir_norm"].eq(direction)].copy()
    if family_filter == "nonpostn":
        subset = subset[~subset["mode_family"].eq("post_n")]
    elif family_filter == "postn":
        subset = subset[subset["mode_family"].eq("post_n")]
    elif family_filter == "same_mode_postn":
        subset = subset[subset["mode_family"].eq("post_n")]
        subset = subset[subset["mode_n"].eq(mt5_mode_n)] if mt5_mode_n is not None else subset.iloc[0:0]
    if subset.empty:
        return None
    return subset.sort_values(["abs_time_diff_minutes", "date_dt"]).iloc[0]


def row_summary(row: pd.Series | None) -> dict[str, object]:
    if row is None:
        return {
            "time": "",
            "diff_minutes": "",
            "mode": "",
            "mode_family": "",
            "mode_n": "",
            "variant": "",
            "trigger_family": "",
            "profit_value": "",
        }
    pcol = profit_col(row.to_frame().T)
    return {
        "time": fmt_dt(row.get("date_dt")),
        "diff_minutes": round(safe_float(row.get("time_diff_minutes")), 6),
        "mode": row.get("mode", ""),
        "mode_family": row.get("mode_family", ""),
        "mode_n": row.get("mode_n", ""),
        "variant": row.get("variant", ""),
        "trigger_family": row.get("trigger_family", ""),
        "profit_value": row.get(pcol, "") if pcol else "",
    }


def count_same_dir(rows: pd.DataFrame, direction: str, mt5_mode_n: int | None) -> dict[str, int]:
    same_dir = rows[rows["dir_norm"].eq(direction)] if not rows.empty else rows
    postn = same_dir[same_dir["mode_family"].eq("post_n")] if not same_dir.empty else same_dir
    nonpostn = same_dir[~same_dir["mode_family"].eq("post_n")] if not same_dir.empty else same_dir
    same_mode = postn[postn["mode_n"].eq(mt5_mode_n)] if mt5_mode_n is not None and not postn.empty else postn.iloc[0:0]
    return {
        "same_dir_any_count": int(len(same_dir)),
        "same_dir_nonpostn_count": int(len(nonpostn)),
        "same_dir_postn_count": int(len(postn)),
        "same_dir_same_mode_postn_count": int(len(same_mode)),
    }


def load_ea_events() -> pd.DataFrame:
    events = read_csv(EA_POSTN_EVENTS).copy()
    events["event_dt"] = events["event_time"].map(parse_dt)
    events["anchor_dt"] = events["anchor_time"].map(parse_dt)
    events["dir_norm"] = events["dir_norm"].map(normalize_dir)
    events["mode_family"] = events["mode"].map(mode_family)
    events["mode_n"] = events["mode"].map(mode_number)
    return events


def build_timeline(targets: pd.DataFrame, tables: dict[str, pd.DataFrame], ea_events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, target in targets.iterrows():
        mt5_id = target["mt5_trade_id"]
        anchor = parse_dt(target["signal_anchor_time"])
        direction = normalize_dir(target["dir_norm"])
        mt5_mode_n = safe_int(target["mt5_mode_n"])
        start = anchor - pd.Timedelta(minutes=NEAR_WINDOW_MINUTES)
        end = anchor + pd.Timedelta(minutes=NEAR_WINDOW_MINUTES)

        ea = ea_events[
            ea_events["anchor_dt"].between(start, end)
            & ea_events["dir_norm"].eq(direction)
        ].copy()
        for _, event in ea.iterrows():
            rows.append(
                {
                    "mt5_trade_id": mt5_id,
                    "source": "ea_log",
                    "layer": "ea_m15_slot1_postn",
                    "event_time": fmt_dt(event.get("event_dt")),
                    "signal_time": fmt_dt(event.get("anchor_dt")),
                    "time_diff_minutes": round(time_diff_minutes(event.get("anchor_dt"), anchor), 6),
                    "dir_norm": event.get("dir_norm", ""),
                    "mode": event.get("mode", ""),
                    "mode_family": event.get("mode_family", ""),
                    "mode_n": event.get("mode_n", ""),
                    "variant": "",
                    "trigger_family": "M15 SLOT1",
                    "event_kind": event.get("event_kind", ""),
                    "same_dir": True,
                    "same_mode": bool(event.get("mode_n", "") == mt5_mode_n),
                    "profit_value": "",
                    "is_target_ea_signal": bool(event.get("anchor_dt") == anchor and event.get("mode_n", "") == mt5_mode_n),
                }
            )

        for layer, table in tables.items():
            py = window_rows(table, anchor, NEAR_WINDOW_MINUTES)
            pcol = profit_col(py)
            for _, row in py.iterrows():
                rows.append(
                    {
                        "mt5_trade_id": mt5_id,
                        "source": "python",
                        "layer": layer,
                        "event_time": "",
                        "signal_time": fmt_dt(row.get("date_dt")),
                        "time_diff_minutes": round(safe_float(row.get("time_diff_minutes")), 6),
                        "dir_norm": row.get("dir_norm", ""),
                        "mode": row.get("mode", ""),
                        "mode_family": row.get("mode_family", ""),
                        "mode_n": row.get("mode_n", ""),
                        "variant": row.get("variant", ""),
                        "trigger_family": row.get("trigger_family", ""),
                        "event_kind": "",
                        "same_dir": bool(row.get("dir_norm", "") == direction),
                        "same_mode": bool(row.get("mode_n", "") == mt5_mode_n) if mt5_mode_n is not None else False,
                        "profit_value": row.get(pcol, "") if pcol else "",
                        "is_target_ea_signal": False,
                    }
                )
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["mt5_trade_id", "signal_time", "source", "layer", "event_kind"]).reset_index(drop=True)
    return out


def build_case_verdict(targets: pd.DataFrame, tables: dict[str, pd.DataFrame], ea_events: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, target in targets.iterrows():
        mt5_id = str(target["mt5_trade_id"])
        anchor = parse_dt(target["signal_anchor_time"])
        direction = normalize_dir(target["dir_norm"])
        mt5_mode_n = safe_int(target["mt5_mode_n"])

        row: dict[str, object] = {
            "mt5_trade_id": mt5_id,
            "signal_anchor_time": fmt_dt(anchor),
            "aligned_time_plus90": target.get("aligned_time_plus90", ""),
            "dir_norm": direction,
            "mt5_signal_src": target.get("mt5_signal_src", ""),
            "mt5_mode_n": mt5_mode_n,
            "mt5_net_profit": safe_float(target.get("mt5_net_profit")),
            "previous_primary_classification": target.get("primary_classification", ""),
            "mapping_status": target.get("mapping_status", ""),
            "mapping_match_tier": target.get("mapping_match_tier", ""),
            "mapping_is_reliable_tier": target.get("mapping_is_reliable_tier", ""),
            "mapping_py_date": target.get("mapping_py_date", ""),
            "mapping_py_mode": target.get("mapping_py_mode", ""),
        }

        exact_ea = ea_events[
            ea_events["anchor_dt"].eq(anchor)
            & ea_events["dir_norm"].eq(direction)
            & ea_events["mode_n"].eq(mt5_mode_n)
        ].copy()
        row["ea_exact_event_count"] = int(len(exact_ea))
        row["ea_exact_event_kinds"] = semijoin(exact_ea.get("event_kind", pd.Series(dtype=str)).tolist())
        row["ea_exact_post_n_counter"] = semijoin(exact_ea.get("post_n_counter", pd.Series(dtype=str)).tolist())
        row["ea_exact_merged_post_n_counter"] = semijoin(exact_ea.get("merged_post_n_counter", pd.Series(dtype=str)).tolist())

        for layer, table in tables.items():
            near = window_rows(table, anchor, NEAR_WINDOW_MINUTES)
            day = window_rows(table, anchor, DAY_WINDOW_MINUTES)
            week = window_rows(table, anchor, WEEK_WINDOW_MINUTES)
            near_counts = count_same_dir(near, direction, mt5_mode_n)
            day_counts = count_same_dir(day, direction, mt5_mode_n)
            week_counts = count_same_dir(week, direction, mt5_mode_n)
            nearest_nonpostn = row_summary(nearest_row(near, direction, mt5_mode_n, "nonpostn"))
            nearest_postn_day = row_summary(nearest_row(day, direction, mt5_mode_n, "postn"))
            nearest_same_mode_week = row_summary(nearest_row(week, direction, mt5_mode_n, "same_mode_postn"))

            prefix = f"{layer}_"
            for key, value in near_counts.items():
                row[f"{prefix}near_{key}"] = value
            for key, value in day_counts.items():
                row[f"{prefix}day_{key}"] = value
            for key, value in week_counts.items():
                row[f"{prefix}week_{key}"] = value
            for key, value in nearest_nonpostn.items():
                row[f"{prefix}nearest_near_nonpostn_{key}"] = value
            for key, value in nearest_postn_day.items():
                row[f"{prefix}nearest_day_postn_{key}"] = value
            for key, value in nearest_same_mode_week.items():
                row[f"{prefix}nearest_week_same_mode_postn_{key}"] = value

        layer12_near_nonpostn = int(row.get("layer12_near_same_dir_nonpostn_count", 0))
        layer12_near_postn = int(row.get("layer12_near_same_dir_postn_count", 0))
        raw_near_nonpostn = int(row.get("raw_near_same_dir_nonpostn_count", 0))
        raw_near_postn = int(row.get("raw_near_same_dir_postn_count", 0))
        layer12_day_postn = int(row.get("layer12_day_same_dir_postn_count", 0))
        raw_day_postn = int(row.get("raw_day_same_dir_postn_count", 0))
        mapping_tier = str(row.get("mapping_match_tier", ""))
        mapping_diff = abs(time_diff_minutes(row.get("mapping_py_date", ""), anchor))

        secondary: list[str] = []
        if "nearby_7d" in mapping_tier or (pd.notna(mapping_diff) and mapping_diff > DAY_WINDOW_MINUTES):
            secondary.append("mapping_far_window_artifact")

        if layer12_near_nonpostn > 0 and layer12_near_postn == 0:
            primary = "trigger_family_label_gap"
            reason = "EA exact post_n exists, while Python Layer1/2 near window has same-direction cross/pre_cross but no post_n"
        elif raw_near_nonpostn > 0 and raw_near_postn == 0:
            primary = "raw_sequence_gap"
            reason = "EA exact post_n exists, while Python raw near window has same-direction non-post_n but no post_n"
        elif raw_day_postn > 0 and layer12_day_postn == 0:
            primary = "slot1_anchor_gap"
            reason = "Python raw has same-direction post_n within 24h, but Layer1/2 does not retain a same-direction post_n"
        elif "nearby_7d" in mapping_tier:
            primary = "mapping_far_window_artifact"
            reason = "nearest mapped Python trade comes from a far relaxed mapping window"
        else:
            primary = "insufficient_evidence"
            reason = "near-trigger evidence does not isolate a repeatable source"

        row["primary_classification"] = primary
        if primary not in secondary:
            secondary.append(primary)
        row["secondary_classifications"] = ";".join(dict.fromkeys(secondary))
        row["classification_reason"] = reason
        row["mapping_time_diff_minutes"] = round(mapping_diff, 6) if pd.notna(mapping_diff) else ""
        rows.append(row)

    return pd.DataFrame(rows)


def build_summaries(case_verdict: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    class_summary = (
        case_verdict.groupby("primary_classification", dropna=False)
        .agg(
            count=("mt5_trade_id", "count"),
            mt5_net_profit_sum=("mt5_net_profit", "sum"),
            reliable_mapped_count=("mapping_is_reliable_tier", lambda s: int(s.map(boolish).sum())),
            mt5_ids=("mt5_trade_id", lambda s: ";".join(s)),
        )
        .reset_index()
        .sort_values(["count", "mt5_net_profit_sum"], ascending=[False, False])
    )
    target_count = int(len(case_verdict))
    trigger_family_label_gap_count = int((case_verdict["primary_classification"] == "trigger_family_label_gap").sum())
    raw_sequence_gap_count = int((case_verdict["primary_classification"] == "raw_sequence_gap").sum())
    slot1_anchor_gap_count = int((case_verdict["primary_classification"] == "slot1_anchor_gap").sum())
    mapping_far_window_artifact_count = int(case_verdict["secondary_classifications"].astype(str).str.contains("mapping_far_window_artifact").sum())
    reliable = int(case_verdict["mapping_is_reliable_tier"].map(boolish).sum())
    diagnostic_gate = False
    final = pd.DataFrame(
        [
            {
                "target_count": target_count,
                "mt5_net_profit_sum": case_verdict["mt5_net_profit"].sum(),
                "primary_class_count": int(case_verdict["primary_classification"].nunique()),
                "trigger_family_label_gap_count": trigger_family_label_gap_count,
                "raw_sequence_gap_count": raw_sequence_gap_count,
                "slot1_anchor_gap_count": slot1_anchor_gap_count,
                "mapping_far_window_artifact_secondary_count": mapping_far_window_artifact_count,
                "reliable_mapped_count": reliable,
                "diagnostic_trigger_family_prototype_gate_open": diagnostic_gate,
                "main_signal_change_gate_open": False,
                "ea_behavior_gate_open": False,
                "mapping_change_gate_open": False,
                "merge_gate_pass": False,
                "recommended_next_action": "inspect_ea_vs_python_slot1_trigger_family_generation_no_main_merge",
            }
        ]
    )
    return class_summary, final


def simple_table(frame: pd.DataFrame, max_rows: int = 40) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def build_report(case_verdict: pd.DataFrame, class_summary: pd.DataFrame, final: pd.DataFrame) -> list[str]:
    f = final.iloc[0].to_dict()
    show_cols = [
        "mt5_trade_id",
        "signal_anchor_time",
        "dir_norm",
        "mt5_signal_src",
        "mt5_net_profit",
        "mapping_match_tier",
        "primary_classification",
        "secondary_classifications",
        "classification_reason",
        "layer12_near_same_dir_nonpostn_count",
        "layer12_near_same_dir_postn_count",
        "layer12_nearest_near_nonpostn_time",
        "layer12_nearest_near_nonpostn_mode",
        "raw_nearest_day_postn_time",
        "raw_nearest_day_postn_diff_minutes",
        "mapping_time_diff_minutes",
    ]
    show_cols = [col for col in show_cols if col in case_verdict.columns]
    return [
        "# Stage-State M15 SLOT1 Near-Trigger Family Drift Audit",
        "",
        "## Final Decision",
        "",
        f"- Target count: `{f['target_count']}`.",
        f"- MT5 net profit sum: `{f['mt5_net_profit_sum']}`.",
        f"- Trigger-family label gap count: `{f['trigger_family_label_gap_count']}`.",
        f"- Raw sequence gap count: `{f['raw_sequence_gap_count']}`.",
        f"- Slot1 anchor gap count: `{f['slot1_anchor_gap_count']}`.",
        f"- Mapping far-window artifact secondary count: `{f['mapping_far_window_artifact_secondary_count']}`.",
        f"- Diagnostic trigger-family prototype gate: `{f['diagnostic_trigger_family_prototype_gate_open']}`.",
        f"- Main signal gate: `{f['main_signal_change_gate_open']}`.",
        f"- EA behavior gate: `{f['ea_behavior_gate_open']}`.",
        f"- Mapping gate: `{f['mapping_change_gate_open']}`.",
        f"- Merge gate: `{f['merge_gate_pass']}`.",
        "",
        "## Classification Summary",
        "",
        simple_table(class_summary),
        "",
        "## Case Verdict",
        "",
        simple_table(case_verdict[show_cols], max_rows=20),
        "",
        "## Interpretation",
        "",
        "- This audit confirms whether the previous no-candidate bucket is a local trigger-family mismatch or a far mapping artifact.",
        "- The result remains diagnostic-only until a repeated trigger-family generation rule can be proven across the affected cohort.",
        "- No main signal, EA behavior, mapping, dynamic-risk, or merge gate is opened here.",
    ]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    targets = read_csv(CASE_REVIEW)
    targets = targets[targets["mt5_trade_id"].isin(TARGET_IDS)].copy()
    tables = load_python_tables()
    ea_events = load_ea_events()

    timeline = build_timeline(targets, tables, ea_events)
    case_verdict = build_case_verdict(targets, tables, ea_events)
    class_summary, final = build_summaries(case_verdict)

    write_csv(timeline, OUT_DIR / "m15_slot1_near_trigger_timeline_pm120.csv")
    write_csv(case_verdict, OUT_DIR / "m15_slot1_near_trigger_case_verdict.csv")
    write_csv(class_summary, OUT_DIR / "m15_slot1_near_trigger_classification_summary.csv")
    write_csv(final, OUT_DIR / "m15_slot1_near_trigger_final_decision.csv")
    write_md(build_report(case_verdict, class_summary, final), OUT_DIR / "m15_slot1_near_trigger_family_drift_audit.md")
    write_md(
        [
            "# M15 SLOT1 Near-Trigger Family Drift Audit",
            "",
            f"- Target count: `{int(final.loc[0, 'target_count'])}`.",
            f"- Trigger-family label gap count: `{int(final.loc[0, 'trigger_family_label_gap_count'])}`.",
            f"- Merge gate: `{bool(final.loc[0, 'merge_gate_pass'])}`.",
        ],
        OUT_DIR / "README.md",
    )
    print(f"Wrote {OUT_DIR}")
    print(final.to_string(index=False))


if __name__ == "__main__":
    main()
