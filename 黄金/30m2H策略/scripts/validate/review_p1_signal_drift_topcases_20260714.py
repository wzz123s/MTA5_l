# -*- coding: utf-8 -*-
"""Review P1 signal-drift top cases after the BUY direction mapping fix."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

REMAINING_DIR = VALIDATION_DIR / "runtime_style_remaining_diff_review_20260714"
RUNTIME_DIR = VALIDATION_DIR / "runtime_style_dynamic_risk_alignment_20260714"
EQ_DIR = VALIDATION_DIR / "trigger_family_equivalence_shift90_close_retry_20260714"
RUNTIME_STAGE_DIR = VALIDATION_DIR / "python_runtime_stage_exit_prototype_20260714"
OUT_DIR = VALIDATION_DIR / "p1_signal_drift_topcase_review_20260714"

SIGNAL_CASES = REMAINING_DIR / "remaining_signal_set_drift_cases.csv"
MATCHED_CASES = REMAINING_DIR / "remaining_matched_residual_cases.csv"
RUNTIME_TRADES = RUNTIME_DIR / "runtime_style_dynamic_risk_trades.csv"
POLICY_MATCHES = EQ_DIR / "bidirectional_m30_m15_90_profit20_selected_matches.csv"
BLOCKERS = RUNTIME_STAGE_DIR / "runtime_stage_exit_remaining_blockers.csv"

WATCH_MT5 = ["mt5_0031", "mt5_0049", "mt5_0068"]
WATCH_PY = ["python_mt5_0079", "python_mt5_0073", "python_mt5_0075", "python_mt5_0092"]


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


def markdown_table(frame: pd.DataFrame, columns: list[str], max_rows: int | None = None) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.loc[:, [c for c in columns if c in frame.columns]].copy()
    if max_rows is not None:
        display = display.head(max_rows)
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


def build_watchlist_review(
    signal_cases: pd.DataFrame,
    matched_cases: pd.DataFrame,
    runtime_trades: pd.DataFrame,
    policy_matches: pd.DataFrame,
    blockers: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    policy = policy_matches[policy_matches["source"] == "python_mt5"].copy()

    for mt5_id in WATCH_MT5:
        selected = policy[policy["mt5_trade_id"] == mt5_id]
        signal = signal_cases[signal_cases["trade_id"] == mt5_id]
        if not selected.empty:
            sel = selected.iloc[0]
            py_id = as_text(sel.get("py_trade_id"))
            rt = runtime_trades[runtime_trades["py_trade_id"] == py_id]
            rt_row = rt.iloc[0] if not rt.empty else pd.Series(dtype=object)
            matched_residual = matched_cases[matched_cases["mt5_trade_id"] == mt5_id]
            blocker_rows = blockers[blockers["mt5_trade_id"] == mt5_id] if not blockers.empty else pd.DataFrame()
            if not blocker_rows.empty and blocker_rows["remaining_priority1_blocker_after_journal"].astype(str).str.lower().eq("true").any():
                status = "matched_but_runtime_blocker_remains"
                next_step = "Resolve runtime Stage-exit blocker or add tick/journal evidence."
            elif not matched_residual.empty:
                status = "matched_with_small_residual"
                next_step = "Review matched residual class before changing signal logic."
            else:
                status = "resolved_by_buy_direction_mapping_fix"
                next_step = "No longer a signal-set drift case; keep under matched runtime PnL review."
            rows.append(
                {
                    "watch_id": mt5_id,
                    "case_status": status,
                    "side": "mt5_watch",
                    "py_trade_id": py_id,
                    "mt5_trade_id": mt5_id,
                    "target_time": sel.get("mt5_aligned_time", ""),
                    "dir_norm": sel.get("dir_norm", ""),
                    "trigger_family": sel.get("mt5_trigger_family", ""),
                    "mode_family": sel.get("mt5_mode_family", ""),
                    "match_tier": sel.get("effective_match_tier", sel.get("match_tier", "")),
                    "py_profit": round(safe_float(sel.get("py_profit")), 6),
                    "mt5_profit": round(safe_float(sel.get("mt5_profit")), 6),
                    "runtime_adjusted_profit": round(safe_float(rt_row.get("runtime_adjusted_total_$")), 6),
                    "runtime_decision": rt_row.get("runtime_adjustment_decision", ""),
                    "primary_diff_class": rt_row.get("primary_diff_class", ""),
                    "gap_or_residual": round(safe_float(rt_row.get("runtime_adjusted_total_$")) - safe_float(sel.get("mt5_profit")), 6),
                    "next_step": next_step,
                }
            )
        elif not signal.empty:
            sig = signal.iloc[0]
            rows.append(
                {
                    "watch_id": mt5_id,
                    "case_status": "remaining_signal_drift",
                    "side": sig.get("side", ""),
                    "py_trade_id": "",
                    "mt5_trade_id": mt5_id,
                    "target_time": sig.get("target_time", ""),
                    "dir_norm": sig.get("dir_norm", ""),
                    "trigger_family": sig.get("trigger_family", ""),
                    "mode_family": sig.get("mode_family", ""),
                    "match_tier": "",
                    "py_profit": "",
                    "mt5_profit": sig.get("source_profit_$", ""),
                    "runtime_adjusted_profit": "",
                    "runtime_decision": "",
                    "primary_diff_class": sig.get("cause_bucket", ""),
                    "gap_or_residual": sig.get("gap_effect_$", ""),
                    "next_step": sig.get("action_bucket", ""),
                }
            )

    for py_id in WATCH_PY:
        selected = policy[policy["py_trade_id"] == py_id]
        signal = signal_cases[signal_cases["trade_id"] == py_id]
        if not selected.empty:
            sel = selected.iloc[0]
            rt = runtime_trades[runtime_trades["py_trade_id"] == py_id]
            rt_row = rt.iloc[0] if not rt.empty else pd.Series(dtype=object)
            rows.append(
                {
                    "watch_id": py_id,
                    "case_status": "matched_after_policy_refresh",
                    "side": "python_watch",
                    "py_trade_id": py_id,
                    "mt5_trade_id": sel.get("mt5_trade_id", ""),
                    "target_time": sel.get("py_date", ""),
                    "dir_norm": sel.get("dir_norm", ""),
                    "trigger_family": sel.get("py_trigger_family", ""),
                    "mode_family": sel.get("py_mode_family", ""),
                    "match_tier": sel.get("effective_match_tier", sel.get("match_tier", "")),
                    "py_profit": round(safe_float(sel.get("py_profit")), 6),
                    "mt5_profit": round(safe_float(sel.get("mt5_profit")), 6),
                    "runtime_adjusted_profit": round(safe_float(rt_row.get("runtime_adjusted_total_$")), 6),
                    "runtime_decision": rt_row.get("runtime_adjustment_decision", ""),
                    "primary_diff_class": rt_row.get("primary_diff_class", ""),
                    "gap_or_residual": round(safe_float(rt_row.get("runtime_adjusted_total_$")) - safe_float(sel.get("mt5_profit")), 6),
                    "next_step": "No longer Python-unmatched under selected policy.",
                }
            )
        elif not signal.empty:
            sig = signal.iloc[0]
            rows.append(
                {
                    "watch_id": py_id,
                    "case_status": "remaining_signal_drift",
                    "side": sig.get("side", ""),
                    "py_trade_id": py_id,
                    "mt5_trade_id": "",
                    "target_time": sig.get("target_time", ""),
                    "dir_norm": sig.get("dir_norm", ""),
                    "trigger_family": sig.get("trigger_family", ""),
                    "mode_family": sig.get("mode_family", ""),
                    "match_tier": "",
                    "py_profit": sig.get("source_profit_$", ""),
                    "mt5_profit": "",
                    "runtime_adjusted_profit": sig.get("source_profit_$", ""),
                    "runtime_decision": "",
                    "primary_diff_class": sig.get("cause_bucket", ""),
                    "gap_or_residual": sig.get("gap_effect_$", ""),
                    "next_step": sig.get("action_bucket", ""),
                }
            )

    return pd.DataFrame(rows)


def build_current_top_cases(signal_cases: pd.DataFrame, matched_cases: pd.DataFrame) -> pd.DataFrame:
    signal_top = signal_cases.head(15).copy()
    signal_top = signal_top.rename(columns={"trade_id": "case_id", "abs_gap_effect_$": "abs_impact"})
    signal_top["case_type"] = "signal_drift"
    signal_top["impact"] = signal_top["gap_effect_$"]
    signal_top["next_step"] = signal_top["action_bucket"]
    signal_cols = [
        "case_type",
        "action_priority",
        "next_step",
        "side",
        "case_id",
        "target_time",
        "trigger_family",
        "mode_family",
        "cause_bucket",
        "impact",
        "abs_impact",
    ]

    matched_top = matched_cases.head(10).copy()
    matched_top = matched_top.rename(columns={"py_trade_id": "case_id", "runtime_abs_residual_$": "abs_impact", "runtime_residual_$": "impact"})
    matched_top["case_type"] = "matched_residual"
    matched_top["side"] = "matched"
    matched_top["target_time"] = matched_top["date"]
    matched_top["trigger_family"] = matched_top.get("trigger_family", "")
    matched_top["mode_family"] = matched_top.get("mode_family", "")
    matched_top["cause_bucket"] = matched_top["primary_diff_class"]
    matched_top["next_step"] = matched_top["action_bucket"]

    return pd.concat(
        [
            signal_top[[c for c in signal_cols if c in signal_top.columns]],
            matched_top[[c for c in signal_cols if c in matched_top.columns]],
        ],
        ignore_index=True,
        sort=False,
    )


def write_report(watchlist: pd.DataFrame, current_top: pd.DataFrame) -> None:
    lines = [
        "# P1 Signal Drift Topcase Review 20260714",
        "",
        "## Key Finding",
        "",
        "- `map_python_mt5_ledger_trades.py` previously normalized `B/BUY/1` as BUY but missed Python `L`.",
        "- After adding `L/LONG` to BUY normalization and rerunning close-retry mapping, Python-MT5 matched trades increased from `34` to `57`, and MT5-unmatched fell from `44` to `21`.",
        "- The previous largest MT5-only cases `mt5_0031` and `mt5_0049` are no longer signal-set drift; both are now matched Stage-exit/PnL cases.",
        "",
        "## Watchlist Status",
        "",
        markdown_table(
            watchlist,
            [
                "watch_id",
                "case_status",
                "py_trade_id",
                "mt5_trade_id",
                "target_time",
                "trigger_family",
                "mode_family",
                "match_tier",
                "py_profit",
                "mt5_profit",
                "runtime_adjusted_profit",
                "gap_or_residual",
                "next_step",
            ],
        ),
        "",
        "## Current Top Work Items",
        "",
        markdown_table(
            current_top,
            [
                "case_type",
                "action_priority",
                "next_step",
                "side",
                "case_id",
                "target_time",
                "trigger_family",
                "mode_family",
                "cause_bucket",
                "impact",
                "abs_impact",
            ],
            max_rows=20,
        ),
        "",
        "## Next Actions",
        "",
        "1. Resolve `python_mt5_0061 / mt5_0045`, the only remaining Stage-exit runtime blocker after the BUY mapping fix.",
        "2. Review `mt5_0068`, the largest remaining MT5-unmatched case, currently classified as `layer3_reject`.",
        "3. Then handle Python-unmatched unique-match conflicts around `2025-10-17` to `2025-10-21`.",
        "4. Keep EA price-side behavior unchanged; the current blocking issues are mapping/runtime evidence and signal-set review items.",
    ]
    write_text(OUT_DIR / "p1_signal_drift_fix_plan.md", "\n".join(lines))


def write_readme() -> None:
    lines = [
        "# P1 Signal Drift Topcase Review 20260714",
        "",
        "Generated by `review_p1_signal_drift_topcases_20260714.py`.",
        "",
        "## Files",
        "",
        "- `p1_signal_drift_topcase_review.csv`: watchlist status for old and current P1 top cases.",
        "- `p1_current_top_work_items.csv`: combined current signal-drift and matched-residual top work items.",
        "- `p1_signal_drift_fix_plan.md`: concise action plan.",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    signal_cases = read_csv(SIGNAL_CASES)
    matched_cases = read_csv(MATCHED_CASES)
    runtime_trades = read_csv(RUNTIME_TRADES)
    policy_matches = read_csv(POLICY_MATCHES)
    blockers = read_csv(BLOCKERS) if BLOCKERS.exists() else pd.DataFrame()

    watchlist = build_watchlist_review(signal_cases, matched_cases, runtime_trades, policy_matches, blockers)
    current_top = build_current_top_cases(signal_cases, matched_cases)

    export_csv(watchlist, OUT_DIR / "p1_signal_drift_topcase_review.csv")
    export_csv(current_top, OUT_DIR / "p1_current_top_work_items.csv")
    write_report(watchlist, current_top)
    write_readme()

    print(watchlist.to_string(index=False))
    print()
    print(current_top.head(20).to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
