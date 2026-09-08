# -*- coding: utf-8 -*-
"""Full-chain prototype for the P0 bridge subset mt5_0005 / mt5_0019.

This prototype excludes mt5_0068 because its +90 Layer3 boundary failed. It
builds two bridge signal rows from data-axis evidence, replays Python Stage
PnL from M30 bars, then reruns dynamic risk and ledger mapping. MT5 ledger
profit is used only as the comparison target, never as Python PnL input.
"""
from __future__ import annotations


import sys
from pathlib import Path

import pandas as pd


ROOT = Path(r"F:\use_code\MTA5_l")
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_SCRIPT_DIR = ROOT / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(ROOT_SCRIPT_DIR))
sys.path.insert(0, str(ROOT))

import _stage12_combo_test as stage_replay  # noqa: E402
import simulate_dynamic_risk_alignment as dyn  # noqa: E402
import map_python_mt5_ledger_trades as mapper  # noqa: E402


STRATEGY_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

SIGNAL_ROOT = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714"
SIGNAL_DIR = SIGNAL_ROOT / "python_h2_context_q2early"
M30_SHIFT90 = SIGNAL_ROOT / "m30_prepared_with_mt5_shift90.csv"

CURRENT_INPUT_DIR = VALIDATION_DIR / "dynamic_risk_inputs_shift90_metadatafix_20260714"
CURRENT_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_shift90_metadatafix_close_retry_20260714"
CURRENT_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_shift90_metadatafix_close_retry_20260714"
LEDGER_DIR = VALIDATION_DIR / "mt5_full_close_retry_fix_20260714"

P0_BRIDGE_DIR = VALIDATION_DIR / "p0_data_axis_bridge_prototype_20260715"
MT5_0068_AUDIT_DIR = VALIDATION_DIR / "mt5_0068_layer3_time_axis_boundary_20260715"

OUT_DIR = VALIDATION_DIR / "p0_subset_full_chain_bridge_20260715"
PROTO_INPUT_DIR = VALIDATION_DIR / "dynamic_risk_inputs_p0_subset_bridge_20260715"
PROTO_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_p0_subset_bridge_20260715"
PROTO_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_p0_subset_bridge_20260715"

SUBSET_IDS = ("mt5_0005", "mt5_0019")
EXCLUDED_IDS = ("mt5_0068",)
SOURCE_VARIANT = "p0_subset_m15_slot1_data_axis_bridge_20260715"

STAGE1_R = 2.0
STAGE2_TRAIL_R = 1.5
STAGE2_FORCE_R = 4.0
SPEC_LO = 5.0
SPEC_HI = 35.0


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def find_signal_file(*tokens: str) -> Path:
    for path in SIGNAL_DIR.glob("*.csv"):
        if all(token in path.name for token in tokens):
            return path
    raise FileNotFoundError(f"Cannot find signal file with tokens: {tokens}")


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"L", "LONG", "BUY", "1"}:
        return "BUY"
    if text in {"S", "SHORT", "SELL", "-1"}:
        return "SELL"
    return text


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
    if any(tag in text for tag in ["slot1", "bridge", "replace", "rescue"]):
        return "M15 SLOT1"
    return "M30 CLOSE"


def load_current_layer3_columns() -> list[str]:
    layer3 = read_csv(find_signal_file("Layer3"))
    return list(layer3.columns)


def load_m30() -> pd.DataFrame:
    m30 = read_csv(M30_SHIFT90).copy()
    m30["date"] = pd.to_datetime(m30["date"], errors="coerce")
    return m30.sort_values("date").reset_index(drop=True)


