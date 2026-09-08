# -*- coding: utf-8 -*-
"""M30-approx runtime-style replay for Priority 1 Stage exit cases.

This is intentionally not a tick-equivalent simulator. It uses M30 OHLC and
SMA values to test whether broker SL can plausibly occur before Python's
bar-level TP/forced/cross exit for the highest-priority mismatch cases.
"""
from __future__ import annotations


from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
RUNTIME_DIR = DATA_DIR / "validation" / "python_runtime_stage_exit_prototype_20260714"
M30_PATH = DATA_DIR / "processed" / "m30_mt5.csv"

STAGE1_R = 2.0
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


def floor_30min(ts: pd.Timestamp) -> pd.Timestamp:
    return ts.floor("30min")


def add_event(events: list[dict[str, object]], event: str, bar: pd.Series, detail: str) -> None:
    events.append(
        {
            "event": event,
            "bar_time": bar["date"],
            "bar_high": bar["high"],
            "bar_low": bar["low"],
            "bar_close": bar["close"],
            "bar_sma5": bar.get("SMA_5"),
            "bar_sma13": bar.get("SMA_13"),
            "detail": detail,
        }
    )


def touched_sl(direction: str, bar: pd.Series, sl: float) -> bool:
    if direction == "SELL":
        return float(bar["high"]) >= sl
    return float(bar["low"]) <= sl


def touched_favorable(direction: str, bar: pd.Series, price: float) -> bool:
    if direction == "SELL":
        return float(bar["low"]) <= price
    return float(bar["high"]) >= price


def target_price(direction: str, entry: float, risk: float, multiple: float) -> float:
    if direction == "SELL":
        return entry - risk * multiple
    return entry + risk * multiple


def maybe_reverse_cross(direction: str, prev: pd.Series | None, curr: pd.Series) -> bool:
    if prev is None:
        return False
    if pd.isna(prev.get("SMA_5")) or pd.isna(prev.get("SMA_13")):
        return False
    if pd.isna(curr.get("SMA_5")) or pd.isna(curr.get("SMA_13")):
        return False
    prev_above = float(prev["SMA_5"]) > float(prev["SMA_13"])
    curr_above = float(curr["SMA_5"]) > float(curr["SMA_13"])
    just_good = (not prev_above) and curr_above
    just_bad = prev_above and (not curr_above)
    return (direction == "BUY" and just_bad) or (direction == "SELL" and just_good)


def first_bar_events(events: Iterable[dict[str, object]]) -> tuple[pd.Timestamp | None, list[dict[str, object]]]:
    event_list = list(events)
    if not event_list:
        return None, []
    first_time = min(pd.to_datetime(e["bar_time"]) for e in event_list)
    first = [e for e in event_list if pd.to_datetime(e["bar_time"]) == first_time]
    return first_time, first


def classify_prediction(first_events: list[dict[str, object]], stage: int) -> str:
    if not first_events:
        return "no_m30_event"
    names = {str(e["event"]) for e in first_events}
    if "broker_sl" in names and len(names) > 1:
        return "ambiguous_same_bar_with_broker_sl"
    if "broker_sl" in names:
        return "broker_sl_first"
    if stage == 1 and "stage1_tp" in names:
        return "stage1_tp_first"
    if stage == 2 and "stage2_force" in names:
        return "stage2_force_first"
    if stage == 2 and "stage2_trail_on" in names:
        return "stage2_trail_on_first"
    if stage == 2 and "stage2_trailing_sl" in names:
        return "stage2_trailing_sl_first"
    if stage == 3 and "stage3_cross" in names:
        return "stage3_cross_first"
    return "other_first"


