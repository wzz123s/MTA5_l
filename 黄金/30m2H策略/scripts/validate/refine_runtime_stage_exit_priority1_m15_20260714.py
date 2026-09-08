# -*- coding: utf-8 -*-
"""M15 refinement for Priority 1 runtime-style Stage exit replay.

This narrows M30 same-bar uncertainty with M15 OHLC. It still is not a tick
replay: if the MT5 exit and a Python-style event fall inside the same M15 bar,
the case remains tick-needed.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
RUNTIME_DIR = DATA_DIR / "validation" / "python_runtime_stage_exit_prototype_20260714"
M15_PATH = DATA_DIR / "processed" / "m15_context_bars.csv"

STAGE1_R = 2.0
STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def load_m15() -> pd.DataFrame:
    df = pd.read_csv(M15_PATH, encoding="utf-8-sig")
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["open", "high", "low", "close", "SMA_5", "SMA_13"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def floor_15min(ts: pd.Timestamp) -> pd.Timestamp:
    return ts.floor("15min")


def bar_end(ts: pd.Timestamp) -> pd.Timestamp:
    return ts + pd.Timedelta(minutes=15)


def target_price(direction: str, entry: float, risk: float, multiple: float) -> float:
    return entry - risk * multiple if direction == "SELL" else entry + risk * multiple


def touched_sl(direction: str, bar: pd.Series, sl: float) -> bool:
    return float(bar["high"]) >= sl if direction == "SELL" else float(bar["low"]) <= sl


def touched_favorable(direction: str, bar: pd.Series, price: float) -> bool:
    return float(bar["low"]) <= price if direction == "SELL" else float(bar["high"]) >= price


def first_bar_time(frame: pd.DataFrame, mask: pd.Series) -> pd.Timestamp | pd.NaT:
    hits = frame[mask].copy()
    if hits.empty:
        return pd.NaT
    return pd.to_datetime(hits["date"].iloc[0])


def classify_refine(row: pd.Series) -> tuple[str, str, bool]:
    mt5_reason = str(row["mt5_deal_reason"])
    if not bool(row["m15_has_coverage"]):
        return "no_m15_coverage", "M15 data does not cover the case window", True

    stage = int(row.get("stage", 0))
    py_event_name = str(row.get("first_m15_python_event_name", ""))
    if stage == 3:
        if mt5_reason == "SL" and pd.notna(row["first_m15_broker_sl_bar"]):
            return "stage3_m15_sl_seen_cross_not_refined", "M15 confirms broker SL touch, but M30 cross chronology is not refined here", True
        return "stage3_cross_not_refined_by_m15", "M15 does not refine M30 Stage3 cross chronology", True

    if stage == 2 and py_event_name == "stage2_trail_on":
        if mt5_reason == "SL":
            mt5_exit_time = pd.to_datetime(row["mt5_exit_time"], errors="coerce")
            trail_time = pd.to_datetime(row["first_m15_python_event_bar"], errors="coerce")
            if pd.notna(trail_time) and mt5_exit_time < trail_time:
                return "mt5_sl_before_stage2_trail_on", "MT5 SL occurs before Stage2 trail-on threshold", False
            return "stage2_trail_on_before_sl_needs_trail_model", "Trail-on occurs before MT5 SL; trailing SL path needs explicit modeling", True

    if mt5_reason != "SL":
        if pd.notna(row["first_m15_broker_sl_bar"]):
            return "non_sl_case_m15_sl_seen", "MT5 exit is not SL; M15 SL touch cannot decide without tick/log detail", True
        return "non_sl_case_no_m15_sl", "MT5 exit is not SL and no M15 SL touch was observed", True

    mt5_exit_time = pd.to_datetime(row["mt5_exit_time"], errors="coerce")
    first_py_event = pd.to_datetime(row["first_m15_python_event_bar"], errors="coerce")

    if pd.isna(first_py_event):
        return "mt5_sl_before_no_python_event", "MT5 SL exists and no Python-style M15 event was observed", False

    if mt5_exit_time < first_py_event:
        return "mt5_sl_before_python_event", "MT5 SL time is before the first Python-style M15 event bar", False

    if first_py_event <= mt5_exit_time < bar_end(first_py_event):
        return "same_m15_bar_order_unknown", "MT5 SL and Python-style event fall in the same M15 bar", True

    if mt5_exit_time >= bar_end(first_py_event):
        return "python_event_before_mt5_sl", "Python-style M15 event bar completes before MT5 SL time", False

    return "undetermined", "Unable to classify M15 ordering", True


def refine_case(case: pd.Series, replay: pd.Series, m15: pd.DataFrame) -> dict[str, object]:
    case_id = str(case["case_id"])
    stage = int(case["stage"])
    direction = str(case["dir_norm"]).upper()
    open_time = pd.to_datetime(case["open_time"], errors="coerce")
    mt5_exit_time = pd.to_datetime(case["exit_time"], errors="coerce")
    entry = float(case["fill_price"])
    orig_sl = float(case["actual_stop"])
    risk = abs(entry - orig_sl)
    start_time = floor_15min(open_time)
    end_time = mt5_exit_time + pd.Timedelta(days=3)
    bars = m15[(m15["date"] >= start_time) & (m15["date"] <= end_time)].copy()
    bars = bars.sort_values("date").reset_index(drop=True)

    has_coverage = not bars.empty and pd.to_datetime(bars["date"].iloc[0]) <= start_time
    first_sl = pd.NaT
    first_stage1_tp = pd.NaT
    first_stage2_trail = pd.NaT
    first_stage2_force = pd.NaT
    first_python_event = pd.NaT
    first_python_event_name = ""

    if has_coverage:
        sl_mask = bars.apply(lambda b: touched_sl(direction, b, orig_sl), axis=1)
        first_sl = first_bar_time(bars, sl_mask)

        if stage == 1:
            tp = target_price(direction, entry, risk, STAGE1_R)
            mask = bars.apply(lambda b: touched_favorable(direction, b, tp), axis=1)
            first_stage1_tp = first_bar_time(bars, mask)
            first_python_event = first_stage1_tp
            first_python_event_name = "stage1_tp" if pd.notna(first_python_event) else ""

        elif stage == 2:
            trail = target_price(direction, entry, risk, STAGE2_TRAIL_R)
            force = target_price(direction, entry, risk, STAGE2_FORCE_R)
            trail_mask = bars.apply(lambda b: touched_favorable(direction, b, trail), axis=1)
            force_mask = bars.apply(lambda b: touched_favorable(direction, b, force), axis=1)
            first_stage2_trail = first_bar_time(bars, trail_mask)
            first_stage2_force = first_bar_time(bars, force_mask)
            py_exit = str(case.get("py_exit", ""))
            relation = str(case.get("exit_relation", ""))
            if "4.0R forced" in py_exit or relation == "py_forced_mt5_sl":
                first_python_event = first_stage2_force
                first_python_event_name = "stage2_force" if pd.notna(first_python_event) else ""
            elif "trail/SL" in py_exit or relation == "both_stop_or_trail":
                first_python_event = first_stage2_trail
                first_python_event_name = "stage2_trail_on" if pd.notna(first_python_event) else ""
            else:
                first_python_event = pd.NaT
                first_python_event_name = "stage2_cross_not_refined_by_m15"

        elif stage == 3:
            # M15 cannot reproduce M30 SMA5/13 reverse-cross chronology.
            first_python_event = pd.NaT
            first_python_event_name = "stage3_cross_not_refined_by_m15"

    open_partial_m15 = bool(pd.notna(first_sl) and first_sl == start_time and open_time > start_time)
    py_event_partial_m15 = bool(pd.notna(first_python_event) and first_python_event == start_time and open_time > start_time)

    temp = {
        "m15_has_coverage": bool(has_coverage),
        "mt5_deal_reason": case.get("mt5_deal_reason"),
        "stage": stage,
        "mt5_exit_time": case.get("exit_time"),
        "first_m15_broker_sl_bar": first_sl,
        "first_m15_python_event_bar": first_python_event,
        "first_m15_python_event_name": first_python_event_name,
    }
    refine_class, refine_reason, still_needs_tick = classify_refine(pd.Series(temp))
    still_needs_tick = bool(still_needs_tick or open_partial_m15 or py_event_partial_m15)

    return {
        "case_id": case_id,
        "stage": stage,
        "dir_norm": direction,
        "open_time": case.get("open_time"),
        "mt5_exit_time": case.get("exit_time"),
        "mt5_deal_reason": case.get("mt5_deal_reason"),
        "exit_relation": case.get("exit_relation"),
        "m30_predicted_runtime_class": replay.get("predicted_runtime_class"),
        "m30_explains_mt5_sl": replay.get("explains_mt5_sl"),
        "m30_needs_tick_for_order": replay.get("needs_tick_for_order"),
        "m15_has_coverage": bool(has_coverage),
        "m15_rows_scanned": int(len(bars)),
        "m15_window_start": start_time,
        "m15_window_end": end_time,
        "first_m15_broker_sl_bar": first_sl,
        "first_m15_stage1_tp_bar": first_stage1_tp,
        "first_m15_stage2_trail_on_bar": first_stage2_trail,
        "first_m15_stage2_force_bar": first_stage2_force,
        "first_m15_python_event_bar": first_python_event,
        "first_m15_python_event_name": first_python_event_name,
        "open_partial_m15": open_partial_m15,
        "py_event_partial_m15": py_event_partial_m15,
        "m15_refine_class": refine_class,
        "m15_refine_reason": refine_reason,
        "still_needs_tick": still_needs_tick,
        "py_exit": case.get("py_exit"),
        "stage_profit_diff": case.get("stage_profit_diff"),
        "sign_pair": case.get("sign_pair"),
    }


def main() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    cases = pd.read_csv(RUNTIME_DIR / "runtime_stage_input_cases.csv", encoding="utf-8-sig")
    replay = pd.read_csv(RUNTIME_DIR / "runtime_stage_priority1_replay.csv", encoding="utf-8-sig")
    m15 = load_m15()

    replay_lookup = {str(row["case_id"]): row for _, row in replay.iterrows()}
    target_ids = set(
        replay[
            replay["needs_tick_for_order"].astype(str).str.lower().isin({"true", "1"})
        ]["case_id"].astype(str)
    )
    target_ids.update({"runtime_stage_case_004", "runtime_stage_case_007"})

    target_cases = cases[cases["case_id"].astype(str).isin(target_ids)].copy()
    target_cases = target_cases.sort_values(["case_id"]).reset_index(drop=True)

    rows = [
        refine_case(case, replay_lookup[str(case["case_id"])], m15)
        for _, case in target_cases.iterrows()
        if str(case["case_id"]) in replay_lookup
    ]
    out = pd.DataFrame(rows)

    summary = (
        out.groupby(["m15_refine_class", "still_needs_tick", "m15_has_coverage"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values("rows", ascending=False)
    )
    by_stage = (
        out.groupby(["stage", "exit_relation", "m15_refine_class", "still_needs_tick"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["stage", "exit_relation", "rows"], ascending=[True, True, False])
    )

    export_csv(out, RUNTIME_DIR / "runtime_stage_priority1_m15_refine.csv")
    export_csv(summary, RUNTIME_DIR / "runtime_stage_priority1_m15_refine_summary.csv")
    export_csv(by_stage, RUNTIME_DIR / "runtime_stage_priority1_m15_refine_by_stage.csv")

    covered = int(out["m15_has_coverage"].sum()) if not out.empty else 0
    total = int(len(out))
    mt5_sl_before = int((out["m15_refine_class"] == "mt5_sl_before_python_event").sum()) if not out.empty else 0
    mt5_sl_before_no_python = int((out["m15_refine_class"] == "mt5_sl_before_no_python_event").sum()) if not out.empty else 0
    mt5_sl_before_trail = int((out["m15_refine_class"] == "mt5_sl_before_stage2_trail_on").sum()) if not out.empty else 0
    stage3_sl_seen = int((out["m15_refine_class"] == "stage3_m15_sl_seen_cross_not_refined").sum()) if not out.empty else 0
    still_tick = int(out["still_needs_tick"].sum()) if not out.empty else 0
    resolved_by_m15 = total - still_tick
    same_bar = int((out["m15_refine_class"] == "same_m15_bar_order_unknown").sum()) if not out.empty else 0
    no_coverage = int((out["m15_refine_class"] == "no_m15_coverage").sum()) if not out.empty else 0

    report = [
        "# Runtime-Style Stage Exit Priority 1 M15 Refine",
        "",
        "## Scope",
        "",
        "- Input: `runtime_stage_priority1_replay.csv` cases with `needs_tick_for_order = True`, plus `runtime_stage_case_004` and `runtime_stage_case_007`.",
        "- Market data: `data/processed/m15_context_bars.csv`.",
        "- This is still OHLC bar-level replay, not tick replay.",
        "",
        "## Key Counts",
        "",
        f"- Refined cases: `{total}`.",
        f"- M15-covered cases: `{covered}`.",
        f"- No M15 coverage: `{no_coverage}`.",
        f"- Still tick/log-needed after M15 refine: `{still_tick}`.",
        f"- Resolved by M15 bar ordering: `{resolved_by_m15}`.",
        f"- MT5 SL before Python-style M15 event: `{mt5_sl_before}`.",
        f"- MT5 SL before any selected Python-style M15 event: `{mt5_sl_before_no_python}`.",
        f"- MT5 SL before Stage2 trail-on threshold: `{mt5_sl_before_trail}`.",
        f"- Stage3 M15 SL seen but M30 cross not refined: `{stage3_sl_seen}`.",
        f"- Same M15 bar order still unknown: `{same_bar}`.",
        "",
        "## Overall Summary",
        "",
        summary.to_markdown(index=False) if not summary.empty else "_No rows_",
        "",
        "## Stage Summary",
        "",
        by_stage.to_markdown(index=False) if not by_stage.empty else "_No rows_",
        "",
        "## Notes",
        "",
        "- 2020/2021 and early 2022 cases are outside current M15 processed coverage and remain tick/log-needed.",
        "- A same-M15-bar result means M15 narrowed the uncertainty but cannot determine tick order.",
        "- Stage3 M30 cross chronology is not recomputed from M15; M15 only refines broker SL timing around the case.",
        "",
        "## Output Files",
        "",
        "- `runtime_stage_priority1_m15_refine.csv`",
        "- `runtime_stage_priority1_m15_refine_summary.csv`",
        "- `runtime_stage_priority1_m15_refine_by_stage.csv`",
    ]
    write_text(RUNTIME_DIR / "runtime_stage_priority1_m15_refine_report.md", "\n".join(report))

    print(summary.to_string(index=False))
    print()
    print(by_stage.to_string(index=False))
    print(f"\nWrote {RUNTIME_DIR}")


if __name__ == "__main__":
    main()
