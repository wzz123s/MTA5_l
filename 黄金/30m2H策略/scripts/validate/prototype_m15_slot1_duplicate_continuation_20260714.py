# -*- coding: utf-8 -*-
"""Prototype suppression of M15 SLOT1 duplicate continuation after exact MT5 matches."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"
OUT_DIR = VALIDATION_DIR / "m15_slot1_duplicate_continuation_prototype_20260714"

INPUT_DIR = VALIDATION_DIR / "dynamic_risk_inputs_shift90_metadatafix_20260714"
DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_shift90_metadatafix_close_retry_20260714"
MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_shift90_metadatafix_close_retry_20260714"
CAUSE_DIR = VALIDATION_DIR / "unmatched_signal_cause_shift90_metadatafix_close_retry_20260714"

START_CAPITAL = 500.0
RISK_PCT = 3.0
MIN_LOT = 0.01
MAX_LOT = 10.0
LOT_STEP = 0.01
VALUE_PER_SPEC_PT_PER_LOT = 10.0


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def mode_family(value: object) -> str:
    text = str(value)
    if "post_n" in text:
        return "post_n"
    if "pre_cross" in text:
        return "pre_cross"
    if "cross" in text:
        return "cross"
    return text


def trigger_family_from_variant(value: object) -> str:
    text = str(value)
    if any(tag in text for tag in ["slot1", "replace", "rescue"]):
        return "M15 SLOT1"
    return "M30 CLOSE"


def add_py_ids(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["py_trade_id"] = [f"python_mt5_{idx + 1:04d}" for idx in range(len(out))]
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["mode_family"] = out["mode"].map(mode_family)
    out["trigger_family"] = out["variant"].map(trigger_family_from_variant)
    return out


def normalize_lots(lot: float) -> float:
    lot = max(MIN_LOT, min(MAX_LOT, lot))
    lot = (lot // LOT_STEP) * LOT_STEP
    if lot < MIN_LOT:
        lot = MIN_LOT
    return round(lot, 2)


def calc_total_lot(balance: float, stop_pts_mql5: float) -> float:
    if stop_pts_mql5 <= 0:
        return MIN_LOT
    risk = balance * RISK_PCT / 100.0
    pts_value = VALUE_PER_SPEC_PT_PER_LOT * (stop_pts_mql5 / 1000.0)
    if pts_value <= 0:
        return MIN_LOT
    return normalize_lots(risk / pts_value)


def calc_stage_lots(balance: float, stop_pts_mql5: float) -> tuple[float, float, float, float]:
    total_lot = calc_total_lot(balance, stop_pts_mql5)
    base_lot = total_lot / 3.0
    if base_lot < MIN_LOT:
        base_lot = MIN_LOT
    stage1 = normalize_lots(base_lot * 0.5)
    stage2 = normalize_lots(base_lot * 1.0)
    stage3 = normalize_lots(base_lot * 1.5)
    return total_lot, stage1, stage2, stage3


def simulate_inputs(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    df = frame.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)
    details: list[dict[str, object]] = []
    balance = START_CAPITAL
    for _, row in df.iterrows():
        total_lot, stage1_lot, stage2_lot, stage3_lot = calc_stage_lots(balance, float(row["stop_pts_mql5"]))
        stage1_dynamic = float(row["stage1_pnl"]) * stage1_lot * VALUE_PER_SPEC_PT_PER_LOT
        stage2_dynamic = float(row["stage2_pnl"]) * stage2_lot * VALUE_PER_SPEC_PT_PER_LOT
        stage3_dynamic = float(row["stage3_pnl"]) * stage3_lot * VALUE_PER_SPEC_PT_PER_LOT
        dynamic_total = stage1_dynamic + stage2_dynamic + stage3_dynamic
        balance_after = balance + dynamic_total
        details.append(
            {
                "date": row["date"],
                "dir": row["dir"],
                "mode": row["mode"],
                "mode_family": mode_family(row["mode"]),
                "variant": row.get("variant", ""),
                "trigger_family": trigger_family_from_variant(row.get("variant", "")),
                "stop_pts_spec": row["stop_pts_spec"],
                "balance_before": round(balance, 6),
                "dynamic_total_$": round(dynamic_total, 6),
                "balance_after": round(balance_after, 6),
                "stage1_exit": row["stage1_exit"],
                "stage2_exit": row["stage2_exit"],
                "stage3_exit": row["stage3_exit"],
            }
        )
        balance = balance_after
    out = pd.DataFrame(details)
    total_profit = float(out["dynamic_total_$"].sum()) if not out.empty else 0.0
    return out, {
        "trade_count": int(len(out)),
        "final_balance": round(START_CAPITAL + total_profit, 6),
        "dynamic_total_profit": round(total_profit, 6),
    }


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.to_markdown(index=False)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    inputs = add_py_ids(read_csv(INPUT_DIR / "python_mt5_dynamic_risk_inputs.csv"))
    trades = add_py_ids(read_csv(DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"))
    candidates = read_csv(MAPPING_DIR / "python_mt5_mt5_candidate_matches.csv")
    selected = read_csv(MAPPING_DIR / "python_mt5_mt5_unique_matches.csv")
    causes = read_csv(CAUSE_DIR / "python_mt5_python_unmatched_cause.csv")

    for frame in [candidates, selected]:
        frame["tier_rank"] = pd.to_numeric(frame["tier_rank"], errors="coerce")
        frame["abs_time_diff_minutes"] = pd.to_numeric(frame["abs_time_diff_minutes"], errors="coerce")
        frame["profit_abs_diff"] = pd.to_numeric(frame.get("profit_abs_diff", frame.get("profit_diff", 0)), errors="coerce").abs()

    selected_by_mt5 = {str(row["mt5_trade_id"]): row for _, row in selected.iterrows()}
    selected_by_py = {str(row["py_trade_id"]): row for _, row in selected.iterrows()}

    rows: list[dict[str, object]] = []
    target_causes = causes[
        (causes["cause_bucket"].astype(str) == "unique_match_conflict")
        & (causes["trigger_family"].astype(str) == "M15 SLOT1")
    ].copy()
    for _, cause in target_causes.iterrows():
        py_id = str(cause["trade_id"])
        py_rows = trades[trades["py_trade_id"].astype(str) == py_id]
        if py_rows.empty:
            continue
        py_row = py_rows.iloc[0]
        if str(py_row["mode_family"]) != "post_n":
            continue
        cand = candidates[candidates["py_trade_id"].astype(str) == py_id].copy()
        cand = cand[cand["match_tier"].astype(str) != "same_dir_7d_unclassified"]
        if cand.empty:
            continue
        cand = cand.sort_values(["tier_rank", "abs_time_diff_minutes", "profit_abs_diff", "mt5_trade_id"])
        best = cand.iloc[0]
        owner = selected_by_mt5.get(str(best["mt5_trade_id"]))
        if owner is None:
            continue
        owner_py_id = str(owner["py_trade_id"])
        owner_rows = trades[trades["py_trade_id"].astype(str) == owner_py_id]
        if owner_rows.empty:
            continue
        owner_py = owner_rows.iloc[0]
        minutes_after_owner = (pd.Timestamp(py_row["date"]) - pd.Timestamp(owner_py["date"])).total_seconds() / 60.0
        is_duplicate = (
            str(best["match_tier"]) in {"nearby_60_all", "nearby_180_all"}
            and str(owner["match_tier"]) == "exact_align90_all"
            and 0 < minutes_after_owner <= 180
            and str(py_row["trigger_family"]) == str(owner_py["trigger_family"])
            and str(py_row["mode_family"]) == str(owner_py["mode_family"])
        )
        rows.append(
            {
                "candidate_py_trade_id": py_id,
                "candidate_date": py_row["date"],
                "candidate_mode": py_row["mode"],
                "candidate_variant": py_row["variant"],
                "candidate_dynamic_$": py_row["dynamic_total_$"],
                "candidate_stop_pts_spec": py_row["stop_pts_spec"],
                "candidate_best_mt5": best["mt5_trade_id"],
                "candidate_match_tier": best["match_tier"],
                "candidate_abs_minutes_to_mt5": best["abs_time_diff_minutes"],
                "owner_py_trade_id": owner_py_id,
                "owner_date": owner_py["date"],
                "owner_mode": owner_py["mode"],
                "owner_dynamic_$": owner_py["dynamic_total_$"],
                "owner_match_tier": owner["match_tier"],
                "minutes_after_owner": minutes_after_owner,
                "prototype_duplicate_flag": is_duplicate,
                "prototype_action": "suppress_continuation_candidate" if is_duplicate else "keep_for_now",
            }
        )

    review = pd.DataFrame(rows)
    suppress_ids = set(review.loc[review["prototype_duplicate_flag"], "candidate_py_trade_id"].astype(str))
    filtered_inputs = inputs[~inputs["py_trade_id"].astype(str).isin(suppress_ids)].drop(columns=["py_trade_id"])
    filtered_trade_rows = trades[~trades["py_trade_id"].astype(str).isin(suppress_ids)].drop(columns=["py_trade_id"])
    filtered_trades, filtered_summary = simulate_inputs(filtered_inputs)
    original_summary = {
        "trade_count": int(len(trades)),
        "final_balance": round(float(trades["dynamic_total_$"].sum()) + START_CAPITAL, 6),
        "dynamic_total_profit": round(float(trades["dynamic_total_$"].sum()), 6),
    }
    summary = pd.DataFrame(
        [
            {"scenario": "metadatafix_current", **original_summary},
            {"scenario": "suppress_duplicate_continuation_prototype", **filtered_summary},
        ]
    )
    if len(summary) == 2:
        summary["delta_vs_current_final_balance"] = summary["final_balance"] - float(summary.loc[0, "final_balance"])
        summary["delta_vs_current_profit"] = summary["dynamic_total_profit"] - float(summary.loc[0, "dynamic_total_profit"])

    suppressed_gap_effect = pd.to_numeric(
        review.loc[review["prototype_duplicate_flag"], "candidate_dynamic_$"],
        errors="coerce",
    ).sum()
    signal_gap_summary = pd.DataFrame(
        [
            {
                "metric": "suppressed_duplicate_rows",
                "value": int(len(suppress_ids)),
                "note": "Rows flagged by the non-destructive duplicate continuation prototype.",
            },
            {
                "metric": "suppressed_signal_gap_effect_sum",
                "value": round(float(suppressed_gap_effect), 6),
                "note": "Approximate post-bridge signal-set gap reduction if these Python-unmatched rows are suppressed.",
            },
            {
                "metric": "raw_dynamic_final_balance_delta",
                "value": round(float(summary.loc[1, "delta_vs_current_final_balance"]), 6) if len(summary) > 1 else "",
                "note": "Raw dynamic-risk replay delta; not the runtime-style adjusted gap metric.",
            },
        ]
    )

    export_csv(review, OUT_DIR / "duplicate_continuation_candidates.csv")
    export_csv(filtered_inputs, OUT_DIR / "python_mt5_inputs_suppress_duplicate_continuation.csv")
    export_csv(filtered_trade_rows, OUT_DIR / "python_mt5_trades_suppress_duplicate_continuation.csv")
    export_csv(filtered_trades, OUT_DIR / "python_mt5_trades_suppress_duplicate_continuation_replayed.csv")
    export_csv(summary, OUT_DIR / "duplicate_continuation_prototype_summary.csv")
    export_csv(signal_gap_summary, OUT_DIR / "duplicate_continuation_signal_gap_summary.csv")

    report = [
        "# M15 SLOT1 Duplicate Continuation Prototype 20260714",
        "",
        "## Candidate Summary",
        "",
        markdown_table(review),
        "",
        "## Fund Prototype",
        "",
        markdown_table(summary),
        "",
        "## Signal Gap Effect",
        "",
        markdown_table(signal_gap_summary),
        "",
        "## Decision",
        "",
        "- This is a non-destructive prototype; it does not change the official signal snapshot.",
        "- Suppression candidates require a nearby MT5 target already occupied by an exact Python match and a following same-family M15 SLOT1 post_n continuation.",
        "- If accepted, the next step is to rerun mapping/remaining P1 on the filtered prototype output before changing signal generation.",
    ]
    write_text(OUT_DIR / "duplicate_continuation_prototype.md", "\n".join(report))
    write_text(OUT_DIR / "README.md", "# m15_slot1_duplicate_continuation_prototype_20260714\n\nPrototype for suppressing post_n continuation after exact MT5 matches.")

    print(f"candidate_rows={len(review)}")
    print(f"suppress_rows={len(suppress_ids)}")
    print(f"suppressed_signal_gap_effect_sum={float(suppressed_gap_effect):.6f}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