def replay_case(row: pd.Series, m30: pd.DataFrame) -> dict[str, object]:
    case_id = str(row["case_id"])
    stage = int(row["stage"])
    direction = str(row["dir_norm"]).upper()
    open_time = pd.to_datetime(row["open_time"], errors="coerce")
    mt5_exit_time = pd.to_datetime(row["exit_time"], errors="coerce")
    entry = float(row["fill_price"])
    orig_sl = float(row["actual_stop"])
    risk = abs(entry - orig_sl)
    start_time = floor_30min(open_time)

    end_time = mt5_exit_time + pd.Timedelta(days=3)
    bars = m30[(m30["date"] >= start_time) & (m30["date"] <= end_time)].copy()
    bars = bars.sort_values("date").reset_index(drop=True)

    current_sl = orig_sl
    trail_on = False
    events: list[dict[str, object]] = []
    trail_on_time = pd.NaT
    trail_sl_updates: list[str] = []

    prev_bar: pd.Series | None = None
    for _, bar in bars.iterrows():
        bar_time = pd.to_datetime(bar["date"])
        is_open_partial_bar = bar_time == start_time and open_time > start_time

        if touched_sl(direction, bar, current_sl):
            add_event(
                events,
                "broker_sl" if not trail_on else "stage2_trailing_sl",
                bar,
                f"sl={current_sl:.5f}; partial_open_bar={is_open_partial_bar}",
            )

        if stage == 1:
            tp = target_price(direction, entry, risk, STAGE1_R)
            if touched_favorable(direction, bar, tp):
                add_event(events, "stage1_tp", bar, f"target={tp:.5f}; partial_open_bar={is_open_partial_bar}")

        elif stage == 2:
            force = target_price(direction, entry, risk, STAGE2_FORCE_R)
            trail = target_price(direction, entry, risk, STAGE2_TRAIL_R)
            if touched_favorable(direction, bar, force):
                add_event(events, "stage2_force", bar, f"target={force:.5f}; partial_open_bar={is_open_partial_bar}")
            if (not trail_on) and touched_favorable(direction, bar, trail):
                trail_on = True
                trail_on_time = bar_time
                add_event(events, "stage2_trail_on", bar, f"target={trail:.5f}; partial_open_bar={is_open_partial_bar}")
            if trail_on and pd.notna(bar.get("SMA_13")):
                sma13 = float(bar["SMA_13"])
                old_sl = current_sl
                if direction == "SELL" and sma13 < current_sl:
                    current_sl = sma13
                elif direction == "BUY" and sma13 > current_sl:
                    current_sl = sma13
                if current_sl != old_sl:
                    trail_sl_updates.append(f"{bar_time:%Y-%m-%d %H:%M}: {old_sl:.5f}->{current_sl:.5f}")

        elif stage == 3:
            if maybe_reverse_cross(direction, prev_bar, bar):
                add_event(events, "stage3_cross", bar, f"partial_open_bar={is_open_partial_bar}")

        prev_bar = bar

    first_time, first = first_bar_events(events)
    predicted = classify_prediction(first, stage)
    first_event_names = ",".join(str(e["event"]) for e in first)
    first_details = " | ".join(str(e["detail"]) for e in first)

    mt5_reason = str(row.get("mt5_deal_reason", ""))
    mt5_is_sl = mt5_reason == "SL"
    explains_mt5_sl = mt5_is_sl and predicted in {
        "broker_sl_first",
        "ambiguous_same_bar_with_broker_sl",
        "stage2_trailing_sl_first",
    }
    contradicts_mt5_sl = mt5_is_sl and predicted in {
        "stage1_tp_first",
        "stage2_force_first",
        "stage3_cross_first",
    }
    needs_tick = predicted == "ambiguous_same_bar_with_broker_sl" or bool(
        first and any("partial_open_bar=True" in str(e["detail"]) for e in first)
    )

    return {
        "case_id": case_id,
        "py_trade_id": row.get("py_trade_id"),
        "mt5_trade_id": row.get("mt5_trade_id"),
        "runtime_priority_reason": row.get("runtime_priority_reason"),
        "stage": stage,
        "dir_norm": direction,
        "open_time": row.get("open_time"),
        "mt5_exit_time": row.get("exit_time"),
        "entry": entry,
        "orig_sl": orig_sl,
        "risk": risk,
        "py_exit": row.get("py_exit"),
        "mt5_local_exit_reason": row.get("mt5_local_exit_reason"),
        "mt5_deal_reason": mt5_reason,
        "exit_relation": row.get("exit_relation"),
        "m30_bars_scanned": len(bars),
        "first_m30_event_time": first_time,
        "first_m30_event_names": first_event_names,
        "first_m30_event_details": first_details,
        "predicted_runtime_class": predicted,
        "explains_mt5_sl": explains_mt5_sl,
        "contradicts_mt5_sl": contradicts_mt5_sl,
        "needs_tick_for_order": needs_tick,
        "trail_on_time": trail_on_time,
        "final_simulated_sl": current_sl,
        "trail_sl_update_count": len(trail_sl_updates),
        "trail_sl_updates_sample": "; ".join(trail_sl_updates[:5]),
        "stage_profit_diff": row.get("stage_profit_diff"),
        "sign_pair": row.get("sign_pair"),
    }


