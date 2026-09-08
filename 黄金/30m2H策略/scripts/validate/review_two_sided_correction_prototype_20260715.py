# -*- coding: utf-8 -*-
"""Two-sided correction accounting prototype.

This diagnostic removes high-confidence Python false positives and injects
selected MT5-only ledger signals as accounting bridge rows. It is not a mergeable
strategy implementation; it measures whether paired deletion/recovery can close
the current signal-set gap before deeper signal-code work.
"""
from __future__ import annotations


import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import map_python_mt5_ledger_trades as mapper  # noqa: E402


STRATEGY_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

CURRENT_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_shift90_metadatafix_close_retry_20260714"
CURRENT_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_shift90_metadatafix_close_retry_20260714"
ROW_IMPACT_DIR = VALIDATION_DIR / "row_level_split_spread_impact_20260715"

OUT_DIR = VALIDATION_DIR / "two_sided_correction_prototype_20260715"
PROTO_DYNAMIC_ROOT = VALIDATION_DIR / "dynamic_risk_alignment_two_sided_correction_20260715"
PROTO_MAPPING_ROOT = VALIDATION_DIR / "mapped_trade_alignment_two_sided_correction_20260715"

START_CAPITAL = 500.0


@dataclass(frozen=True)
class TwoSidedConfig:
    name: str
    remove_priorities: tuple[str, ...]
    recover_priorities: tuple[str, ...]


