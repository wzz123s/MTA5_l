# -*- coding: utf-8 -*-
"""Run a lightweight full-chain check for the duplicate-continuation filtered prototype."""
from __future__ import annotations


import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import map_python_mt5_ledger_trades as mapper  # noqa: E402


STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"
OUT_DIR = VALIDATION_DIR / "duplicate_filtered_full_chain_review_20260714"

CURRENT_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_shift90_metadatafix_close_retry_20260714"
FILTER_PROTO_DIR = VALIDATION_DIR / "m15_slot1_duplicate_continuation_prototype_20260714"
MAPPING_CURRENT_DIR = VALIDATION_DIR / "mapped_trade_alignment_shift90_metadatafix_close_retry_20260714"
MAPPING_FILTERED_DIR = VALIDATION_DIR / "mapped_trade_alignment_shift90_metadatafix_duplicatefilter_20260714"
POST_BRIDGE_DIR = VALIDATION_DIR / "post_bridge_remaining_p1_review_20260714"

RUNTIME_DIRECT_GAP = 477.153976
MATCHED_RESIDUAL_SUM = 42.738057


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.to_markdown(index=False)


def prepare_mapping_input() -> Path:
    input_dir = OUT_DIR / "mapping_input"
    input_dir.mkdir(parents=True, exist_ok=True)
    for name in ["python_only_dynamic_risk_trades.csv", "mt5_ledger_unique_signals.csv"]:
        frame = read_csv(CURRENT_DYNAMIC_DIR / name)
        export_csv(frame, input_dir / name)
    filtered = read_csv(FILTER_PROTO_DIR / "python_mt5_trades_suppress_duplicate_continuation.csv")
    export_csv(filtered, input_dir / "python_mt5_dynamic_risk_trades.csv")
    return input_dir


def run_mapping(input_dir: Path) -> None:
    mapper.INPUT_DIR = input_dir
    mapper.OUT_DIR = MAPPING_FILTERED_DIR
    mapper.main()


def compare_mapping() -> pd.DataFrame:
    old = read_csv(MAPPING_CURRENT_DIR / "unique_match_summary.csv")
    new = read_csv(MAPPING_FILTERED_DIR / "unique_match_summary.csv")
    rows = []
    for source in ["python_mt5"]:
        old_row = old[old["source"] == source].iloc[0]
        new_row = new[new["source"] == source].iloc[0]
        rows.append(
            {
                "source": source,
                "current_python_trades": old_row["python_trades"],
                "filtered_python_trades": new_row["python_trades"],
                "current_matched_unique": old_row["matched_unique"],
                "filtered_matched_unique": new_row["matched_unique"],
                "current_python_unmatched": old_row["python_unmatched"],
                "filtered_python_unmatched": new_row["python_unmatched"],
                "current_mt5_unmatched": old_row["mt5_unmatched"],
                "filtered_mt5_unmatched": new_row["mt5_unmatched"],
            }
        )
    return pd.DataFrame(rows)


def projection_summary() -> pd.DataFrame:
    signal_summary = read_csv(FILTER_PROTO_DIR / "duplicate_continuation_signal_gap_summary.csv")
    suppressed = float(
        signal_summary.loc[
            signal_summary["metric"] == "suppressed_signal_gap_effect_sum",
            "value",
        ].iloc[0]
    )
    post_bridge = read_csv(POST_BRIDGE_DIR / "post_bridge_priority_summary.csv")
    current_signal_gap = float(
        post_bridge.loc[
            post_bridge["metric"] == "signal_set_gap_effect_sum_no_fund_change",
            "value",
        ].iloc[0]
    )
    projected_signal_gap = current_signal_gap - suppressed
    projected_runtime_gap = MATCHED_RESIDUAL_SUM + projected_signal_gap
    return pd.DataFrame(
        [
            {
                "metric": "current_runtime_direct_gap",
                "value": RUNTIME_DIRECT_GAP,
                "note": "Current runtime-style adjusted direct gap.",
            },
            {
                "metric": "current_signal_set_gap",
                "value": current_signal_gap,
                "note": "Post-bridge signal-set gap before duplicate suppression.",
            },
            {
                "metric": "suppressed_signal_gap_effect",
                "value": suppressed,
                "note": "Net Python-unmatched gap effect of the duplicate-continuation candidates.",
            },
            {
                "metric": "projected_signal_set_gap",
                "value": round(projected_signal_gap, 6),
                "note": "Current signal gap minus suppressed duplicate continuation effect.",
            },
            {
                "metric": "projected_runtime_gap",
                "value": round(projected_runtime_gap, 6),
                "note": "Matched residual sum plus projected signal-set gap.",
            },
        ]
    )


def top_unmatched_after_filter() -> pd.DataFrame:
    py_unmatched = read_csv(MAPPING_FILTERED_DIR / "python_mt5_unmatched_python_trades.csv")
    py_unmatched["dynamic_total_$"] = pd.to_numeric(py_unmatched["dynamic_total_$"], errors="coerce")
    py_unmatched["abs_dynamic_total_$"] = py_unmatched["dynamic_total_$"].abs()
    return py_unmatched.sort_values("abs_dynamic_total_$", ascending=False).head(10).reset_index(drop=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    input_dir = prepare_mapping_input()
    run_mapping(input_dir)
    mapping = compare_mapping()
    projection = projection_summary()
    top_unmatched = top_unmatched_after_filter()

    export_csv(mapping, OUT_DIR / "mapping_before_after_summary.csv")
    export_csv(projection, OUT_DIR / "runtime_gap_projection_summary.csv")
    export_csv(top_unmatched, OUT_DIR / "filtered_top_python_unmatched.csv")

    report = [
        "# Duplicate Filtered Full-Chain Review 20260714",
        "",
        "## Mapping Before/After",
        "",
        markdown_table(mapping),
        "",
        "## Runtime Gap Projection",
        "",
        markdown_table(projection),
        "",
        "## Filtered Top Python-Unmatched",
        "",
        markdown_table(top_unmatched[["py_trade_id", "date", "trigger_family", "mode_family", "mode", "dynamic_total_$", "abs_dynamic_total_$"]]),
        "",
        "## Decision",
        "",
        "- The filtered prototype removes two Python-MT5 trades and keeps matched_unique unchanged.",
        "- The projected runtime gap improves only by the suppressed signal-set effect; this is a projection, not a full runtime re-simulation.",
        "- Continue with the next largest non-bridge P1 after confirming whether this projection is worth turning into a signal-generation rule.",
    ]
    write_text(OUT_DIR / "duplicate_filtered_full_chain_review.md", "\n".join(report))
    write_text(OUT_DIR / "README.md", "# duplicate_filtered_full_chain_review_20260714\n\nLightweight mapping and runtime-gap projection for the duplicate-continuation filtered prototype.")

    print(mapping.to_string(index=False))
    print(projection.to_string(index=False))


if __name__ == "__main__":
    main()
