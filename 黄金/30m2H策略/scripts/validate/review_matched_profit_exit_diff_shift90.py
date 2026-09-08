# -*- coding: utf-8 -*-
"""Break down matched shift90 profit/exit differences."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = next(p for p in ROOT.iterdir() if p.is_dir() and p.name.startswith("30m2H"))
DATA_DIR = STRATEGY_DIR / "data"
EQ_DIR = DATA_DIR / "validation" / "trigger_family_equivalence_shift90_20260713"
DYNAMIC_DIR = DATA_DIR / "validation" / "dynamic_risk_alignment_shift90_20260713"
MT5_LEDGER_DIR = DATA_DIR / "validation" / "mt5_ledger_deinitfix_full_20260713_v1"
OUT_DIR = DATA_DIR / "validation" / "matched_profit_exit_diff_shift90_20260713"

POLICY_FILE = EQ_DIR / "bidirectional_m30_m15_90_profit20_selected_matches.csv"


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def normalize_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"S", "SELL"}:
        return "SELL"
    if text in {"B", "BUY", "L"}:
        return "BUY"
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


def trigger_family_from_tag(value: object) -> str:
    text = str(value).replace("[", "").replace("]", "").strip()
    if text.startswith("M15"):
        return "M15 SLOT1"
    if text.startswith("M30"):
        return "M30 CLOSE"
    return text


def profit_bucket(value: object) -> str:
    try:
        v = abs(float(value))
    except Exception:
        return "none"
    if pd.isna(v):
        return "none"
    if v <= 1:
        return "<=1"
    if v <= 5:
        return "<=5"
    if v <= 20:
        return "<=20"
    if v <= 50:
        return "<=50"
    if v <= 100:
        return "<=100"
    return ">100"


def price_bucket(value: object) -> str:
    try:
        v = abs(float(value))
    except Exception:
        return "none"
    if pd.isna(v):
        return "none"
    if v <= 0.01:
        return "<=0.01"
    if v <= 0.1:
        return "<=0.1"
    if v <= 1:
        return "<=1"
    if v <= 5:
        return "<=5"
    return ">5"


def load_python_trades() -> pd.DataFrame:
    df = pd.read_csv(DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv", encoding="utf-8-sig")
    df = df.copy()
    df["py_trade_id"] = [f"python_mt5_{i + 1:04d}" for i in range(len(df))]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df[
        [
            "py_trade_id",
            "date",
            "dynamic_total_lot",
            "stage1_lot",
            "stage2_lot",
            "stage3_lot",
            "stage1_dynamic_$",
            "stage2_dynamic_$",
            "stage3_dynamic_$",
            "stage1_exit",
            "stage2_exit",
            "stage3_exit",
            "fixed_total_$",
            "fixed_equity_$",
        ]
    ].copy()


def load_mt5_stage_ledger() -> pd.DataFrame:
    ledger = pd.read_csv(MT5_LEDGER_DIR / "30m2H_strategy_trade_ledger.csv", encoding="utf-8-sig")
    ledger = ledger.copy()
    ledger["signal_anchor_time"] = pd.to_datetime(ledger["signal_anchor_time"], format="%Y.%m.%d %H:%M", errors="coerce")
    ledger["trigger_family"] = ledger["trigger_tag"].map(trigger_family_from_tag)
    ledger["mode_family"] = ledger["signal_src"].map(mode_family)
    ledger["dir_norm"] = ledger["dir"].map(normalize_dir)
    for col in ["stage", "signal_entry", "signal_stop", "fill_price", "actual_stop", "lots", "stop_pts", "exit_price", "net_profit"]:
        ledger[col] = pd.to_numeric(ledger[col], errors="coerce")

    key_cols = ["signal_anchor_time", "trigger_family", "mode_family", "dir_norm"]
    rows: list[dict[str, object]] = []
    for _, grp in ledger.sort_values(["signal_anchor_time", "stage"]).groupby(key_cols, sort=False):
        grp = grp.sort_values("stage")
        rows.append(
            {
                "mt5_signal_anchor_time": grp["signal_anchor_time"].iloc[0],
                "mt5_trigger_family_join": grp["trigger_family"].iloc[0],
                "mt5_mode_family_join": grp["mode_family"].iloc[0],
                "mt5_dir_norm_join": grp["dir_norm"].iloc[0],
                "mt5_stage_count": int(len(grp)),
                "mt5_signal_entry": float(grp["signal_entry"].iloc[0]),
                "mt5_signal_stop": float(grp["signal_stop"].iloc[0]),
                "mt5_avg_fill_price": float(grp["fill_price"].mean()),
                "mt5_actual_stop": float(grp["actual_stop"].iloc[0]),
                "mt5_total_lots": float(grp["lots"].sum()),
                "mt5_stage_lots": ",".join(f"{float(v):.2f}" for v in grp["lots"].tolist()),
                "mt5_stage_net_profit": ",".join(f"{float(v):.2f}" for v in grp["net_profit"].tolist()),
                "mt5_exit_prices": ",".join(f"{float(v):.3f}" for v in grp["exit_price"].tolist()),
                "mt5_local_exit_reasons": ";".join(str(v) for v in grp["local_exit_reason"].tolist()),
                "mt5_deal_reasons": ";".join(str(v) for v in grp["deal_reason"].tolist()),
                "mt5_stage_list": ",".join(str(int(v)) for v in grp["stage"].tolist()),
            }
        )
    out = pd.DataFrame(rows)
    out["mt5_trade_id"] = [f"mt5_{i + 1:04d}" for i in range(len(out))]
    return out


def classify_primary(row: pd.Series) -> str:
    structural = str(row.get("effective_match_tier", "")).startswith("equiv_")
    profit_abs = row.get("profit_abs_diff")
    stop_diff = row.get("stop_pts_spec_diff")
    entry_fill_diff = row.get("entry_fill_diff")
    any_sl_same = str(row.get("any_sl_same", "")).lower() in {"true", "1"}
    all_sl_same = str(row.get("all_sl_same", "")).lower() in {"true", "1"}

    try:
        p = abs(float(profit_abs))
    except Exception:
        p = float("nan")
    try:
        s = abs(float(stop_diff))
    except Exception:
        s = float("nan")
    try:
        e = abs(float(entry_fill_diff))
    except Exception:
        e = float("nan")

    if p <= 5 and any_sl_same and all_sl_same:
        return "pnl_aligned"
    if structural and p > 20:
        return "structural_equiv_but_pnl_diff"
    py_exit_text = ";".join(
        str(row.get(col, ""))
        for col in ["stage1_exit", "stage2_exit", "stage3_exit"]
    )
    mt5_reason_text = str(row.get("mt5_deal_reasons", ""))
    if p > 20 and any(tag in py_exit_text for tag in ["trail", "TP", "forced", "M30 merged cross"]):
        return "stage_exit_detail_diff"
    if p > 20 and ("EXPERT" in mt5_reason_text):
        return "mt5_expert_exit_diff"
    if not any_sl_same or not all_sl_same:
        return "exit_reason_diff"
    if pd.notna(s) and s > 1:
        return "stop_distance_diff"
    if pd.notna(e) and e > 1:
        return "entry_fill_diff"
    if p > 20:
        return "profit_diff_unexplained_by_basic_flags"
    return "minor_or_mixed_diff"


def build_details() -> pd.DataFrame:
    selected = pd.read_csv(POLICY_FILE, encoding="utf-8-sig")
    py = load_python_trades()
    mt5_stage = load_mt5_stage_ledger()
    details = selected.merge(py, on="py_trade_id", how="left", suffixes=("", "_py_detail"))
    details = details.merge(mt5_stage, on="mt5_trade_id", how="left")
    for col in ["py_entry", "py_stop", "mt5_signal_entry", "mt5_signal_stop", "mt5_avg_fill_price", "mt5_actual_stop", "profit_diff", "profit_abs_diff", "stop_pts_spec_diff"]:
        if col in details.columns:
            details[col] = pd.to_numeric(details[col], errors="coerce")
    details["entry_signal_diff"] = details["py_entry"] - details["mt5_signal_entry"]
    details["entry_fill_diff"] = details["py_entry"] - details["mt5_avg_fill_price"]
    details["stop_price_diff"] = details["py_stop"] - details["mt5_actual_stop"]
    details["profit_diff_bucket"] = details["profit_abs_diff"].map(profit_bucket)
    details["entry_fill_diff_bucket"] = details["entry_fill_diff"].map(price_bucket)
    details["stop_price_diff_bucket"] = details["stop_price_diff"].map(price_bucket)
    details["stop_pts_diff_bucket"] = details["stop_pts_spec_diff"].map(price_bucket)
    details["py_stage_lots"] = (
        details["stage1_lot"].map(lambda v: f"{float(v):.2f}" if pd.notna(v) else "")
        + ","
        + details["stage2_lot"].map(lambda v: f"{float(v):.2f}" if pd.notna(v) else "")
        + ","
        + details["stage3_lot"].map(lambda v: f"{float(v):.2f}" if pd.notna(v) else "")
    )
    details["py_stage_dynamic_profit"] = (
        details["stage1_dynamic_$"].map(lambda v: f"{float(v):.2f}" if pd.notna(v) else "")
        + ","
        + details["stage2_dynamic_$"].map(lambda v: f"{float(v):.2f}" if pd.notna(v) else "")
        + ","
        + details["stage3_dynamic_$"].map(lambda v: f"{float(v):.2f}" if pd.notna(v) else "")
    )
    details["lot_total_diff"] = pd.to_numeric(details["dynamic_total_lot"], errors="coerce") - pd.to_numeric(details["mt5_total_lots"], errors="coerce")
    details["structural_equivalent"] = details["effective_match_tier"].astype(str).str.startswith("equiv_")
    details["pnl_equivalent_20"] = details["profit_abs_diff"] <= 20
    details["primary_diff_class"] = details.apply(classify_primary, axis=1)
    return details


def grouped(frame: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=cols + ["rows"])
    return (
        frame.groupby(cols, dropna=False)
        .size()
        .reset_index(name="rows")
        .sort_values(cols + ["rows"], ascending=[True] * len(cols) + [False])
    )


def render_report(details: pd.DataFrame, summaries: dict[str, pd.DataFrame], top_diff: pd.DataFrame) -> str:
    lines = [
        "# Matched Profit / Exit Difference Review - shift90",
        "",
        "## Primary Diff Class Summary",
        "",
        summaries["primary"].to_markdown(index=False),
        "",
        "## Tier / Profit Bucket Summary",
        "",
        summaries["tier_profit"].to_markdown(index=False),
        "",
        "## SL Consistency Summary",
        "",
        summaries["sl"].to_markdown(index=False),
        "",
        "## Structural Equivalence Summary",
        "",
        summaries["structural"].to_markdown(index=False),
        "",
        "## Top Profit Differences",
        "",
        top_diff.to_markdown(index=False),
        "",
        "## Interpretation",
        "",
        "- `pnl_aligned` means profit difference is within 5 dollars and SL flags agree.",
        "- `structural_equiv_but_pnl_diff` means M30/M15 trigger labels can be structurally reconciled, but PnL is still too different for full equivalence.",
        "- Large residuals should be traced through stage exits, fill/entry differences, and MT5 deal reasons before changing EA signal logic.",
        "",
        "## Output Files",
        "",
        "- `matched_profit_exit_diff_details.csv`",
        "- `matched_profit_exit_primary_summary.csv`",
        "- `matched_profit_exit_tier_profit_summary.csv`",
        "- `matched_profit_exit_sl_summary.csv`",
        "- `matched_profit_exit_structural_summary.csv`",
        "- `matched_profit_exit_top_diffs.csv`",
    ]
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    details = build_details()
    detail_cols = [
        "policy",
        "effective_match_tier",
        "py_trade_id",
        "mt5_trade_id",
        "py_date",
        "mt5_aligned_time",
        "abs_time_diff_minutes",
        "dir_norm",
        "py_trigger_family",
        "mt5_trigger_family",
        "py_mode_family",
        "mt5_mode_family",
        "py_mode",
        "mt5_signal_src",
        "py_variant",
        "py_profit",
        "mt5_profit",
        "profit_diff",
        "profit_abs_diff",
        "profit_diff_bucket",
        "py_entry",
        "mt5_signal_entry",
        "mt5_avg_fill_price",
        "entry_fill_diff",
        "entry_fill_diff_bucket",
        "py_stop",
        "mt5_actual_stop",
        "stop_price_diff",
        "stop_price_diff_bucket",
        "py_stop_pts_spec",
        "mt5_stop_pts_spec",
        "stop_pts_spec_diff",
        "dynamic_total_lot",
        "mt5_total_lots",
        "lot_total_diff",
        "py_stage_lots",
        "mt5_stage_lots",
        "py_stage_dynamic_profit",
        "mt5_stage_net_profit",
        "py_any_sl",
        "mt5_any_sl",
        "py_all_sl",
        "mt5_all_sl",
        "any_sl_same",
        "all_sl_same",
        "stage1_exit",
        "stage2_exit",
        "stage3_exit",
        "mt5_exit_prices",
        "mt5_deal_reasons",
        "structural_equivalent",
        "pnl_equivalent_20",
        "primary_diff_class",
    ]
    detail_view = details[[c for c in detail_cols if c in details.columns]].copy()
    top_diff = detail_view.sort_values("profit_abs_diff", ascending=False).head(20)

    summaries = {
        "primary": grouped(details, ["primary_diff_class"]),
        "tier_profit": grouped(details, ["effective_match_tier", "profit_diff_bucket"]),
        "sl": grouped(details, ["any_sl_same", "all_sl_same", "profit_diff_bucket"]),
        "structural": grouped(details, ["structural_equivalent", "pnl_equivalent_20", "primary_diff_class"]),
    }

    export_csv(detail_view, OUT_DIR / "matched_profit_exit_diff_details.csv")
    export_csv(summaries["primary"], OUT_DIR / "matched_profit_exit_primary_summary.csv")
    export_csv(summaries["tier_profit"], OUT_DIR / "matched_profit_exit_tier_profit_summary.csv")
    export_csv(summaries["sl"], OUT_DIR / "matched_profit_exit_sl_summary.csv")
    export_csv(summaries["structural"], OUT_DIR / "matched_profit_exit_structural_summary.csv")
    export_csv(top_diff, OUT_DIR / "matched_profit_exit_top_diffs.csv")
    write_text(OUT_DIR / "matched_profit_exit_diff_report.md", render_report(detail_view, summaries, top_diff))

    print(summaries["primary"].to_string(index=False))
    print()
    print(summaries["structural"].to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
