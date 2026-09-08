# -*- coding: utf-8 -*-
"""Prototype MT5-compatible valuation and StageLots for Python dynamic risk.

This is a non-destructive execution-model prototype. It does not change the
signal set, EA code, or baseline dynamic-risk snapshots. It only reruns Python
dynamic-risk accounting with MT5/EA-style contract value and StageLots.
"""
from __future__ import annotations


import math
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import map_python_mt5_ledger_trades as mapper  # noqa: E402
import simulate_dynamic_risk_alignment as base_dyn  # noqa: E402


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

LEDGER_DIR = VALIDATION_DIR / "mt5_full_close_retry_fix_20260714"

CURRENT_INPUT_DIR = VALIDATION_DIR / "dynamic_risk_inputs_shift90_metadatafix_20260714"
CURRENT_BASE_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_shift90_metadatafix_close_retry_20260714"
CURRENT_BASE_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_shift90_metadatafix_close_retry_20260714"
CURRENT_EXEC_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_metadatafix_20260715"
CURRENT_EXEC_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_metadatafix_20260715"

P0_INPUT_DIR = VALIDATION_DIR / "dynamic_risk_inputs_p0_subset_bridge_20260715"
P0_BASE_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_p0_subset_bridge_20260715"
P0_BASE_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_p0_subset_bridge_20260715"
P0_EXEC_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_exec_model_p0_subset_bridge_20260715"
P0_EXEC_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_p0_subset_bridge_20260715"

OUT_DIR = VALIDATION_DIR / "execution_model_normalization_20260715"

START_CAPITAL = 500.0
RISK_PCT = 3.0
MIN_LOT = 0.01
MAX_LOT = 10.0
LOT_STEP = 0.01

# MT5 close-retry ledger for XAUUSDm implies about $100 per 1.0 price point
# per 1.00 lot, equivalent to about $0.1 per MQL point/tick when point=0.001.
MT5_TICK_VALUE_PER_LOT = 0.1
MT5_PRICE_POINT_VALUE_PER_LOT = 100.0

TARGET_MT5_IDS = ["mt5_0005", "mt5_0019"]


@dataclass(frozen=True)
class Scenario:
    name: str
    input_dir: Path
    baseline_dynamic_dir: Path
    baseline_mapping_dir: Path
    exec_dynamic_dir: Path
    exec_mapping_dir: Path
    python_mt5_variant: str


