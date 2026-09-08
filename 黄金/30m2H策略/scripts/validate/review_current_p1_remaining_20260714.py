# -*- coding: utf-8 -*-
"""Review the current remaining P1 items after the BUY mapping fix."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

RUNTIME_DIR = VALIDATION_DIR / "python_runtime_stage_exit_prototype_20260714"
EQ_DIR = VALIDATION_DIR / "trigger_family_equivalence_shift90_close_retry_20260714"
REMAINING_DIR = VALIDATION_DIR / "runtime_style_remaining_diff_review_20260714"
CAUSE_DIR = VALIDATION_DIR / "unmatched_signal_cause_shift90_close_retry_20260714"
LEDGER_DIR = VALIDATION_DIR / "ea_stage2_trail_ledger_full_20260714"
SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_20260712" / "python_h2_context_q2early"
PROCESSED_DIR = DATA_DIR / "processed"
OUT_DIR = VALIDATION_DIR / "current_p1_remaining_review_20260714"

BLOCKER_PY_ID = "python_mt5_0061"
BLOCKER_MT5_ID = "mt5_0045"
LAYER3_MT5_ID = "mt5_0068"


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def as_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def safe_float(value: object) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return 0.0
    return float(parsed)


def parse_time(value: object) -> pd.Timestamp:
    return pd.to_datetime(value, errors="coerce")


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL", "-1"}:
        return "SELL"
    if text in {"B", "BUY", "L", "LONG", "1"}:
        return "BUY"
    return text


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.loc[:, [c for c in columns if c in frame.columns]].copy()
    columns = list(display.columns)
    rows = [[as_text(value) for value in row] for row in display.to_numpy()]
    widths = [len(col) for col in columns]
    for row in rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))

    def render(row: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(row)) + " |"

    header = render(columns)
    sep = "| " + " | ".join("-" * width for width in widths) + " |"
    return "\n".join([header, sep, *[render(row) for row in rows]])


def prepare_bars(path: Path) -> pd.DataFrame:
    df = read_csv(path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["open", "high", "low", "close", "SMA_5", "SMA_13"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def first_close_below_ma(bars: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, object]:
    window = bars[(bars["date"] >= start) & (bars["date"] <= end)].copy()
    if window.empty:
        return {"first_close_below_sma5_time": "", "first_close_below_sma13_time": ""}
    below5 = window[window["close"] < window["SMA_5"]]
    below13 = window[window["close"] < window["SMA_13"]]
    return {
        "first_close_below_sma5_time": below5["date"].iloc[0] if not below5.empty else "",
        "first_close_below_sma5_close": round(float(below5["close"].iloc[0]), 6) if not below5.empty else "",
        "first_close_below_sma5_ma": round(float(below5["SMA_5"].iloc[0]), 6) if not below5.empty else "",
        "first_close_below_sma13_time": below13["date"].iloc[0] if not below13.empty else "",
        "first_close_below_sma13_close": round(float(below13["close"].iloc[0]), 6) if not below13.empty else "",
        "first_close_below_sma13_ma": round(float(below13["SMA_13"].iloc[0]), 6) if not below13.empty else "",
    }


def build_stage_blocker_review() -> pd.DataFrame:
    integrated = read_csv(RUNTIME_DIR / "runtime_stage_exit_integrated_alignment.csv")
    blockers = read_csv(RUNTIME_DIR / "runtime_stage_exit_remaining_blockers.csv")
    replay = read_csv(RUNTIME_DIR / "runtime_stage_priority1_replay.csv")
    selected = read_csv(EQ_DIR / "bidirectional_m30_m15_90_profit20_selected_matches.csv")
    ledger = read_csv(LEDGER_DIR / "30m2H_strategy_trade_ledger.csv")
    m30 = prepare_bars(PROCESSED_DIR / "m30_mt5.csv")
    m15 = prepare_bars(PROCESSED_DIR / "m15_context_bars.csv")

    row = integrated[(integrated["py_trade_id"] == BLOCKER_PY_ID) & (pd.to_numeric(integrated["stage"], errors="coerce") == 3)].iloc[0]
    blocker = blockers[(blockers["py_trade_id"] == BLOCKER_PY_ID) & (blockers["mt5_trade_id"] == BLOCKER_MT5_ID)].iloc[0]
    replay_row = replay[(replay["py_trade_id"] == BLOCKER_PY_ID) & (pd.to_numeric(replay["stage"], errors="coerce") == 3)].iloc[0]
    match = selected[(selected["py_trade_id"] == BLOCKER_PY_ID) & (selected["mt5_trade_id"] == BLOCKER_MT5_ID)].iloc[0]
    ledger_rows = ledger[ledger["position_id"].astype(str).isin(["265", "266", "267"])].copy()

    cross_time = parse_time(replay_row.get("first_m30_event_time"))
    sl_time = parse_time(row.get("exit_time"))
    open_time = parse_time(row.get("open_time"))
    minutes_cross_before_sl = ""
    if pd.notna(cross_time) and pd.notna(sl_time):
        minutes_cross_before_sl = round((sl_time - cross_time).total_seconds() / 60.0, 6)

    ma_probe = first_close_below_ma(m15, open_time, sl_time)

    trigger_relaxed = as_text(match.get("py_trigger_family")) != as_text(match.get("mt5_trigger_family"))
    if trigger_relaxed:
        conclusion = "mapping_policy_risk_plus_unresolved_stage3_cross"
        action = "First verify whether this relaxed M15-vs-M30 match should drive runtime adjustment; if yes, add EA Stage3 cross diagnostics/tick evidence around the first M30 cross before changing EA behavior."
    else:
        conclusion = "unresolved_stage3_cross_before_sl"
        action = "Add EA Stage3 cross diagnostics or tick/journal evidence around the first M30 cross before broker SL."

    out = pd.DataFrame(
        [
            {
                "case_id": row.get("case_id"),
                "py_trade_id": BLOCKER_PY_ID,
                "mt5_trade_id": BLOCKER_MT5_ID,
                "stage": 3,
                "dir_norm": row.get("dir_norm"),
                "match_tier": match.get("effective_match_tier", match.get("match_tier")),
                "trigger_pair": f"{match.get('py_trigger_family')} -> {match.get('mt5_trigger_family')}",
                "mode_pair": f"{match.get('py_mode_family')} -> {match.get('mt5_mode_family')}",
                "py_date": match.get("py_date"),
                "mt5_aligned_time": match.get("mt5_aligned_time"),
                "open_time": row.get("open_time"),
                "first_m30_cross_time": replay_row.get("first_m30_event_time"),
                "mt5_sl_time": row.get("exit_time"),
                "minutes_cross_before_sl": minutes_cross_before_sl,
                "py_stage_profit": row.get("py_stage_profit"),
                "mt5_stage_profit": row.get("mt5_stage_profit"),
                "journal_class": blocker.get("journal_class"),
                "journal_lines_found": blocker.get("journal_lines_found"),
                "first_stop_loss_time": blocker.get("first_stop_loss_time"),
                "ledger_stage1_exit": ledger_rows.loc[ledger_rows["stage"].astype(str) == "1", "exit_time"].iloc[0],
                "ledger_stage2_exit": ledger_rows.loc[ledger_rows["stage"].astype(str) == "2", "exit_time"].iloc[0],
                "ledger_stage3_exit": ledger_rows.loc[ledger_rows["stage"].astype(str) == "3", "exit_time"].iloc[0],
                **ma_probe,
                "review_conclusion": conclusion,
                "next_action": action,
            }
        ]
    )
    return out


def nearest_summary(frame: pd.DataFrame, target: pd.Timestamp, direction: str, trigger_family: str, mode_family: str, layer_name: str) -> dict[str, object]:
    if frame.empty:
        return {f"{layer_name}_rows_within_180m": 0}
    df = frame.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["dir_norm"] = df["dir"].map(normalize_dir)
    if "trigger_family" not in df.columns:
        df["trigger_family"] = df["variant"].astype(str).map(lambda v: "M15 SLOT1" if any(tag in v for tag in ["slot1", "replace", "rescue"]) else "M30 CLOSE")
    if "mode_family" not in df.columns:
        df["mode_family"] = df["mode"].astype(str).map(lambda v: "post_n" if "post_n" in v else ("pre_cross" if "pre_cross" in v else ("cross" if "cross" in v else v)))
    same_dir = df[df["dir_norm"] == direction].copy()
    same_dir["minutes_from_target"] = (same_dir["date"] - target).dt.total_seconds() / 60.0
    same_dir["abs_minutes"] = same_dir["minutes_from_target"].abs()
    within = same_dir[same_dir["abs_minutes"] <= 180].copy()
    same_tm = same_dir[(same_dir["trigger_family"] == trigger_family) & (same_dir["mode_family"] == mode_family)].copy()
    nearest = same_tm.sort_values("abs_minutes").head(1)
    result = {
        f"{layer_name}_rows_within_180m": int(len(within)),
        f"{layer_name}_same_trigger_mode_within_180m": int(((within["trigger_family"] == trigger_family) & (within["mode_family"] == mode_family)).sum()) if not within.empty else 0,
        f"{layer_name}_nearest_same_trigger_mode_time": nearest["date"].iloc[0] if not nearest.empty else "",
        f"{layer_name}_nearest_same_trigger_mode_abs_minutes": round(float(nearest["abs_minutes"].iloc[0]), 6) if not nearest.empty else "",
    }
    return result


def build_layer3_reject_review() -> tuple[pd.DataFrame, pd.DataFrame]:
    signal_cases = read_csv(REMAINING_DIR / "remaining_signal_set_drift_cases.csv")
    cause = read_csv(CAUSE_DIR / "python_mt5_mt5_unmatched_cause.csv")
    raw = read_csv(SIGNAL_DIR / "raw_candidates.csv")
    accepted = read_csv(SIGNAL_DIR / "候选信号_Layer1_Layer2通过.csv")
    picked = read_csv(SIGNAL_DIR / "最终信号_Layer3入选.csv")
    executed = read_csv(VALIDATION_DIR / "dynamic_risk_alignment_shift90_close_retry_20260714" / "python_mt5_dynamic_risk_trades.csv")
    mt5_unique = read_csv(VALIDATION_DIR / "dynamic_risk_alignment_shift90_close_retry_20260714" / "mt5_ledger_unique_signals.csv")

    case = signal_cases[signal_cases["trade_id"] == LAYER3_MT5_ID].iloc[0]
    cause_row = cause[cause["trade_id"] == LAYER3_MT5_ID].iloc[0]
    mt5 = mt5_unique[mt5_unique["signal_anchor_time"].astype(str) == "2026-02-02 23:30:00"].iloc[0]

    target = parse_time(case.get("target_time"))
    direction = as_text(case.get("dir_norm"))
    trigger = as_text(case.get("trigger_family"))
    mode = as_text(case.get("mode_family"))

    raw = raw.copy()
    raw["date"] = pd.to_datetime(raw["date"], errors="coerce")
    raw["dir_norm"] = raw["dir"].map(normalize_dir)
    raw["mode_family"] = raw["mode"].astype(str).map(lambda v: "post_n" if "post_n" in v else ("pre_cross" if "pre_cross" in v else ("cross" if "cross" in v else v)))
    raw["trigger_family"] = "M30 CLOSE"
    raw["minutes_from_target"] = (raw["date"] - target).dt.total_seconds() / 60.0
    raw["abs_minutes"] = raw["minutes_from_target"].abs()
    raw_window = raw[(raw["dir_norm"] == direction) & (raw["abs_minutes"] <= 180)].sort_values("abs_minutes").copy()

    raw_spec_pass = int(raw_window["spec_pass"].astype(str).str.lower().eq("true").sum()) if not raw_window.empty else 0
    if raw_window.empty:
        subcause = "no_raw_candidate_in_target_window"
    elif raw_spec_pass == 0:
        subcause = "target_window_raw_candidates_all_spec_reject"
    else:
        subcause = "raw_candidate_exists_but_missing_accepted_or_layer3"

    layer_summary = {}
    layer_summary.update(nearest_summary(accepted, target, direction, trigger, mode, "accepted"))
    layer_summary.update(nearest_summary(picked, target, direction, trigger, mode, "picked"))
    layer_summary.update(nearest_summary(executed, target, direction, trigger, mode, "executed"))

    review = pd.DataFrame(
        [
            {
                "mt5_trade_id": LAYER3_MT5_ID,
                "target_time": case.get("target_time"),
                "signal_anchor_time": mt5.get("signal_anchor_time"),
                "dir_norm": direction,
                "trigger_family": trigger,
                "mode_family": mode,
                "mt5_signal_src": mt5.get("signal_src"),
                "mt5_profit": case.get("source_profit_$"),
                "mt5_stop_pts_spec": mt5.get("stop_pts_spec"),
                "cause_bucket_before": cause_row.get("cause_bucket"),
                "accepted_nearest_time_before": cause_row.get("accepted_date"),
                "accepted_nearest_abs_minutes_before": cause_row.get("accepted_abs_minutes"),
                "parent_status_before": cause_row.get("parent_status"),
                "raw_same_dir_rows_within_180m": int(len(raw_window)),
                "raw_spec_pass_rows_within_180m": raw_spec_pass,
                "raw_nearest_time": raw_window["date"].iloc[0] if not raw_window.empty else "",
                "raw_nearest_mode": raw_window["mode"].iloc[0] if not raw_window.empty else "",
                "raw_nearest_spec_pass": raw_window["spec_pass"].iloc[0] if not raw_window.empty else "",
                "raw_nearest_spec_reason": raw_window["spec_reason"].iloc[0] if not raw_window.empty else "",
                **layer_summary,
                "review_subcause": subcause,
                "next_action": "Review Python StopSpec/M15 SLOT1 rescue rules around 2026-02-03; current evidence points to target-window raw spec rejection rather than a true Layer3-only reject.",
            }
        ]
    )

    raw_cols = [
        "date",
        "minutes_from_target",
        "dir",
        "mode",
        "variant",
        "entry",
        "stop",
        "sd",
        "spec_pass",
        "spec_reason",
        "pnl",
        "won",
    ]
    return review, raw_window[[c for c in raw_cols if c in raw_window.columns]].copy()


def build_summary(stage_review: pd.DataFrame, layer3_review: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "item": "python_mt5_0061_mt5_0045",
                "status": stage_review["review_conclusion"].iloc[0],
                "impact": "-55.809800 matched residual if left unadjusted",
                "recommended_next_step": stage_review["next_action"].iloc[0],
            },
            {
                "item": "mt5_0068",
                "status": layer3_review["review_subcause"].iloc[0],
                "impact": "-230.63 signal-set gap",
                "recommended_next_step": layer3_review["next_action"].iloc[0],
            },
        ]
    )


def write_report(summary: pd.DataFrame, stage_review: pd.DataFrame, layer3_review: pd.DataFrame, raw_window: pd.DataFrame) -> None:
    lines = [
        "# Current P1 Remaining Review 20260714",
        "",
        "## Summary",
        "",
        markdown_table(summary, ["item", "status", "impact", "recommended_next_step"]),
        "",
        "## Stage-Exit Blocker",
        "",
        markdown_table(
            stage_review,
            [
                "case_id",
                "py_trade_id",
                "mt5_trade_id",
                "match_tier",
                "trigger_pair",
                "mode_pair",
                "first_m30_cross_time",
                "mt5_sl_time",
                "minutes_cross_before_sl",
                "journal_class",
                "review_conclusion",
            ],
        ),
        "",
        "## Layer3 Reject Review",
        "",
        markdown_table(
            layer3_review,
            [
                "mt5_trade_id",
                "target_time",
                "dir_norm",
                "trigger_family",
                "mode_family",
                "mt5_profit",
                "raw_same_dir_rows_within_180m",
                "raw_spec_pass_rows_within_180m",
                "raw_nearest_time",
                "raw_nearest_mode",
                "raw_nearest_spec_reason",
                "accepted_same_trigger_mode_within_180m",
                "picked_same_trigger_mode_within_180m",
                "executed_same_trigger_mode_within_180m",
                "review_subcause",
            ],
        ),
        "",
        "## Raw Candidates Near mt5_0068",
        "",
        markdown_table(raw_window, ["date", "minutes_from_target", "dir", "mode", "entry", "stop", "sd", "spec_pass", "spec_reason", "pnl"]),
        "",
        "## Decision",
        "",
        "- Do not open the EA price-side repair gate from these two cases.",
        "- `python_mt5_0061 / mt5_0045` is a relaxed M15-vs-M30 mapping plus unresolved Stage3 cross-vs-SL chronology issue.",
        "- `mt5_0068` should be reclassified from generic `layer3_reject` to target-window raw StopSpec rejection / missing accepted parent.",
    ]
    write_text(OUT_DIR / "current_p1_remaining_review.md", "\n".join(lines))


def write_readme() -> None:
    lines = [
        "# Current P1 Remaining Review 20260714",
        "",
        "Generated by `review_current_p1_remaining_20260714.py`.",
        "",
        "## Files",
        "",
        "- `current_p1_remaining_summary.csv`",
        "- `stage_exit_blocker_python_mt5_0061.csv`",
        "- `layer3_reject_mt5_0068.csv`",
        "- `layer3_reject_mt5_0068_raw_window.csv`",
        "- `current_p1_remaining_review.md`",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stage_review = build_stage_blocker_review()
    layer3_review, raw_window = build_layer3_reject_review()
    summary = build_summary(stage_review, layer3_review)

    export_csv(summary, OUT_DIR / "current_p1_remaining_summary.csv")
    export_csv(stage_review, OUT_DIR / "stage_exit_blocker_python_mt5_0061.csv")
    export_csv(layer3_review, OUT_DIR / "layer3_reject_mt5_0068.csv")
    export_csv(raw_window, OUT_DIR / "layer3_reject_mt5_0068_raw_window.csv")
    write_report(summary, stage_review, layer3_review, raw_window)
    write_readme()

    print(summary.to_string(index=False))
    print()
    print(stage_review.to_string(index=False))
    print()
    print(layer3_review.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
