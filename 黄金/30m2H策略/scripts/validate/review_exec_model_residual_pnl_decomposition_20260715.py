# -*- coding: utf-8 -*-
"""Decompose residual PnL after the execution-model normalization prototype."""
from __future__ import annotations


import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import simulate_dynamic_risk_alignment as dyn  # noqa: E402


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"
LEDGER_DIR = VALIDATION_DIR / "mt5_full_close_retry_fix_20260714"
OUT_DIR = VALIDATION_DIR / "exec_model_residual_pnl_decomposition_20260715"

MT5_PRICE_POINT_VALUE_PER_LOT = 100.0


@dataclass(frozen=True)
class Scenario:
    name: str
    dynamic_dir: Path
    mapping_dir: Path


SCENARIOS = [
    Scenario(
        name="metadatafix_exec_model",
        dynamic_dir=VALIDATION_DIR / "dynamic_risk_alignment_exec_model_metadatafix_20260715",
        mapping_dir=VALIDATION_DIR / "mapped_trade_alignment_exec_model_metadatafix_20260715",
    ),
    Scenario(
        name="p0_subset_exec_model",
        dynamic_dir=VALIDATION_DIR / "dynamic_risk_alignment_exec_model_p0_subset_bridge_20260715",
        mapping_dir=VALIDATION_DIR / "mapped_trade_alignment_exec_model_p0_subset_bridge_20260715",
    ),
]


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


def num(value: object, default: float = 0.0) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(out):
        return default
    return float(out)


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL", "SHORT", "-1"}:
        return "SELL"
    if text in {"B", "BUY", "L", "LONG", "1"}:
        return "BUY"
    return text


def direction_points(direction: str, entry: float, exit_price: float) -> float:
    if normalize_dir(direction) == "BUY":
        return exit_price - entry
    return entry - exit_price


def py_row_by_id(dynamic: pd.DataFrame, py_trade_id: str) -> pd.Series:
    idx = int(str(py_trade_id).rsplit("_", 1)[1]) - 1
    if idx < 0 or idx >= len(dynamic):
        raise IndexError(f"py_trade_id out of range: {py_trade_id}")
    return dynamic.iloc[idx]


def load_mt5_stage_ledger() -> pd.DataFrame:
    stage = read_csv(LEDGER_DIR / "30m2H_strategy_trade_ledger.csv").copy()
    stage["_anchor_dt"] = stage["signal_anchor_time"].map(to_dt)
    stage["trigger_family"] = stage["trigger_tag"].astype(str).str.replace("[", "", regex=False).str.replace("]", "", regex=False)
    stage["mode_family"] = stage["signal_src"].map(dyn.mode_family)
    stage["dir_norm"] = stage["dir"].map(normalize_dir)
    for col in [
        "stage",
        "fill_price",
        "exit_price",
        "lots",
        "profit",
        "swap",
        "commission",
        "net_profit",
    ]:
        stage[col] = pd.to_numeric(stage[col], errors="coerce")
    return stage


def stage_rows_for_match(stage_ledger: pd.DataFrame, match: pd.Series) -> pd.DataFrame:
    anchor = to_dt(match["mt5_signal_anchor_time"])
    signal_src = str(match["mt5_signal_src"])
    direction = normalize_dir(match["dir_norm"])
    rows = stage_ledger[
        (stage_ledger["_anchor_dt"] == anchor)
        & (stage_ledger["signal_src"].astype(str) == signal_src)
        & (stage_ledger["dir_norm"] == direction)
    ].copy()
    rows = rows.sort_values("stage").reset_index(drop=True)
    return rows