SCENARIOS = [
    Scenario(
        name="metadatafix",
        input_dir=CURRENT_INPUT_DIR,
        baseline_dynamic_dir=CURRENT_BASE_DYNAMIC_DIR,
        baseline_mapping_dir=CURRENT_BASE_MAPPING_DIR,
        exec_dynamic_dir=CURRENT_EXEC_DYNAMIC_DIR,
        exec_mapping_dir=CURRENT_EXEC_MAPPING_DIR,
        python_mt5_variant="exec_model_metadatafix_20260715",
    ),
    Scenario(
        name="p0_subset_bridge",
        input_dir=P0_INPUT_DIR,
        baseline_dynamic_dir=P0_BASE_DYNAMIC_DIR,
        baseline_mapping_dir=P0_BASE_MAPPING_DIR,
        exec_dynamic_dir=P0_EXEC_DYNAMIC_DIR,
        exec_mapping_dir=P0_EXEC_MAPPING_DIR,
        python_mt5_variant="exec_model_p0_subset_bridge_20260715",
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


def normalize_lots(lot: float) -> float:
    step = LOT_STEP
    lot = max(MIN_LOT, min(MAX_LOT, lot))
    lot = math.floor((lot / step) + 1e-12) * step
    return round(max(MIN_LOT, lot), 2)


def calc_total_lot_mt5(balance: float, stop_pts_mql5: float) -> float:
    if stop_pts_mql5 <= 0:
        return MIN_LOT
    risk = balance * RISK_PCT / 100.0
    pts_val = MT5_TICK_VALUE_PER_LOT * stop_pts_mql5
    if pts_val <= 0:
        return MIN_LOT
    lot = risk / pts_val
    # EA CalcLot() calls NormalizeDouble(lot, 2) before clamp/floor.
    lot = round(lot + 1e-12, 2)
    lot = max(MIN_LOT, min(MAX_LOT, lot))
    lot = math.floor((lot / LOT_STEP) + 1e-12) * LOT_STEP
    return round(max(MIN_LOT, lot), 2)


def calc_stage_lots_mt5(balance: float, stop_pts_mql5: float) -> tuple[float, float, float, float]:
    total_lot = calc_total_lot_mt5(balance, stop_pts_mql5)
    base_lot = total_lot / 3.0
    if base_lot < MIN_LOT:
        base_lot = MIN_LOT
    stage1 = normalize_lots(base_lot * 0.5)
    stage2 = normalize_lots(base_lot * 1.0)
    stage3 = normalize_lots(base_lot * 1.5)
    return total_lot, stage1, stage2, stage3


def simulate_dynamic_source_mt5_model(cfg: base_dyn.DynamicSource) -> tuple[pd.DataFrame, dict[str, object]]:
    df = read_csv(cfg.path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)

    details: list[dict[str, object]] = []
    balance = START_CAPITAL

    for _, row in df.iterrows():
        stop_pts_mql5 = float(pd.to_numeric(pd.Series([row["stop_pts_mql5"]]), errors="coerce").iloc[0])
        total_lot, stage1_lot, stage2_lot, stage3_lot = calc_stage_lots_mt5(balance, stop_pts_mql5)
        stage1_dynamic = float(row["stage1_pnl"]) * stage1_lot * MT5_PRICE_POINT_VALUE_PER_LOT
        stage2_dynamic = float(row["stage2_pnl"]) * stage2_lot * MT5_PRICE_POINT_VALUE_PER_LOT
        stage3_dynamic = float(row["stage3_pnl"]) * stage3_lot * MT5_PRICE_POINT_VALUE_PER_LOT
        dynamic_total = stage1_dynamic + stage2_dynamic + stage3_dynamic
        balance_after = balance + dynamic_total

        details.append(
            {
                "source": cfg.name,
                "date": row["date"],
                "dir": row["dir"],
                "mode": row["mode"],
                "mode_family": base_dyn.mode_family(row["mode"]),
                "variant": row.get("variant", ""),
                "trigger_family": base_dyn.trigger_family_from_variant(row.get("variant", "")),
                "entry": row["entry"],
                "stop": row["stop"],
                "stop_pts_spec": row["stop_pts_spec"],
                "stop_pts_mql5": row["stop_pts_mql5"],
                "balance_before": round(balance, 6),
                "dynamic_total_lot": total_lot,
                "stage1_lot": stage1_lot,
                "stage2_lot": stage2_lot,
                "stage3_lot": stage3_lot,
                "stage1_dynamic_$": round(stage1_dynamic, 6),
                "stage2_dynamic_$": round(stage2_dynamic, 6),
                "stage3_dynamic_$": round(stage3_dynamic, 6),
                "dynamic_total_$": round(dynamic_total, 6),
                "balance_after": round(balance_after, 6),
                "fixed_total_$": row["total_$"],
                "fixed_equity_$": row["equity_$"],
                "stage1_exit": row["stage1_exit"],
                "stage2_exit": row["stage2_exit"],
                "stage3_exit": row["stage3_exit"],
                "exec_model": "mt5_value_stage_lots_parity",
                "mt5_tick_value_per_lot": MT5_TICK_VALUE_PER_LOT,
                "mt5_price_point_value_per_lot": MT5_PRICE_POINT_VALUE_PER_LOT,
            }
        )
        balance = balance_after

    out = pd.DataFrame(details)
    total_profit = float(out["dynamic_total_$"].sum()) if not out.empty else 0.0
    win_count = int((out["dynamic_total_$"] > 0).sum()) if not out.empty else 0
    any_sl_mask = (
        (out["stage1_exit"] == "SL hit")
        | out["stage2_exit"].astype(str).str.contains("SL", regex=False)
        | out["stage3_exit"].astype(str).str.contains("SL", regex=False)
    ) if not out.empty else pd.Series(dtype=bool)
    full_sl_mask = (
        (out["stage1_exit"] == "SL hit")
        & out["stage2_exit"].astype(str).str.contains("SL", regex=False)
        & out["stage3_exit"].astype(str).str.contains("SL", regex=False)
    ) if not out.empty else pd.Series(dtype=bool)
    summary = {
        "source": cfg.name,
        "trade_count": int(len(out)),
        "final_balance": round(START_CAPITAL + total_profit, 6),
        "dynamic_total_profit": round(total_profit, 6),
        "win_count": win_count,
        "win_rate_pct": round((win_count / len(out) * 100.0) if len(out) else 0.0, 4),
        "any_stage_sl_count": int(any_sl_mask.sum()) if not out.empty else 0,
        "all_stage_sl_count": int(full_sl_mask.sum()) if not out.empty else 0,
        "avg_stop_pts_spec": round(float(out["stop_pts_spec"].mean()), 6) if not out.empty else 0.0,
        "avg_total_lot": round(float(out["dynamic_total_lot"].mean()), 6) if not out.empty else 0.0,
        "exec_model": "mt5_value_stage_lots_parity",
    }
    return out, summary


def run_dynamic_alignment(scenario: Scenario) -> pd.DataFrame:
    scenario.exec_dynamic_dir.mkdir(parents=True, exist_ok=True)
    base_dyn.LEDGER_DIR = LEDGER_DIR

    sources = [
        base_dyn.DynamicSource("python_only", scenario.input_dir / "python_only_dynamic_risk_inputs.csv"),
        base_dyn.DynamicSource("python_mt5", scenario.input_dir / "python_mt5_dynamic_risk_inputs.csv"),
    ]

    mt5_df, mt5_summary = base_dyn.build_mt5_ledger_summary()
    mt5_summary["source_variant"] = "mt5_full_close_retry_fix_20260714"
    mt5_summary["exec_model"] = "mt5_ledger_reference"
    export_csv(mt5_df, scenario.exec_dynamic_dir / "mt5_ledger_unique_signals.csv")

    summaries: list[dict[str, object]] = []
    overlap_rows: list[dict[str, object]] = []
    for cfg in sources:
        detail, summary = simulate_dynamic_source_mt5_model(cfg)
        source_variant = scenario.python_mt5_variant if cfg.name == "python_mt5" else f"{scenario.name}_python_only_exec_model"
        detail["source_variant"] = source_variant
        summary["source_variant"] = source_variant
        summaries.append(summary)
        export_csv(detail, scenario.exec_dynamic_dir / f"{cfg.name}_dynamic_risk_trades.csv")

        overlap = base_dyn.compare_key_overlap(detail, mt5_df, cfg.name)
        export_csv(overlap, scenario.exec_dynamic_dir / f"{cfg.name}_vs_mt5_ledger_key_overlap.csv")
        counts = overlap["match_status"].value_counts()
        overlap_rows.append(
            {
                "source": cfg.name,
                "shared": int(counts.get("shared", 0)),
                "python_only": int(counts.get("python_only", 0)),
                "mt5_only": int(counts.get("mt5_only", 0)),
            }
        )

    summary_df = pd.DataFrame(summaries + [mt5_summary])
    overlap_summary = pd.DataFrame(overlap_rows)
    export_csv(summary_df, scenario.exec_dynamic_dir / "dynamic_risk_compare_summary.csv")
    export_csv(overlap_summary, scenario.exec_dynamic_dir / "dynamic_risk_key_overlap_summary.csv")
    write_text(
        scenario.exec_dynamic_dir / "dynamic_risk_alignment_report.md",
        f"# Dynamic Risk Alignment - execution model normalization ({scenario.name})\n\n"
        "## Summary\n\n"
        + markdown_table(summary_df)
        + "\n\n## Exact Key Overlap\n\n"
        + markdown_table(overlap_summary)
        + "\n\n## Notes\n\n"
        + "- This is a non-destructive prototype.\n"
        + f"- MT5 tick value per 1.00 lot: `{MT5_TICK_VALUE_PER_LOT}`.\n"
        + f"- MT5 price-point value per 1.00 lot: `{MT5_PRICE_POINT_VALUE_PER_LOT}`.\n"
        + "- Stage lots follow EA CalcLot()/StageLots() approximation.",
    )
    return summary_df


def run_mapping(scenario: Scenario) -> pd.DataFrame:
    mapper.INPUT_DIR = scenario.exec_dynamic_dir
    mapper.OUT_DIR = scenario.exec_mapping_dir
    mapper.main()
    return read_csv(scenario.exec_mapping_dir / "unique_match_summary.csv")


def invalid_spec_count(input_dir: Path, source: str = "python_mt5") -> int:
    frame = read_csv(input_dir / f"{source}_dynamic_risk_inputs.csv")
    vals = pd.to_numeric(frame["stop_pts_spec"], errors="coerce")
    return int(((vals < 5.0) | (vals > 35.0)).sum())


def direct_gap(dynamic_summary: pd.DataFrame, source: str = "python_mt5") -> float:
    py = dynamic_summary[dynamic_summary["source"] == source].iloc[0]
    mt5 = dynamic_summary[dynamic_summary["source"] == "mt5_ledger"].iloc[0]
    return float(py["final_balance"]) - float(mt5["final_balance"])


def source_row(frame: pd.DataFrame, source: str) -> pd.Series:
    return frame[frame["source"] == source].iloc[0]


def build_decision_rows(scenario: Scenario) -> list[dict[str, object]]:
    base_dynamic = read_csv(scenario.baseline_dynamic_dir / "dynamic_risk_compare_summary.csv")
    exec_dynamic = read_csv(scenario.exec_dynamic_dir / "dynamic_risk_compare_summary.csv")
    base_mapping = read_csv(scenario.baseline_mapping_dir / "unique_match_summary.csv")
    exec_mapping = read_csv(scenario.exec_mapping_dir / "unique_match_summary.csv")

    rows: list[dict[str, object]] = []
    for model, dynamic, mapping, dynamic_dir, mapping_dir in [
        ("baseline", base_dynamic, base_mapping, scenario.baseline_dynamic_dir, scenario.baseline_mapping_dir),
        ("exec_model", exec_dynamic, exec_mapping, scenario.exec_dynamic_dir, scenario.exec_mapping_dir),
    ]:
        py = source_row(dynamic, "python_mt5")
        mt5 = source_row(dynamic, "mt5_ledger")
        mp = source_row(mapping, "python_mt5")
        rows.append(
            {
                "scenario": scenario.name,
                "model": model,
                "python_mt5_trades": int(py["trade_count"]),
                "python_mt5_final_balance": float(py["final_balance"]),
                "mt5_final_balance": float(mt5["final_balance"]),
                "direct_gap": round(direct_gap(dynamic), 6),
                "abs_direct_gap": abs(round(direct_gap(dynamic), 6)),
                "matched_unique": int(mp["matched_unique"]),
                "reliable_tier_matched": int(mp["reliable_tier_matched"]),
                "relaxed_tier_matched": int(mp["relaxed_tier_matched"]),
                "python_unmatched": int(mp["python_unmatched"]),
                "mt5_unmatched": int(mp["mt5_unmatched"]),
                "matched_python_profit": float(mp["matched_python_profit"]),
                "matched_mt5_profit": float(mp["matched_mt5_profit"]),
                "matched_profit_diff": float(mp["matched_profit_diff"]),
                "abs_matched_profit_diff": abs(float(mp["matched_profit_diff"])),
                "invalid_spec_rows": invalid_spec_count(scenario.input_dir),
                "dynamic_dir": str(dynamic_dir),
                "mapping_dir": str(mapping_dir),
            }
        )

    base = rows[0]
    exec_row = rows[1]
    exec_row["direct_gap_delta_vs_baseline"] = round(float(exec_row["direct_gap"]) - float(base["direct_gap"]), 6)
    exec_row["abs_direct_gap_delta_vs_baseline"] = round(
        float(exec_row["abs_direct_gap"]) - float(base["abs_direct_gap"]), 6
    )
    exec_row["matched_profit_diff_delta_vs_baseline"] = round(
        float(exec_row["matched_profit_diff"]) - float(base["matched_profit_diff"]), 6
    )
    exec_row["abs_matched_profit_diff_delta_vs_baseline"] = round(
        float(exec_row["abs_matched_profit_diff"]) - float(base["abs_matched_profit_diff"]), 6
    )
    exec_row["matched_unique_delta_vs_baseline"] = int(exec_row["matched_unique"]) - int(base["matched_unique"])
    exec_row["reliable_tier_delta_vs_baseline"] = int(exec_row["reliable_tier_matched"]) - int(base["reliable_tier_matched"])
    exec_row["relaxed_tier_delta_vs_baseline"] = int(exec_row["relaxed_tier_matched"]) - int(base["relaxed_tier_matched"])
    return rows


def build_target_gap_summary() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model, mapping_dir in [
        ("p0_baseline", P0_BASE_MAPPING_DIR),
        ("p0_exec_model", P0_EXEC_MAPPING_DIR),
    ]:
        matches = read_csv(mapping_dir / "python_mt5_mt5_unique_matches.csv")
        for mt5_id in TARGET_MT5_IDS:
            hit = matches[matches["mt5_trade_id"] == mt5_id]
            if hit.empty:
                rows.append({"model": model, "mt5_trade_id": mt5_id, "matched": False})
                continue
            row = hit.iloc[0]
            profit_diff = float(row["profit_diff"])
            rows.append(
                {
                    "model": model,
                    "mt5_trade_id": mt5_id,
                    "matched": True,
                    "match_tier": row["match_tier"],
                    "py_trade_id": row["py_trade_id"],
                    "py_profit": float(row["py_profit"]),
                    "mt5_profit": float(row["mt5_profit"]),
                    "profit_diff_py_minus_mt5": profit_diff,
                    "abs_profit_diff": abs(profit_diff),
                    "py_stage_lots": stage_lots_for_trade(model, str(row["py_trade_id"])),
                }
            )
    out = pd.DataFrame(rows)
    base_lookup = {
        row["mt5_trade_id"]: float(row["abs_profit_diff"])
        for _, row in out[out["model"] == "p0_baseline"].iterrows()
        if bool(row.get("matched", False))
    }
    deltas: list[object] = []
    for _, row in out.iterrows():
        if row["model"] != "p0_exec_model" or not bool(row.get("matched", False)):
            deltas.append("")
            continue
        deltas.append(round(float(row["abs_profit_diff"]) - base_lookup.get(row["mt5_trade_id"], 0.0), 6))
    out["abs_profit_diff_delta_vs_p0_baseline"] = deltas
    return out


def stage_lots_for_trade(model: str, py_trade_id: str) -> str:
    if model == "p0_baseline":
        dynamic_path = P0_BASE_DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"
    else:
        dynamic_path = P0_EXEC_DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv"
    try:
        idx = int(str(py_trade_id).rsplit("_", 1)[1]) - 1
    except (IndexError, ValueError):
        return ""
    dynamic = read_csv(dynamic_path)
    if idx >= len(dynamic):
        return ""
    row = dynamic.iloc[idx]
    return f"{float(row['stage1_lot']):.2f}/{float(row['stage2_lot']):.2f}/{float(row['stage3_lot']):.2f}"


def write_report(decision: pd.DataFrame, targets: pd.DataFrame) -> None:
    exec_rows = decision[decision["model"] == "exec_model"].copy()
    p0_exec = exec_rows[exec_rows["scenario"] == "p0_subset_bridge"].iloc[0]
    metadata_exec = exec_rows[exec_rows["scenario"] == "metadatafix"].iloc[0]
    prototype_gate = (
        float(p0_exec["abs_direct_gap_delta_vs_baseline"]) < 0
        and float(p0_exec["abs_matched_profit_diff_delta_vs_baseline"]) < 0
        and int(p0_exec["matched_unique_delta_vs_baseline"]) >= 0
        and int(p0_exec["reliable_tier_delta_vs_baseline"]) >= 0
        and float(metadata_exec["abs_direct_gap_delta_vs_baseline"]) < 0
        and float(metadata_exec["abs_matched_profit_diff_delta_vs_baseline"]) < 0
        and int(metadata_exec["matched_unique_delta_vs_baseline"]) >= 0
        and int(metadata_exec["reliable_tier_delta_vs_baseline"]) >= 0
    )
    lines = [
        "# Python-MT5 execution-model normalization prototype",
        "",
        "## Scope",
        "",
        "- Non-destructive prototype; no EA change and no signal-set change.",
        "- Recalculates Python dynamic risk using MT5-compatible value and EA StageLots parity.",
        f"- MT5 tick value per 1.00 lot: `{MT5_TICK_VALUE_PER_LOT}`.",
        f"- MT5 price-point value per 1.00 lot: `{MT5_PRICE_POINT_VALUE_PER_LOT}`.",
        "",
        "## Decision",
        "",
        f"- Execution-model prototype gate pass: `{bool(prototype_gate)}`.",
        "- Interpretation: pass requires full-sample absolute direct-gap and matched-profit improvement without reducing matched/reliable coverage.",
        "- This is not a final merge approval; residual full-sample PnL gap must still be decomposed.",
        "",
        "## Decision Matrix",
        "",
        markdown_table(decision),
        "",
        "## P0 Target Rows",
        "",
        markdown_table(targets),
        "",
        "## Output Files",
        "",
        "- `execution_model_decision_matrix.csv`",
        "- `execution_model_p0_target_gap_summary.csv`",
        f"- `{CURRENT_EXEC_DYNAMIC_DIR}`",
        f"- `{CURRENT_EXEC_MAPPING_DIR}`",
        f"- `{P0_EXEC_DYNAMIC_DIR}`",
        f"- `{P0_EXEC_MAPPING_DIR}`",
    ]
    write_text(OUT_DIR / "execution_model_normalization_review.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base_dyn.LEDGER_DIR = LEDGER_DIR

    for scenario in SCENARIOS:
        run_dynamic_alignment(scenario)
        run_mapping(scenario)

    decision_rows: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        decision_rows.extend(build_decision_rows(scenario))
    decision = pd.DataFrame(decision_rows)
    export_csv(decision, OUT_DIR / "execution_model_decision_matrix.csv")

    targets = build_target_gap_summary()
    export_csv(targets, OUT_DIR / "execution_model_p0_target_gap_summary.csv")
    write_report(decision, targets)

    print(decision.to_string(index=False))
    print()
    print(targets.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
