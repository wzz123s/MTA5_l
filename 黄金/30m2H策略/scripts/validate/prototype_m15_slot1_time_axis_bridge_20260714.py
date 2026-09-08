# -*- coding: utf-8 -*-
"""Prototype a non-destructive M15 SLOT1 time-axis bridge for Python-MT5 review."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"
OUT_DIR = VALIDATION_DIR / "m15_slot1_time_axis_bridge_20260714"

MT5_SIGNAL_CSV = (
    VALIDATION_DIR
    / "mt5_log_session_diff_v326_full_20260712_m30postn_strict_veto_initfix_ea_diag"
    / "session_03"
    / "mt5_signals.csv"
)
LEDGER_CSV = VALIDATION_DIR / "ea_stage2_trail_ledger_full_20260714" / "30m2H_strategy_trade_ledger.csv"
REMAINING_CSV = VALIDATION_DIR / "runtime_style_remaining_diff_review_20260714" / "remaining_signal_set_drift_cases.csv"
RAW_CANDIDATES_CSV = DATA_DIR / "signals_mt5_shift90_20260712" / "python_h2_context_q2early" / "raw_candidates.csv"
M30_CSV = DATA_DIR / "processed" / "m30_mt5.csv"
M15_CSV = DATA_DIR / "processed" / "m15_context_bars.csv"


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


def time_key(value: object) -> str:
    ts = parse_time(value)
    if pd.isna(ts):
        return ""
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def mt5_time_key(value: object) -> str:
    ts = parse_mt5_time(value)
    if pd.isna(ts):
        ts = parse_time(value)
    if pd.isna(ts):
        return ""
    return ts.strftime("%Y-%m-%d %H:%M:%S")


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"L", "LONG", "BUY", "B", "1"}:
        return "BUY"
    if text in {"S", "SHORT", "SELL", "-1"}:
        return "SELL"
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


def safe_float(value: object) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return float("nan")
    return float(parsed)


def as_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def nearest_before_after(times: pd.Series, target: pd.Timestamp) -> tuple[object, object]:
    valid = pd.to_datetime(times, errors="coerce").dropna().sort_values()
    before = valid[valid <= target]
    after = valid[valid >= target]
    return (
        before.iloc[-1] if not before.empty else "",
        after.iloc[0] if not after.empty else "",
    )


def nearest_raw_candidate(raw: pd.DataFrame, target: pd.Timestamp, direction: str, mode: str) -> dict[str, object]:
    if raw.empty:
        return {}
    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["dir_norm"] = df["dir"].map(normalize_dir)
    df["mode_family"] = df["mode"].map(mode_family)
    same_dir = df[df["dir_norm"] == direction].copy()
    if same_dir.empty:
        return {}
    same_dir["abs_minutes"] = (same_dir["date"] - target).dt.total_seconds().abs() / 60.0
    any_row = same_dir.sort_values("abs_minutes").iloc[0]
    result = {
        "nearest_raw_any_mode_time": any_row.get("date", ""),
        "nearest_raw_any_mode_abs_minutes": safe_float(any_row.get("abs_minutes")),
        "nearest_raw_any_mode_mode": any_row.get("mode", ""),
        "nearest_raw_any_mode_entry": safe_float(any_row.get("entry")),
        "nearest_raw_any_mode_stop": safe_float(any_row.get("stop")),
        "nearest_raw_any_mode_sd": safe_float(any_row.get("sd")),
        "nearest_raw_any_mode_spec_pass": any_row.get("spec_pass", ""),
        "nearest_raw_any_mode_spec_reason": any_row.get("spec_reason", ""),
        "nearest_raw_time": any_row.get("date", ""),
        "nearest_raw_abs_minutes": safe_float(any_row.get("abs_minutes")),
        "nearest_raw_mode": any_row.get("mode", ""),
        "nearest_raw_entry": safe_float(any_row.get("entry")),
        "nearest_raw_stop": safe_float(any_row.get("stop")),
        "nearest_raw_sd": safe_float(any_row.get("sd")),
        "nearest_raw_spec_pass": any_row.get("spec_pass", ""),
        "nearest_raw_spec_reason": any_row.get("spec_reason", ""),
    }
    same_mode = same_dir[same_dir["mode_family"] == mode].copy()
    if not same_mode.empty:
        row = same_mode.sort_values("abs_minutes").iloc[0]
        result.update(
            {
                "nearest_raw_time": row.get("date", ""),
                "nearest_raw_abs_minutes": safe_float(row.get("abs_minutes")),
                "nearest_raw_mode": row.get("mode", ""),
                "nearest_raw_entry": safe_float(row.get("entry")),
                "nearest_raw_stop": safe_float(row.get("stop")),
                "nearest_raw_sd": safe_float(row.get("sd")),
                "nearest_raw_spec_pass": row.get("spec_pass", ""),
                "nearest_raw_spec_reason": row.get("spec_reason", ""),
            }
        )
    else:
        result.update(
            {
                "nearest_raw_time": any_row.get("date", ""),
                "nearest_raw_abs_minutes": safe_float(any_row.get("abs_minutes")),
                "nearest_raw_mode": any_row.get("mode", ""),
                "nearest_raw_entry": safe_float(any_row.get("entry")),
                "nearest_raw_stop": safe_float(any_row.get("stop")),
                "nearest_raw_sd": safe_float(any_row.get("sd")),
                "nearest_raw_spec_pass": any_row.get("spec_pass", ""),
                "nearest_raw_spec_reason": any_row.get("spec_reason", ""),
            }
        )
    return result


def build_ledger_lookup() -> dict[tuple[str, str, str], dict[str, object]]:
    ledger = read_csv(LEDGER_CSV)
    ledger = ledger[ledger["trigger_tag"].astype(str).str.contains("M15 SLOT1", regex=False)].copy()
    ledger["raw_anchor_key"] = ledger["signal_anchor_time"].map(mt5_time_key)
    ledger["dir_norm"] = ledger["dir"].map(normalize_dir)
    ledger["mode_family"] = ledger["signal_src"].map(mode_family)
    rows: dict[tuple[str, str, str], dict[str, object]] = {}
    for key, group in ledger.groupby(["raw_anchor_key", "dir_norm", "mode_family"], dropna=False):
        first = group.iloc[0]
        rows[key] = {
            "ledger_stage_rows": int(len(group)),
            "ledger_signal_entry": safe_float(first.get("signal_entry")),
            "ledger_signal_stop": safe_float(first.get("signal_stop")),
            "ledger_fill_price": safe_float(first.get("fill_price")),
            "ledger_actual_stop": safe_float(first.get("actual_stop")),
            "ledger_stop_pts_spec": safe_float(first.get("stop_pts")) / 1000.0,
            "ledger_net_profit": safe_float(pd.to_numeric(group["net_profit"], errors="coerce").sum()),
            "ledger_local_exit_reasons": ";".join(sorted(set(group["local_exit_reason"].dropna().astype(str)))),
            "ledger_deal_reasons": ";".join(sorted(set(group["deal_reason"].dropna().astype(str)))),
        }
    return rows


def build_remaining_lookup() -> dict[tuple[str, str, str], dict[str, object]]:
    remaining = read_csv(REMAINING_CSV)
    mt5_only = remaining[
        (remaining["side"].astype(str) == "mt5_unmatched")
        & (remaining["trigger_family"].astype(str) == "M15 SLOT1")
    ].copy()
    mt5_only["target_key"] = mt5_only["target_time"].map(time_key)
    mt5_only["dir_norm"] = mt5_only["dir_norm"].map(normalize_dir)
    mt5_only["mode_family"] = mt5_only["mode_family"].map(mode_family)
    rows: dict[tuple[str, str, str], dict[str, object]] = {}
    for _, row in mt5_only.iterrows():
        key = (row["target_key"], row["dir_norm"], row["mode_family"])
        rows[key] = {
            "remaining_trade_id": row.get("trade_id", ""),
            "remaining_gap_effect": row.get("gap_effect_$", ""),
            "remaining_abs_gap_effect": row.get("abs_gap_effect_$", ""),
            "remaining_cause_bucket": row.get("cause_bucket", ""),
            "remaining_parent_status": row.get("parent_status", ""),
            "remaining_action_bucket": row.get("action_bucket", ""),
        }
    return rows


def build_bridge_candidates() -> pd.DataFrame:
    mt5 = read_csv(MT5_SIGNAL_CSV)
    mt5 = mt5[mt5["trigger"].astype(str) == "M15 SLOT1"].copy()
    mt5["shifted_anchor"] = pd.to_datetime(mt5["anchor_time"], errors="coerce")
    mt5["raw_anchor"] = pd.to_datetime(mt5["mt5_raw_anchor_time"], errors="coerce")
    mt5["log_time"] = pd.to_datetime(mt5["log_time"], errors="coerce")
    mt5["log_time_plus90"] = mt5["log_time"] + pd.Timedelta(minutes=90)
    mt5["dir_norm"] = mt5["dir"].map(normalize_dir)
    mt5["mode_family"] = mt5["mode_norm"].map(mode_family)

    m30 = read_csv(M30_CSV)
    m30["date"] = pd.to_datetime(m30["date"], errors="coerce")
    m30_dates = set(m30["date"].dropna())
    m15 = read_csv(M15_CSV)
    m15["date"] = pd.to_datetime(m15["date"], errors="coerce")
    m15_dates = set(m15["date"].dropna())
    raw = read_csv(RAW_CANDIDATES_CSV)

    ledger_lookup = build_ledger_lookup()
    remaining_lookup = build_remaining_lookup()

    rows: list[dict[str, object]] = []
    for _, row in mt5.iterrows():
        shifted_anchor = row["shifted_anchor"]
        raw_anchor = row["raw_anchor"]
        log_time_plus90 = row["log_time_plus90"]
        direction = normalize_dir(row["dir_norm"])
        family = mode_family(row["mode_family"])
        shifted_key = time_key(shifted_anchor)
        raw_key = time_key(raw_anchor)

        m30_has_shifted = pd.notna(shifted_anchor) and shifted_anchor in m30_dates
        m15_has_shifted_log = pd.notna(log_time_plus90) and log_time_plus90 in m15_dates
        m30_prev, m30_next = nearest_before_after(m30["date"], shifted_anchor)
        m15_prev, m15_next = nearest_before_after(m15["date"], log_time_plus90)

        ledger_key = (raw_key, direction, family)
        ledger = ledger_lookup.get(ledger_key, {})
        remaining_key = (shifted_key, direction, family)
        remaining = remaining_lookup.get(remaining_key, {})
        raw_nearest = nearest_raw_candidate(raw, shifted_anchor, direction, family)

        has_time_axis_gap = not bool(m30_has_shifted and m15_has_shifted_log)
        in_remaining = bool(remaining)
        if has_time_axis_gap and in_remaining:
            bridge_class = "time_axis_bridge_candidate"
            bridge_decision = "reclass_unmatched_cause_only"
        elif has_time_axis_gap:
            bridge_class = "time_axis_gap_not_current_remaining"
            bridge_decision = "track_only"
        else:
            bridge_class = "normal_time_axis_available"
            bridge_decision = "no_bridge_needed"

        rows.append(
            {
                "shifted_anchor": shifted_anchor,
                "raw_anchor": raw_anchor,
                "log_time": row["log_time"],
                "log_time_plus90": log_time_plus90,
                "dir_norm": direction,
                "trigger_family": "M15 SLOT1",
                "mode_family": family,
                "mode_raw": row.get("mode_raw", ""),
                "mt5_stop_dist": row.get("mt5_stop_dist", ""),
                "processed_m30_has_shifted_anchor": bool(m30_has_shifted),
                "processed_m30_prev": m30_prev,
                "processed_m30_next": m30_next,
                "processed_m15_has_log_plus90": bool(m15_has_shifted_log),
                "processed_m15_prev": m15_prev,
                "processed_m15_next": m15_next,
                "has_time_axis_gap": bool(has_time_axis_gap),
                "in_current_remaining_drift": in_remaining,
                "bridge_class": bridge_class,
                "bridge_decision": bridge_decision,
                **remaining,
                **ledger,
                **raw_nearest,
            }
        )

    return pd.DataFrame(rows).sort_values(["shifted_anchor", "dir_norm", "mode_family"]).reset_index(drop=True)


def reclass_remaining(candidates: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    remaining = read_csv(REMAINING_CSV)
    bridge = candidates[candidates["bridge_class"] == "time_axis_bridge_candidate"].copy()
    bridge["target_key"] = bridge["shifted_anchor"].map(time_key)
    bridge["dir_norm"] = bridge["dir_norm"].map(normalize_dir)
    bridge["mode_family"] = bridge["mode_family"].map(mode_family)
    bridge_map = {
        (row["target_key"], row["dir_norm"], row["mode_family"]): row
        for _, row in bridge.iterrows()
    }

    rows = []
    for _, row in remaining.iterrows():
        out = row.to_dict()
        target_key = time_key(row.get("target_time"))
        key = (target_key, normalize_dir(row.get("dir_norm")), mode_family(row.get("mode_family")))
        candidate = bridge_map.get(key)
        original = str(row.get("cause_bucket", ""))
        if candidate is not None and str(row.get("side")) == "mt5_unmatched":
            out["bridge_reclass_applied"] = True
            out["bridge_cause_bucket"] = "time_axis_bridge_candidate"
            out["bridge_decision"] = "reclass_cause_only_no_fund_change"
            out["bridge_note"] = (
                "MT5 M15 SLOT1 shifted anchor/log time falls into processed data gap; "
                "do not treat nearest later raw candidate as same runtime entry."
            )
            out["bridge_raw_anchor"] = candidate.get("raw_anchor", "")
            out["bridge_log_time"] = candidate.get("log_time", "")
            out["bridge_ledger_signal_entry"] = candidate.get("ledger_signal_entry", "")
            out["bridge_ledger_signal_stop"] = candidate.get("ledger_signal_stop", "")
            out["bridge_ledger_stop_pts_spec"] = candidate.get("ledger_stop_pts_spec", "")
        else:
            out["bridge_reclass_applied"] = False
            out["bridge_cause_bucket"] = original
            out["bridge_decision"] = "unchanged"
            out["bridge_note"] = ""
            out["bridge_raw_anchor"] = ""
            out["bridge_log_time"] = ""
            out["bridge_ledger_signal_entry"] = ""
            out["bridge_ledger_signal_stop"] = ""
            out["bridge_ledger_stop_pts_spec"] = ""
        rows.append(out)

    out_df = pd.DataFrame(rows)
    changed = out_df[out_df["bridge_reclass_applied"] == True].copy()  # noqa: E712
    return out_df, changed


def build_summary(candidates: pd.DataFrame, changed: pd.DataFrame) -> pd.DataFrame:
    rows = [
        {"metric": "m15_slot1_signals", "value": int(len(candidates))},
        {
            "metric": "m30_shifted_anchor_gap",
            "value": int((~candidates["processed_m30_has_shifted_anchor"]).sum()),
        },
        {
            "metric": "m15_log_plus90_gap",
            "value": int((~candidates["processed_m15_has_log_plus90"]).sum()),
        },
        {"metric": "any_time_axis_gap", "value": int(candidates["has_time_axis_gap"].sum())},
        {
            "metric": "current_remaining_m15_slot1_with_gap",
            "value": int((candidates["bridge_class"] == "time_axis_bridge_candidate").sum()),
        },
        {"metric": "remaining_reclass_changed_cases", "value": int(len(changed))},
        {
            "metric": "mt5_0068_reclassified",
            "value": int((changed["trade_id"].astype(str) == "mt5_0068").sum()) if not changed.empty else 0,
        },
    ]
    return pd.DataFrame(rows)


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


def write_report(summary: pd.DataFrame, candidates: pd.DataFrame, changed: pd.DataFrame) -> None:
    focus = candidates[candidates["remaining_trade_id"].astype(str) == "mt5_0068"].copy()
    lines = [
        "# M15 SLOT1 Time-Axis Bridge Prototype 20260714",
        "",
        "## Summary",
        "",
        markdown_table(summary, ["metric", "value"]),
        "",
        "## Reclassified Remaining Cases",
        "",
        markdown_table(
            changed,
            [
                "trade_id",
                "target_time",
                "dir_norm",
                "mode_family",
                "cause_bucket",
                "bridge_cause_bucket",
                "gap_effect_$",
                "bridge_decision",
            ],
        ),
        "",
        "## mt5_0068 Evidence",
        "",
        markdown_table(
            focus,
            [
                "remaining_trade_id",
                "shifted_anchor",
                "raw_anchor",
                "log_time",
                "log_time_plus90",
                "ledger_signal_entry",
                "ledger_signal_stop",
                "ledger_stop_pts_spec",
                "processed_m30_has_shifted_anchor",
                "processed_m30_prev",
                "processed_m30_next",
                "processed_m15_has_log_plus90",
                "processed_m15_prev",
                "processed_m15_next",
                "nearest_raw_any_mode_time",
                "nearest_raw_any_mode_mode",
                "nearest_raw_any_mode_sd",
                "nearest_raw_any_mode_spec_reason",
                "nearest_raw_time",
                "nearest_raw_mode",
                "nearest_raw_sd",
                "nearest_raw_spec_reason",
                "bridge_class",
            ],
        ),
        "",
        "## Decision",
        "",
        "- This prototype changes classification only; it does not change signals, trades, or the fund curve.",
        "- MT5 M15 SLOT1 samples with shifted anchors inside processed-data gaps should not be judged by the nearest later Python raw candidate.",
        "- Keep the EA price-side repair gate closed.",
    ]
    write_text(OUT_DIR / "m15_slot1_time_axis_bridge_report.md", "\n".join(lines))


def write_readme() -> None:
    lines = [
        "# M15 SLOT1 Time-Axis Bridge Prototype 20260714",
        "",
        "Generated by `prototype_m15_slot1_time_axis_bridge_20260714.py`.",
        "",
        "## Files",
        "",
        "- `m15_slot1_time_axis_bridge_candidates.csv`",
        "- `remaining_signal_set_drift_bridge_reclass.csv`",
        "- `bridge_reclass_changed_cases.csv`",
        "- `m15_slot1_time_axis_gap_summary.csv`",
        "- `m15_slot1_time_axis_bridge_report.md`",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates = build_bridge_candidates()
    reclassed, changed = reclass_remaining(candidates)
    summary = build_summary(candidates, changed)

    export_csv(candidates, OUT_DIR / "m15_slot1_time_axis_bridge_candidates.csv")
    export_csv(reclassed, OUT_DIR / "remaining_signal_set_drift_bridge_reclass.csv")
    export_csv(changed, OUT_DIR / "bridge_reclass_changed_cases.csv")
    export_csv(summary, OUT_DIR / "m15_slot1_time_axis_gap_summary.csv")
    write_report(summary, candidates, changed)
    write_readme()

    print(summary.to_string(index=False))
    print()
    print(changed[["trade_id", "target_time", "cause_bucket", "bridge_cause_bucket", "gap_effect_$"]].to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