def build_bridge_signals() -> pd.DataFrame:
    bridge = read_csv(P0_BRIDGE_DIR / "p0_bridge_raw_candidates.csv").copy()
    bridge = bridge[bridge["mt5_trade_id"].isin(SUBSET_IDS)].copy()
    bridge = bridge[bridge["picked_bridge_pass"].astype(str).str.lower().isin(["true", "1"])].copy()
    if set(bridge["mt5_trade_id"]) != set(SUBSET_IDS):
        raise RuntimeError("Expected both subset IDs to pass picked_bridge_pass")

    excluded = read_csv(MT5_0068_AUDIT_DIR / "mt5_0068_boundary_decision.csv")
    excluded_decision = excluded["decision"].astype(str).iloc[0] if not excluded.empty else ""
    if "do_not_include" not in excluded_decision:
        raise RuntimeError("mt5_0068 audit does not explicitly exclude it from +90 full-chain")

    m30 = load_m30()
    m30_lookup = {pd.Timestamp(v): int(i) for i, v in enumerate(m30["date"])}
    layer3_cols = load_current_layer3_columns()

    rows: list[dict[str, object]] = []
    for _, src in bridge.iterrows():
        date = pd.to_datetime(src["date"], errors="coerce")
        if date not in m30_lookup:
            raise RuntimeError(f"M30 shifted date missing for bridge signal: {src['mt5_trade_id']} {date}")
        i = m30_lookup[date]
        row = {col: "" for col in layer3_cols}
        row.update(
            {
                "anchor_i": i,
                "i": i,
                "date": date,
                "entry_time": pd.to_datetime(src["entry_time"], errors="coerce"),
                "mode": src["mode"],
                "dir": src["dir"],
                "entry": float(src["entry"]),
                "stop": float(src["stop"]),
                "sd": float(src["sd"]),
                "exit_i": "",
                "won": "",
                "pnl": pd.NA,
                "variant": "p0_subset_m15_slot1_data_axis_bridge",
                "Bias_5": float(src["Bias_5"]),
                "Bias_13": float(src["Bias_13"]),
                "Bias_55": float(src["Bias_55"]),
                "gap": "",
                "spec_pass": True,
                "spec_reason": "ok",
                "trigger": "M15 SLOT1",
                "layer3_eval_time": pd.to_datetime(src["layer3_eval_time"], errors="coerce"),
                "Bias_5_ea": float(src["Bias_5"]),
                "layer3_threshold_ea": float(src["layer3_threshold_ea"]),
                "layer3_pass_ea": True,
                "bridge_mt5_trade_id": src["mt5_trade_id"],
                "bridge_source": "p0_subset_full_chain_bridge",
            }
        )
        rows.append(row)
    out = pd.DataFrame(rows)
    return out.sort_values("date").reset_index(drop=True)


def replay_bridge_stage(bridge_signals: pd.DataFrame) -> pd.DataFrame:
    m30 = load_m30()
    stage = stage_replay.summarize_variant(m30, bridge_signals, STAGE1_R, STAGE2_TRAIL_R, STAGE2_FORCE_R)
    stage = stage.merge(
        bridge_signals[["date", "mode", "dir", "bridge_mt5_trade_id"]],
        on=["date", "mode", "dir"],
        how="left",
    )
    return stage


def build_bridge_dynamic_inputs(bridge_signals: pd.DataFrame, bridge_stage: pd.DataFrame) -> pd.DataFrame:
    layer3 = bridge_signals.copy()
    stage = bridge_stage.copy()
    key_cols = ["date", "mode", "dir"]
    for frame in (layer3, stage):
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")

    merged = layer3.merge(stage, on=key_cols, how="outer", indicator=True, suffixes=("_signal", "_stage"))
    merged["source"] = "python_mt5"
    merged["source_variant"] = SOURCE_VARIANT
    merged["stop_price_diff"] = (pd.to_numeric(merged["entry"], errors="coerce") - pd.to_numeric(merged["stop"], errors="coerce")).abs()
    merged["stop_pts_spec"] = merged["stop_price_diff"]
    merged["stop_pts_mql5"] = merged["stop_price_diff"] * 1000.0
    merged["signal_stage_pnl_gap"] = pd.to_numeric(merged.get("pnl"), errors="coerce") - pd.to_numeric(merged["total_$"], errors="coerce")
    return merged


