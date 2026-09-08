# -*- coding: utf-8 -*-
"""Rerun Python-MT5 remap/residual review on the stage-state full MT5 ledger.

This wrapper is intentionally non-destructive: it reuses the existing dynamic
risk, mapping, and residual decomposition modules, but writes all artifacts to
stage-state-specific output directories.
"""
from __future__ import annotations


import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import review_execution_model_normalization_20260715 as exec_norm  # noqa: E402
import review_exec_model_residual_pnl_decomposition_20260715 as residual  # noqa: E402


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

STAGE_STATE_LEDGER_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"
OUT_DIR = VALIDATION_DIR / "stage_state_full_remap_residual_review_20260716"
RESIDUAL_OUT_DIR = VALIDATION_DIR / "exec_model_residual_stage_state_20260716"

MT5_LEDGER_VARIANT = "mt5_stage_state_full_2018_20260707_20260716"


@dataclass(frozen=True)
class StageStateScenario:
    name: str
    input_dir: Path
    previous_dynamic_dir: Path
    previous_mapping_dir: Path
    new_dynamic_dir: Path
    new_mapping_dir: Path
    python_mt5_variant: str


SCENARIOS = [
    StageStateScenario(
        name="metadatafix",
        input_dir=VALIDATION_DIR / "dynamic_risk_inputs_shift90_metadatafix_20260714",
        previous_dynamic_dir=VALIDATION_DIR / "dynamic_risk_alignment_exec_model_metadatafix_20260715",
        previous_mapping_dir=VALIDATION_DIR / "mapped_trade_alignment_exec_model_metadatafix_20260715",
        new_dynamic_dir=VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_metadatafix_20260716",
        new_mapping_dir=VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716",
        python_mt5_variant="exec_model_stage_state_metadatafix_20260716",
    ),
    StageStateScenario(
        name="p0_subset_bridge",
        input_dir=VALIDATION_DIR / "dynamic_risk_inputs_p0_subset_bridge_20260715",
        previous_dynamic_dir=VALIDATION_DIR / "dynamic_risk_alignment_exec_model_p0_subset_bridge_20260715",
        previous_mapping_dir=VALIDATION_DIR / "mapped_trade_alignment_exec_model_p0_subset_bridge_20260715",
        new_dynamic_dir=VALIDATION_DIR / "dynamic_risk_alignment_exec_model_stage_state_p0_subset_bridge_20260716",
        new_mapping_dir=VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_p0_subset_bridge_20260716",
        python_mt5_variant="exec_model_stage_state_p0_subset_bridge_20260716",
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


def markdown_table(frame: pd.DataFrame, max_rows: int = 60) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def num(value: object, default: float = 0.0) -> float:
    out = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(out):
        return default
    return float(out)


def source_row(frame: pd.DataFrame, source: str) -> pd.Series:
    hit = frame[frame["source"] == source]
    if hit.empty:
        raise ValueError(f"Missing source={source}")
    return hit.iloc[0]


def scenario_for_exec_norm(scenario: StageStateScenario) -> exec_norm.Scenario:
    return exec_norm.Scenario(
        name=f"stage_state_{scenario.name}",
        input_dir=scenario.input_dir,
        baseline_dynamic_dir=scenario.previous_dynamic_dir,
        baseline_mapping_dir=scenario.previous_mapping_dir,
        exec_dynamic_dir=scenario.new_dynamic_dir,
        exec_mapping_dir=scenario.new_mapping_dir,
        python_mt5_variant=scenario.python_mt5_variant,
    )


def patch_mt5_variant_label(dynamic_dir: Path) -> None:
    summary_path = dynamic_dir / "dynamic_risk_compare_summary.csv"
    if not summary_path.exists():
        return
    summary = read_csv(summary_path)
    if "source_variant" in summary.columns:
        summary.loc[summary["source"] == "mt5_ledger", "source_variant"] = MT5_LEDGER_VARIANT
        export_csv(summary, summary_path)


def run_dynamic_and_mapping() -> None:
    exec_norm.LEDGER_DIR = STAGE_STATE_LEDGER_DIR
    exec_norm.base_dyn.LEDGER_DIR = STAGE_STATE_LEDGER_DIR

    for scenario in SCENARIOS:
        norm_scenario = scenario_for_exec_norm(scenario)
        exec_norm.run_dynamic_alignment(norm_scenario)
        patch_mt5_variant_label(scenario.new_dynamic_dir)
        exec_norm.run_mapping(norm_scenario)


def run_residual_decomposition() -> None:
    residual.LEDGER_DIR = STAGE_STATE_LEDGER_DIR
    residual.OUT_DIR = RESIDUAL_OUT_DIR
    residual.SCENARIOS = [
        residual.Scenario(
            name=f"stage_state_{scenario.name}_exec_model",
            dynamic_dir=scenario.new_dynamic_dir,
            mapping_dir=scenario.new_mapping_dir,
        )
        for scenario in SCENARIOS
    ]
    residual.main()


def ledger_summary() -> pd.DataFrame:
    ledger = read_csv(STAGE_STATE_LEDGER_DIR / "30m2H_strategy_trade_ledger.csv")
    net_profit = pd.to_numeric(ledger["net_profit"], errors="coerce")
    deinit_mask = ledger["local_exit_reason"].astype(str).eq("deinit_history")
    rows = [
        {
            "ledger_dir": MT5_LEDGER_VARIANT,
            "ledger_rows": int(len(ledger)),
            "unique_anchors": int(ledger["signal_anchor_time"].nunique()),
            "deinit_rows": int(deinit_mask.sum()),
            "ledger_net_sum": round(float(net_profit.sum()), 6),
            "stage_groups_with_three_rows": int((ledger.groupby("signal_anchor_time")["stage"].count() == 3).sum()),
        }
    ]
    return pd.DataFrame(rows)


def dynamic_gap(dynamic_dir: Path) -> tuple[pd.Series, pd.Series, float]:
    dynamic = read_csv(dynamic_dir / "dynamic_risk_compare_summary.csv")
    py = source_row(dynamic, "python_mt5")
    mt5 = source_row(dynamic, "mt5_ledger")
    gap = num(py["final_balance"]) - num(mt5["final_balance"])
    return py, mt5, gap


def map_row(mapping_dir: Path) -> pd.Series:
    mapping = read_csv(mapping_dir / "unique_match_summary.csv")
    return source_row(mapping, "python_mt5")


def overlap_row(dynamic_dir: Path) -> pd.Series:
    overlap = read_csv(dynamic_dir / "dynamic_risk_key_overlap_summary.csv")
    return source_row(overlap, "python_mt5")


def residual_row(name: str, components: pd.DataFrame) -> pd.Series:
    key = f"stage_state_{name}_exec_model"
    hit = components[components["scenario"] == key]
    if hit.empty:
        raise ValueError(f"Missing residual scenario={key}")
    return hit.iloc[0]


def build_remap_summary() -> tuple[pd.DataFrame, pd.DataFrame]:
    components = read_csv(RESIDUAL_OUT_DIR / "exec_model_residual_gap_components.csv")
    rows: list[dict[str, object]] = []
    delta_rows: list[dict[str, object]] = []

    for scenario in SCENARIOS:
        new_py, new_mt5, new_direct_gap = dynamic_gap(scenario.new_dynamic_dir)
        old_py, old_mt5, old_direct_gap = dynamic_gap(scenario.previous_dynamic_dir)
        new_map = map_row(scenario.new_mapping_dir)
        old_map = map_row(scenario.previous_mapping_dir)
        new_overlap = overlap_row(scenario.new_dynamic_dir)
        old_overlap = overlap_row(scenario.previous_dynamic_dir)
        comp = residual_row(scenario.name, components)

        rows.append(
            {
                "scenario": scenario.name,
                "python_mt5_trades": int(num(new_py["trade_count"])),
                "python_mt5_final_balance": round(num(new_py["final_balance"]), 6),
                "mt5_trades": int(num(new_mt5["trade_count"])),
                "mt5_final_balance": round(num(new_mt5["final_balance"]), 6),
                "direct_gap_py_minus_mt5": round(new_direct_gap, 6),
                "matched_unique": int(num(new_map["matched_unique"])),
                "reliable_tier_matched": int(num(new_map["reliable_tier_matched"])),
                "relaxed_tier_matched": int(num(new_map["relaxed_tier_matched"])),
                "python_unmatched": int(num(new_map["python_unmatched"])),
                "mt5_unmatched": int(num(new_map["mt5_unmatched"])),
                "matched_profit_diff_py_minus_mt5": round(num(new_map["matched_profit_diff"]), 6),
                "signal_set_gap_py_minus_mt5": round(num(comp["signal_set_gap_py_minus_mt5"]), 6),
                "missing_stage_groups": int(num(comp["missing_stage_groups"])),
                "key_shared": int(num(new_overlap["shared"])),
                "key_python_only": int(num(new_overlap["python_only"])),
                "key_mt5_only": int(num(new_overlap["mt5_only"])),
            }
        )
        delta_rows.append(
            {
                "scenario": scenario.name,
                "previous_mt5_ledger": "mt5_full_close_retry_fix_20260714",
                "new_mt5_ledger": MT5_LEDGER_VARIANT,
                "python_final_delta_new_minus_previous": round(
                    num(new_py["final_balance"]) - num(old_py["final_balance"]), 6
                ),
                "mt5_final_delta_new_minus_previous": round(
                    num(new_mt5["final_balance"]) - num(old_mt5["final_balance"]), 6
                ),
                "direct_gap_delta_new_minus_previous": round(new_direct_gap - old_direct_gap, 6),
                "matched_unique_delta": int(num(new_map["matched_unique"])) - int(num(old_map["matched_unique"])),
                "reliable_tier_delta": int(num(new_map["reliable_tier_matched"]))
                - int(num(old_map["reliable_tier_matched"])),
                "relaxed_tier_delta": int(num(new_map["relaxed_tier_matched"]))
                - int(num(old_map["relaxed_tier_matched"])),
                "python_unmatched_delta": int(num(new_map["python_unmatched"])) - int(num(old_map["python_unmatched"])),
                "mt5_unmatched_delta": int(num(new_map["mt5_unmatched"])) - int(num(old_map["mt5_unmatched"])),
                "matched_profit_diff_delta": round(
                    num(new_map["matched_profit_diff"]) - num(old_map["matched_profit_diff"]), 6
                ),
                "key_shared_delta": int(num(new_overlap["shared"])) - int(num(old_overlap["shared"])),
                "key_python_only_delta": int(num(new_overlap["python_only"])) - int(num(old_overlap["python_only"])),
                "key_mt5_only_delta": int(num(new_overlap["mt5_only"])) - int(num(old_overlap["mt5_only"])),
            }
        )

    return pd.DataFrame(rows), pd.DataFrame(delta_rows)


def export_residual_highlights() -> tuple[pd.DataFrame, pd.DataFrame]:
    trades = read_csv(RESIDUAL_OUT_DIR / "exec_model_residual_trade_decomposition.csv")
    drivers = read_csv(RESIDUAL_OUT_DIR / "exec_model_residual_primary_driver_summary.csv")
    top = trades.sort_values("abs_profit_diff", ascending=False).head(25).copy()
    export_csv(top, OUT_DIR / "stage_state_full_top_residual_trades.csv")
    export_csv(drivers, OUT_DIR / "stage_state_full_residual_primary_driver_summary.csv")
    return top, drivers


def write_report(
    ledger: pd.DataFrame,
    remap: pd.DataFrame,
    delta: pd.DataFrame,
    top: pd.DataFrame,
    drivers: pd.DataFrame,
) -> None:
    metadata = remap[remap["scenario"] == "metadatafix"].iloc[0]
    gate_pass = (
        int(metadata["deinit_rows"]) == 0 if "deinit_rows" in metadata.index else True
    ) and abs(num(metadata["direct_gap_py_minus_mt5"])) <= 500.0
    lines = [
        "# Stage-state full ledger remap and residual review",
        "",
        "## Scope",
        "",
        f"- MT5 ledger: `{STAGE_STATE_LEDGER_DIR}`.",
        "- Reuses execution-model dynamic risk and unique mapping logic.",
        "- Reruns residual decomposition against the stage-state full ledger.",
        "- This is a diagnostic gate only; no EA or Python strategy logic is changed.",
        "",
        "## Gate Decision",
        "",
        f"- Merge gate pass: `{bool(gate_pass)}`.",
        "- Gate rule here: deinit rows must be zero and metadatafix direct gap must be within `$500`.",
        "- The stage-state bug fix removes the deinit artifact, but the full-sample accounting gap must remain blocked if the new MT5 final balance is far from Python-MT5.",
        "",
        "## Ledger Summary",
        "",
        markdown_table(ledger),
        "",
        "## Remap Summary",
        "",
        markdown_table(remap),
        "",
        "## Delta vs Close-retry Execution Model",
        "",
        markdown_table(delta),
        "",
        "## Residual Driver Summary",
        "",
        markdown_table(drivers.head(20)),
        "",
        "## Top Residual Trades",
        "",
        markdown_table(top),
        "",
        "## Interpretation",
        "",
        "- `deinit_rows=0` confirms the stage-state ledger lifecycle fix works at full-sample level.",
        "- If `mt5_final_delta_new_minus_previous` is strongly negative while Python final is unchanged, the remaining issue is not Python risk sizing; it is MT5 stage lifecycle / signal admission / exit behavior after removing the deinit artifact.",
        "- `matched_profit_diff_py_minus_mt5` explains the mapped rows; `signal_set_gap_py_minus_mt5` is the unmatched signal-set contribution.",
        "- Next repair should target the highest residual trades and the extra/lost MT5 anchors before changing broad admission rules.",
        "",
        "## Output Files",
        "",
        "- `stage_state_full_ledger_summary.csv`",
        "- `stage_state_full_remap_summary.csv`",
        "- `stage_state_full_delta_vs_close_retry_exec_model.csv`",
        "- `stage_state_full_top_residual_trades.csv`",
        "- `stage_state_full_residual_primary_driver_summary.csv`",
        f"- `{RESIDUAL_OUT_DIR}`",
        f"- `{SCENARIOS[0].new_dynamic_dir}`",
        f"- `{SCENARIOS[0].new_mapping_dir}`",
        f"- `{SCENARIOS[1].new_dynamic_dir}`",
        f"- `{SCENARIOS[1].new_mapping_dir}`",
    ]
    write_text(OUT_DIR / "stage_state_full_remap_residual_review.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_dynamic_and_mapping()
    run_residual_decomposition()

    ledger = ledger_summary()
    remap, delta = build_remap_summary()
    ledger_deinit = int(ledger.iloc[0]["deinit_rows"])
    remap["deinit_rows"] = ledger_deinit
    top, drivers = export_residual_highlights()

    export_csv(ledger, OUT_DIR / "stage_state_full_ledger_summary.csv")
    export_csv(remap, OUT_DIR / "stage_state_full_remap_summary.csv")
    export_csv(delta, OUT_DIR / "stage_state_full_delta_vs_close_retry_exec_model.csv")
    write_report(ledger, remap, delta, top, drivers)

    print(ledger.to_string(index=False))
    print()
    print(remap.to_string(index=False))
    print()
    print(delta.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
