# -*- coding: utf-8 -*-
"""Review Python-unmatched unique-match conflicts after the post-bridge P1 reorder."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"
OUT_DIR = VALIDATION_DIR / "unique_match_conflict_review_20260714"

POST_BRIDGE_DIR = VALIDATION_DIR / "post_bridge_remaining_p1_review_20260714"
MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_shift90_close_retry_20260714"
UNMATCHED_CAUSE_DIR = VALIDATION_DIR / "unmatched_signal_cause_shift90_close_retry_20260714"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_shift90_close_retry_20260714"
DYNAMIC_INPUT_DIR = VALIDATION_DIR / "dynamic_risk_inputs_shift90_20260713"
SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_20260712" / "python_h2_context_q2early"


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


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL", "-1"}:
        return "SELL"
    if text in {"B", "BUY", "L", "LONG", "1"}:
        return "BUY"
    return text


def to_dt(value: object) -> pd.Timestamp:
    if pd.isna(value):
        return pd.NaT
    text = str(value).strip()
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        parsed = pd.to_datetime(text.replace(".", "-"), errors="coerce")
    return parsed


def coerce_num(frame: pd.DataFrame, columns: list[str]) -> None:
    for col in columns:
        if col in frame.columns:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")


def add_python_trade_ids(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    out = frame.copy()
    if "py_trade_id" not in out.columns or out["py_trade_id"].isna().all():
        out["py_trade_id"] = [f"{prefix}_{idx + 1:04d}" for idx in range(len(out))]
    out["date_dt"] = out["date"].map(to_dt)
    out["dir_norm"] = out["dir"].map(normalize_dir)
    return out


def mark_signal_frame(frame: pd.DataFrame, layer: str) -> pd.DataFrame:
    out = frame.copy()
    out["layer"] = layer
    out["date_dt"] = out["date"].map(to_dt)
    out["dir_norm"] = out["dir"].map(normalize_dir)
    if "trigger" not in out.columns:
        out["trigger"] = ""
    coerce_num(out, ["entry", "stop", "sd", "total_$", "pnl"])
    return out


def load_python_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    py_trades = add_python_trade_ids(read_csv(DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"), "python_mt5")
    py_inputs = add_python_trade_ids(read_csv(DYNAMIC_INPUT_DIR / "python_mt5_dynamic_risk_inputs.csv"), "python_mt5")
    raw = mark_signal_frame(read_csv(SIGNAL_DIR / "raw_candidates.csv"), "raw")
    accepted = mark_signal_frame(read_csv(SIGNAL_DIR / "候选信号_Layer1_Layer2通过.csv"), "accepted")
    layer3 = mark_signal_frame(read_csv(SIGNAL_DIR / "最终信号_Layer3入选.csv"), "layer3")
    stage = mark_signal_frame(read_csv(SIGNAL_DIR / "执行交易_Stage结果.csv"), "stage")
    return py_trades, py_inputs, raw, accepted, layer3, stage


def load_mt5_signals() -> pd.DataFrame:
    mt5 = read_csv(DYNAMIC_DIR / "mt5_ledger_unique_signals.csv").copy()
    mt5["mt5_trade_id"] = [f"mt5_{idx + 1:04d}" for idx in range(len(mt5))]
    mt5["signal_anchor_dt"] = mt5["signal_anchor_time"].map(to_dt)
    mt5["aligned_dt"] = mt5["signal_anchor_dt"] + pd.Timedelta(minutes=90)
    mt5["dir_norm"] = mt5["dir"].map(normalize_dir)
    coerce_num(mt5, ["net_profit", "stop_pts_spec", "balance_before", "balance_after"])
    return mt5


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.loc[:, [col for col in columns if col in frame.columns]].copy()
    if display.empty:
        return "_No columns._"
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


def nearest_signal_rows(
    target_time: pd.Timestamp,
    direction: str,
    frames: list[pd.DataFrame],
    window_minutes: int = 180,
) -> pd.DataFrame:
    rows = []
    for frame in frames:
        cur = frame[frame["dir_norm"] == direction].copy()
        cur["minutes_from_target"] = (cur["date_dt"] - target_time).dt.total_seconds() / 60.0
        cur = cur[cur["minutes_from_target"].abs() <= window_minutes]
        rows.append(cur)
    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    cols = [
        "layer",
        "date",
        "minutes_from_target",
        "trigger",
        "mode",
        "dir",
        "variant",
        "entry",
        "stop",
        "sd",
        "spec_pass",
        "spec_reason",
        "layer3_pass_ea",
        "total_$",
        "stage1_exit",
        "stage2_exit",
        "stage3_exit",
        "stage3_time",
    ]
    for col in cols:
        if col not in out.columns:
            out[col] = ""
    return out[cols].sort_values(["date", "layer", "mode"]).reset_index(drop=True)


def classify_case(
    py_input: pd.Series | None,
    best_candidate: pd.Series | None,
    selected_match: pd.Series | None,
) -> tuple[str, str]:
    spec_pass = str(py_input.get("spec_pass", "") if py_input is not None else "").strip().lower()
    spec_reason = str(py_input.get("spec_reason", "") if py_input is not None else "")
    sd = pd.to_numeric(py_input.get("sd", None), errors="coerce") if py_input is not None else pd.NA
    actual_spec_pass = bool(pd.notna(sd) and 5.0 <= float(sd) <= 35.0)
    tier = str(best_candidate.get("match_tier", "") if best_candidate is not None else "")
    abs_minutes = pd.to_numeric(best_candidate.get("abs_time_diff_minutes", None), errors="coerce") if best_candidate is not None else pd.NA
    selected_tier = str(selected_match.get("match_tier", "") if selected_match is not None else "")

    if spec_pass == "false" and actual_spec_pass:
        if pd.notna(abs_minutes) and float(abs_minutes) > 24 * 60:
            return (
                "stale_spec_metadata_plus_low_confidence_far_candidate",
                f"Rescued trade has stale spec_reason={spec_reason}, but current sd={float(sd):.6f} is in spec; best occupied candidate is {tier} at {float(abs_minutes):.0f} minutes.",
            )
        return (
            "stale_spec_metadata_on_rescue",
            f"Rescued trade has stale spec_reason={spec_reason}, but current sd={float(sd):.6f} is in spec; recompute metadata before using spec labels.",
        )
    if spec_pass == "false" and not actual_spec_pass:
        return (
            "actual_python_signal_spec_fail_leak_or_rescue_policy_mismatch",
            f"Python trade is present in Layer3/dynamic input while current sd is out of spec ({spec_reason}); review rescue/replace admission before mapping changes.",
        )
    if best_candidate is None:
        return (
            "no_mt5_candidate_in_mapping_window",
            "No candidate MT5 trade was found; review Python-only signal generation or ledger evidence.",
        )
    if pd.notna(abs_minutes) and float(abs_minutes) > 24 * 60:
        return (
            "low_confidence_far_candidate_conflict",
            f"Best occupied candidate is {tier} at {float(abs_minutes):.0f} minutes; do not treat as a true shared trade without a tighter cluster rule.",
        )
    if tier == "nearby_60_all" and selected_tier == "exact_align90_all":
        return (
            "duplicate_python_continuation_after_exact_mt5_match",
            "A nearby Python continuation competes with an MT5 trade already occupied by an exact Python match; review one-cluster/one-trade suppression.",
        )
    return (
        "occupied_mt5_candidate_mapping_conflict",
        "The closest candidate MT5 trade is already selected by another Python trade; inspect selected owner before changing signal rules.",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    post_bridge = read_csv(POST_BRIDGE_DIR / "post_bridge_signal_set_cases.csv")
    work_items = read_csv(POST_BRIDGE_DIR / "post_bridge_next_work_items.csv")
    candidates = read_csv(MAPPING_DIR / "python_mt5_mt5_candidate_matches.csv")
    selected = read_csv(MAPPING_DIR / "python_mt5_mt5_unique_matches.csv")
    unmatched_cause = read_csv(UNMATCHED_CAUSE_DIR / "python_mt5_python_unmatched_cause.csv")
    py_trades, py_inputs, raw, accepted, layer3, stage = load_python_frames()
    mt5 = load_mt5_signals()

    coerce_num(candidates, ["tier_rank", "abs_time_diff_minutes", "profit_diff", "profit_abs_diff"])
    coerce_num(selected, ["tier_rank", "abs_time_diff_minutes", "profit_diff", "profit_abs_diff"])
    coerce_num(post_bridge, ["gap_effect_$", "abs_gap_effect_$", "post_bridge_gap_effect_$", "post_bridge_abs_gap_effect_$"])
    if "profit_abs_diff" not in candidates.columns:
        candidates["profit_abs_diff"] = pd.to_numeric(candidates["profit_diff"], errors="coerce").abs()
    if "profit_abs_diff" not in selected.columns:
        selected["profit_abs_diff"] = pd.to_numeric(selected["profit_diff"], errors="coerce").abs()

    target_cases = post_bridge[
        (post_bridge["side"].astype(str) == "python_unmatched")
        & (post_bridge["effective_cause_bucket"].astype(str) == "unique_match_conflict")
    ].copy()
    target_cases = target_cases.sort_values("post_bridge_abs_gap_effect_$", ascending=False).reset_index(drop=True)
    focus_ids = set(target_cases.head(10)["trade_id"].astype(str))
    top3_ids = set(work_items[work_items["effective_cause"].astype(str) == "unique_match_conflict"].head(3)["id"].astype(str))

    selected_by_mt5 = {str(row["mt5_trade_id"]): row for _, row in selected.iterrows()}
    summary_rows: list[dict[str, object]] = []
    occupancy_rows: list[dict[str, object]] = []
    chain_frames: list[pd.DataFrame] = []

    for _, case in target_cases.iterrows():
        py_id = str(case["trade_id"])
        py_trade_rows = py_trades[py_trades["py_trade_id"].astype(str) == py_id]
        py_input_rows = py_inputs[py_inputs["py_trade_id"].astype(str) == py_id]
        cause_rows = unmatched_cause[unmatched_cause["trade_id"].astype(str) == py_id]
        py_trade = py_trade_rows.iloc[0] if not py_trade_rows.empty else None
        py_input = py_input_rows.iloc[0] if not py_input_rows.empty else None
        cause = cause_rows.iloc[0] if not cause_rows.empty else None

        cand = candidates[candidates["py_trade_id"].astype(str) == py_id].copy()
        cand = cand[cand["match_tier"].astype(str) != "same_dir_7d_unclassified"]
        cand = cand.sort_values(["tier_rank", "abs_time_diff_minutes", "profit_abs_diff", "mt5_trade_id"])
        best = cand.iloc[0] if not cand.empty else None
        selected_owner = selected_by_mt5.get(str(best["mt5_trade_id"])) if best is not None else None
        classification, recommendation = classify_case(py_input, best, selected_owner)

        target_time = to_dt(case.get("target_time", ""))
        direction = str(case.get("dir_norm", ""))
        chain = nearest_signal_rows(target_time, direction, [raw, accepted, layer3, stage])
        if not chain.empty and py_id in focus_ids:
            chain.insert(0, "case_trade_id", py_id)
            chain_frames.append(chain)

        selected_owner_id = as_text(selected_owner.get("py_trade_id", "")) if selected_owner is not None else ""
        best_mt5 = as_text(best.get("mt5_trade_id", "")) if best is not None else ""
        best_mt5_rows = mt5[mt5["mt5_trade_id"].astype(str) == best_mt5]
        best_mt5_row = best_mt5_rows.iloc[0] if not best_mt5_rows.empty else None

        summary_rows.append(
            {
                "trade_id": py_id,
                "is_top3_focus": py_id in top3_ids,
                "target_time": case.get("target_time", ""),
                "dir_norm": direction,
                "trigger_family": case.get("trigger_family", ""),
                "mode_family": case.get("mode_family", ""),
                "mode_or_signal_src": case.get("mode_or_signal_src", ""),
                "variant": py_trade.get("variant", "") if py_trade is not None else "",
                "gap_effect_$": case.get("post_bridge_gap_effect_$", case.get("gap_effect_$", "")),
                "dynamic_profit_$": py_trade.get("dynamic_total_$", "") if py_trade is not None else "",
                "spec_pass": py_input.get("spec_pass", "") if py_input is not None else "",
                "spec_reason": py_input.get("spec_reason", "") if py_input is not None else "",
                "sd": py_input.get("sd", "") if py_input is not None else "",
                "actual_spec_pass": bool(
                    pd.notna(pd.to_numeric(py_input.get("sd", None), errors="coerce"))
                    and 5.0 <= float(pd.to_numeric(py_input.get("sd", None), errors="coerce")) <= 35.0
                )
                if py_input is not None
                else "",
                "spec_flag_stale": bool(
                    str(py_input.get("spec_pass", "")).strip().lower() == "false"
                    and pd.notna(pd.to_numeric(py_input.get("sd", None), errors="coerce"))
                    and 5.0 <= float(pd.to_numeric(py_input.get("sd", None), errors="coerce")) <= 35.0
                )
                if py_input is not None
                else "",
                "stage1_exit": py_input.get("stage1_exit", "") if py_input is not None else "",
                "stage2_exit": py_input.get("stage2_exit", "") if py_input is not None else "",
                "stage3_exit": py_input.get("stage3_exit", "") if py_input is not None else "",
                "best_candidate_mt5": best_mt5,
                "best_candidate_tier": best.get("match_tier", "") if best is not None else "",
                "best_candidate_abs_minutes": best.get("abs_time_diff_minutes", "") if best is not None else "",
                "best_candidate_profit_diff": best.get("profit_diff", "") if best is not None else "",
                "best_candidate_mt5_profit": best.get("mt5_profit", "") if best is not None else "",
                "selected_owner_py": selected_owner_id,
                "selected_owner_tier": selected_owner.get("match_tier", "") if selected_owner is not None else "",
                "selected_owner_abs_minutes": selected_owner.get("abs_time_diff_minutes", "") if selected_owner is not None else "",
                "selected_owner_profit_diff": selected_owner.get("profit_diff", "") if selected_owner is not None else "",
                "mt5_aligned_time": best_mt5_row.get("aligned_dt", "") if best_mt5_row is not None else "",
                "mt5_trigger_family": best_mt5_row.get("trigger_family", "") if best_mt5_row is not None else "",
                "mt5_mode_family": best_mt5_row.get("mode_family", "") if best_mt5_row is not None else "",
                "mt5_signal_src": best_mt5_row.get("signal_src", "") if best_mt5_row is not None else "",
                "mt5_net_profit": best_mt5_row.get("net_profit", "") if best_mt5_row is not None else "",
                "unmatched_mt5_status": cause.get("mt5_status", "") if cause is not None else "",
                "unmatched_mt5_abs_minutes": cause.get("mt5_abs_minutes", "") if cause is not None else "",
                "review_classification": classification,
                "recommendation": recommendation,
            }
        )

        for _, cand_row in cand.head(8).iterrows():
            owner = selected_by_mt5.get(str(cand_row["mt5_trade_id"]))
            occupancy_rows.append(
                {
                    "case_trade_id": py_id,
                    "candidate_mt5": cand_row.get("mt5_trade_id", ""),
                    "candidate_tier": cand_row.get("match_tier", ""),
                    "candidate_rank": cand_row.get("tier_rank", ""),
                    "candidate_abs_minutes": cand_row.get("abs_time_diff_minutes", ""),
                    "candidate_trigger_same": cand_row.get("trigger_same", ""),
                    "candidate_mode_same": cand_row.get("mode_same", ""),
                    "candidate_py_profit": cand_row.get("py_profit", ""),
                    "candidate_mt5_profit": cand_row.get("mt5_profit", ""),
                    "candidate_profit_diff": cand_row.get("profit_diff", ""),
                    "selected_owner_py": owner.get("py_trade_id", "") if owner is not None else "",
                    "selected_owner_tier": owner.get("match_tier", "") if owner is not None else "",
                    "selected_owner_abs_minutes": owner.get("abs_time_diff_minutes", "") if owner is not None else "",
                    "selected_owner_profit_diff": owner.get("profit_diff", "") if owner is not None else "",
                }
            )

    summary = pd.DataFrame(summary_rows)
    occupancy = pd.DataFrame(occupancy_rows)
    chain_all = pd.concat(chain_frames, ignore_index=True) if chain_frames else pd.DataFrame()

    classification_summary = (
        summary.groupby("review_classification", dropna=False)
        .agg(
            rows=("trade_id", "count"),
            gap_sum_usd=("gap_effect_$", lambda s: pd.to_numeric(s, errors="coerce").sum()),
            abs_gap_sum_usd=("gap_effect_$", lambda s: pd.to_numeric(s, errors="coerce").abs().sum()),
        )
        .reset_index()
        .sort_values("abs_gap_sum_usd", ascending=False)
        if not summary.empty
        else pd.DataFrame(columns=["review_classification", "rows", "gap_sum_usd", "abs_gap_sum_usd"])
    )

    export_csv(summary, OUT_DIR / "unique_match_conflict_case_summary.csv")
    export_csv(occupancy, OUT_DIR / "unique_match_conflict_candidate_occupancy.csv")
    export_csv(chain_all, OUT_DIR / "unique_match_conflict_signal_chain_window.csv")
    export_csv(classification_summary, OUT_DIR / "unique_match_conflict_classification_summary.csv")

    report_lines = [
        "# Unique Match Conflict Review 20260714",
        "",
        "## Summary",
        "",
        markdown_table(classification_summary, ["review_classification", "rows", "gap_sum_usd", "abs_gap_sum_usd"]),
        "",
        "## Top Focus Cases",
        "",
        markdown_table(
            summary[summary["is_top3_focus"] == True].head(10),  # noqa: E712
            [
                "trade_id",
                "target_time",
                "mode_or_signal_src",
                "gap_effect_$",
                "spec_pass",
                "spec_reason",
                "sd",
                "actual_spec_pass",
                "spec_flag_stale",
                "best_candidate_mt5",
                "best_candidate_tier",
                "best_candidate_abs_minutes",
                "selected_owner_py",
                "selected_owner_tier",
                "review_classification",
            ],
        ),
        "",
        "## Decision",
        "",
        "- These cases are not evidence for reopening the EA price-side repair gate.",
        "- Current top `spec_pass=False` labels are stale metadata after rescue/reanchor; their current `sd` is inside the 5-35 StopSpec range.",
        "- Recompute rescue metadata before using `spec_pass/spec_reason` as a gating or diagnostic field.",
        "- `nearby_60_all` cases whose MT5 target is already occupied by an exact match should be reviewed as duplicate continuation/cluster policy.",
        "",
        "## Output Files",
        "",
        "- `unique_match_conflict_case_summary.csv`",
        "- `unique_match_conflict_candidate_occupancy.csv`",
        "- `unique_match_conflict_signal_chain_window.csv`",
        "- `unique_match_conflict_classification_summary.csv`",
    ]
    write_text(OUT_DIR / "unique_match_conflict_review.md", "\n".join(report_lines))
    write_text(
        OUT_DIR / "README.md",
        "\n".join(
            [
                "# unique_match_conflict_review_20260714",
                "",
                "Post-bridge review of Python-MT5 Python-unmatched unique-match conflicts.",
                "The review expands mapping occupancy, Python signal-chain evidence, and per-case repair direction.",
            ]
        ),
    )

    print(f"target_unique_conflicts={len(summary)}")
    print(f"top3_focus={len(summary[summary['is_top3_focus'] == True])}")  # noqa: E712
    if not classification_summary.empty:
        top = classification_summary.iloc[0]
        print(f"top_classification={top['review_classification']} rows={top['rows']} abs_gap={top['abs_gap_sum_usd']:.6f}")
    spec_fail = summary[summary["spec_pass"].astype(str).str.lower() == "false"]
    stale = summary[summary["spec_flag_stale"] == True]  # noqa: E712
    print(f"spec_fail_label_rows={len(spec_fail)}")
    print(f"stale_spec_label_rows={len(stale)}")


if __name__ == "__main__":
    main()