def build_proto_inputs(bridge_inputs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    PROTO_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    python_only = read_csv(CURRENT_INPUT_DIR / "python_only_dynamic_risk_inputs.csv")
    current_mt5 = read_csv(CURRENT_INPUT_DIR / "python_mt5_dynamic_risk_inputs.csv")
    proto_mt5 = pd.concat([current_mt5, bridge_inputs], ignore_index=True, sort=False)
    proto_mt5["date"] = pd.to_datetime(proto_mt5["date"], errors="coerce")
    proto_mt5 = proto_mt5.sort_values(["date", "trigger", "mode", "dir"], na_position="last").reset_index(drop=True)

    export_csv(python_only, PROTO_INPUT_DIR / "python_only_dynamic_risk_inputs.csv")
    export_csv(proto_mt5, PROTO_INPUT_DIR / "python_mt5_dynamic_risk_inputs.csv")

    summary = pd.DataFrame(
        [
            {
                "source": "python_only",
                "rows": int(len(python_only)),
                "invalid_spec_rows": invalid_spec_count(python_only),
                "output": str(PROTO_INPUT_DIR / "python_only_dynamic_risk_inputs.csv"),
            },
            {
                "source": "python_mt5",
                "rows": int(len(proto_mt5)),
                "invalid_spec_rows": invalid_spec_count(proto_mt5),
                "output": str(PROTO_INPUT_DIR / "python_mt5_dynamic_risk_inputs.csv"),
            },
        ]
    )
    export_csv(summary, PROTO_INPUT_DIR / "dynamic_risk_input_prepare_summary.csv")
    write_text(
        PROTO_INPUT_DIR / "dynamic_risk_input_prepare_report.md",
        "# Dynamic risk inputs - P0 subset bridge\n\n" + markdown_table(summary),
    )
    return python_only, proto_mt5


def invalid_spec_count(frame: pd.DataFrame) -> int:
    vals = pd.to_numeric(frame["stop_pts_spec"], errors="coerce")
    return int(((vals < SPEC_LO) | (vals > SPEC_HI)).sum())


def run_dynamic_alignment() -> pd.DataFrame:
    PROTO_DYNAMIC_DIR.mkdir(parents=True, exist_ok=True)
    dyn.LEDGER_DIR = LEDGER_DIR
    sources = [
        dyn.DynamicSource("python_only", PROTO_INPUT_DIR / "python_only_dynamic_risk_inputs.csv"),
        dyn.DynamicSource("python_mt5", PROTO_INPUT_DIR / "python_mt5_dynamic_risk_inputs.csv"),
    ]

    mt5_df, mt5_summary = dyn.build_mt5_ledger_summary()
    export_csv(mt5_df, PROTO_DYNAMIC_DIR / "mt5_ledger_unique_signals.csv")

    summaries: list[dict[str, object]] = []
    overlap_rows: list[dict[str, object]] = []
    for cfg in sources:
        detail, summary = dyn.simulate_dynamic_source(cfg)
        summary["source_variant"] = SOURCE_VARIANT if cfg.name == "python_mt5" else "baseline"
        detail["source_variant"] = SOURCE_VARIANT if cfg.name == "python_mt5" else "baseline"
        export_csv(detail, PROTO_DYNAMIC_DIR / f"{cfg.name}_dynamic_risk_trades.csv")

        overlap = dyn.compare_key_overlap(detail, mt5_df, cfg.name)
        export_csv(overlap, PROTO_DYNAMIC_DIR / f"{cfg.name}_vs_mt5_ledger_key_overlap.csv")
        counts = overlap["match_status"].value_counts()
        overlap_rows.append(
            {
                "source": cfg.name,
                "shared": int(counts.get("shared", 0)),
                "python_only": int(counts.get("python_only", 0)),
                "mt5_only": int(counts.get("mt5_only", 0)),
            }
        )
        summaries.append(summary)

    mt5_summary["source_variant"] = "mt5_full_close_retry_fix_20260714"
    summary_df = pd.DataFrame(summaries + [mt5_summary])
    overlap_summary = pd.DataFrame(overlap_rows)
    export_csv(summary_df, PROTO_DYNAMIC_DIR / "dynamic_risk_compare_summary.csv")
    export_csv(overlap_summary, PROTO_DYNAMIC_DIR / "dynamic_risk_key_overlap_summary.csv")
    write_text(
        PROTO_DYNAMIC_DIR / "dynamic_risk_alignment_report.md",
        "# Dynamic Risk Alignment - P0 subset bridge\n\n## Summary\n\n"
        + markdown_table(summary_df)
        + "\n\n## Exact Key Overlap\n\n"
        + markdown_table(overlap_summary),
    )
    return summary_df


def run_mapping() -> pd.DataFrame:
    mapper.INPUT_DIR = PROTO_DYNAMIC_DIR
    mapper.OUT_DIR = PROTO_MAPPING_DIR
    mapper.main()
    return read_csv(PROTO_MAPPING_DIR / "unique_match_summary.csv")


def load_current_summaries() -> tuple[pd.DataFrame, pd.DataFrame]:
    return (
        read_csv(CURRENT_DYNAMIC_DIR / "dynamic_risk_compare_summary.csv"),
        read_csv(CURRENT_MAPPING_DIR / "unique_match_summary.csv"),
    )


def direct_gap(summary: pd.DataFrame, source: str) -> float:
    py = summary[summary["source"] == source].iloc[0]
    mt5 = summary[summary["source"] == "mt5_ledger"].iloc[0]
    return float(py["final_balance"]) - float(mt5["final_balance"])


def build_decision_matrix(
    bridge_stage: pd.DataFrame,
    bridge_inputs: pd.DataFrame,
    current_dynamic: pd.DataFrame,
    proto_dynamic: pd.DataFrame,
    current_mapping: pd.DataFrame,
    proto_mapping: pd.DataFrame,
) -> pd.DataFrame:
    current_py = current_dynamic[current_dynamic["source"] == "python_mt5"].iloc[0]
    proto_py = proto_dynamic[proto_dynamic["source"] == "python_mt5"].iloc[0]
    current_map = current_mapping[current_mapping["source"] == "python_mt5"].iloc[0]
    proto_map = proto_mapping[proto_mapping["source"] == "python_mt5"].iloc[0]
    current_gap = direct_gap(current_dynamic, "python_mt5")
    proto_gap = direct_gap(proto_dynamic, "python_mt5")
    current_input = read_csv(CURRENT_INPUT_DIR / "python_mt5_dynamic_risk_inputs.csv")
    proto_input = read_csv(PROTO_INPUT_DIR / "python_mt5_dynamic_risk_inputs.csv")

    return pd.DataFrame(
        [
            {
                "variant": "current_metadatafix",
                "python_mt5_trades": int(current_py["trade_count"]),
                "python_mt5_final_balance": float(current_py["final_balance"]),
                "mt5_final_balance": float(current_dynamic[current_dynamic["source"] == "mt5_ledger"].iloc[0]["final_balance"]),
                "direct_gap": round(current_gap, 6),
                "matched_unique": int(current_map["matched_unique"]),
                "reliable_tier_matched": int(current_map["reliable_tier_matched"]),
                "relaxed_tier_matched": int(current_map["relaxed_tier_matched"]),
                "python_unmatched": int(current_map["python_unmatched"]),
                "mt5_unmatched": int(current_map["mt5_unmatched"]),
                "matched_profit_diff": float(current_map["matched_profit_diff"]),
                "invalid_spec_rows": invalid_spec_count(current_input),
                "bridge_rows": 0,
                "bridge_stage_total_$": 0.0,
            },
            {
                "variant": "p0_subset_mt5_0005_0019",
                "python_mt5_trades": int(proto_py["trade_count"]),
                "python_mt5_final_balance": float(proto_py["final_balance"]),
                "mt5_final_balance": float(proto_dynamic[proto_dynamic["source"] == "mt5_ledger"].iloc[0]["final_balance"]),
                "direct_gap": round(proto_gap, 6),
                "direct_gap_delta_vs_current": round(proto_gap - current_gap, 6),
                "matched_unique": int(proto_map["matched_unique"]),
                "reliable_tier_matched": int(proto_map["reliable_tier_matched"]),
                "reliable_tier_delta": int(proto_map["reliable_tier_matched"]) - int(current_map["reliable_tier_matched"]),
                "relaxed_tier_matched": int(proto_map["relaxed_tier_matched"]),
                "python_unmatched": int(proto_map["python_unmatched"]),
                "mt5_unmatched": int(proto_map["mt5_unmatched"]),
                "matched_profit_diff": float(proto_map["matched_profit_diff"]),
                "matched_profit_diff_delta": round(float(proto_map["matched_profit_diff"]) - float(current_map["matched_profit_diff"]), 6),
                "matched_unique_delta": int(proto_map["matched_unique"]) - int(current_map["matched_unique"]),
                "mt5_unmatched_delta": int(proto_map["mt5_unmatched"]) - int(current_map["mt5_unmatched"]),
                "invalid_spec_rows": invalid_spec_count(proto_input),
                "invalid_spec_rows_delta": invalid_spec_count(proto_input) - invalid_spec_count(current_input),
                "bridge_rows": int(len(bridge_inputs)),
                "bridge_stage_total_$": round(float(pd.to_numeric(bridge_stage["total_$"], errors="coerce").sum()), 6),
            },
        ]
    )


def bridge_vs_ledger(bridge_stage: pd.DataFrame) -> pd.DataFrame:
    mt5 = read_csv(PROTO_DYNAMIC_DIR / "mt5_ledger_unique_signals.csv")
    mt5["mt5_trade_id"] = [f"mt5_{i + 1:04d}" for i in range(len(mt5))]
    mt5 = mt5[mt5["mt5_trade_id"].isin(SUBSET_IDS)][
        ["mt5_trade_id", "signal_anchor_time", "trigger_family", "mode_family", "dir", "stop_pts_spec", "net_profit"]
    ].copy()
    bridge = bridge_stage.rename(columns={"bridge_mt5_trade_id": "mt5_trade_id"}).copy()
    bridge["python_stage_fixed_total_$"] = pd.to_numeric(bridge["total_$"], errors="coerce")
    out = bridge.merge(mt5, on="mt5_trade_id", how="left", suffixes=("_python", "_mt5"))
    out["fixed_total_minus_mt5_net"] = out["python_stage_fixed_total_$"] - pd.to_numeric(out["net_profit"], errors="coerce")
    cols = [
        "mt5_trade_id",
        "date",
        "mode",
        "dir_python",
        "stage1_pnl",
        "stage2_pnl",
        "stage3_pnl",
        "total_points",
        "python_stage_fixed_total_$",
        "net_profit",
        "fixed_total_minus_mt5_net",
        "stage1_exit",
        "stage2_exit",
        "stage3_exit",
    ]
    return out[[c for c in cols if c in out.columns]]


def render_report(
    decision: pd.DataFrame,
    bridge_signals: pd.DataFrame,
    bridge_stage: pd.DataFrame,
    bridge_compare: pd.DataFrame,
    proto_mapping: pd.DataFrame,
) -> str:
    variant = decision[decision["variant"] == "p0_subset_mt5_0005_0019"].iloc[0]
    merge_gate = (
        variant.get("invalid_spec_rows_delta", 999) <= 0
        and variant.get("matched_unique_delta", -999) >= 0
        and variant.get("direct_gap_delta_vs_current", -999) >= 0
        and variant.get("matched_profit_diff_delta", -999) >= 0
    )
    signal_gate = (
        variant.get("invalid_spec_rows_delta", 999) <= 0
        and variant.get("matched_unique_delta", -999) >= 0
        and variant.get("direct_gap_delta_vs_current", -999) >= 0
    )
    lines = [
        "# P0 subset full-chain bridge prototype",
        "",
        "## Scope",
        "",
        "- Included: `mt5_0005`, `mt5_0019`.",
        "- Excluded: `mt5_0068`, because the +90 Layer3/time-axis audit failed.",
        "- Python PnL is generated by Stage replay on M30 bars. MT5 ledger net profit is comparison-only.",
        "",
        "## Decision",
        "",
        f"- Signal admission gate pass: `{signal_gate}`.",
        f"- Merge gate pass: `{merge_gate}`.",
        f"- Direct gap delta vs current: `{variant.get('direct_gap_delta_vs_current', '')}`.",
        f"- matched_unique delta: `{variant.get('matched_unique_delta', '')}`.",
        f"- reliable_tier delta: `{variant.get('reliable_tier_delta', '')}`.",
        f"- mt5_unmatched delta: `{variant.get('mt5_unmatched_delta', '')}`.",
        f"- matched_profit_diff delta: `{variant.get('matched_profit_diff_delta', '')}`.",
        f"- invalid spec rows delta: `{variant.get('invalid_spec_rows_delta', '')}`.",
        "- Interpretation: the two rows are valid signal recoveries, but Python Stage/dynamic PnL remains far below MT5 ledger PnL.",
        "",
        "## Decision Matrix",
        "",
        markdown_table(decision),
        "",
        "## Bridge Signals",
        "",
        markdown_table(
            bridge_signals[
                [
                    "bridge_mt5_trade_id",
                    "date",
                    "entry_time",
                    "mode",
                    "dir",
                    "entry",
                    "stop",
                    "sd",
                    "Bias_5_ea",
                    "layer3_threshold_ea",
                ]
            ]
        ),
        "",
        "## Bridge Stage Replay",
        "",
        markdown_table(bridge_stage),
        "",
        "## Bridge Python Stage vs MT5 Ledger",
        "",
        markdown_table(bridge_compare),
        "",
        "## Mapping Summary",
        "",
        markdown_table(proto_mapping),
        "",
        "## Output Files",
        "",
        "- `bridge_layer3_rows.csv`",
        "- `bridge_stage_replay_rows.csv`",
        "- `bridge_dynamic_input_rows.csv`",
        "- `bridge_stage_vs_mt5_ledger.csv`",
        "- `decision_matrix.csv`",
        f"- `{PROTO_INPUT_DIR}`",
        f"- `{PROTO_DYNAMIC_DIR}`",
        f"- `{PROTO_MAPPING_DIR}`",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bridge_signals = build_bridge_signals()
    bridge_stage = replay_bridge_stage(bridge_signals)
    bridge_inputs = build_bridge_dynamic_inputs(bridge_signals, bridge_stage)
    build_proto_inputs(bridge_inputs)
    proto_dynamic = run_dynamic_alignment()
    proto_mapping = run_mapping()
    current_dynamic, current_mapping = load_current_summaries()
    decision = build_decision_matrix(bridge_stage, bridge_inputs, current_dynamic, proto_dynamic, current_mapping, proto_mapping)
    bridge_compare = bridge_vs_ledger(bridge_stage)

    export_csv(bridge_signals, OUT_DIR / "bridge_layer3_rows.csv")
    export_csv(bridge_stage, OUT_DIR / "bridge_stage_replay_rows.csv")
    export_csv(bridge_inputs, OUT_DIR / "bridge_dynamic_input_rows.csv")
    export_csv(bridge_compare, OUT_DIR / "bridge_stage_vs_mt5_ledger.csv")
    export_csv(decision, OUT_DIR / "decision_matrix.csv")
    write_text(
        OUT_DIR / "p0_subset_full_chain_bridge_review.md",
        render_report(decision, bridge_signals, bridge_stage, bridge_compare, proto_mapping),
    )
    write_text(OUT_DIR / "README.md", "# P0 subset full-chain bridge\n\nSee `p0_subset_full_chain_bridge_review.md`.\n")
    print(decision.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
