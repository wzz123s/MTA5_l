# -*- coding: utf-8 -*-
"""Quantify matched-PnL impact of deinit/end-of-test MT5 ledger rows."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
RESIDUAL_DIR = VALIDATION_DIR / "exec_model_residual_pnl_decomposition_20260715"
LEDGER_DIR = VALIDATION_DIR / "mt5_full_close_retry_fix_20260714"
AUDIT_DIR = VALIDATION_DIR / "mt5_0031_deinit_history_audit_20260715"
OUT_DIR = VALIDATION_DIR / "deinit_history_isolation_impact_20260715"


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


def num(value: object, default: float = 0.0) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(out):
        return default
    return float(out)


def bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index)
    return frame[column].astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def deinit_ledger_mask(ledger: pd.DataFrame) -> pd.Series:
    local_reason = ledger.get("local_exit_reason", pd.Series("", index=ledger.index)).astype(str).str.strip().str.lower()
    deal_comment = ledger.get("deal_comment", pd.Series("", index=ledger.index)).astype(str).str.strip().str.lower()
    return local_reason.eq("deinit_history") | deal_comment.str.contains("end of test", na=False)


def deinit_stage_mask(stage: pd.DataFrame) -> pd.Series:
    local_reason = stage.get("mt5_local_exit_reason", pd.Series("", index=stage.index)).astype(str).str.strip().str.lower()
    return local_reason.eq("deinit_history")


def round_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in out.select_dtypes(include=["number"]).columns:
        out[col] = out[col].round(6)
    return out


def build_deinit_inventory() -> tuple[pd.DataFrame, pd.DataFrame]:
    ledger = read_csv(LEDGER_DIR / "30m2H_strategy_trade_ledger.csv")
    ledger_deinit = ledger[deinit_ledger_mask(ledger)].copy()
    keep = [
        "signal_anchor_time",
        "trigger_tag",
        "signal_src",
        "dir",
        "stage",
        "ticket",
        "position_id",
        "open_time",
        "exit_time",
        "fill_price",
        "exit_price",
        "lots",
        "profit",
        "swap",
        "commission",
        "net_profit",
        "local_exit_reason",
        "deal_reason",
        "deal_comment",
        "deal_ticket",
    ]
    ledger_deinit = ledger_deinit[[c for c in keep if c in ledger_deinit.columns]].reset_index(drop=True)

    audit_decision_path = AUDIT_DIR / "mt5_0031_decision.csv"
    audit_decision = read_csv(audit_decision_path) if audit_decision_path.exists() else pd.DataFrame()
    return ledger_deinit, audit_decision


def build_trade_flags(stage: pd.DataFrame, trade: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    deinit_stage = stage[deinit_stage_mask(stage)].copy()
    group_cols = ["scenario", "py_trade_id", "mt5_trade_id"]
    effect_cols = [
        "residual_mt5_minus_py",
        "lot_sizing_effect_mt5_minus_py",
        "stage_exit_points_effect_mt5_minus_py",
        "swap_commission_effect_mt5_minus_py",
        "rounding_unexplained_effect_mt5_minus_py",
    ]

    if deinit_stage.empty:
        flags = trade[group_cols].copy()
        flags["has_deinit_stage"] = False
        flags["deinit_stage_rows"] = 0
        flags["deinit_stages"] = ""
        for col in effect_cols:
            flags[f"deinit_{col}"] = 0.0
    else:
        flags = (
            deinit_stage.groupby(group_cols, dropna=False)
            .agg(
                deinit_stage_rows=("stage", "count"),
                deinit_stages=("stage", lambda s: ",".join(str(int(v)) for v in s if pd.notna(v))),
                **{f"deinit_{col}": (col, "sum") for col in effect_cols},
            )
            .reset_index()
        )
        flags["has_deinit_stage"] = True

    flagged = trade.merge(flags, on=group_cols, how="left")
    flagged["has_deinit_stage"] = bool_series(flagged, "has_deinit_stage")
    flagged["deinit_stage_rows"] = pd.to_numeric(flagged["deinit_stage_rows"], errors="coerce").fillna(0).astype(int)
    flagged["deinit_stages"] = flagged["deinit_stages"].fillna("")
    for col in effect_cols:
        flag_col = f"deinit_{col}"
        flagged[flag_col] = pd.to_numeric(flagged[flag_col], errors="coerce").fillna(0.0)

    flagged["residual_after_stage_deinit_isolation_mt5_minus_py"] = (
        flagged["residual_mt5_minus_py"] - flagged["deinit_residual_mt5_minus_py"]
    )
    flagged["profit_diff_after_stage_deinit_isolation_py_minus_mt5"] = -flagged[
        "residual_after_stage_deinit_isolation_mt5_minus_py"
    ]
    flagged["abs_residual_after_stage_deinit_isolation"] = flagged[
        "residual_after_stage_deinit_isolation_mt5_minus_py"
    ].abs()
    return deinit_stage, flagged


def build_gap_summary(components: pd.DataFrame, deinit_stage: pd.DataFrame, flagged_trade: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    scenarios = sorted(components["scenario"].dropna().unique())
    for scenario in scenarios:
        comp = components[components["scenario"] == scenario].iloc[0]
        stages = deinit_stage[deinit_stage["scenario"] == scenario]
        trades = flagged_trade[(flagged_trade["scenario"] == scenario) & (flagged_trade["has_deinit_stage"])]
        deinit_residual = float(stages["residual_mt5_minus_py"].sum()) if not stages.empty else 0.0
        original_residual = num(comp["residual_mt5_minus_py_sum"])
        adjusted_residual = original_residual - deinit_residual
        adjusted_matched_diff = -adjusted_residual
        direct_gap = num(comp["direct_gap_py_minus_mt5"])
        rows.append(
            {
                "scenario": scenario,
                "ledger_deinit_stage_rows_in_matched_residual": int(len(stages)),
                "matched_trades_with_deinit_stage": int(len(trades)),
                "original_direct_gap_py_minus_mt5": direct_gap,
                "original_matched_profit_diff_py_minus_mt5": num(comp["matched_profit_diff_py_minus_mt5"]),
                "original_signal_set_gap_py_minus_mt5": num(comp["signal_set_gap_py_minus_mt5"]),
                "original_residual_mt5_minus_py": original_residual,
                "deinit_stage_residual_mt5_minus_py": deinit_residual,
                "deinit_stage_lot_effect_mt5_minus_py": float(stages["lot_sizing_effect_mt5_minus_py"].sum())
                if not stages.empty
                else 0.0,
                "deinit_stage_exit_points_effect_mt5_minus_py": float(
                    stages["stage_exit_points_effect_mt5_minus_py"].sum()
                )
                if not stages.empty
                else 0.0,
                "deinit_stage_swap_commission_effect_mt5_minus_py": float(
                    stages["swap_commission_effect_mt5_minus_py"].sum()
                )
                if not stages.empty
                else 0.0,
                "deinit_stage_rounding_effect_mt5_minus_py": float(
                    stages["rounding_unexplained_effect_mt5_minus_py"].sum()
                )
                if not stages.empty
                else 0.0,
                "stage_isolated_residual_mt5_minus_py": adjusted_residual,
                "stage_isolated_matched_profit_diff_py_minus_mt5": adjusted_matched_diff,
                "stage_isolated_signal_set_gap_py_minus_mt5_residual_only": direct_gap - adjusted_matched_diff,
                "direct_gap_py_minus_mt5_not_recomputed": True,
                "direct_gap_if_only_deinit_residual_removed_from_mt5": direct_gap + deinit_residual,
                "trade_level_deinit_trade_residual_mt5_minus_py": float(trades["residual_mt5_minus_py"].sum())
                if not trades.empty
                else 0.0,
                "trade_level_residual_excluding_deinit_trades_mt5_minus_py": float(
                    flagged_trade[(flagged_trade["scenario"] == scenario) & (~flagged_trade["has_deinit_stage"])][
                        "residual_mt5_minus_py"
                    ].sum()
                ),
                "next_gate": "ea_stage_state_tracking_overwrite_fix"
                if abs(deinit_residual) > abs(original_residual)
                else "continue_stage_exit_tick_ordering_review",
            }
        )
    return pd.DataFrame(rows)


def group_after_trade_isolation(flagged_trade: pd.DataFrame) -> pd.DataFrame:
    base = flagged_trade[~flagged_trade["has_deinit_stage"]].copy()
    if base.empty:
        return pd.DataFrame()
    group_cols = ["scenario", "is_reliable_tier", "match_tier", "py_trigger_family", "py_mode_family", "dir_norm"]
    grouped = (
        base.groupby(group_cols, dropna=False)
        .agg(
            trades=("py_trade_id", "count"),
            profit_diff_py_minus_mt5=("profit_diff_py_minus_mt5", "sum"),
            residual_mt5_minus_py=("residual_mt5_minus_py", "sum"),
            abs_profit_diff=("abs_profit_diff", "sum"),
            lot_sizing_effect=("lot_sizing_effect_mt5_minus_py", "sum"),
            stage_exit_points_effect=("stage_exit_points_effect_mt5_minus_py", "sum"),
            swap_commission_effect=("swap_commission_effect_mt5_minus_py", "sum"),
            rounding_unexplained_effect=("rounding_unexplained_effect_mt5_minus_py", "sum"),
        )
        .reset_index()
    )
    grouped["abs_residual_mt5_minus_py"] = grouped["residual_mt5_minus_py"].abs()
    return grouped.sort_values(["scenario", "abs_residual_mt5_minus_py"], ascending=[True, False])


def exit_reason_after_stage_isolation(stage: pd.DataFrame) -> pd.DataFrame:
    base = stage[~deinit_stage_mask(stage)].copy()
    if base.empty:
        return pd.DataFrame()
    grouped = (
        base.groupby(["scenario", "mt5_local_exit_reason", "mt5_deal_reason"], dropna=False)
        .agg(
            rows=("stage", "count"),
            residual_mt5_minus_py=("residual_mt5_minus_py", "sum"),
            abs_residual_mt5_minus_py=("residual_mt5_minus_py", lambda s: s.abs().sum()),
            lot_sizing_effect=("lot_sizing_effect_mt5_minus_py", "sum"),
            stage_exit_points_effect=("stage_exit_points_effect_mt5_minus_py", "sum"),
            swap_commission_effect=("swap_commission_effect_mt5_minus_py", "sum"),
        )
        .reset_index()
    )
    return grouped.sort_values(["scenario", "abs_residual_mt5_minus_py"], ascending=[True, False])


def top_after_isolation(flagged_trade: pd.DataFrame, stage: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    trade_top = flagged_trade[~flagged_trade["has_deinit_stage"]].copy()
    trade_top = trade_top.sort_values("abs_profit_diff", ascending=False).head(40)
    stage_top = stage[~deinit_stage_mask(stage)].copy()
    stage_top["abs_residual_mt5_minus_py"] = stage_top["residual_mt5_minus_py"].abs()
    stage_top = stage_top.sort_values("abs_residual_mt5_minus_py", ascending=False).head(60)
    return trade_top, stage_top


def write_report(
    ledger_deinit: pd.DataFrame,
    audit_decision: pd.DataFrame,
    deinit_stage: pd.DataFrame,
    gap_summary: pd.DataFrame,
    flagged_trade: pd.DataFrame,
    group_after: pd.DataFrame,
    exit_after: pd.DataFrame,
    trade_top: pd.DataFrame,
    stage_top: pd.DataFrame,
) -> None:
    deinit_trade_cols = [
        "scenario",
        "py_trade_id",
        "mt5_trade_id",
        "match_tier",
        "is_reliable_tier",
        "py_trigger_family",
        "py_mode_family",
        "dir_norm",
        "profit_diff_py_minus_mt5",
        "residual_mt5_minus_py",
        "deinit_stage_rows",
        "deinit_stages",
        "deinit_residual_mt5_minus_py",
        "residual_after_stage_deinit_isolation_mt5_minus_py",
    ]
    top_cols = [
        "scenario",
        "py_trade_id",
        "mt5_trade_id",
        "match_tier",
        "is_reliable_tier",
        "py_trigger_family",
        "py_mode_family",
        "dir_norm",
        "profit_diff_py_minus_mt5",
        "abs_profit_diff",
        "primary_residual_driver",
        "lot_sizing_effect_mt5_minus_py",
        "stage_exit_points_effect_mt5_minus_py",
        "swap_commission_effect_mt5_minus_py",
    ]
    stage_top_cols = [
        "scenario",
        "py_trade_id",
        "mt5_trade_id",
        "stage",
        "residual_mt5_minus_py",
        "abs_residual_mt5_minus_py",
        "py_dynamic_$",
        "mt5_net_profit",
        "mt5_local_exit_reason",
        "mt5_deal_reason",
        "py_stage_exit",
        "mt5_open_time",
        "mt5_exit_time",
    ]
    deinit_trades = flagged_trade[flagged_trade["has_deinit_stage"]].copy()
    lines = [
        "# Deinit-history isolation impact",
        "",
        "## Scope",
        "",
        "- Inputs are existing execution-model residual decomposition outputs.",
        "- No EA change, no signal-set change, no baseline overwrite.",
        "- Direct gap is reported as unchanged unless a separate adjusted MT5 ledger/balance is built.",
        "- Stage-level isolation removes only `deinit_history` residual components from matched residual accounting.",
        "- Trade-level isolation excludes matched trades that contain a deinit/end-of-test stage from residual top lists.",
        "",
        "## Ledger Deinit Inventory",
        "",
        markdown_table(ledger_deinit),
        "",
        "## Prior Single-Trade Audit Decision",
        "",
        markdown_table(audit_decision),
        "",
        "## Gap Impact",
        "",
        markdown_table(gap_summary),
        "",
        "## Matched Deinit Stage Rows",
        "",
        markdown_table(deinit_stage),
        "",
        "## Trades Containing Deinit Stage",
        "",
        markdown_table(deinit_trades[[c for c in deinit_trade_cols if c in deinit_trades.columns]]),
        "",
        "## Top Residual Groups After Trade-Level Isolation",
        "",
        markdown_table(group_after.head(25)),
        "",
        "## Exit Reason Summary After Stage-Level Isolation",
        "",
        markdown_table(exit_after.head(25)),
        "",
        "## Top Residual Trades After Trade-Level Isolation",
        "",
        markdown_table(trade_top[[c for c in top_cols if c in trade_top.columns]].head(25)),
        "",
        "## Top Residual Stages After Stage-Level Isolation",
        "",
        markdown_table(stage_top[[c for c in stage_top_cols if c in stage_top.columns]].head(25)),
        "",
        "## Interpretation",
        "",
        "- The deinit/end-of-test artifact is not an ordinary Stage exit/tick-ordering residual.",
        "- If deinit residual is larger than the original matched residual magnitude, the next gate must be EA stage state tracking / overwrite fix.",
        "- After isolation, remaining residual should be reviewed separately; it must not be used to tune broad Stage exit logic until unmanaged deinit rows are removed from the EA ledger.",
        "",
        "## Output Files",
        "",
        "- `deinit_ledger_rows.csv`",
        "- `deinit_matched_stage_rows.csv`",
        "- `deinit_trade_flags.csv`",
        "- `deinit_isolation_gap_summary.csv`",
        "- `deinit_group_summary_after_trade_isolation.csv`",
        "- `deinit_exit_reason_summary_after_stage_isolation.csv`",
        "- `deinit_top_residual_trades_after_trade_isolation.csv`",
        "- `deinit_top_residual_stages_after_stage_isolation.csv`",
    ]
    write_text(OUT_DIR / "deinit_history_isolation_impact_review.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    components = read_csv(RESIDUAL_DIR / "exec_model_residual_gap_components.csv")
    trade = read_csv(RESIDUAL_DIR / "exec_model_residual_trade_decomposition.csv")
    stage = read_csv(RESIDUAL_DIR / "exec_model_residual_stage_decomposition.csv")

    ledger_deinit, audit_decision = build_deinit_inventory()
    deinit_stage, flagged_trade = build_trade_flags(stage, trade)
    gap_summary = build_gap_summary(components, deinit_stage, flagged_trade)
    group_after = group_after_trade_isolation(flagged_trade)
    exit_after = exit_reason_after_stage_isolation(stage)
    trade_top, stage_top = top_after_isolation(flagged_trade, stage)

    outputs = {
        "deinit_ledger_rows.csv": ledger_deinit,
        "deinit_matched_stage_rows.csv": deinit_stage,
        "deinit_trade_flags.csv": flagged_trade,
        "deinit_isolation_gap_summary.csv": gap_summary,
        "deinit_group_summary_after_trade_isolation.csv": group_after,
        "deinit_exit_reason_summary_after_stage_isolation.csv": exit_after,
        "deinit_top_residual_trades_after_trade_isolation.csv": trade_top,
        "deinit_top_residual_stages_after_stage_isolation.csv": stage_top,
    }
    for name, frame in outputs.items():
        export_csv(round_numeric(frame), OUT_DIR / name)

    write_report(
        round_numeric(ledger_deinit),
        round_numeric(audit_decision),
        round_numeric(deinit_stage),
        round_numeric(gap_summary),
        round_numeric(flagged_trade),
        round_numeric(group_after),
        round_numeric(exit_after),
        round_numeric(trade_top),
        round_numeric(stage_top),
    )

    print(round_numeric(gap_summary).to_string(index=False))
    print()
    print(round_numeric(trade_top.head(12)).to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