def decompose_stage(match: pd.Series, py_row: pd.Series, mt5_stage: pd.Series) -> dict[str, object]:
    stage_num = int(mt5_stage["stage"])
    py_lot = num(py_row[f"stage{stage_num}_lot"])
    py_dynamic = num(py_row[f"stage{stage_num}_dynamic_$"])
    py_points = py_dynamic / (py_lot * MT5_PRICE_POINT_VALUE_PER_LOT) if py_lot > 0 else 0.0

    mt5_lot = num(mt5_stage["lots"])
    mt5_points = direction_points(match["dir_norm"], num(mt5_stage["fill_price"]), num(mt5_stage["exit_price"]))
    mt5_gross = num(mt5_stage["profit"])
    mt5_net = num(mt5_stage["net_profit"])
    cost_effect = mt5_net - mt5_gross
    lot_effect = py_points * (mt5_lot - py_lot) * MT5_PRICE_POINT_VALUE_PER_LOT
    exit_effect = (mt5_points - py_points) * mt5_lot * MT5_PRICE_POINT_VALUE_PER_LOT
    residual = mt5_net - py_dynamic
    unexplained = residual - lot_effect - exit_effect - cost_effect

    return {
        "stage": stage_num,
        "py_stage_lot": py_lot,
        "mt5_lot": mt5_lot,
        "py_stage_points": py_points,
        "mt5_stage_points": mt5_points,
        "stage_points_diff_mt5_minus_py": mt5_points - py_points,
        "py_dynamic_$": py_dynamic,
        "mt5_gross_profit": mt5_gross,
        "mt5_net_profit": mt5_net,
        "residual_mt5_minus_py": residual,
        "lot_sizing_effect_mt5_minus_py": lot_effect,
        "stage_exit_points_effect_mt5_minus_py": exit_effect,
        "swap_commission_effect_mt5_minus_py": cost_effect,
        "rounding_unexplained_effect_mt5_minus_py": unexplained,
        "py_stage_exit": py_row[f"stage{stage_num}_exit"],
        "mt5_local_exit_reason": mt5_stage["local_exit_reason"],
        "mt5_deal_reason": mt5_stage["deal_reason"],
        "mt5_open_time": to_dt(mt5_stage["open_time"]),
        "mt5_exit_time": to_dt(mt5_stage["exit_time"]),
        "mt5_fill_price": num(mt5_stage["fill_price"]),
        "mt5_exit_price": num(mt5_stage["exit_price"]),
    }


def classify_primary(row: pd.Series) -> str:
    values = {
        "lot_sizing": abs(num(row["lot_sizing_effect_mt5_minus_py"])),
        "stage_exit_points": abs(num(row["stage_exit_points_effect_mt5_minus_py"])),
        "swap_commission": abs(num(row["swap_commission_effect_mt5_minus_py"])),
        "rounding_unexplained": abs(num(row["rounding_unexplained_effect_mt5_minus_py"])),
    }
    if max(values.values()) < 1e-6:
        return "aligned_or_tiny"
    return max(values, key=values.get)


