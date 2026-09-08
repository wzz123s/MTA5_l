# -*- coding: utf-8 -*-
"""Summarize the effect of the M15 rescue metadata fix across the validation chain."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"
OUT_DIR = VALIDATION_DIR / "metadatafix_chain_effect_20260714"

OLD_SIGNAL = DATA_DIR / "signals_mt5_shift90_20260712" / "python_h2_context_q2early" / "最终信号_Layer3入选.csv"
NEW_SIGNAL = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early" / "最终信号_Layer3入选.csv"
OLD_DYNAMIC = VALIDATION_DIR / "dynamic_risk_alignment_shift90_close_retry_20260714" / "dynamic_risk_compare_summary.csv"
NEW_DYNAMIC = VALIDATION_DIR / "dynamic_risk_alignment_shift90_metadatafix_close_retry_20260714" / "dynamic_risk_compare_summary.csv"
OLD_MAPPING = VALIDATION_DIR / "mapped_trade_alignment_shift90_close_retry_20260714" / "unique_match_summary.csv"
NEW_MAPPING = VALIDATION_DIR / "mapped_trade_alignment_shift90_metadatafix_close_retry_20260714" / "unique_match_summary.csv"
OLD_CAUSE = VALIDATION_DIR / "unmatched_signal_cause_shift90_close_retry_20260714" / "python_mt5_python_unmatched_cause.csv"
NEW_CAUSE = VALIDATION_DIR / "unmatched_signal_cause_shift90_metadatafix_close_retry_20260714" / "python_mt5_python_unmatched_cause.csv"


FOCUS_IDS = ["python_mt5_0079", "python_mt5_0073", "python_mt5_0075"]


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


def actual_spec_pass(frame: pd.DataFrame) -> pd.Series:
    sd = pd.to_numeric(frame["sd"], errors="coerce")
    return sd.between(5.0, 35.0, inclusive="both")


def signal_spec_summary(path: Path, label: str) -> dict[str, object]:
    df = read_csv(path)
    rescue = df[df["variant"].astype(str) == "ea_slot1_runtime_rescue"].copy()
    rescue["actual_spec_pass"] = actual_spec_pass(rescue)
    rescue["spec_flag_false"] = rescue["spec_pass"].astype(str).str.lower().eq("false")
    rescue["stale_false_but_actual_ok"] = rescue["spec_flag_false"] & rescue["actual_spec_pass"]
    return {
        "snapshot": label,
        "layer3_rows": int(len(df)),
        "rescue_rows": int(len(rescue)),
        "rescue_spec_false_labels": int(rescue["spec_flag_false"].sum()),
        "rescue_stale_false_but_actual_ok": int(rescue["stale_false_but_actual_ok"].sum()),
        "rescue_actual_spec_fail": int((~rescue["actual_spec_pass"]).sum()),
    }


def compare_dynamic() -> pd.DataFrame:
    old = read_csv(OLD_DYNAMIC)
    new = read_csv(NEW_DYNAMIC)
    rows = []
    for source in ["python_mt5", "mt5_ledger"]:
        old_row = old[old["source"] == source].iloc[0]
        new_row = new[new["source"] == source].iloc[0]
        rows.append(
            {
                "source": source,
                "old_trade_count": old_row["trade_count"],
                "new_trade_count": new_row["trade_count"],
                "old_final_balance": old_row["final_balance"],
                "new_final_balance": new_row["final_balance"],
                "final_balance_delta": round(float(new_row["final_balance"]) - float(old_row["final_balance"]), 6),
            }
        )
    return pd.DataFrame(rows)


def compare_mapping() -> pd.DataFrame:
    old = read_csv(OLD_MAPPING)
    new = read_csv(NEW_MAPPING)
    rows = []
    for source in ["python_mt5"]:
        old_row = old[old["source"] == source].iloc[0]
        new_row = new[new["source"] == source].iloc[0]
        rows.append(
            {
                "source": source,
                "old_matched_unique": old_row["matched_unique"],
                "new_matched_unique": new_row["matched_unique"],
                "old_python_unmatched": old_row["python_unmatched"],
                "new_python_unmatched": new_row["python_unmatched"],
                "old_mt5_unmatched": old_row["mt5_unmatched"],
                "new_mt5_unmatched": new_row["mt5_unmatched"],
            }
        )
    return pd.DataFrame(rows)


def compare_focus_causes() -> pd.DataFrame:
    old = read_csv(OLD_CAUSE)
    new = read_csv(NEW_CAUSE)
    rows = []
    for trade_id in FOCUS_IDS:
        old_row = old[old["trade_id"].astype(str) == trade_id].iloc[0]
        new_row = new[new["trade_id"].astype(str) == trade_id].iloc[0]
        rows.append(
            {
                "trade_id": trade_id,
                "target_time": new_row["target_time"],
                "profit": new_row["profit"],
                "old_cause": old_row["cause_bucket"],
                "new_cause": new_row["cause_bucket"],
                "new_mt5_abs_minutes": new_row["mt5_abs_minutes"],
                "new_mt5_date": new_row["mt5_date"],
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    spec_summary = pd.DataFrame(
        [
            signal_spec_summary(OLD_SIGNAL, "before_metadatafix"),
            signal_spec_summary(NEW_SIGNAL, "after_metadatafix"),
        ]
    )
    dynamic = compare_dynamic()
    mapping = compare_mapping()
    focus = compare_focus_causes()

    export_csv(spec_summary, OUT_DIR / "signal_rescue_spec_metadata_summary.csv")
    export_csv(dynamic, OUT_DIR / "dynamic_risk_before_after_summary.csv")
    export_csv(mapping, OUT_DIR / "mapping_before_after_summary.csv")
    export_csv(focus, OUT_DIR / "top_case_cause_shift.csv")

    report = [
        "# Metadatafix Chain Effect 20260714",
        "",
        "## Signal Metadata",
        "",
        markdown_table(spec_summary),
        "",
        "## Dynamic Risk",
        "",
        markdown_table(dynamic),
        "",
        "## Mapping",
        "",
        markdown_table(mapping),
        "",
        "## Top Case Cause Shift",
        "",
        markdown_table(focus),
        "",
        "## Decision",
        "",
        "- The rescue metadata fix removes stale `spec_pass=False` labels for M15 SLOT1 runtime rescue rows.",
        "- Dynamic final balances and unique mapping counts are unchanged.",
        "- `python_mt5_0073` and `python_mt5_0079` move from ordinary unique-match conflict to low-confidence far-candidate conflict.",
        "- `python_mt5_0075` remains the next real nearby unique-match conflict / duplicate continuation case.",
    ]
    write_text(OUT_DIR / "metadatafix_chain_effect.md", "\n".join(report))
    write_text(OUT_DIR / "README.md", "# metadatafix_chain_effect_20260714\n\nBefore/after validation for M15 rescue spec metadata and unmatched cause threshold.")

    print(spec_summary.to_string(index=False))
    print(dynamic.to_string(index=False))
    print(mapping.to_string(index=False))
    print(focus.to_string(index=False))


if __name__ == "__main__":
    main()