CONFIGS = [
    TwoSidedConfig(
        "remove_p0_python_only",
        remove_priorities=("P0_remove_high_conf_ea_diag_false_positive",),
        recover_priorities=(),
    ),
    TwoSidedConfig(
        "remove_p0_add_p0_mt5_bridge",
        remove_priorities=("P0_remove_high_conf_ea_diag_false_positive",),
        recover_priorities=("P0_recover_time_axis_positive_mt5_only",),
    ),
    TwoSidedConfig(
        "remove_p0_add_p0p1_mt5_bridge",
        remove_priorities=("P0_remove_high_conf_ea_diag_false_positive",),
        recover_priorities=(
            "P0_recover_time_axis_positive_mt5_only",
            "P1_recover_positive_m15_slot1_mt5_only",
        ),
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


def num(value: object, default: float = 0.0) -> float:
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return default
    return float(parsed)


def norm_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"L", "LONG", "BUY"}:
        return "BUY"
    if text in {"S", "SHORT", "SELL"}:
        return "SELL"
    return text


def py_dir(value: object) -> str:
    direction = norm_dir(value)
    if direction == "BUY":
        return "L"
    if direction == "SELL":
        return "S"
    return direction


def mode_from_signal(signal_src: object, mode_family: object) -> str:
    text = str(signal_src)
    if "post_n" in text:
        prefix = text.split("_", 1)[0]
        return prefix if prefix.startswith("post_n") else "post_n"
    family = str(mode_family)
    return family if family and family != "nan" else text


def sl_exits(any_sl: bool, all_sl: bool, reason: object) -> tuple[str, str, str]:
    if all_sl:
        return "SL bridge", "SL bridge", "SL bridge"
    if any_sl:
        return "SL bridge", "MT5 ledger bridge", "MT5 ledger bridge"
    text = str(reason) if str(reason) and str(reason) != "nan" else "MT5 ledger bridge"
    return text, text, text


def load_current() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    py_only = read_csv(CURRENT_DYNAMIC_DIR / "python_only_dynamic_risk_trades.csv")
    py_mt5 = read_csv(CURRENT_DYNAMIC_DIR / "python_mt5_dynamic_risk_trades.csv")
    mt5 = read_csv(CURRENT_DYNAMIC_DIR / "mt5_ledger_unique_signals.csv")
    mt5["mt5_trade_id"] = [f"mt5_{idx:04d}" for idx in range(1, len(mt5) + 1)]
    mt5["signal_anchor_time"] = pd.to_datetime(mt5["signal_anchor_time"], errors="coerce")
    mt5["aligned_time"] = mt5["signal_anchor_time"] + pd.Timedelta(minutes=90)
    return py_only, py_mt5, mt5


def build_core_key(frame: pd.DataFrame) -> pd.Series:
    date = pd.to_datetime(frame["date"], errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S")
    return (
        date
        + "|"
        + frame["dir"].map(norm_dir).astype(str)
        + "|"
        + frame["trigger_family"].astype(str)
        + "|"
        + frame["mode"].astype(str)
        + "|"
        + frame["variant"].astype(str)
    )


def remove_python_rows(py_mt5: pd.DataFrame, removal_seed: pd.DataFrame, priorities: tuple[str, ...]) -> tuple[pd.DataFrame, pd.DataFrame]:
    selected = removal_seed[removal_seed["two_sided_priority"].isin(priorities)].copy()
    if selected.empty:
        return py_mt5.copy(), selected
    work = py_mt5.copy()
    work["_core_key"] = build_core_key(work)
    selected = selected.rename(columns={"date": "date_raw"}).copy()
    selected["date"] = selected["date_raw"]
    selected["dir"] = selected["dir_norm"].map(py_dir)
    selected["_core_key"] = build_core_key(selected)
    removed = work[work["_core_key"].isin(set(selected["_core_key"]))].copy()
    kept = work[~work["_core_key"].isin(set(selected["_core_key"]))].drop(columns=["_core_key"])
    return kept, removed.drop(columns=["_core_key"])


def build_bridge_rows(recovery_seed: pd.DataFrame, mt5: pd.DataFrame, priorities: tuple[str, ...]) -> pd.DataFrame:
    selected = recovery_seed[recovery_seed["two_sided_priority"].isin(priorities)].copy()
    if selected.empty:
        return pd.DataFrame()
    selected = selected.merge(mt5, on="mt5_trade_id", how="left", suffixes=("_seed", "_mt5"))
    rows: list[dict[str, object]] = []
    for _, row in selected.iterrows():
        direction = norm_dir(row.get("dir_norm_seed", row.get("dir_norm", row.get("dir", ""))))
        stop_pts_spec = num(row.get("bridge_ledger_stop_pts_spec"), num(row.get("stop_pts_spec"), 0.0))
        entry = num(row.get("bridge_ledger_signal_entry"), 0.0)
        stop = num(row.get("bridge_ledger_signal_stop"), 0.0)
        if entry == 0.0 and stop == 0.0 and stop_pts_spec:
            entry = 0.0
            stop = -stop_pts_spec if direction == "BUY" else stop_pts_spec
        profit = num(row.get("net_profit_seed"), num(row.get("net_profit"), 0.0))
        mode_family = str(row.get("mode_family_seed", row.get("mode_family", "")))
        mode = mode_from_signal(row.get("signal_src_seed", row.get("signal_src", "")), mode_family)
        any_sl = str(row.get("any_sl", "")).strip().lower() in {"true", "1", "yes"}
        all_sl = str(row.get("all_sl", "")).strip().lower() in {"true", "1", "yes"}
        stage1_exit, stage2_exit, stage3_exit = sl_exits(any_sl, all_sl, row.get("deal_reasons", "MT5 ledger bridge"))
        rows.append(
            {
                "source": "python_mt5",
                "date": pd.to_datetime(row.get("aligned_time_seed", row.get("aligned_time")), errors="coerce"),
                "dir": py_dir(direction),
                "mode": mode,
                "mode_family": mode_family,
                "variant": str(row.get("two_sided_priority", "mt5_bridge")).lower(),
                "trigger_family": row.get("trigger_family_seed", row.get("trigger_family", "")),
                "entry": entry,
                "stop": stop,
                "stop_pts_spec": stop_pts_spec,
                "stop_pts_mql5": stop_pts_spec * 1000.0,
                "balance_before": 0.0,
                "dynamic_total_lot": 0.0,
                "stage1_lot": 0.0,
                "stage2_lot": 0.0,
                "stage3_lot": 0.0,
                "stage1_dynamic_$": round(profit / 3.0, 6),
                "stage2_dynamic_$": round(profit / 3.0, 6),
                "stage3_dynamic_$": round(profit - round(profit / 3.0, 6) * 2, 6),
                "dynamic_total_$": round(profit, 6),
                "balance_after": 0.0,
                "fixed_total_$": round(profit, 6),
                "fixed_equity_$": 0.0,
                "stage1_exit": stage1_exit,
                "stage2_exit": stage2_exit,
                "stage3_exit": stage3_exit,
                "source_variant": "two_sided_accounting_bridge",
                "bridge_mt5_trade_id": row.get("mt5_trade_id", ""),
                "bridge_priority": row.get("two_sided_priority", ""),
                "bridge_note": row.get("two_sided_note", ""),
            }
        )
    return pd.DataFrame(rows)


def recompute_accounting_balances(frame: pd.DataFrame, source_variant: str) -> pd.DataFrame:
    out = frame.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["dynamic_total_$"] = pd.to_numeric(out["dynamic_total_$"], errors="coerce").fillna(0.0)
    out = out.sort_values(["date", "source_variant", "variant", "mode"]).reset_index(drop=True)
    balance = START_CAPITAL
    balances_before = []
    balances_after = []
    for _, row in out.iterrows():
        balances_before.append(round(balance, 6))
        balance += float(row["dynamic_total_$"])
        balances_after.append(round(balance, 6))
    out["balance_before"] = balances_before
    out["balance_after"] = balances_after
    out["source_variant"] = source_variant
    return out


def summarize_dynamic(source: str, frame: pd.DataFrame, source_variant: str) -> dict[str, object]:
    total = float(pd.to_numeric(frame["dynamic_total_$"], errors="coerce").fillna(0.0).sum())
    wins = int((pd.to_numeric(frame["dynamic_total_$"], errors="coerce").fillna(0.0) > 0).sum())
    any_sl = (
        frame["stage1_exit"].astype(str).str.contains("SL", regex=False)
        | frame["stage2_exit"].astype(str).str.contains("SL", regex=False)
        | frame["stage3_exit"].astype(str).str.contains("SL", regex=False)
    )
    all_sl = (
        frame["stage1_exit"].astype(str).str.contains("SL", regex=False)
        & frame["stage2_exit"].astype(str).str.contains("SL", regex=False)
        & frame["stage3_exit"].astype(str).str.contains("SL", regex=False)
    )
    return {
        "source": source,
        "trade_count": int(len(frame)),
        "final_balance": round(START_CAPITAL + total, 6),
        "dynamic_total_profit": round(total, 6),
        "win_count": wins,
        "win_rate_pct": round((wins / len(frame) * 100.0) if len(frame) else 0.0, 4),
        "any_stage_sl_count": int(any_sl.sum()),
        "all_stage_sl_count": int(all_sl.sum()),
        "avg_stop_pts_spec": round(float(pd.to_numeric(frame["stop_pts_spec"], errors="coerce").dropna().mean()), 6),
        "avg_total_lot": round(float(pd.to_numeric(frame["dynamic_total_lot"], errors="coerce").dropna().mean()), 6),
        "source_variant": source_variant,
    }


def summarize_mt5(mt5: pd.DataFrame) -> dict[str, object]:
    total = float(pd.to_numeric(mt5["net_profit"], errors="coerce").fillna(0.0).sum())
    wins = int((pd.to_numeric(mt5["net_profit"], errors="coerce").fillna(0.0) > 0).sum())
    any_sl = mt5["any_sl"].astype(str).str.lower().isin({"true", "1", "yes"})
    all_sl = mt5["all_sl"].astype(str).str.lower().isin({"true", "1", "yes"})
    return {
        "source": "mt5_ledger",
        "trade_count": int(len(mt5)),
        "final_balance": round(START_CAPITAL + total, 6),
        "dynamic_total_profit": round(total, 6),
        "win_count": wins,
        "win_rate_pct": round((wins / len(mt5) * 100.0) if len(mt5) else 0.0, 4),
        "any_stage_sl_count": int(any_sl.sum()),
        "all_stage_sl_count": int(all_sl.sum()),
        "avg_stop_pts_spec": round(float(pd.to_numeric(mt5["stop_pts_spec"], errors="coerce").dropna().mean()), 6),
        "avg_total_lot": "",
        "source_variant": "mt5_full_close_retry_fix_20260714",
    }


def compare_key_overlap(py_df: pd.DataFrame, mt5_df: pd.DataFrame, source: str) -> pd.DataFrame:
    py_keys = py_df[["date", "trigger_family", "mode_family", "dir"]].copy()
    py_keys["date"] = pd.to_datetime(py_keys["date"], errors="coerce")
    py_keys["dir"] = py_keys["dir"].map(norm_dir)
    py_keys["key_status"] = "python"
    mt5_keys = mt5_df[["signal_anchor_time", "trigger_family", "mode_family", "dir"]].copy()
    mt5_keys = mt5_keys.rename(columns={"signal_anchor_time": "date"})
    mt5_keys["date"] = pd.to_datetime(mt5_keys["date"], errors="coerce")
    mt5_keys["dir"] = mt5_keys["dir"].map(norm_dir)
    mt5_keys["key_status"] = "mt5"
    merged = py_keys.merge(
        mt5_keys,
        on=["date", "trigger_family", "mode_family", "dir"],
        how="outer",
        indicator=True,
        suffixes=("_py", "_mt5"),
    )
    merged["source"] = source
    merged["match_status"] = merged["_merge"].map(
        {"both": "shared", "left_only": "python_only", "right_only": "mt5_only"}
    )
    return merged.drop(columns=["_merge"])


def write_dynamic_snapshot(
    cfg: TwoSidedConfig,
    py_only: pd.DataFrame,
    py_mt5_variant: pd.DataFrame,
    mt5: pd.DataFrame,
    removed: pd.DataFrame,
    bridges: pd.DataFrame,
) -> Path:
    out_dir = PROTO_DYNAMIC_ROOT / cfg.name
    out_dir.mkdir(parents=True, exist_ok=True)
    mt5_export = mt5.drop(columns=["mt5_trade_id", "aligned_time"], errors="ignore")
    export_csv(py_only, out_dir / "python_only_dynamic_risk_trades.csv")
    export_csv(py_mt5_variant, out_dir / "python_mt5_dynamic_risk_trades.csv")
    export_csv(mt5_export, out_dir / "mt5_ledger_unique_signals.csv")
    export_csv(removed, out_dir / "removed_python_rows.csv")
    export_csv(bridges, out_dir / "bridge_mt5_rows.csv")

    summary = pd.DataFrame(
        [
            summarize_dynamic("python_only", py_only, "baseline"),
            summarize_dynamic("python_mt5", py_mt5_variant, cfg.name),
            summarize_mt5(mt5),
        ]
    )
    export_csv(summary, out_dir / "dynamic_risk_compare_summary.csv")

    overlaps = []
    for source, frame in [("python_only", py_only), ("python_mt5", py_mt5_variant)]:
        overlap = compare_key_overlap(frame, mt5, source)
        overlaps.append(overlap)
        export_csv(overlap, out_dir / f"{source}_vs_mt5_ledger_key_overlap.csv")
    overlap_summary = []
    for overlap in overlaps:
        source = overlap["source"].iloc[0] if not overlap.empty else ""
        counts = overlap["match_status"].value_counts()
        overlap_summary.append(
            {
                "source": source,
                "shared": int(counts.get("shared", 0)),
                "python_only": int(counts.get("python_only", 0)),
                "mt5_only": int(counts.get("mt5_only", 0)),
            }
        )
    export_csv(pd.DataFrame(overlap_summary), out_dir / "dynamic_risk_key_overlap_summary.csv")
    return out_dir


def run_mapping(input_dir: Path, cfg_name: str) -> Path:
    out_dir = PROTO_MAPPING_ROOT / cfg_name
    mapper.INPUT_DIR = input_dir
    mapper.OUT_DIR = out_dir
    mapper.main()
    return out_dir


def build_gap_components(run: str, dynamic_dir: Path, mapping_dir: Path) -> dict[str, object]:
    summary = read_csv(dynamic_dir / "dynamic_risk_compare_summary.csv")
    py_total = float(summary.loc[summary["source"] == "python_mt5", "dynamic_total_profit"].iloc[0])
    mt5_total = float(summary.loc[summary["source"] == "mt5_ledger", "dynamic_total_profit"].iloc[0])
    matches = read_csv(mapping_dir / "python_mt5_mt5_unique_matches.csv")
    py_unmatched = read_csv(mapping_dir / "python_mt5_unmatched_python_trades.csv")
    mt5_unmatched = read_csv(mapping_dir / "python_mt5_unmatched_mt5_trades.csv")

    matched_profit_diff = float(pd.to_numeric(matches["profit_diff"], errors="coerce").fillna(0.0).sum())
    py_unmatched_effect = float(pd.to_numeric(py_unmatched["dynamic_total_$"], errors="coerce").fillna(0.0).sum())
    mt5_unmatched_effect = -float(pd.to_numeric(mt5_unmatched["net_profit"], errors="coerce").fillna(0.0).sum())
    signal_set_gap = py_unmatched_effect + mt5_unmatched_effect
    return {
        "run": run,
        "python_mt5_total_profit": round(py_total, 6),
        "mt5_total_profit": round(mt5_total, 6),
        "direct_dynamic_gap_python_minus_mt5": round(py_total - mt5_total, 6),
        "matched_profit_diff": round(matched_profit_diff, 6),
        "python_unmatched_gap_effect": round(py_unmatched_effect, 6),
        "mt5_unmatched_gap_effect": round(mt5_unmatched_effect, 6),
        "signal_set_gap_effect": round(signal_set_gap, 6),
        "reconstructed_dynamic_gap": round(matched_profit_diff + signal_set_gap, 6),
    }


def build_mapping_summary(run: str, mapping_dir: Path) -> dict[str, object]:
    summary = read_csv(mapping_dir / "unique_match_summary.csv")
    row = summary[summary["source"] == "python_mt5"].iloc[0].to_dict()
    row["run"] = run
    return row


def build_decision_matrix(current_gap: dict[str, object], current_mapping: dict[str, object], rows: list[dict[str, object]]) -> pd.DataFrame:
    out_rows = []
    current_gap_val = float(current_gap["direct_dynamic_gap_python_minus_mt5"])
    current_matched = int(current_mapping["matched_unique"])
    current_py_unmatched = int(current_mapping["python_unmatched"])
    current_mt5_unmatched = int(current_mapping["mt5_unmatched"])
    for row in rows:
        out_rows.append(
            {
                "run": row["run"],
                "direct_gap": row["direct_dynamic_gap_python_minus_mt5"],
                "direct_gap_delta_vs_current": round(float(row["direct_dynamic_gap_python_minus_mt5"]) - current_gap_val, 6),
                "matched_unique": row["matched_unique"],
                "matched_unique_delta": int(row["matched_unique"]) - current_matched,
                "python_unmatched": row["python_unmatched"],
                "python_unmatched_delta": int(row["python_unmatched"]) - current_py_unmatched,
                "mt5_unmatched": row["mt5_unmatched"],
                "mt5_unmatched_delta": int(row["mt5_unmatched"]) - current_mt5_unmatched,
                "matched_profit_diff": row["matched_profit_diff"],
                "signal_set_gap_effect": row["signal_set_gap_effect"],
            }
        )
    return pd.DataFrame(out_rows)


def markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PROTO_DYNAMIC_ROOT.mkdir(parents=True, exist_ok=True)
    PROTO_MAPPING_ROOT.mkdir(parents=True, exist_ok=True)

    py_only, current_py_mt5, mt5 = load_current()
    removal_seed = read_csv(ROW_IMPACT_DIR / "two_sided_seed_python_removals.csv")
    recovery_seed = read_csv(ROW_IMPACT_DIR / "two_sided_seed_mt5_recoveries.csv")

    current_gap_components = build_gap_components("current_metadatafix", CURRENT_DYNAMIC_DIR, CURRENT_MAPPING_DIR)
    current_mapping_summary = build_mapping_summary("current_metadatafix", CURRENT_MAPPING_DIR)

    gap_rows = [current_gap_components]
    mapping_rows = [current_mapping_summary]
    bridge_summary_rows = []
    removal_summary_rows = []

    for cfg in CONFIGS:
        kept, removed = remove_python_rows(current_py_mt5, removal_seed, cfg.remove_priorities)
        bridges = build_bridge_rows(recovery_seed, mt5, cfg.recover_priorities)
        if bridges.empty:
            variant = kept.copy()
        else:
            variant = pd.concat([kept, bridges], ignore_index=True, sort=False)
        variant = recompute_accounting_balances(variant, cfg.name)

        dynamic_dir = write_dynamic_snapshot(cfg, py_only, variant, mt5, removed, bridges)
        mapping_dir = run_mapping(dynamic_dir, cfg.name)

        gap = build_gap_components(cfg.name, dynamic_dir, mapping_dir)
        mapping = build_mapping_summary(cfg.name, mapping_dir)
        gap_rows.append(gap)
        mapping_rows.append(mapping)
        removal_summary_rows.append(
            {
                "run": cfg.name,
                "removed_count": int(len(removed)),
                "removed_profit_sum": round(float(pd.to_numeric(removed.get("dynamic_total_$", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum()), 6),
                "removed_dates": ";".join(pd.to_datetime(removed.get("date", pd.Series(dtype=str)), errors="coerce").dt.strftime("%Y-%m-%d %H:%M:%S").dropna().astype(str).tolist()),
            }
        )
        bridge_summary_rows.append(
            {
                "run": cfg.name,
                "bridge_count": int(len(bridges)),
                "bridge_profit_sum": round(float(pd.to_numeric(bridges.get("dynamic_total_$", pd.Series(dtype=float)), errors="coerce").fillna(0.0).sum()), 6),
                "bridge_mt5_trade_ids": ";".join(bridges.get("bridge_mt5_trade_id", pd.Series(dtype=str)).astype(str).tolist()) if not bridges.empty else "",
            }
        )

    gap_df = pd.DataFrame(gap_rows)
    mapping_df = pd.DataFrame(mapping_rows)
    removal_df = pd.DataFrame(removal_summary_rows)
    bridge_df = pd.DataFrame(bridge_summary_rows)

    combined_rows = []
    for gap in gap_rows[1:]:
        mapping = next(row for row in mapping_rows if row["run"] == gap["run"])
        combined = {**gap, **mapping}
        combined_rows.append(combined)
    decision = build_decision_matrix(current_gap_components, current_mapping_summary, combined_rows)

    export_csv(gap_df, OUT_DIR / "gap_components.csv")
    export_csv(mapping_df, OUT_DIR / "mapping_summary.csv")
    export_csv(removal_df, OUT_DIR / "removed_python_summary.csv")
    export_csv(bridge_df, OUT_DIR / "bridge_mt5_summary.csv")
    export_csv(decision, OUT_DIR / "decision_matrix.csv")

    report = [
        "# Two-sided correction accounting prototype",
        "",
        "## Scope",
        "",
        "- Diagnostic accounting bridge only; not a mergeable signal implementation.",
        "- Removes P0 Python false positives backed by EA M15 diagnostics.",
        "- Injects selected MT5-only rows using MT5 ledger net profit to test whether paired recovery improves the signal-set gap.",
        "",
        "## Removed Python Rows",
        markdown_table(removal_df),
        "",
        "## Bridge MT5 Rows",
        markdown_table(bridge_df),
        "",
        "## Gap Components",
        markdown_table(gap_df),
        "",
        "## Mapping Summary",
        markdown_table(
            mapping_df[
                [
                    "run",
                    "source",
                    "python_trades",
                    "mt5_trades",
                    "matched_unique",
                    "reliable_tier_matched",
                    "relaxed_tier_matched",
                    "python_unmatched",
                    "mt5_unmatched",
                    "matched_profit_diff",
                ]
            ]
        ),
        "",
        "## Decision Matrix",
        markdown_table(decision),
        "",
        "## Interpretation",
        "",
        "- `remove_p0_python_only` measures the cost of removing only the two confirmed false positives.",
        "- `remove_p0_add_p0_mt5_bridge` tests the first paired correction using only P0 time-axis MT5-only candidates.",
        "- `remove_p0_add_p0p1_mt5_bridge` adds P1 MT5-only candidates as a broader accounting stress test.",
        "- A variant can justify deeper signal-code work only if it improves direct gap and mapping coverage without reintroducing the two false positives.",
    ]
    write_text(OUT_DIR / "two_sided_correction_prototype_review.md", "\n".join(report))
    write_text(OUT_DIR / "README.md", "Two-sided correction accounting prototype outputs.\n")


if __name__ == "__main__":
    main()