def main() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    cases = pd.read_csv(RUNTIME_DIR / "runtime_stage_input_cases.csv", encoding="utf-8-sig")
    priority1 = cases[cases["runtime_priority"] == 1].copy()
    m30 = load_m30()

    rows = [replay_case(row, m30) for _, row in priority1.iterrows()]
    replay = pd.DataFrame(rows)

    summary = (
        replay.groupby(["stage", "exit_relation", "predicted_runtime_class", "explains_mt5_sl", "contradicts_mt5_sl", "needs_tick_for_order"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(["stage", "exit_relation", "rows"], ascending=[True, True, False])
    )
    overall = (
        replay.groupby(["predicted_runtime_class", "explains_mt5_sl", "contradicts_mt5_sl", "needs_tick_for_order"], dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values("rows", ascending=False)
    )
    mt5_sl_cases = replay[replay["mt5_deal_reason"].astype(str).eq("SL")]
    mt5_sl_explained = int(mt5_sl_cases["explains_mt5_sl"].sum()) if not mt5_sl_cases.empty else 0
    mt5_sl_total = int(len(mt5_sl_cases))
    non_sl_cases = int(len(replay) - mt5_sl_total)
    needs_tick_total = int(replay["needs_tick_for_order"].sum())

    export_csv(replay, RUNTIME_DIR / "runtime_stage_priority1_replay.csv")
    export_csv(summary, RUNTIME_DIR / "runtime_stage_priority1_summary.csv")
    export_csv(overall, RUNTIME_DIR / "runtime_stage_priority1_overall_summary.csv")

    report = [
        "# Runtime-Style Stage Exit Priority 1 Replay",
        "",
        "## Scope",
        "",
        "- Input: `runtime_stage_input_cases.csv`, filtered to `runtime_priority = 1`.",
        "- Market data: `data/processed/m30_mt5.csv`.",
        "- This is an M30 OHLC approximation, not a tick-equivalent replay.",
        "",
        "## Overall Summary",
        "",
        overall.to_markdown(index=False),
        "",
        "## Key Counts",
        "",
        f"- Priority 1 cases: `{len(replay)}`.",
        f"- MT5 SL cases: `{mt5_sl_total}`.",
        f"- MT5 SL explained by M30 approximation: `{mt5_sl_explained}`.",
        f"- Non-SL MT5 cases in Priority 1: `{non_sl_cases}`.",
        f"- Cases requiring tick/order detail for exact ordering: `{needs_tick_total}`.",
        "",
        "## Stage Summary",
        "",
        summary.to_markdown(index=False),
        "",
        "## Interpretation Rules",
        "",
        "- `broker_sl_first` means the M30 bar sequence can explain the MT5 broker SL before Python's modeled exit.",
        "- `ambiguous_same_bar_with_broker_sl` means broker SL and a Python-style event occur in the same M30 bar; tick order is required.",
        "- `stage*_first` classes contradict an MT5 SL if no broker SL appears in the same first bar.",
        "- `partial_open_bar=True` marks cases where the first scanned M30 bar already started before the EA open time.",
        "",
        "## Output Files",
        "",
        "- `runtime_stage_priority1_replay.csv`",
        "- `runtime_stage_priority1_summary.csv`",
        "- `runtime_stage_priority1_overall_summary.csv`",
    ]
    write_text(RUNTIME_DIR / "runtime_stage_priority1_report.md", "\n".join(report))

    print(overall.to_string(index=False))
    print()
    print(summary.to_string(index=False))
    print(f"\nWrote {RUNTIME_DIR}")


if __name__ == "__main__":
    main()
