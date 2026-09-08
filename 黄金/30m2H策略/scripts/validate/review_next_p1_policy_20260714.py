# -*- coding: utf-8 -*-
"""Review the next P1 policy decisions after current remaining P1 triage."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"
OUT_DIR = VALIDATION_DIR / "next_p1_policy_review_20260714"

CURRENT_P1_DIR = VALIDATION_DIR / "current_p1_remaining_review_20260714"
LEDGER_DIR = VALIDATION_DIR / "ea_stage2_trail_ledger_full_20260714"
SMOKE_DIR = VALIDATION_DIR / "ea_stage2_trail_ledger_smoke_20260714" / "20260202"
EQ_DIR = VALIDATION_DIR / "trigger_family_equivalence_shift90_close_retry_20260714"
MT5_SIGNAL_CSV = (
    VALIDATION_DIR
    / "mt5_log_session_diff_v326_full_20260712_m30postn_strict_veto_initfix_ea_diag"
    / "session_03"
    / "mt5_signals.csv"
)


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def parse_time(value: object) -> pd.Timestamp:
    return pd.to_datetime(value, errors="coerce")


def parse_mt5_time(value: object) -> pd.Timestamp:
    return pd.to_datetime(value, format="%Y.%m.%d %H:%M", errors="coerce")


def as_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def safe_float(value: object) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return float("nan")
    return float(parsed)


def bool_text(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def nearest_before_after(times: pd.Series, target: pd.Timestamp) -> tuple[object, object]:
    valid = pd.to_datetime(times, errors="coerce").dropna().sort_values()
    before = valid[valid <= target]
    after = valid[valid >= target]
    return (
        before.iloc[-1] if not before.empty else "",
        after.iloc[0] if not after.empty else "",
    )


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

    return "\n".join(
        [
            render(columns),
            "| " + " | ".join("-" * width for width in widths) + " |",
            *[render(row) for row in rows],
        ]
    )


def review_mt5_0068() -> pd.DataFrame:
    ledger = read_csv(LEDGER_DIR / "30m2H_strategy_trade_ledger.csv")
    ledger_rows = ledger[
        (ledger["signal_anchor_time"].astype(str) == "2026.02.02 23:30")
        & (ledger["signal_src"].astype(str).str.contains("pre_cross_m15_slot1", regex=False))
        & (ledger["dir"].astype(str).str.upper() == "BUY")
    ].copy()
    if ledger_rows.empty:
        raise RuntimeError("Cannot find mt5_0068 rows in EA ledger")

    first_ledger = ledger_rows.iloc[0]
    signal_entry = safe_float(first_ledger["signal_entry"])
    signal_stop = safe_float(first_ledger["signal_stop"])
    stop_pts_mql = safe_float(first_ledger["stop_pts"])
    stop_pts_spec = stop_pts_mql / 1000.0

    mt5_signals = read_csv(MT5_SIGNAL_CSV)
    mt5_signals["anchor_time"] = pd.to_datetime(mt5_signals["anchor_time"], errors="coerce")
    signal = mt5_signals[
        (mt5_signals["anchor_time"] == pd.Timestamp("2026-02-03 01:00:00"))
        & (mt5_signals["trigger"].astype(str) == "M15 SLOT1")
        & (mt5_signals["dir"].astype(str) == "L")
    ].iloc[0]
    raw_anchor = parse_time(signal["mt5_raw_anchor_time"])
    aligned_anchor = parse_time(signal["anchor_time"])
    log_time = parse_time(signal["log_time"])

    signals_export = read_csv(LEDGER_DIR / "30m2H_strategy_signals_export.csv")
    signals_export["bar_time_dt"] = pd.to_datetime(signals_export["bar_time"], format="%Y.%m.%d %H:%M", errors="coerce")
    raw_anchor_row = signals_export[signals_export["bar_time_dt"] == raw_anchor]
    raw_anchor_row = raw_anchor_row.iloc[0] if not raw_anchor_row.empty else pd.Series(dtype=object)
    nearby_export = signals_export[
        (signals_export["bar_time_dt"] >= raw_anchor - pd.Timedelta(hours=3))
        & (signals_export["bar_time_dt"] <= raw_anchor + pd.Timedelta(hours=3))
    ].copy()
    nearby_export["sma13_stop_abs_diff"] = (pd.to_numeric(nearby_export["m30_sma13"], errors="coerce") - signal_stop).abs()
    stop_source = nearby_export.sort_values("sma13_stop_abs_diff").head(1)
    stop_source_row = stop_source.iloc[0] if not stop_source.empty else pd.Series(dtype=object)

    processed_m30 = read_csv(DATA_DIR / "processed" / "m30_mt5.csv")
    processed_m30["date"] = pd.to_datetime(processed_m30["date"], errors="coerce")
    m30_before, m30_after = nearest_before_after(processed_m30["date"], aligned_anchor)
    has_aligned_m30 = bool((processed_m30["date"] == aligned_anchor).any())

    processed_m15 = read_csv(DATA_DIR / "processed" / "m15_context_bars.csv")
    processed_m15["date"] = pd.to_datetime(processed_m15["date"], errors="coerce")
    shifted_log_time = log_time + pd.Timedelta(minutes=90)
    m15_before, m15_after = nearest_before_after(processed_m15["date"], shifted_log_time)
    has_shifted_log_m15 = bool((processed_m15["date"] == shifted_log_time).any())

    raw_window = read_csv(CURRENT_P1_DIR / "layer3_reject_mt5_0068_raw_window.csv")
    nearest_raw = raw_window.iloc[0] if not raw_window.empty else pd.Series(dtype=object)

    diag_path = SMOKE_DIR / "30m2H_strategy_stage_price_diag.csv"
    diag = read_csv(diag_path) if diag_path.exists() else pd.DataFrame()
    if not diag.empty:
        diag_hit = diag[
            (diag["signal_anchor_time"].astype(str) == "2026.02.02 23:30")
            & (diag["trigger_tag"].astype(str) == "[M15 SLOT1]")
        ].copy()
    else:
        diag_hit = pd.DataFrame()
    first_diag = diag_hit.iloc[0] if not diag_hit.empty else pd.Series(dtype=object)

    has_time_gap = not has_aligned_m30 or not has_shifted_log_m15
    python_raw_misses_exact = not raw_window.empty and parse_time(nearest_raw.get("date")) != aligned_anchor
    if has_time_gap and python_raw_misses_exact:
        decision = "fix_python_mt5_time_axis_or_slot1_bridge_before_signal_logic"
        status = "time_axis_gap_plus_mt5_runtime_slot1_entry"
        next_step = (
            "Do not patch EA or Layer3. Add a Python-MT5 diagnostic bridge for M15 SLOT1 "
            "signals whose shifted anchor falls in a missing processed M30/M15 bar, then rerun mt5_0068."
        )
    else:
        decision = "review_stop_rescue_formula"
        status = "stop_rescue_formula_still_open"
        next_step = "Recompute StopSpec/rescue with exact slot1 proxy and EA stop source."

    return pd.DataFrame(
        [
            {
                "item": "mt5_0068",
                "status": status,
                "decision": decision,
                "mt5_shifted_anchor": aligned_anchor,
                "mt5_raw_anchor": raw_anchor,
                "mt5_log_time": log_time,
                "mt5_log_time_plus90": shifted_log_time,
                "ledger_signal_entry": round(signal_entry, 6),
                "ledger_signal_stop": round(signal_stop, 6),
                "ledger_stop_pts_spec": round(stop_pts_spec, 6),
                "ledger_stage_rows": int(len(ledger_rows)),
                "ledger_net_profit": round(float(pd.to_numeric(ledger_rows["net_profit"], errors="coerce").sum()), 6),
                "mt5_signal_stop_dist": safe_float(signal.get("mt5_stop_dist")),
                "signals_export_raw_anchor_close": safe_float(raw_anchor_row.get("close")),
                "signals_export_raw_anchor_m30_sma13": safe_float(raw_anchor_row.get("m30_sma13")),
                "signals_export_raw_anchor_decision": raw_anchor_row.get("decision", ""),
                "stop_source_candidate_time": stop_source_row.get("bar_time_dt", ""),
                "stop_source_candidate_m30_sma13": safe_float(stop_source_row.get("m30_sma13")),
                "stop_source_abs_diff": safe_float(stop_source_row.get("sma13_stop_abs_diff")),
                "processed_m30_has_shifted_anchor": has_aligned_m30,
                "processed_m30_prev": m30_before,
                "processed_m30_next": m30_after,
                "processed_m15_has_shifted_log_time": has_shifted_log_m15,
                "processed_m15_prev": m15_before,
                "processed_m15_next": m15_after,
                "python_nearest_raw_time": nearest_raw.get("date", ""),
                "python_nearest_raw_mode": nearest_raw.get("mode", ""),
                "python_nearest_raw_sd": safe_float(nearest_raw.get("sd")),
                "python_nearest_raw_spec_reason": nearest_raw.get("spec_reason", ""),
                "stage_price_diag_first_time": first_diag.get("time", ""),
                "stage_price_diag_first_bid": safe_float(first_diag.get("bid")),
                "stage_price_diag_first_ask": safe_float(first_diag.get("ask")),
                "next_step": next_step,
            }
        ]
    )


def review_python_mt5_0061() -> pd.DataFrame:
    selected = read_csv(EQ_DIR / "bidirectional_m30_m15_90_profit20_selected_matches.csv")
    policy_summary = read_csv(EQ_DIR / "trigger_family_equivalence_policy_summary.csv")
    tier_counts = read_csv(EQ_DIR / "trigger_family_equivalence_tier_counts.csv")
    row = selected[
        (selected["py_trade_id"].astype(str) == "python_mt5_0061")
        & (selected["mt5_trade_id"].astype(str) == "mt5_0045")
    ].iloc[0]

    policy = str(row.get("policy"))
    policy_row = policy_summary[policy_summary["policy"].astype(str) == policy].iloc[0]
    policy_tiers = tier_counts[tier_counts["policy"].astype(str) == policy].copy()
    same_tier = policy_tiers[
        policy_tiers["effective_match_tier"].astype(str) == str(row.get("effective_match_tier"))
    ]
    same_tier_rows = int(same_tier["rows"].iloc[0]) if not same_tier.empty else 0

    effective_reliable = bool_text(row.get("effective_is_reliable"))
    trigger_same = bool_text(row.get("trigger_same"))
    if (not effective_reliable) and (not trigger_same):
        decision = "exclude_from_runtime_pnl_adjustment_keep_for_accounting_only"
        status = "selected_policy_nonreliable_trigger_relaxed_match"
        next_step = (
            "Do not use this pair to prove a Stage3 runtime bug. Keep it in accounting diff, "
            "or move it to signal-set drift, until tick/journal evidence validates the relaxed M15-vs-M30 match."
        )
    else:
        decision = "runtime_adjustment_can_remain_candidate"
        status = "selected_policy_reliable_or_same_trigger"
        next_step = "If kept as runtime candidate, collect EA Stage3 cross/tick evidence before behavior changes."

    return pd.DataFrame(
        [
            {
                "item": "python_mt5_0061_mt5_0045",
                "status": status,
                "decision": decision,
                "policy": policy,
                "effective_match_tier": row.get("effective_match_tier"),
                "effective_is_reliable": effective_reliable,
                "effective_tier_rank": row.get("effective_tier_rank"),
                "same_effective_tier_rows_in_policy": same_tier_rows,
                "policy_matched_unique": int(policy_row.get("matched_unique")),
                "policy_reliable_tier_matched": int(policy_row.get("reliable_tier_matched")),
                "policy_relaxed_tier_matched": int(policy_row.get("relaxed_tier_matched")),
                "trigger_same": trigger_same,
                "mode_same": bool_text(row.get("mode_same")),
                "py_trigger_family": row.get("py_trigger_family"),
                "mt5_trigger_family": row.get("mt5_trigger_family"),
                "py_mode_family": row.get("py_mode_family"),
                "mt5_mode_family": row.get("mt5_mode_family"),
                "py_date": row.get("py_date"),
                "mt5_aligned_time": row.get("mt5_aligned_time"),
                "abs_time_diff_minutes": row.get("abs_time_diff_minutes"),
                "py_profit": row.get("py_profit"),
                "mt5_profit": row.get("mt5_profit"),
                "profit_diff": row.get("profit_diff"),
                "next_step": next_step,
            }
        ]
    )


def build_summary(mt5_0068: pd.DataFrame, py0061: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "item": "mt5_0068",
                "status": mt5_0068["status"].iloc[0],
                "decision": mt5_0068["decision"].iloc[0],
                "next_step": mt5_0068["next_step"].iloc[0],
            },
            {
                "item": "python_mt5_0061_mt5_0045",
                "status": py0061["status"].iloc[0],
                "decision": py0061["decision"].iloc[0],
                "next_step": py0061["next_step"].iloc[0],
            },
        ]
    )


def write_report(summary: pd.DataFrame, mt5_0068: pd.DataFrame, py0061: pd.DataFrame) -> None:
    lines = [
        "# Next P1 Policy Review 20260714",
        "",
        "## Summary",
        "",
        markdown_table(summary, ["item", "status", "decision", "next_step"]),
        "",
        "## mt5_0068 StopSpec / Slot1",
        "",
        markdown_table(
            mt5_0068,
            [
                "item",
                "mt5_shifted_anchor",
                "mt5_raw_anchor",
                "mt5_log_time",
                "ledger_signal_entry",
                "ledger_signal_stop",
                "ledger_stop_pts_spec",
                "processed_m30_has_shifted_anchor",
                "processed_m30_prev",
                "processed_m30_next",
                "python_nearest_raw_time",
                "python_nearest_raw_sd",
                "python_nearest_raw_spec_reason",
                "decision",
            ],
        ),
        "",
        "## python_mt5_0061 Mapping Policy",
        "",
        markdown_table(
            py0061,
            [
                "item",
                "policy",
                "effective_match_tier",
                "effective_is_reliable",
                "trigger_same",
                "py_trigger_family",
                "mt5_trigger_family",
                "abs_time_diff_minutes",
                "profit_diff",
                "decision",
            ],
        ),
        "",
        "## Decision",
        "",
        "- Keep the EA price-side repair gate closed.",
        "- Treat `mt5_0068` as a Python-MT5 time-axis / M15 SLOT1 bridge issue before changing signal math.",
        "- Treat `python_mt5_0061 / mt5_0045` as a non-reliable relaxed mapping for accounting only until direct EA evidence exists.",
    ]
    write_text(OUT_DIR / "next_p1_policy_review.md", "\n".join(lines))


def write_readme() -> None:
    lines = [
        "# Next P1 Policy Review 20260714",
        "",
        "Generated by `review_next_p1_policy_20260714.py`.",
        "",
        "## Files",
        "",
        "- `next_p1_policy_summary.csv`",
        "- `mt5_0068_stop_rescue_policy.csv`",
        "- `python_mt5_0061_relaxed_policy_review.csv`",
        "- `next_p1_policy_review.md`",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mt5_0068 = review_mt5_0068()
    py0061 = review_python_mt5_0061()
    summary = build_summary(mt5_0068, py0061)

    export_csv(summary, OUT_DIR / "next_p1_policy_summary.csv")
    export_csv(mt5_0068, OUT_DIR / "mt5_0068_stop_rescue_policy.csv")
    export_csv(py0061, OUT_DIR / "python_mt5_0061_relaxed_policy_review.csv")
    write_report(summary, mt5_0068, py0061)
    write_readme()

    print(summary.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