def build_decomposition(scenario: Scenario, stage_ledger: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dynamic = read_csv(scenario.dynamic_dir / "python_mt5_dynamic_risk_trades.csv")
    matches = read_csv(scenario.mapping_dir / "python_mt5_mt5_unique_matches.csv")
    summary = read_csv(scenario.dynamic_dir / "dynamic_risk_compare_summary.csv")
    map_summary = read_csv(scenario.mapping_dir / "unique_match_summary.csv")

    stage_rows: list[dict[str, object]] = []
    trade_rows: list[dict[str, object]] = []
    missing_rows: list[dict[str, object]] = []

    for _, match in matches.iterrows():
        py_row = py_row_by_id(dynamic, str(match["py_trade_id"]))
        mt5_stages = stage_rows_for_match(stage_ledger, match)
        if len(mt5_stages) != 3:
            missing_rows.append(
                {
                    "scenario": scenario.name,
                    "py_trade_id": match["py_trade_id"],
                    "mt5_trade_id": match["mt5_trade_id"],
                    "stage_rows_found": int(len(mt5_stages)),
                    "mt5_signal_anchor_time": match["mt5_signal_anchor_time"],
                    "mt5_signal_src": match["mt5_signal_src"],
                    "dir_norm": match["dir_norm"],
                }
            )
            continue

        per_stage: list[dict[str, object]] = []
        for _, mt5_stage in mt5_stages.iterrows():
            row = decompose_stage(match, py_row, mt5_stage)
            row.update(
                {
                    "scenario": scenario.name,
                    "py_trade_id": match["py_trade_id"],
                    "mt5_trade_id": match["mt5_trade_id"],
                    "match_tier": match["match_tier"],
                    "is_reliable_tier": str(match["is_reliable_tier"]).lower() in {"true", "1"},
                    "py_trigger_family": match["py_trigger_family"],
                    "py_mode_family": match["py_mode_family"],
                    "dir_norm": match["dir_norm"],
                    "py_date": match["py_date"],
                    "mt5_signal_anchor_time": match["mt5_signal_anchor_time"],
                }
            )
            stage_rows.append(row)
            per_stage.append(row)

        trade = {
            "scenario": scenario.name,
            "py_trade_id": match["py_trade_id"],
            "mt5_trade_id": match["mt5_trade_id"],
            "match_tier": match["match_tier"],
            "is_reliable_tier": str(match["is_reliable_tier"]).lower() in {"true", "1"},
            "py_trigger_family": match["py_trigger_family"],
            "py_mode_family": match["py_mode_family"],
            "dir_norm": match["dir_norm"],
            "py_date": match["py_date"],
            "mt5_signal_anchor_time": match["mt5_signal_anchor_time"],
            "py_profit": num(match["py_profit"]),
            "mt5_profit": num(match["mt5_profit"]),
            "profit_diff_py_minus_mt5": num(match["profit_diff"]),
            "residual_mt5_minus_py": -num(match["profit_diff"]),
            "abs_profit_diff": abs(num(match["profit_diff"])),
        }
        for col in [
            "lot_sizing_effect_mt5_minus_py",
            "stage_exit_points_effect_mt5_minus_py",
            "swap_commission_effect_mt5_minus_py",
            "rounding_unexplained_effect_mt5_minus_py",
        ]:
            trade[col] = sum(num(row[col]) for row in per_stage)
        trade["reconstructed_residual_mt5_minus_py"] = sum(
            num(trade[col])
            for col in [
                "lot_sizing_effect_mt5_minus_py",
                "stage_exit_points_effect_mt5_minus_py",
                "swap_commission_effect_mt5_minus_py",
                "rounding_unexplained_effect_mt5_minus_py",
            ]
        )
        trade["reconstruction_error"] = trade["residual_mt5_minus_py"] - trade["reconstructed_residual_mt5_minus_py"]
        trade_rows.append(trade)

    stage_df = pd.DataFrame(stage_rows)
    trade_df = pd.DataFrame(trade_rows)
    missing_df = pd.DataFrame(missing_rows)
    if not trade_df.empty:
        trade_df["primary_residual_driver"] = trade_df.apply(classify_primary, axis=1)

    py_summary = summary[summary["source"] == "python_mt5"].iloc[0]
    mt5_summary = summary[summary["source"] == "mt5_ledger"].iloc[0]
    map_row = map_summary[map_summary["source"] == "python_mt5"].iloc[0]
    direct_gap = num(py_summary["final_balance"]) - num(mt5_summary["final_balance"])
    matched_profit_diff = num(map_row["matched_profit_diff"])
    signal_set_gap = direct_gap - matched_profit_diff
    component_rows = [
        {
            "scenario": scenario.name,
            "direct_gap_py_minus_mt5": direct_gap,
            "matched_profit_diff_py_minus_mt5": matched_profit_diff,
            "signal_set_gap_py_minus_mt5": signal_set_gap,
            "matched_unique": int(num(map_row["matched_unique"])),
            "reliable_tier_matched": int(num(map_row["reliable_tier_matched"])),
            "relaxed_tier_matched": int(num(map_row["relaxed_tier_matched"])),
            "trade_decomp_rows": int(len(trade_df)),
            "missing_stage_groups": int(len(missing_df)),
            "residual_mt5_minus_py_sum": float(trade_df["residual_mt5_minus_py"].sum()) if not trade_df.empty else 0.0,
            "lot_sizing_effect_sum": float(trade_df["lot_sizing_effect_mt5_minus_py"].sum()) if not trade_df.empty else 0.0,
            "stage_exit_points_effect_sum": float(trade_df["stage_exit_points_effect_mt5_minus_py"].sum()) if not trade_df.empty else 0.0,
            "swap_commission_effect_sum": float(trade_df["swap_commission_effect_mt5_minus_py"].sum()) if not trade_df.empty else 0.0,
            "rounding_unexplained_effect_sum": float(trade_df["rounding_unexplained_effect_mt5_minus_py"].sum()) if not trade_df.empty else 0.0,
        }
    ]
    component_df = pd.DataFrame(component_rows)
    return stage_df, trade_df, component_df, missing_df


def group_trade_residuals(trade_df: pd.DataFrame) -> pd.DataFrame:
    if trade_df.empty:
        return pd.DataFrame()
    group_cols = ["scenario", "is_reliable_tier", "match_tier", "py_trigger_family", "py_mode_family", "dir_norm"]
    grouped = trade_df.groupby(group_cols, dropna=False).agg(
        trades=("py_trade_id", "count"),
        profit_diff_py_minus_mt5=("profit_diff_py_minus_mt5", "sum"),
        residual_mt5_minus_py=("residual_mt5_minus_py", "sum"),
        abs_profit_diff=("abs_profit_diff", "sum"),
        lot_sizing_effect=("lot_sizing_effect_mt5_minus_py", "sum"),
        stage_exit_points_effect=("stage_exit_points_effect_mt5_minus_py", "sum"),
        swap_commission_effect=("swap_commission_effect_mt5_minus_py", "sum"),
        rounding_unexplained_effect=("rounding_unexplained_effect_mt5_minus_py", "sum"),
    ).reset_index()
    grouped["abs_residual_mt5_minus_py"] = grouped["residual_mt5_minus_py"].abs()
    return grouped.sort_values(["scenario", "abs_residual_mt5_minus_py"], ascending=[True, False])


def summarize_exit_reasons(stage_df: pd.DataFrame) -> pd.DataFrame:
    if stage_df.empty:
        return pd.DataFrame()
    grouped = stage_df.groupby(["scenario", "mt5_local_exit_reason", "mt5_deal_reason"], dropna=False).agg(
        rows=("stage", "count"),
        residual_mt5_minus_py=("residual_mt5_minus_py", "sum"),
        abs_residual_mt5_minus_py=("residual_mt5_minus_py", lambda s: s.abs().sum()),
        lot_sizing_effect=("lot_sizing_effect_mt5_minus_py", "sum"),
        stage_exit_points_effect=("stage_exit_points_effect_mt5_minus_py", "sum"),
        swap_commission_effect=("swap_commission_effect_mt5_minus_py", "sum"),
    ).reset_index()
    return grouped.sort_values(["scenario", "abs_residual_mt5_minus_py"], ascending=[True, False])


def summarize_primary_drivers(trade_df: pd.DataFrame) -> pd.DataFrame:
    if trade_df.empty:
        return pd.DataFrame()
    grouped = trade_df.groupby(["scenario", "primary_residual_driver", "is_reliable_tier"], dropna=False).agg(
        trades=("py_trade_id", "count"),
        residual_mt5_minus_py=("residual_mt5_minus_py", "sum"),
        abs_profit_diff=("abs_profit_diff", "sum"),
        lot_sizing_effect=("lot_sizing_effect_mt5_minus_py", "sum"),
        stage_exit_points_effect=("stage_exit_points_effect_mt5_minus_py", "sum"),
        swap_commission_effect=("swap_commission_effect_mt5_minus_py", "sum"),
    ).reset_index()
    return grouped.sort_values(["scenario", "abs_profit_diff"], ascending=[True, False])


def round_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in out.select_dtypes(include=["number"]).columns:
        out[col] = out[col].round(6)
    return out


def write_report(
    components: pd.DataFrame,
    groups: pd.DataFrame,
    exit_reasons: pd.DataFrame,
    drivers: pd.DataFrame,
    trade_df: pd.DataFrame,
    stage_df: pd.DataFrame,
    missing_df: pd.DataFrame,
) -> None:
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
        "rounding_unexplained_effect_mt5_minus_py",
    ]
    top = trade_df.sort_values("abs_profit_diff", ascending=False).head(20)
    lines = [
        "# Execution-model residual PnL decomposition",
        "",
        "## Scope",
        "",
        "- Inputs are execution-model dynamic/mapping snapshots only.",
        "- No EA change, no signal-set change, no baseline overwrite.",
        "- Decomposition uses MT5-minus-Python sign for component effects.",
        "",
        "## Gap Components",
        "",
        markdown_table(components),
        "",
        "## Residual Groups",
        "",
        markdown_table(groups.head(25)),
        "",
        "## Exit Reason Summary",
        "",
        markdown_table(exit_reasons.head(20)),
        "",
        "## Primary Driver Summary",
        "",
        markdown_table(drivers.head(20)),
        "",
        "## Top Residual Trades",
        "",
        markdown_table(top[[c for c in top_cols if c in top.columns]]),
        "",
        "## Missing Stage Groups",
        "",
        markdown_table(missing_df),
        "",
        "## Interpretation",
        "",
        "- `matched_profit_diff_py_minus_mt5` is the mapped matched PnL residual used by the existing mapping summary.",
        "- `signal_set_gap_py_minus_mt5 = direct_gap - matched_profit_diff`; it measures unmatched Python vs unmatched MT5 contribution.",
        "- Stage/trade decomposition is only for matched rows whose MT5 stage ledger group is found.",
        "- If reliable-tier residual dominates, next work should target Stage exit/tick ordering. If relaxed-tier residual dominates, mapping policy must be fixed before changing execution logic.",
        "",
        "## Output Files",
        "",
        "- `exec_model_residual_gap_components.csv`",
        "- `exec_model_residual_trade_decomposition.csv`",
        "- `exec_model_residual_stage_decomposition.csv`",
        "- `exec_model_residual_group_summary.csv`",
        "- `exec_model_residual_exit_reason_summary.csv`",
        "- `exec_model_residual_primary_driver_summary.csv`",
        "- `exec_model_residual_top_trades.csv`",
        "- `exec_model_residual_missing_stage_groups.csv`",
    ]
    write_text(OUT_DIR / "exec_model_residual_pnl_decomposition_review.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dyn.LEDGER_DIR = LEDGER_DIR
    stage_ledger = load_mt5_stage_ledger()

    all_stage: list[pd.DataFrame] = []
    all_trade: list[pd.DataFrame] = []
    all_components: list[pd.DataFrame] = []
    all_missing: list[pd.DataFrame] = []

    for scenario in SCENARIOS:
        stage_df, trade_df, component_df, missing_df = build_decomposition(scenario, stage_ledger)
        all_stage.append(stage_df)
        all_trade.append(trade_df)
        all_components.append(component_df)
        all_missing.append(missing_df)

    stage = round_numeric(pd.concat(all_stage, ignore_index=True)) if all_stage else pd.DataFrame()
    trade = round_numeric(pd.concat(all_trade, ignore_index=True)) if all_trade else pd.DataFrame()
    components = round_numeric(pd.concat(all_components, ignore_index=True)) if all_components else pd.DataFrame()
    missing = pd.concat(all_missing, ignore_index=True) if all_missing else pd.DataFrame()
    groups = round_numeric(group_trade_residuals(trade))
    exit_reasons = round_numeric(summarize_exit_reasons(stage))
    drivers = round_numeric(summarize_primary_drivers(trade))
    top = trade.sort_values("abs_profit_diff", ascending=False).head(40).copy()

    export_csv(components, OUT_DIR / "exec_model_residual_gap_components.csv")
    export_csv(trade, OUT_DIR / "exec_model_residual_trade_decomposition.csv")
    export_csv(stage, OUT_DIR / "exec_model_residual_stage_decomposition.csv")
    export_csv(groups, OUT_DIR / "exec_model_residual_group_summary.csv")
    export_csv(exit_reasons, OUT_DIR / "exec_model_residual_exit_reason_summary.csv")
    export_csv(drivers, OUT_DIR / "exec_model_residual_primary_driver_summary.csv")
    export_csv(top, OUT_DIR / "exec_model_residual_top_trades.csv")
    export_csv(missing, OUT_DIR / "exec_model_residual_missing_stage_groups.csv")
    write_report(components, groups, exit_reasons, drivers, trade, stage, missing)

    print(components.to_string(index=False))
    print()
    print(groups.head(12).to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
