# -*- coding: utf-8 -*-
"""Stage2 trailing-SL refinement for runtime-style exit analysis.

This script models Stage2 trail-on and SMA13 SL ratcheting with M30 bars. It is
diagnostic only and does not claim tick-order equivalence.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
RUNTIME_DIR = DATA_DIR / "validation" / "python_runtime_stage_exit_prototype_20260714"
M30_PATH = DATA_DIR / "processed" / "m30_mt5.csv"

STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def load_m30() -> pd.DataFrame:
    df = pd.read_csv(M30_PATH, encoding="utf-8-sig")
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    for col in ["open", "high", "low", "close", "SMA_5", "SMA_13"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def floor_30(ts: pd.Timestamp) -> pd.Timestamp:
    return ts.floor("30min")


def target_price(direction: str, entry: float, risk: float, multiple: float) -> float:
    return entry - risk * multiple if direction == "SELL" else entry + risk * multiple


def touched_sl(direction: str, bar: pd.Series, sl: float) -> bool:
    return float(bar["high"]) >= sl if direction == "SELL" else float(bar["low"]) <= sl


def touched_favorable(direction: str, bar: pd.Series, price: float) -> bool:
    return float(bar["low"]) <= price if direction == "SELL" else float(bar["high"]) >= price


def improve_sl(direction: str, current_sl: float, sma13: float) -> tuple[float, bool]:
    if pd.isna(sma13) or sma13 <= 0:
        return current_sl, False
    new_sl = current_sl
    if direction == "SELL" and sma13 < current_sl:
        new_sl = round(float(sma13), 5)
    elif direction == "BUY" and sma13 > current_sl:
        new_sl = round(float(sma13), 5)
    return new_sl, abs(new_sl - current_sl) >= 0.001


def classify(row: dict[str, object]) -> tuple[str, str, bool]:
    mt5_reason = str(row["mt5_deal_reason"])
    if not bool(row["m30_has_coverage"]):
        return "no_m30_coverage", "M30 data does not cover the case window", True

    if mt5_reason != "SL":
        return "non_sl_stage2_case", "MT5 Stage2 is not broker SL", True

    mt5_exit = pd.to_datetime(row["mt5_exit_time"], errors="coerce")
    initial_touch = pd.to_datetime(row["first_initial_sl_touch_bar"], errors="coerce")
    force_bar = pd.to_datetime(row["first_force_bar"], errors="coerce")
    trail_on = pd.to_datetime(row["trail_on_bar"], errors="coerce")
    trail_touch = pd.to_datetime(row["first_trail_sl_touch_bar"], errors="coerce")

    if pd.notna(initial_touch) and initial_touch <= mt5_exit.floor("30min"):
        if pd.isna(force_bar) or initial_touch <= force_bar:
            return "initial_sl_before_force", "Initial broker SL is touched before any forced exit bar", False

    if pd.notna(force_bar) and force_bar < mt5_exit.floor("30min"):
        return "force_before_mt5_sl_needs_session_log", "4R force appears before MT5 SL; need close/session log", True

    if pd.notna(trail_on) and pd.isna(trail_touch):
        return "trail_on_no_trail_sl_touch_before_exit", "Trail-on occurs but simulated trail SL is not touched before MT5 exit", True

    if pd.notna(trail_touch):
        if trail_touch <= mt5_exit.floor("30min"):
            return "trail_sl_touch_before_or_at_mt5_sl", "Simulated trail SL touch occurs before/at MT5 SL bar", False
        return "mt5_sl_before_simulated_trail_sl", "MT5 SL occurs before simulated trail SL touch", True

    if pd.isna(trail_on):
        return "sl_before_trail_on_or_no_trail", "No trail-on before MT5 SL in M30 simulation", False

    return "undetermined_stage2_trail", "Unable to classify Stage2 trail ordering", True


def is_partial_open_event(event_time: pd.Timestamp | pd.NaT, open_time: pd.Timestamp) -> bool:
    if pd.isna(event_time) or pd.isna(open_time):
        return False
    event_time = pd.to_datetime(event_time)
    return event_time == floor_30(open_time) and open_time > event_time


def refine_case(case: pd.Series, m15_row: pd.Series | None, m30: pd.DataFrame) -> dict[str, object]:
    case_id = str(case["case_id"])
    direction = str(case["dir_norm"]).upper()
    open_time = pd.to_datetime(case["open_time"], errors="coerce")
    mt5_exit = pd.to_datetime(case["exit_time"], errors="coerce")
    entry = float(case["fill_price"])
    orig_sl = float(case["actual_stop"])
    risk = abs(entry - orig_sl)
    start = floor_30(open_time)
    end = mt5_exit + pd.Timedelta(days=3)
    bars = m30[(m30["date"] >= start) & (m30["date"] <= end)].copy()
    bars = bars.sort_values("date").reset_index(drop=True)

    force_target = target_price(direction, entry, risk, STAGE2_FORCE_R)
    trail_target = target_price(direction, entry, risk, STAGE2_TRAIL_R)

    current_sl = orig_sl
    trail_on = False
    trail_on_bar = pd.NaT
    first_force_bar = pd.NaT
    first_initial_sl_touch = pd.NaT
    first_trail_sl_touch = pd.NaT
    updates: list[str] = []
    same_bar_notes: list[str] = []

    for _, bar in bars.iterrows():
        t = pd.to_datetime(bar["date"])
        if pd.isna(first_initial_sl_touch) and touched_sl(direction, bar, orig_sl):
            first_initial_sl_touch = t

        if trail_on and pd.isna(first_trail_sl_touch) and touched_sl(direction, bar, current_sl):
            first_trail_sl_touch = t

        force_hit = touched_favorable(direction, bar, force_target)
        trail_hit = touched_favorable(direction, bar, trail_target)

        if pd.isna(first_force_bar) and force_hit:
            first_force_bar = t

        if (not trail_on) and trail_hit:
            trail_on = True
            trail_on_bar = t

        if trail_on:
            new_sl, changed = improve_sl(direction, current_sl, float(bar["SMA_13"]))
            if changed:
                updates.append(f"{t:%Y-%m-%d %H:%M}: {current_sl:.5f}->{new_sl:.5f}")
                current_sl = new_sl

        event_count = sum(
            [
                pd.notna(first_initial_sl_touch) and first_initial_sl_touch == t,
                pd.notna(first_force_bar) and first_force_bar == t,
                pd.notna(trail_on_bar) and trail_on_bar == t,
                pd.notna(first_trail_sl_touch) and first_trail_sl_touch == t,
            ]
        )
        if event_count > 1:
            same_bar_notes.append(f"{t:%Y-%m-%d %H:%M}")

    mt5_exit_price = float(case["exit_price"]) if pd.notna(case.get("exit_price")) else float("nan")
    dist_to_orig = abs(mt5_exit_price - orig_sl) if pd.notna(mt5_exit_price) else float("nan")
    dist_to_final_sim_sl = abs(mt5_exit_price - current_sl) if pd.notna(mt5_exit_price) else float("nan")
    partial_initial = is_partial_open_event(first_initial_sl_touch, open_time)
    partial_trail_on = is_partial_open_event(trail_on_bar, open_time)
    partial_force = is_partial_open_event(first_force_bar, open_time)
    partial_trail_sl = is_partial_open_event(first_trail_sl_touch, open_time)

    row = {
        "case_id": case_id,
        "py_trade_id": case.get("py_trade_id"),
        "mt5_trade_id": case.get("mt5_trade_id"),
        "stage": int(case["stage"]),
        "dir_norm": direction,
        "open_time": case.get("open_time"),
        "mt5_exit_time": case.get("exit_time"),
        "mt5_deal_reason": case.get("mt5_deal_reason"),
        "mt5_local_exit_reason": case.get("mt5_local_exit_reason"),
        "py_exit": case.get("py_exit"),
        "exit_relation": case.get("exit_relation"),
        "entry": entry,
        "orig_sl": orig_sl,
        "mt5_exit_price": mt5_exit_price,
        "risk": risk,
        "trail_target_1_5r": trail_target,
        "force_target_4r": force_target,
        "m30_has_coverage": bool(not bars.empty),
        "m30_rows_scanned": int(len(bars)),
        "first_initial_sl_touch_bar": first_initial_sl_touch,
        "trail_on_bar": trail_on_bar,
        "first_force_bar": first_force_bar,
        "first_trail_sl_touch_bar": first_trail_sl_touch,
        "trail_update_count": len(updates),
        "trail_updates_sample": "; ".join(updates[:8]),
        "final_simulated_sl": current_sl,
        "mt5_exit_dist_to_orig_sl": dist_to_orig,
        "mt5_exit_dist_to_final_sim_sl": dist_to_final_sim_sl,
        "same_m30_event_bars": "; ".join(same_bar_notes[:8]),
        "partial_open_initial_sl": partial_initial,
        "partial_open_trail_on": partial_trail_on,
        "partial_open_force": partial_force,
        "partial_open_trail_sl": partial_trail_sl,
        "m15_refine_class": "" if m15_row is None else m15_row.get("m15_refine_class"),
        "m15_still_needs_tick": "" if m15_row is None else m15_row.get("still_needs_tick"),
    }
    refine_class, reason, needs_log = classify(row)
    row["stage2_trail_refine_class"] = refine_class
    row["stage2_trail_refine_reason"] = reason
    row["needs_log_or_tick"] = bool(
        needs_log
        or len(same_bar_notes) > 0
        or partial_initial
        or partial_trail_on
        or partial_force
        or partial_trail_sl
    )
    return row


def main() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    cases = pd.read_csv(RUNTIME_DIR / "runtime_stage_input_cases.csv", encoding="utf-8-sig")
    m15_refine = pd.read_csv(RUNTIME_DIR / "runtime_stage_priority1_m15_refine.csv", encoding="utf-8-sig")
    m30 = load_m30()

    stage2 = cases[(cases["runtime_priority"] == 1) & (cases["stage"] == 2)].copy()
    m15_lookup = {str(row["case_id"]): row for _, row in m15_refine.iterrows()}

    rows = [
        refine_case(case, m15_lookup.get(str(case["case_id"])), m30)
        for _, case in stage2.sort_values("case_id").iterrows()
    ]
    out = pd.DataFrame(rows)

    summary = (
        out.groupby(["stage2_trail_refine_class", "needs_log_or_tick"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values("rows", ascending=False)
    )
    relation_summary = (
        out.groupby(["exit_relation", "stage2_trail_refine_class", "needs_log_or_tick"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["exit_relation", "rows"], ascending=[True, False])
    )

    export_csv(out, RUNTIME_DIR / "runtime_stage2_trail_refine.csv")
    export_csv(summary, RUNTIME_DIR / "runtime_stage2_trail_refine_summary.csv")
    export_csv(relation_summary, RUNTIME_DIR / "runtime_stage2_trail_refine_by_relation.csv")

    needs = int(out["needs_log_or_tick"].sum()) if not out.empty else 0
    partial = int(
        (
            out["partial_open_initial_sl"]
            | out["partial_open_trail_on"]
            | out["partial_open_force"]
            | out["partial_open_trail_sl"]
        ).sum()
    ) if not out.empty else 0
    initial_first = int((out["stage2_trail_refine_class"] == "initial_sl_before_force").sum()) if not out.empty else 0
    force_before = int((out["stage2_trail_refine_class"] == "force_before_mt5_sl_needs_session_log").sum()) if not out.empty else 0
    trail_touch = int((out["stage2_trail_refine_class"] == "trail_sl_touch_before_or_at_mt5_sl").sum()) if not out.empty else 0

    report = [
        "# Runtime Stage2 Trail Refine",
        "",
        "## Scope",
        "",
        "- Input: Priority 1 Stage2 cases from `runtime_stage_input_cases.csv`.",
        "- Market data: `data/processed/m30_mt5.csv`.",
        "- Trail model: after 1.5R, SELL trail SL ratchets down to M30 SMA13; BUY trail SL ratchets up to M30 SMA13.",
        "- This is M30 bar-level diagnostic logic, not tick/order-log equivalent.",
        "",
        "## Key Counts",
        "",
        f"- Stage2 cases: `{len(out)}`.",
        f"- Initial SL before force: `{initial_first}`.",
        f"- Trail SL touch before/at MT5 SL bar: `{trail_touch}`.",
        f"- Force before MT5 SL, session/log needed: `{force_before}`.",
        f"- First event in partial opening M30 bar: `{partial}`.",
        f"- Need log/tick after refine: `{needs}`.",
        "",
        "## Summary",
        "",
        summary.to_markdown(index=False) if not summary.empty else "_No rows_",
        "",
        "## Relation Summary",
        "",
        relation_summary.to_markdown(index=False) if not relation_summary.empty else "_No rows_",
        "",
        "## Output Files",
        "",
        "- `runtime_stage2_trail_refine.csv`",
        "- `runtime_stage2_trail_refine_summary.csv`",
        "- `runtime_stage2_trail_refine_by_relation.csv`",
    ]
    write_text(RUNTIME_DIR / "runtime_stage2_trail_refine_report.md", "\n".join(report))

    print(summary.to_string(index=False))
    print()
    print(relation_summary.to_string(index=False))
    print(f"\nWrote {RUNTIME_DIR}")


if __name__ == "__main__":
    main()
