# -*- coding: utf-8 -*-
"""Build a non-destructive runtime-style funds curve diagnostic.

This script starts from the ClosePos-retry Python-MT5 dynamic-risk result and
only adjusts the matched ``stage_exit_detail_diff`` trades whose Priority 1
runtime blockers have been resolved by the runtime evidence layer. It does not
regenerate signals and it does not re-lot later trades from the adjusted balance.
The goal is to isolate how much of the matched PnL residual is explained by EA
runtime exit semantics.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_shift90_close_retry_20260714"
MATCHED_DIR = VALIDATION_DIR / "matched_profit_exit_diff_shift90_close_retry_20260714"
RUNTIME_DIR = VALIDATION_DIR / "python_runtime_stage_exit_prototype_20260714"
OUT_DIR = VALIDATION_DIR / "runtime_style_dynamic_risk_alignment_20260714"

PY_MT5_TRADES = DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"
BASE_SUMMARY = DYNAMIC_DIR / "dynamic_risk_compare_summary.csv"
MATCHED_DETAILS = MATCHED_DIR / "matched_profit_exit_diff_details.csv"
RUNTIME_STAGE = RUNTIME_DIR / "runtime_stage_exit_integrated_alignment.csv"
JOURNAL_BLOCKERS = RUNTIME_DIR / "runtime_stage_exit_remaining_blockers.csv"

START_CAPITAL = 500.0


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


def bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def safe_float(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return float(parsed)


def safe_int(value: object, default: int = 0) -> int:
    parsed = pd.to_numeric(value, errors="coerce")
    if pd.isna(parsed):
        return default
    return int(parsed)


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    if frame.empty:
        return "_No rows._"
    display = frame.loc[:, columns].copy()
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


def load_python_mt5_trades() -> pd.DataFrame:
    trades = read_csv(PY_MT5_TRADES).copy()
    trades["date"] = pd.to_datetime(trades["date"])
    trades = trades.sort_values("date").reset_index(drop=True)
    trades["py_trade_id"] = [f"python_mt5_{idx + 1:04d}" for idx in range(len(trades))]
    trades["original_row_order"] = range(len(trades))
    return trades


def build_stage_status(stage: pd.DataFrame, journal: pd.DataFrame) -> pd.DataFrame:
    stage = stage.copy()
    if journal.empty:
        journal_lookup = pd.DataFrame(columns=["case_id"])
    else:
        journal_lookup = journal[
            [
                "case_id",
                "journal_class",
                "remaining_priority1_blocker_after_journal",
                "needs_more_journal_or_tick",
                "journal_note",
            ]
        ].drop_duplicates("case_id")

    out = stage.merge(journal_lookup, on="case_id", how="left")

    final_blockers: list[bool] = []
    final_strict: list[bool] = []
    final_status: list[str] = []
    final_note: list[str] = []

    for _, row in out.iterrows():
        priority = safe_int(row.get("runtime_priority"))
        journal_class = as_text(row.get("journal_class"))
        if journal_class:
            blocker = bool_value(row.get("remaining_priority1_blocker_after_journal"))
            strict = bool_value(row.get("needs_more_journal_or_tick"))
            status = "priority1_resolved_by_journal" if priority == 1 and not blocker else "priority1_journal_pending"
            note = as_text(row.get("journal_note"))
        else:
            blocker = bool_value(row.get("remaining_priority1_blocker"))
            strict = bool_value(row.get("requires_strict_tick_replay"))
            level = as_text(row.get("runtime_resolution_level"))
            if priority != 1:
                status = "not_priority1_reprocessed"
            elif blocker:
                status = "priority1_blocker"
            elif level.startswith("confirmed"):
                status = "priority1_confirmed"
            elif strict:
                status = "priority1_explained_strict_replay_pending"
            else:
                status = "priority1_explained"
            note = as_text(row.get("runtime_evidence_note"))

        final_blockers.append(blocker)
        final_strict.append(strict)
        final_status.append(status)
        final_note.append(note)

    out["final_priority1_blocker"] = final_blockers
    out["final_requires_strict_replay"] = final_strict
    out["stage_runtime_final_status"] = final_status
    out["stage_runtime_final_note"] = final_note
    return out


def build_trade_runtime_status(stage_status: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for py_trade_id, grp in stage_status.groupby("py_trade_id", sort=False):
        priority1 = grp[pd.to_numeric(grp["runtime_priority"], errors="coerce") == 1]
        blockers = int(priority1["final_priority1_blocker"].map(bool).sum()) if not priority1.empty else 0
        strict_pending = int(priority1["final_requires_strict_replay"].map(bool).sum()) if not priority1.empty else 0
        journal_resolved = int((priority1["stage_runtime_final_status"] == "priority1_resolved_by_journal").sum()) if not priority1.empty else 0
        confirmed = int((priority1["stage_runtime_final_status"] == "priority1_confirmed").sum()) if not priority1.empty else 0

        if priority1.empty:
            status = "no_priority1_stage"
        elif blockers > 0:
            status = "has_priority1_blocker"
        elif strict_pending > 0:
            status = "priority1_explained_strict_replay_pending"
        else:
            status = "priority1_resolved"

        rows.append(
            {
                "py_trade_id": py_trade_id,
                "stage_rows": int(len(grp)),
                "priority1_rows": int(len(priority1)),
                "final_priority1_blockers": blockers,
                "priority1_strict_replay_pending_rows": strict_pending,
                "priority1_journal_resolved_rows": journal_resolved,
                "priority1_confirmed_rows": confirmed,
                "trade_runtime_status": status,
            }
        )
    return pd.DataFrame(rows)


def add_adjustments(trades: pd.DataFrame, matched: pd.DataFrame, trade_status: pd.DataFrame) -> pd.DataFrame:
    keep_cols = [
        "py_trade_id",
        "mt5_trade_id",
        "mt5_profit",
        "py_profit",
        "profit_diff",
        "profit_abs_diff",
        "primary_diff_class",
        "py_stage_dynamic_profit",
        "mt5_stage_net_profit",
        "py_any_sl",
        "mt5_any_sl",
        "py_all_sl",
        "mt5_all_sl",
        "stage1_exit",
        "stage2_exit",
        "stage3_exit",
        "mt5_deal_reasons",
    ]
    matched_keep = matched[[c for c in keep_cols if c in matched.columns]].drop_duplicates("py_trade_id")
    out = trades.merge(matched_keep, on="py_trade_id", how="left", suffixes=("", "_matched"))
    out = out.merge(trade_status, on="py_trade_id", how="left")

    decisions: list[str] = []
    adjusted_profit: list[float] = []
    adjustment_basis: list[str] = []
    for _, row in out.iterrows():
        original_profit = safe_float(row.get("dynamic_total_$"))
        diff_class = as_text(row.get("primary_diff_class"))
        mt5_profit = safe_float(row.get("mt5_profit"))
        blockers = safe_int(row.get("final_priority1_blockers"))
        strict_pending = safe_int(row.get("priority1_strict_replay_pending_rows"))

        if not diff_class:
            decisions.append("unmatched_not_adjusted")
            adjusted_profit.append(original_profit)
            adjustment_basis.append("No matched MT5 trade in the current mapping.")
        elif diff_class != "stage_exit_detail_diff":
            decisions.append(f"{diff_class}_not_adjusted")
            adjusted_profit.append(original_profit)
            adjustment_basis.append("Primary difference is outside runtime Stage-exit adjustment scope.")
        elif blockers > 0:
            decisions.append("stage_exit_detail_pending_blocker_not_adjusted")
            adjusted_profit.append(original_profit)
            adjustment_basis.append("Priority 1 runtime blocker remains, so the trade is left unchanged.")
        else:
            decisions.append("stage_exit_detail_runtime_adjusted_to_mt5_profit")
            adjusted_profit.append(mt5_profit)
            if strict_pending > 0:
                adjustment_basis.append("Priority 1 blocker is resolved; strict tick replay remains as a lower-level audit item.")
            else:
                adjustment_basis.append("Priority 1 runtime evidence is resolved, so matched MT5 net profit is used.")

    out["runtime_adjustment_decision"] = decisions
    out["runtime_adjusted_total_$"] = [round(v, 6) for v in adjusted_profit]
    out["runtime_adjustment_$"] = (out["runtime_adjusted_total_$"] - out["dynamic_total_$"]).round(6)
    out["runtime_adjustment_basis"] = adjustment_basis

    balance = START_CAPITAL
    before_values: list[float] = []
    after_values: list[float] = []
    for value in out["runtime_adjusted_total_$"].tolist():
        before_values.append(round(balance, 6))
        balance += safe_float(value)
        after_values.append(round(balance, 6))
    out["runtime_balance_before"] = before_values
    out["runtime_balance_after"] = after_values
    return out


def build_stage_adjustment(stage_status: pd.DataFrame, adjusted_trades: pd.DataFrame) -> pd.DataFrame:
    decision_lookup = adjusted_trades[
        ["py_trade_id", "runtime_adjustment_decision", "runtime_adjustment_basis"]
    ].drop_duplicates("py_trade_id")
    out = stage_status.merge(decision_lookup, on="py_trade_id", how="left")
    adjusted_mask = out["runtime_adjustment_decision"] == "stage_exit_detail_runtime_adjusted_to_mt5_profit"
    out["runtime_adjusted_stage_profit"] = out["py_stage_profit"].map(safe_float)
    out.loc[adjusted_mask, "runtime_adjusted_stage_profit"] = out.loc[adjusted_mask, "mt5_stage_profit"].map(safe_float)
    out["runtime_stage_adjustment_$"] = (
        out["runtime_adjusted_stage_profit"].map(safe_float) - out["py_stage_profit"].map(safe_float)
    ).round(6)

    columns = [
        "case_id",
        "py_trade_id",
        "mt5_trade_id",
        "stage",
        "runtime_priority",
        "stage_runtime_final_status",
        "final_priority1_blocker",
        "final_requires_strict_replay",
        "py_exit",
        "mt5_local_exit_reason",
        "mt5_deal_reason",
        "py_stage_profit",
        "mt5_stage_profit",
        "runtime_adjusted_stage_profit",
        "runtime_stage_adjustment_$",
        "runtime_adjustment_decision",
        "runtime_adjustment_basis",
        "stage_runtime_final_note",
    ]
    return out[[c for c in columns if c in out.columns]]


def build_summary(adjusted: pd.DataFrame, base_summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    def add_row(source: str, profit_col: str, balance_col: str = "", include_adjustments: bool = False) -> None:
        profit = float(adjusted[profit_col].sum()) if not adjusted.empty else 0.0
        final_balance = float(adjusted[balance_col].iloc[-1]) if balance_col and not adjusted.empty else START_CAPITAL + profit
        win_count = int((adjusted[profit_col] > 0).sum()) if not adjusted.empty else 0
        any_sl = (
            (adjusted["stage1_exit"].astype(str).str.contains("SL", regex=False))
            | (adjusted["stage2_exit"].astype(str).str.contains("SL", regex=False))
            | (adjusted["stage3_exit"].astype(str).str.contains("SL", regex=False))
        )
        all_sl = (
            (adjusted["stage1_exit"].astype(str).str.contains("SL", regex=False))
            & (adjusted["stage2_exit"].astype(str).str.contains("SL", regex=False))
            & (adjusted["stage3_exit"].astype(str).str.contains("SL", regex=False))
        )
        rows.append(
            {
                "source": source,
                "trade_count": int(len(adjusted)),
                "final_balance": round(final_balance, 6),
                "dynamic_total_profit": round(profit, 6),
                "win_count": win_count,
                "win_rate_pct": round((win_count / len(adjusted) * 100.0) if len(adjusted) else 0.0, 4),
                "any_stage_sl_count": int(any_sl.sum()),
                "all_stage_sl_count": int(all_sl.sum()),
                "adjusted_trade_count": int((adjusted["runtime_adjustment_decision"] == "stage_exit_detail_runtime_adjusted_to_mt5_profit").sum()) if include_adjustments else 0,
                "strict_replay_pending_adjusted_trades": int(
                    (
                        (adjusted["runtime_adjustment_decision"] == "stage_exit_detail_runtime_adjusted_to_mt5_profit")
                        & (pd.to_numeric(adjusted["priority1_strict_replay_pending_rows"], errors="coerce").fillna(0) > 0)
                    ).sum()
                ) if include_adjustments else 0,
            }
        )

    add_row("python_mt5_close_retry_original", "dynamic_total_$", "", include_adjustments=False)
    add_row("python_mt5_runtime_stage_exit_adjusted", "runtime_adjusted_total_$", "runtime_balance_after", include_adjustments=True)

    if not base_summary.empty:
        mt5 = base_summary[base_summary["source"] == "mt5_ledger"]
        if not mt5.empty:
            row = mt5.iloc[0].to_dict()
            rows.append(
                {
                    "source": "mt5_ledger_reference_close_retry",
                    "trade_count": safe_int(row.get("trade_count")),
                    "final_balance": round(safe_float(row.get("final_balance")), 6),
                    "dynamic_total_profit": round(safe_float(row.get("dynamic_total_profit")), 6),
                    "win_count": safe_int(row.get("win_count")),
                    "win_rate_pct": round(safe_float(row.get("win_rate_pct")), 4),
                    "any_stage_sl_count": safe_int(row.get("any_stage_sl_count")),
                    "all_stage_sl_count": safe_int(row.get("all_stage_sl_count")),
                    "adjusted_trade_count": "",
                    "strict_replay_pending_adjusted_trades": "",
                }
            )
    return pd.DataFrame(rows)


def build_diff_class_summary(adjusted: pd.DataFrame) -> pd.DataFrame:
    matched = adjusted[adjusted["primary_diff_class"].notna()].copy()
    rows: list[dict[str, object]] = []
    for diff_class, grp in matched.groupby("primary_diff_class", sort=True):
        original_residual = grp["dynamic_total_$"].map(safe_float) - grp["mt5_profit"].map(safe_float)
        runtime_residual = grp["runtime_adjusted_total_$"].map(safe_float) - grp["mt5_profit"].map(safe_float)
        rows.append(
            {
                "primary_diff_class": diff_class,
                "rows": int(len(grp)),
                "adjusted_rows": int((grp["runtime_adjustment_decision"] == "stage_exit_detail_runtime_adjusted_to_mt5_profit").sum()),
                "original_py_profit_sum": round(float(grp["dynamic_total_$"].sum()), 6),
                "runtime_adjusted_profit_sum": round(float(grp["runtime_adjusted_total_$"].sum()), 6),
                "mt5_profit_sum": round(float(grp["mt5_profit"].sum()), 6),
                "original_residual_sum": round(float(original_residual.sum()), 6),
                "runtime_residual_sum": round(float(runtime_residual.sum()), 6),
                "original_abs_residual_sum": round(float(original_residual.abs().sum()), 6),
                "runtime_abs_residual_sum": round(float(runtime_residual.abs().sum()), 6),
                "original_abs_residual_mean": round(float(original_residual.abs().mean()), 6),
                "runtime_abs_residual_mean": round(float(runtime_residual.abs().mean()), 6),
            }
        )
    return pd.DataFrame(rows)


def build_matched_residual_summary(adjusted: pd.DataFrame) -> pd.DataFrame:
    matched = adjusted[adjusted["primary_diff_class"].notna()].copy()
    stage = matched[matched["primary_diff_class"] == "stage_exit_detail_diff"].copy()

    def row(label: str, frame: pd.DataFrame) -> dict[str, object]:
        if frame.empty:
            return {
                "scope": label,
                "rows": 0,
                "adjusted_rows": 0,
                "original_residual_sum": 0.0,
                "runtime_residual_sum": 0.0,
                "original_abs_residual_sum": 0.0,
                "runtime_abs_residual_sum": 0.0,
                "original_abs_residual_mean": 0.0,
                "runtime_abs_residual_mean": 0.0,
            }
        original_residual = frame["dynamic_total_$"].map(safe_float) - frame["mt5_profit"].map(safe_float)
        runtime_residual = frame["runtime_adjusted_total_$"].map(safe_float) - frame["mt5_profit"].map(safe_float)
        return {
            "scope": label,
            "rows": int(len(frame)),
            "adjusted_rows": int((frame["runtime_adjustment_decision"] == "stage_exit_detail_runtime_adjusted_to_mt5_profit").sum()),
            "original_residual_sum": round(float(original_residual.sum()), 6),
            "runtime_residual_sum": round(float(runtime_residual.sum()), 6),
            "original_abs_residual_sum": round(float(original_residual.abs().sum()), 6),
            "runtime_abs_residual_sum": round(float(runtime_residual.abs().sum()), 6),
            "original_abs_residual_mean": round(float(original_residual.abs().mean()), 6),
            "runtime_abs_residual_mean": round(float(runtime_residual.abs().mean()), 6),
        }

    return pd.DataFrame([row("all_matched_trades", matched), row("stage_exit_detail_diff_only", stage)])


def build_report(
    summary: pd.DataFrame,
    matched_residual: pd.DataFrame,
    diff_summary: pd.DataFrame,
    stage_adjustment: pd.DataFrame,
) -> str:
    blocker_count = int(stage_adjustment["final_priority1_blocker"].map(bool).sum()) if not stage_adjustment.empty else 0
    strict_rows = int(stage_adjustment["final_requires_strict_replay"].map(bool).sum()) if not stage_adjustment.empty else 0
    adjusted_stage_rows = int((stage_adjustment["runtime_adjustment_decision"] == "stage_exit_detail_runtime_adjusted_to_mt5_profit").sum()) if not stage_adjustment.empty else 0

    lines = [
        "# Runtime Style Dynamic Risk Alignment 20260714",
        "",
        "## Method",
        "",
        "- Base source: `dynamic_risk_alignment_shift90_close_retry_20260714/python_mt5_dynamic_risk_trades.csv`.",
        "- Adjustment source: matched `stage_exit_detail_diff` trades from `matched_profit_exit_diff_shift90_close_retry_20260714`.",
        "- Runtime evidence source: integrated Stage exit evidence plus remaining-blocker journal review.",
        "- This is a diagnostic funds-curve replay: it keeps the Python-MT5 signal set and existing dynamic lots, then substitutes MT5 net PnL only for resolved runtime Stage-exit trades.",
        "- It does not re-generate signals, re-open orders, or re-lot downstream trades from the adjusted balance.",
        "",
        "## Overall Funds Curve",
        "",
        markdown_table(
            summary,
            [
                "source",
                "trade_count",
                "final_balance",
                "dynamic_total_profit",
                "win_count",
                "win_rate_pct",
                "any_stage_sl_count",
                "all_stage_sl_count",
                "adjusted_trade_count",
                "strict_replay_pending_adjusted_trades",
            ],
        ),
        "",
        "## Matched Residual",
        "",
        markdown_table(
            matched_residual,
            [
                "scope",
                "rows",
                "adjusted_rows",
                "original_residual_sum",
                "runtime_residual_sum",
                "original_abs_residual_sum",
                "runtime_abs_residual_sum",
                "original_abs_residual_mean",
                "runtime_abs_residual_mean",
            ],
        ),
        "",
        "## Primary Diff Class Residual",
        "",
        markdown_table(
            diff_summary,
            [
                "primary_diff_class",
                "rows",
                "adjusted_rows",
                "original_residual_sum",
                "runtime_residual_sum",
                "original_abs_residual_sum",
                "runtime_abs_residual_sum",
            ],
        ),
        "",
        "## Runtime Evidence Gate",
        "",
        f"- Final Priority 1 stage blockers used by this adjustment: `{blocker_count}`.",
        f"- Stage rows still marked as strict replay audit items: `{strict_rows}`.",
        f"- Stage rows adjusted to MT5 stage PnL for the trade-level runtime replay: `{adjusted_stage_rows}`.",
        "",
        "## Interpretation",
        "",
        "- The matched Stage-exit PnL residual should collapse only for the adjusted `stage_exit_detail_diff` class.",
        "- The all-trade final balance is still not expected to match MT5 ledger, because Python-MT5 has 98 trades while the MT5 ledger has 78 trades and unmatched signal-set drift is outside this replay.",
        "- A full production runtime model would need to replay order lifecycle and re-lot subsequent trades from adjusted balances; this output is the safer diagnostic step before that larger rewrite.",
    ]
    return "\n".join(lines)


def write_readme() -> None:
    lines = [
        "# Runtime Style Dynamic Risk Alignment 20260714",
        "",
        "Generated by `simulate_runtime_style_dynamic_risk_20260714.py`.",
        "",
        "## Files",
        "",
        "- `runtime_style_dynamic_risk_trades.csv`: all Python-MT5 trades with original and runtime-adjusted PnL/balance.",
        "- `runtime_style_stage_exit_pnl_adjustment.csv`: stage-level adjustment evidence for the Stage-exit diff trades.",
        "- `runtime_style_dynamic_risk_summary.csv`: original, runtime-adjusted, and MT5 reference summary.",
        "- `runtime_style_matched_profit_residual_summary.csv`: matched-subset residual before/after adjustment.",
        "- `runtime_style_primary_diff_class_summary.csv`: residual summary by primary diff class.",
        "- `runtime_style_dynamic_risk_report.md`: human-readable report.",
        "",
        "## Boundary",
        "",
        "This is a non-destructive diagnostic replay. It adjusts resolved Stage-exit PnL only; it does not change EA behavior or regenerate the Python signal set.",
    ]
    write_text(OUT_DIR / "README.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    trades = load_python_mt5_trades()
    matched = read_csv(MATCHED_DETAILS)
    stage = read_csv(RUNTIME_STAGE)
    journal = read_csv(JOURNAL_BLOCKERS) if JOURNAL_BLOCKERS.exists() else pd.DataFrame()
    base_summary = read_csv(BASE_SUMMARY) if BASE_SUMMARY.exists() else pd.DataFrame()

    stage_status = build_stage_status(stage, journal)
    trade_status = build_trade_runtime_status(stage_status)
    adjusted = add_adjustments(trades, matched, trade_status)
    stage_adjustment = build_stage_adjustment(stage_status, adjusted)
    summary = build_summary(adjusted, base_summary)
    diff_summary = build_diff_class_summary(adjusted)
    matched_residual = build_matched_residual_summary(adjusted)

    export_csv(adjusted, OUT_DIR / "runtime_style_dynamic_risk_trades.csv")
    export_csv(stage_adjustment, OUT_DIR / "runtime_style_stage_exit_pnl_adjustment.csv")
    export_csv(summary, OUT_DIR / "runtime_style_dynamic_risk_summary.csv")
    export_csv(matched_residual, OUT_DIR / "runtime_style_matched_profit_residual_summary.csv")
    export_csv(diff_summary, OUT_DIR / "runtime_style_primary_diff_class_summary.csv")
    write_text(OUT_DIR / "runtime_style_dynamic_risk_report.md", build_report(summary, matched_residual, diff_summary, stage_adjustment))
    write_readme()

    print(summary.to_string(index=False))
    print()
    print(matched_residual.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
