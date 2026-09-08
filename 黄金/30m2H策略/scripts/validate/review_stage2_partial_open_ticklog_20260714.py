# -*- coding: utf-8 -*-
"""Review Stage2 partial-open cases with available deal/M15/diag evidence.

The earlier Stage2 trail refinement marks several rows as tick/log-needed
because the first M30 event falls in the opening M30 bar. This script narrows
those cases using the data already available in the repo:

- close-retry MT5 trade ledger / deal comment
- M15 refinement output
- optional EA stage price smoke diagnostics

It still does not replace exported MT5 ticks or tester journal logs.
"""
from __future__ import annotations


import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"
RUNTIME_DIR = VALIDATION_DIR / "python_runtime_stage_exit_prototype_20260714"
MT5_DIR = VALIDATION_DIR / "mt5_full_close_retry_fix_20260714"
SMOKE_DIR = VALIDATION_DIR / "ea_stage_price_side_smoke_20260714"

SL_RE = re.compile(r"\bsl\s+([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)
PRICE_TOLERANCE = 0.10


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def parse_time(value: object) -> pd.Timestamp:
    return pd.to_datetime(value, errors="coerce")


def parse_sl_comment(comment: object) -> float:
    if pd.isna(comment):
        return float("nan")
    match = SL_RE.search(str(comment))
    if not match:
        return float("nan")
    return float(match.group(1))


def safe_float(value: object) -> float:
    return pd.to_numeric(value, errors="coerce")


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def classify_sl_price(deal_sl: float, actual_stop: float, final_sim_sl: float) -> tuple[str, float, float]:
    dist_initial = abs(deal_sl - actual_stop) if pd.notna(deal_sl) else float("nan")
    dist_final = abs(deal_sl - final_sim_sl) if pd.notna(deal_sl) and pd.notna(final_sim_sl) else float("nan")

    if pd.isna(deal_sl):
        return "no_sl_comment_price", dist_initial, dist_final
    if pd.notna(dist_initial) and dist_initial <= PRICE_TOLERANCE:
        return "initial_sl_price", dist_initial, dist_final
    if pd.notna(dist_final) and pd.notna(dist_initial) and dist_final < dist_initial:
        return "trail_or_modified_sl_price", dist_initial, dist_final
    return "sl_price_unclassified", dist_initial, dist_final


def load_diag_files() -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    if not SMOKE_DIR.exists():
        return pd.DataFrame()

    for path in SMOKE_DIR.rglob("30m2H_strategy_stage_price_diag.csv"):
        df = read_csv(path)
        if df.empty:
            continue
        df = df.copy()
        df["diag_source"] = str(path.relative_to(VALIDATION_DIR))
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        for col in [
            "entry",
            "orig_sl",
            "current_sl",
            "bid",
            "ask",
            "close_side_price",
            "close_abs_rr",
            "close_profit_rr",
        ]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        frames.append(df)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values("time").reset_index(drop=True)


def diag_match(case: pd.Series, diag: pd.DataFrame) -> pd.DataFrame:
    if diag.empty:
        return diag
    anchor = str(case.get("signal_anchor_time", ""))
    stage = int(case.get("stage", 0))
    entry = float(case.get("fill_price"))
    stop = float(case.get("actual_stop"))

    matched = diag[
        (diag["signal_anchor_time"].astype(str) == anchor)
        & (pd.to_numeric(diag["stage"], errors="coerce") == stage)
        & ((diag["entry"] - entry).abs() <= PRICE_TOLERANCE)
        & ((diag["orig_sl"] - stop).abs() <= PRICE_TOLERANCE)
    ].copy()
    return matched.sort_values("time").reset_index(drop=True)


def summarize_diag(case: pd.Series, diag_rows: pd.DataFrame) -> dict[str, object]:
    open_time = parse_time(case.get("open_time"))
    exit_time = parse_time(case.get("exit_time"))
    direction = str(case.get("dir_norm", "")).upper()
    actual_stop = float(case.get("actual_stop"))

    result: dict[str, object] = {
        "diag_available": False,
        "diag_source": "",
        "diag_rows": 0,
        "diag_first_time": pd.NaT,
        "diag_last_time": pd.NaT,
        "diag_covers_open_to_exit": False,
        "diag_first_stop_side_touch_time": pd.NaT,
        "diag_first_trail_on_time": pd.NaT,
        "diag_first_trailing_time": pd.NaT,
        "diag_max_close_side_before_exit": float("nan"),
        "diag_min_close_side_before_exit": float("nan"),
        "diag_last_current_sl_before_exit": float("nan"),
        "diag_stop_side_touch_seen": False,
        "diag_trail_seen": False,
        "diag_note": "",
    }
    if diag_rows.empty or pd.isna(open_time) or pd.isna(exit_time):
        return result

    window = diag_rows[(diag_rows["time"] >= open_time) & (diag_rows["time"] <= exit_time)].copy()
    if window.empty:
        result["diag_available"] = True
        result["diag_source"] = "; ".join(sorted(diag_rows["diag_source"].astype(str).unique()))
        result["diag_rows"] = int(len(diag_rows))
        result["diag_first_time"] = diag_rows["time"].min()
        result["diag_last_time"] = diag_rows["time"].max()
        result["diag_note"] = "diag rows exist, but none fall inside open-to-exit window"
        return result

    close_side = pd.to_numeric(window["close_side_price"], errors="coerce")
    current_sl = pd.to_numeric(window["current_sl"], errors="coerce")
    if direction == "SELL":
        touch_mask = close_side >= current_sl.fillna(actual_stop)
    else:
        touch_mask = close_side <= current_sl.fillna(actual_stop)

    trail_on_mask = window["legacy_action_text"].astype(str).str.contains("stage2_trail_on", case=False, na=False)
    trailing_mask = window["legacy_action_text"].astype(str).str.contains("stage2_trailing", case=False, na=False)
    trail_mask = trail_on_mask | trailing_mask

    result.update(
        {
            "diag_available": True,
            "diag_source": "; ".join(sorted(window["diag_source"].astype(str).unique())),
            "diag_rows": int(len(window)),
            "diag_first_time": window["time"].min(),
            "diag_last_time": window["time"].max(),
            "diag_covers_open_to_exit": bool(window["time"].min() <= open_time and window["time"].max() >= exit_time),
            "diag_first_stop_side_touch_time": window.loc[touch_mask, "time"].min() if touch_mask.any() else pd.NaT,
            "diag_first_trail_on_time": window.loc[trail_on_mask, "time"].min() if trail_on_mask.any() else pd.NaT,
            "diag_first_trailing_time": window.loc[trailing_mask, "time"].min() if trailing_mask.any() else pd.NaT,
            "diag_max_close_side_before_exit": close_side.max(),
            "diag_min_close_side_before_exit": close_side.min(),
            "diag_last_current_sl_before_exit": current_sl.dropna().iloc[-1] if current_sl.notna().any() else float("nan"),
            "diag_stop_side_touch_seen": bool(touch_mask.any()),
            "diag_trail_seen": bool(trail_mask.any()),
        }
    )

    if not result["diag_covers_open_to_exit"]:
        result["diag_note"] = "diag window is sampled and may miss the broker stop tick"
    elif not result["diag_stop_side_touch_seen"]:
        result["diag_note"] = "diag covers the window and does not sample a stop-side touch before deal exit"
    else:
        result["diag_note"] = "diag samples stop-side touch before deal exit"
    return result


def review_case(case: pd.Series, trail: pd.Series, m15: pd.Series | None, diag: pd.DataFrame) -> dict[str, object]:
    open_time = parse_time(case.get("open_time"))
    exit_time = parse_time(case.get("exit_time"))
    actual_stop = float(case.get("actual_stop"))
    final_sim_sl = safe_float(trail.get("final_simulated_sl"))
    deal_sl = parse_sl_comment(case.get("deal_comment"))
    sl_kind, dist_initial, dist_final = classify_sl_price(deal_sl, actual_stop, final_sim_sl)

    diag_rows = diag_match(case, diag)
    diag_summary = summarize_diag(case, diag_rows)

    m15_has = False if m15 is None else bool_value(m15.get("m15_has_coverage"))
    m15_still = True if m15 is None else bool_value(m15.get("still_needs_tick"))
    m15_class = "" if m15 is None else str(m15.get("m15_refine_class", ""))
    m15_first_sl = pd.NaT if m15 is None else parse_time(m15.get("first_m15_broker_sl_bar"))
    m15_open_partial = False if m15 is None else bool_value(m15.get("open_partial_m15"))

    deal_after_open = bool(pd.notna(open_time) and pd.notna(exit_time) and exit_time > open_time)
    deal_reason = str(case.get("mt5_deal_reason", ""))
    partial_flags = [
        bool_value(trail.get("partial_open_initial_sl")),
        bool_value(trail.get("partial_open_trail_on")),
        bool_value(trail.get("partial_open_force")),
        bool_value(trail.get("partial_open_trail_sl")),
    ]
    partial_open_m30 = any(partial_flags)

    if deal_reason != "SL":
        review_class = "non_sl_not_reviewed"
        still_needs = True
        evidence = "MT5 deal reason is not SL"
    elif sl_kind == "trail_or_modified_sl_price" and diag_summary["diag_trail_seen"]:
        review_class = "resolved_as_trail_or_modified_sl_with_diag"
        still_needs = False
        evidence = "deal SL price is closer to simulated/modified SL and diag shows Stage2 trail activity"
    elif sl_kind == "trail_or_modified_sl_price":
        review_class = "modified_sl_price_needs_trail_ledger_or_tick"
        still_needs = True
        evidence = "deal SL price looks modified/trailing, but current evidence lacks the real SL modify path"
    elif sl_kind == "initial_sl_price" and m15_has and (not m15_open_partial) and (not m15_still):
        review_class = "resolved_as_initial_sl_after_open_with_m15"
        still_needs = False
        evidence = "deal SL matches initial stop and M15 ordering is not partial/tick-needed"
    elif sl_kind == "initial_sl_price" and diag_summary["diag_available"] and deal_after_open:
        review_class = "broker_initial_sl_confirmed_but_sequence_needs_tick"
        still_needs = True
        evidence = "deal confirms initial SL after open; sampled diag does not fully prove within-bar first-touch sequence"
    elif sl_kind == "initial_sl_price" and deal_after_open:
        review_class = "broker_initial_sl_confirmed_but_no_tick_source"
        still_needs = True
        evidence = "deal confirms initial SL after open, but no M15/diag coverage can prove the partial-open sequence"
    elif m15_has and not m15_still:
        review_class = "resolved_by_m15_but_sl_price_unclassified"
        still_needs = False
        evidence = "M15 ordering no longer needs tick, but SL price classification is not exact"
    else:
        review_class = "needs_exported_tick_or_tester_log"
        still_needs = True
        evidence = "current CSV/diag evidence cannot decide the partial-open sequence"

    return {
        "case_id": case.get("case_id"),
        "signal_anchor_time": case.get("signal_anchor_time"),
        "stage": int(case.get("stage")),
        "dir_norm": case.get("dir_norm"),
        "open_time": case.get("open_time"),
        "mt5_exit_time": case.get("exit_time"),
        "exit_relation": case.get("exit_relation"),
        "py_exit": case.get("py_exit"),
        "mt5_deal_reason": deal_reason,
        "deal_comment": case.get("deal_comment"),
        "deal_sl_price": deal_sl,
        "actual_stop": actual_stop,
        "final_simulated_sl": final_sim_sl,
        "deal_sl_kind": sl_kind,
        "deal_sl_dist_to_initial": dist_initial,
        "deal_sl_dist_to_final_sim": dist_final,
        "partial_open_m30": partial_open_m30,
        "partial_open_initial_sl": bool_value(trail.get("partial_open_initial_sl")),
        "partial_open_trail_on": bool_value(trail.get("partial_open_trail_on")),
        "m15_has_coverage": m15_has,
        "m15_refine_class": m15_class,
        "m15_first_broker_sl_bar": m15_first_sl,
        "m15_open_partial": m15_open_partial,
        "m15_still_needs_tick": m15_still,
        "deal_after_open": deal_after_open,
        **diag_summary,
        "partial_open_review_class": review_class,
        "review_evidence": evidence,
        "still_needs_tick_or_log": still_needs,
    }


def main() -> None:
    trail = read_csv(RUNTIME_DIR / "runtime_stage2_trail_refine.csv")
    cases = read_csv(RUNTIME_DIR / "runtime_stage_input_cases.csv")
    m15 = read_csv(RUNTIME_DIR / "runtime_stage_priority1_m15_refine.csv")
    # The ledger read is intentionally retained as a presence check for the
    # close-retry baseline used by runtime_stage_input_cases.
    ledger = read_csv(MT5_DIR / "30m2H_strategy_trade_ledger.csv")
    diag = load_diag_files()

    partial = trail[trail["needs_log_or_tick"].map(bool_value)].copy()
    case_lookup = {str(row["case_id"]): row for _, row in cases.iterrows()}
    m15_lookup = {str(row["case_id"]): row for _, row in m15.iterrows()}

    rows = []
    for _, trail_row in partial.sort_values("case_id").iterrows():
        case_id = str(trail_row["case_id"])
        case = case_lookup.get(case_id)
        if case is None:
            continue
        rows.append(review_case(case, trail_row, m15_lookup.get(case_id), diag))

    out = pd.DataFrame(rows)
    summary = (
        out.groupby(["partial_open_review_class", "still_needs_tick_or_log"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["still_needs_tick_or_log", "rows"], ascending=[True, False])
    )
    sl_summary = (
        out.groupby(["deal_sl_kind", "partial_open_review_class"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["deal_sl_kind", "rows"], ascending=[True, False])
    )

    out_path = RUNTIME_DIR / "runtime_stage2_partial_open_ticklog_review.csv"
    summary_path = RUNTIME_DIR / "runtime_stage2_partial_open_ticklog_summary.csv"
    sl_summary_path = RUNTIME_DIR / "runtime_stage2_partial_open_ticklog_sl_summary.csv"
    report_path = RUNTIME_DIR / "runtime_stage2_partial_open_ticklog_review.md"

    export_csv(out, out_path)
    export_csv(summary, summary_path)
    export_csv(sl_summary, sl_summary_path)

    resolved = int((~out["still_needs_tick_or_log"]).sum()) if not out.empty else 0
    still = int(out["still_needs_tick_or_log"].sum()) if not out.empty else 0
    diag_rows = int(out["diag_available"].sum()) if not out.empty else 0
    ledger_rows = len(ledger)

    report = [
        "# Runtime Stage2 Partial-Open Tick/Log Review",
        "",
        "## Scope",
        "",
        "- Input: `runtime_stage2_trail_refine.csv` rows with `needs_log_or_tick = True`.",
        "- Evidence used: close-retry MT5 ledger/deal comment, M15 refine output, and available EA stage price smoke diagnostics.",
        "- This is still not an exported tick replay or full tester journal parser.",
        "",
        "## Key Counts",
        "",
        f"- Reviewed partial-open Stage2 cases: `{len(out)}`.",
        f"- Resolved without new tick/log export: `{resolved}`.",
        f"- Still needs exported tick/tester log: `{still}`.",
        f"- Cases with matching stage-price diag rows: `{diag_rows}`.",
        f"- Close-retry ledger rows checked: `{ledger_rows}`.",
        "",
        "## Review Summary",
        "",
        summary.to_markdown(index=False) if not summary.empty else "_No rows_",
        "",
        "## SL Price Summary",
        "",
        sl_summary.to_markdown(index=False) if not sl_summary.empty else "_No rows_",
        "",
        "## Notes",
        "",
        "- `broker_initial_sl_confirmed_*` means the MT5 deal itself confirms a broker SL after open, but current data still cannot prove the exact first-touch order inside the opening bar.",
        "- `resolved_as_trail_or_modified_sl_*` means the deal SL price is closer to the simulated/modified SL than to the initial SL; this removes it from the initial-SL partial-open bucket.",
        "- Remaining `still_needs_tick_or_log = True` rows require exported MT5 ticks or tester journal around the open/exit window.",
        "",
        "## Output Files",
        "",
        "- `runtime_stage2_partial_open_ticklog_review.csv`",
        "- `runtime_stage2_partial_open_ticklog_summary.csv`",
        "- `runtime_stage2_partial_open_ticklog_sl_summary.csv`",
    ]
    write_text(report_path, "\n".join(report))

    print(summary.to_string(index=False))
    print()
    print(sl_summary.to_string(index=False))
    print(f"\nWrote {RUNTIME_DIR}")


if __name__ == "__main__":
    main()
