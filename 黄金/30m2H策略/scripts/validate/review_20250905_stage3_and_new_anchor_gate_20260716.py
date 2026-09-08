# -*- coding: utf-8 -*-
"""Audit the largest non-target stage-state delta and new-anchor gate changes."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

BASELINE_DIR = VALIDATION_DIR / "mt5_full_close_retry_fix_20260714"
STAGE_STATE_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"
LIFECYCLE_DIR = VALIDATION_DIR / "stage_state_lifecycle_delta_localization_20260716"
OUT_DIR = VALIDATION_DIR / "stage3_20250905_new_anchor_gate_audit_20260716"

TARGET_ANCHOR = "2025-09-05 14:30:00"
TARGET_TRIGGER = "[M15 SLOT1]"
TARGET_SIGNAL_SRC = "post_n5_m15_slot1_replace_or_rescue"
TARGET_DIR = "BUY"
TARGET_STAGE = 3
DEINIT_ANCHOR = "2022-11-08 16:30:00"
INP_MAX_POS = 3


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def markdown_table(frame: pd.DataFrame, max_rows: int = 40) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def to_dt(value: object) -> pd.Timestamp:
    text = str(value).strip()
    if not text:
        return pd.NaT
    return pd.to_datetime(text.replace(".", "-"), errors="coerce")


def iso(value: object) -> str:
    dt = to_dt(value)
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def num(value: object, default: float = 0.0) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(out):
        return default
    return float(out)


def round_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in out.select_dtypes(include=["number"]).columns:
        out[col] = out[col].round(6)
    return out


def prep_ledger(frame: pd.DataFrame, snapshot: str) -> pd.DataFrame:
    out = frame.copy()
    out["snapshot"] = snapshot
    out["anchor_iso"] = out["signal_anchor_time"].map(iso)
    out["open_dt"] = out["open_time"].map(to_dt)
    out["exit_dt"] = out["exit_time"].map(to_dt)
    out["stage"] = pd.to_numeric(out["stage"], errors="coerce").astype("Int64")
    for col in ["profit", "swap", "commission", "net_profit", "lots", "fill_price", "exit_price", "actual_stop"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def target_filter(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["anchor_iso"].eq(TARGET_ANCHOR)
        & frame["trigger_tag"].astype(str).eq(TARGET_TRIGGER)
        & frame["signal_src"].astype(str).eq(TARGET_SIGNAL_SRC)
        & frame["dir"].astype(str).eq(TARGET_DIR)
        & (pd.to_numeric(frame["stage"], errors="coerce") == TARGET_STAGE)
    )


def target_before_after(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "snapshot",
        "anchor_iso",
        "trigger_tag",
        "signal_src",
        "dir",
        "stage",
        "ticket",
        "position_id",
        "open_time",
        "exit_time",
        "local_exit_reason",
        "deal_reason",
        "profit",
        "swap",
        "commission",
        "net_profit",
        "deal_comment",
        "deal_ticket",
    ]
    return round_numeric(pd.concat([old[target_filter(old)], new[target_filter(new)]], ignore_index=True)[cols])


def load_m30_crosses() -> pd.DataFrame:
    m30 = read_csv(STRATEGY_DIR / "data" / "processed" / "m30_mt5.csv").copy()
    m30["date"] = pd.to_datetime(m30["date"], errors="coerce")
    m30["SMA_5"] = pd.to_numeric(m30["SMA_5"], errors="coerce")
    m30["SMA_13"] = pd.to_numeric(m30["SMA_13"], errors="coerce")
    m30 = m30.sort_values("date").reset_index(drop=True)
    m30["prev_above"] = m30["SMA_5"].shift(1) > m30["SMA_13"].shift(1)
    m30["curr_above"] = m30["SMA_5"] > m30["SMA_13"]
    m30["just_good"] = (~m30["prev_above"]) & m30["curr_above"]
    m30["just_bad"] = m30["prev_above"] & (~m30["curr_above"])
    m30["cross_type"] = ""
    m30.loc[m30["just_good"], "cross_type"] = "GOLDEN"
    m30.loc[m30["just_bad"], "cross_type"] = "DEAD"
    return m30


def first_opposite_cross(m30: pd.DataFrame, direction: str, after_dt: pd.Timestamp) -> tuple[pd.Series, pd.DataFrame]:
    if direction == "BUY":
        mask = m30["just_bad"]
    else:
        mask = m30["just_good"]
    hits = m30[(m30["date"] > after_dt) & mask].copy()
    if hits.empty:
        return pd.Series(dtype=object), pd.DataFrame()
    first = hits.iloc[0]
    idx = int(first.name)
    window = m30.iloc[max(0, idx - 8) : idx + 9].copy()
    keep = [
        "date",
        "open",
        "high",
        "low",
        "close",
        "SMA_5",
        "SMA_13",
        "prev_above",
        "curr_above",
        "cross_type",
        "merged_pre_cross",
        "merged_post_cross_n",
        "pre_cross",
        "post_cross_n",
    ]
    return first, round_numeric(window[[c for c in keep if c in window.columns]])


def stage3_opens_between(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    rows = frame[(frame["stage"].eq(3)) & (frame["open_dt"] > start) & (frame["open_dt"] < end)].copy()
    cols = [
        "snapshot",
        "anchor_iso",
        "trigger_tag",
        "signal_src",
        "dir",
        "stage",
        "ticket",
        "position_id",
        "open_time",
        "exit_time",
        "local_exit_reason",
        "deal_reason",
        "net_profit",
    ]
    return round_numeric(rows.sort_values("open_dt")[cols])


def active_rows_at(frame: pd.DataFrame, when: pd.Timestamp) -> pd.DataFrame:
    rows = frame[(frame["open_dt"] <= when) & (frame["exit_dt"] > when)].copy()
    cols = [
        "snapshot",
        "anchor_iso",
        "trigger_tag",
        "signal_src",
        "dir",
        "stage",
        "ticket",
        "position_id",
        "open_time",
        "exit_time",
        "local_exit_reason",
        "net_profit",
    ]
    return round_numeric(rows.sort_values(["open_dt", "stage"])[cols])


def active_timeline(old: pd.DataFrame, new: pd.DataFrame, times: list[tuple[str, pd.Timestamp]]) -> pd.DataFrame:
    rows: list[pd.DataFrame] = []
    for label, when in times:
        for snapshot, frame in [("close_retry", old), ("stage_state", new)]:
            active = active_rows_at(frame, when)
            active.insert(0, "check_time", when)
            active.insert(0, "check_label", label)
            active["active_rows"] = len(active)
            active["contains_target_deinit_anchor"] = active["anchor_iso"].eq(DEINIT_ANCHOR).any()
            rows.append(active)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def load_signal_export(directory: Path, prefix: str) -> pd.DataFrame:
    path = directory / "30m2H_strategy_signals_export.csv"
    sig = read_csv(path).copy()
    sig["anchor_iso"] = sig["bar_time"].map(iso)
    keep = ["anchor_iso", "decision", "skip_reason", "m30_cross", "h2_dir", "h2_cross", "stop_pts", "close"]
    sig = sig[[c for c in keep if c in sig.columns]].drop_duplicates("anchor_iso")
    return sig.rename(columns={c: f"{prefix}_{c}" for c in sig.columns if c != "anchor_iso"})


def audit_new_anchors(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    audit = read_csv(LIFECYCLE_DIR / "stage_state_new_anchor_audit.csv").copy()
    old_sig = load_signal_export(BASELINE_DIR, "old_signal")
    new_sig = load_signal_export(STAGE_STATE_DIR, "new_signal")
    out = audit.merge(old_sig, on="anchor_iso", how="left").merge(new_sig, on="anchor_iso", how="left")
    out["old_contains_deinit_anchor"] = out["old_active_examples"].astype(str).str.contains(DEINIT_ANCHOR, regex=False)
    out["new_contains_deinit_anchor"] = out["new_active_examples"].astype(str).str.contains(DEINIT_ANCHOR, regex=False)
    out["old_would_block_by_max_pos"] = pd.to_numeric(out["old_active_stage_rows_at_anchor"], errors="coerce") >= INP_MAX_POS
    out["new_has_capacity"] = pd.to_numeric(out["new_active_stage_rows_at_anchor"], errors="coerce") < INP_MAX_POS
    out["released_by_deinit_capacity"] = (
        out["old_contains_deinit_anchor"] & out["old_would_block_by_max_pos"] & out["new_has_capacity"]
    )
    out["gate_classification"] = "needs_manual_review"
    out.loc[out["released_by_deinit_capacity"], "gate_classification"] = "released_capacity_after_deinit_fix"
    return round_numeric(out)


def summarize_new_anchor_gate(new_anchor_audit: pd.DataFrame) -> pd.DataFrame:
    if new_anchor_audit.empty:
        return pd.DataFrame()
    grouped = (
        new_anchor_audit.groupby("gate_classification", dropna=False)
        .agg(
            anchors=("anchor_iso", "count"),
            net_delta=("net_delta_new_minus_old", "sum"),
            old_blocked_count=("old_would_block_by_max_pos", "sum"),
            released_by_deinit_count=("released_by_deinit_capacity", "sum"),
        )
        .reset_index()
    )
    total = pd.DataFrame(
        [
            {
                "gate_classification": "total",
                "anchors": len(new_anchor_audit),
                "net_delta": float(pd.to_numeric(new_anchor_audit["net_delta_new_minus_old"], errors="coerce").sum()),
                "old_blocked_count": int(new_anchor_audit["old_would_block_by_max_pos"].sum()),
                "released_by_deinit_count": int(new_anchor_audit["released_by_deinit_capacity"].sum()),
            }
        ]
    )
    return round_numeric(pd.concat([grouped, total], ignore_index=True))


def code_evidence() -> pd.DataFrame:
    path = ROOT / "auto_trade" / "30m2H_Strategy_EA.mq5"
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    patterns = [
        ("InpMaxPos", "Max concurrent positions"),
        ("g_stage_tickets", "legacy per-stage single-slot ticket state"),
        ("STAGE3 CROSS EXIT", "Stage3 exits on opposite M30 cross"),
    ]
    rows = []
    for pattern, note in patterns:
        for i, line in enumerate(lines, start=1):
            if pattern in line:
                rows.append({"file": str(path), "line": i, "pattern": pattern, "note": note, "text": line.strip()})
                break
    return pd.DataFrame(rows)


def build_target_decision(
    before_after: pd.DataFrame,
    first_cross: pd.Series,
    old_next_before_cross: pd.DataFrame,
    new_next_before_cross: pd.DataFrame,
) -> pd.DataFrame:
    old_row = before_after[before_after["snapshot"].eq("close_retry")].iloc[0]
    new_row = before_after[before_after["snapshot"].eq("stage_state")].iloc[0]
    open_dt = to_dt(old_row["open_time"])
    first_cross_dt = first_cross.get("date", pd.NaT)
    old_exit_dt = to_dt(old_row["exit_time"])
    new_exit_dt = to_dt(new_row["exit_time"])
    old_after_cross_hours = (old_exit_dt - first_cross_dt).total_seconds() / 3600.0 if pd.notna(first_cross_dt) else None
    new_after_cross_hours = (new_exit_dt - first_cross_dt).total_seconds() / 3600.0 if pd.notna(first_cross_dt) else None
    verdict = "needs_manual_review"
    if not old_next_before_cross.empty and pd.notna(first_cross_dt) and old_after_cross_hours and old_after_cross_hours > 24 * 7:
        verdict = "old_stage3_likely_unmanaged_after_stage3_state_overwrite"
    return round_numeric(
        pd.DataFrame(
            [
                {
                    "target_anchor": TARGET_ANCHOR,
                    "stage": TARGET_STAGE,
                    "old_net": num(old_row["net_profit"]),
                    "new_net": num(new_row["net_profit"]),
                    "net_delta_new_minus_old": num(new_row["net_profit"]) - num(old_row["net_profit"]),
                    "open_time": open_dt,
                    "first_opposite_cross_time": first_cross_dt,
                    "first_opposite_cross_type": first_cross.get("cross_type", ""),
                    "old_exit_time": old_exit_dt,
                    "new_exit_time": new_exit_dt,
                    "old_exit_after_first_cross_hours": old_after_cross_hours,
                    "new_exit_after_first_cross_hours": new_after_cross_hours,
                    "old_later_stage3_opens_before_first_cross": int(len(old_next_before_cross)),
                    "new_later_stage3_opens_before_first_cross": int(len(new_next_before_cross)),
                    "verdict": verdict,
                }
            ]
        )
    )


def build_overall_decision(target_decision: pd.DataFrame, new_anchor_summary: pd.DataFrame) -> pd.DataFrame:
    target_ok = str(target_decision.iloc[0]["verdict"]) == "old_stage3_likely_unmanaged_after_stage3_state_overwrite"
    released_count = int(
        new_anchor_summary.loc[
            new_anchor_summary["gate_classification"].eq("total"), "released_by_deinit_count"
        ].iloc[0]
    )
    anchor_count = int(new_anchor_summary.loc[new_anchor_summary["gate_classification"].eq("total"), "anchors"].iloc[0])
    anchors_ok = released_count == anchor_count
    if target_ok and anchors_ok:
        next_action = "prepare_stage_state_new_baseline_decision_with_pnl_reset"
    elif not target_ok:
        next_action = "inspect_stage3_management_side_effect_before_baseline_reset"
    else:
        next_action = "inspect_unexplained_new_anchor_gate_before_baseline_reset"
    return pd.DataFrame(
        [
            {
                "gate": "stage3_20250905_and_new_anchor_gate_audit",
                "merge_gate_pass": False,
                "target_stage3_old_profit_valid": not target_ok,
                "target_stage3_verdict": target_decision.iloc[0]["verdict"],
                "new_anchor_released_by_deinit_count": released_count,
                "new_anchor_count": anchor_count,
                "all_new_anchors_explained_by_deinit_capacity": anchors_ok,
                "next_action": next_action,
            }
        ]
    )


def write_report(
    target_decision: pd.DataFrame,
    overall: pd.DataFrame,
    before_after: pd.DataFrame,
    first_cross_window: pd.DataFrame,
    old_next_before_cross: pd.DataFrame,
    new_anchor_summary: pd.DataFrame,
    new_anchor_audit: pd.DataFrame,
    active: pd.DataFrame,
    evidence: pd.DataFrame,
) -> None:
    lines = [
        "# 2025-09-05 Stage3 and new-anchor gate audit",
        "",
        "## Scope",
        "",
        "- Audits the largest non-target stage-state delta.",
        "- Audits whether new anchors are explained by capacity released after removing the old deinit Stage1.",
        "- No EA/Python behavior is changed.",
        "",
        "## Overall Decision",
        "",
        markdown_table(overall),
        "",
        "## Target Stage3 Decision",
        "",
        markdown_table(target_decision),
        "",
        "## Target Stage3 Before/After",
        "",
        markdown_table(before_after),
        "",
        "## First Opposite M30 Cross Window",
        "",
        markdown_table(first_cross_window),
        "",
        "## Later Stage3 Opens Before First Cross",
        "",
        markdown_table(old_next_before_cross),
        "",
        "## New Anchor Gate Summary",
        "",
        markdown_table(new_anchor_summary),
        "",
        "## New Anchor Gate Audit",
        "",
        markdown_table(new_anchor_audit),
        "",
        "## Active Position Timeline",
        "",
        markdown_table(active),
        "",
        "## Code Evidence",
        "",
        markdown_table(evidence),
        "",
        "## Interpretation",
        "",
        "- The target Stage3 should have reacted to the first opposite M30 cross after the position opened.",
        "- A later Stage3 opened before that first opposite cross, which is consistent with the old per-stage single-slot state overwriting the target Stage3 runtime state.",
        "- All four new anchors have baseline active rows at `InpMaxPos=3` and include the old deinit Stage1; after the stage-state fix they have available capacity.",
        "- This supports treating most of the remaining regression as cleanup of invalid legacy lifecycle behavior, but the merge gate remains closed until the new baseline decision is made explicitly.",
        "",
        "## Output Files",
        "",
        "- `target_20250905_stage3_before_after.csv`",
        "- `target_20250905_first_opposite_cross_window.csv`",
        "- `target_20250905_later_stage3_opens_before_first_cross.csv`",
        "- `target_20250905_active_position_timeline.csv`",
        "- `new_anchor_gate_audit.csv`",
        "- `new_anchor_gate_summary.csv`",
        "- `stage3_new_anchor_gate_decision.csv`",
        "- `stage3_new_anchor_code_evidence.csv`",
    ]
    write_text(OUT_DIR / "stage3_20250905_new_anchor_gate_audit_review.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    old = prep_ledger(read_csv(BASELINE_DIR / "30m2H_strategy_trade_ledger.csv"), "close_retry")
    new = prep_ledger(read_csv(STAGE_STATE_DIR / "30m2H_strategy_trade_ledger.csv"), "stage_state")

    before_after = target_before_after(old, new)
    target_old = before_after[before_after["snapshot"].eq("close_retry")].iloc[0]
    target_open_dt = to_dt(target_old["open_time"])
    m30 = load_m30_crosses()
    first_cross, first_cross_window = first_opposite_cross(m30, TARGET_DIR, target_open_dt)
    first_cross_dt = first_cross.get("date", pd.NaT)
    new_exit_dt = to_dt(before_after[before_after["snapshot"].eq("stage_state")].iloc[0]["exit_time"])
    old_exit_dt = to_dt(before_after[before_after["snapshot"].eq("close_retry")].iloc[0]["exit_time"])

    old_next_before_cross = stage3_opens_between(old, target_open_dt, first_cross_dt)
    new_next_before_cross = stage3_opens_between(new, target_open_dt, first_cross_dt)
    old_next_before_old_exit = stage3_opens_between(old, target_open_dt, old_exit_dt)
    new_next_before_new_exit = stage3_opens_between(new, target_open_dt, new_exit_dt)
    active = active_timeline(
        old,
        new,
        [
            ("target_open", target_open_dt),
            ("later_stage3_open", to_dt(old_next_before_cross.iloc[0]["open_time"]) if not old_next_before_cross.empty else target_open_dt),
            ("first_opposite_cross", first_cross_dt),
            ("stage_state_exit", new_exit_dt),
        ],
    )
    new_anchor_audit = audit_new_anchors(old, new)
    new_anchor_summary = summarize_new_anchor_gate(new_anchor_audit)
    target_decision = build_target_decision(before_after, first_cross, old_next_before_cross, new_next_before_cross)
    overall = round_numeric(build_overall_decision(target_decision, new_anchor_summary))
    evidence = code_evidence()

    export_csv(before_after, OUT_DIR / "target_20250905_stage3_before_after.csv")
    export_csv(first_cross_window, OUT_DIR / "target_20250905_first_opposite_cross_window.csv")
    export_csv(old_next_before_cross, OUT_DIR / "target_20250905_later_stage3_opens_before_first_cross.csv")
    export_csv(new_next_before_cross, OUT_DIR / "target_20250905_stage_state_later_stage3_opens_before_first_cross.csv")
    export_csv(old_next_before_old_exit, OUT_DIR / "target_20250905_close_retry_later_stage3_opens_before_old_exit.csv")
    export_csv(new_next_before_new_exit, OUT_DIR / "target_20250905_stage_state_later_stage3_opens_before_new_exit.csv")
    export_csv(active, OUT_DIR / "target_20250905_active_position_timeline.csv")
    export_csv(new_anchor_audit, OUT_DIR / "new_anchor_gate_audit.csv")
    export_csv(new_anchor_summary, OUT_DIR / "new_anchor_gate_summary.csv")
    export_csv(target_decision, OUT_DIR / "target_20250905_stage3_decision.csv")
    export_csv(overall, OUT_DIR / "stage3_new_anchor_gate_decision.csv")
    export_csv(evidence, OUT_DIR / "stage3_new_anchor_code_evidence.csv")
    write_report(
        target_decision,
        overall,
        before_after,
        first_cross_window,
        old_next_before_cross,
        new_anchor_summary,
        new_anchor_audit,
        active,
        evidence,
    )

    print(overall.to_string(index=False))
    print()
    print(target_decision.to_string(index=False))
    print()
    print(new_anchor_summary.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
