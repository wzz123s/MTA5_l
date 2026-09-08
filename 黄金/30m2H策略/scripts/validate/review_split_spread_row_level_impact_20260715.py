# -*- coding: utf-8 -*-
"""Row-level impact decomposition for targeted split and spread-stop prototypes."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

CURRENT_DYNAMIC_DIR = VALIDATION_DIR / "dynamic_risk_alignment_shift90_metadatafix_close_retry_20260714"
CURRENT_MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_shift90_metadatafix_close_retry_20260714"

PROTO_DYNAMIC_ROOT = VALIDATION_DIR / "dynamic_risk_alignment_targeted_split_runtime_rescue_spread_20260715"
PROTO_MAPPING_ROOT = VALIDATION_DIR / "mapped_trade_alignment_targeted_split_runtime_rescue_spread_20260715"
PROTO_REVIEW_DIR = VALIDATION_DIR / "targeted_split_runtime_rescue_spread_review_20260715"

OUT_DIR = VALIDATION_DIR / "row_level_split_spread_impact_20260715"

VARIANTS = [
    "python_h2_context_q2early_current_spread_stop_nofilter",
    "python_h2_context_q2early_current_spread_stop_strict",
    "python_h2_context_q2early_targeted_split_strict",
    "python_h2_context_q2early_targeted_split_spread_stop_strict",
    "python_h2_context_q2early_targeted_split_spread_stop_nofilter",
]

FOCUS_VARIANTS = [
    "python_h2_context_q2early_current_spread_stop_nofilter",
    "python_h2_context_q2early_targeted_split_strict",
    "python_h2_context_q2early_targeted_split_spread_stop_nofilter",
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig", low_memory=False)


def export_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((text.rstrip() + "\n").encode("utf-8-sig"))


def as_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def norm_dir(value: object) -> str:
    text = str(value).strip().upper()
    if text in {"L", "LONG", "BUY"}:
        return "BUY"
    if text in {"S", "SHORT", "SELL"}:
        return "SELL"
    return text


def short_name(run: str) -> str:
    return run.replace("python_h2_context_q2early_", "")


def markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def load_dynamic(dynamic_dir: Path, run: str) -> pd.DataFrame:
    frame = read_csv(dynamic_dir / "python_mt5_dynamic_risk_trades.csv")
    frame = frame.copy()
    frame["run"] = run
    frame["row_no"] = range(1, len(frame) + 1)
    frame["py_trade_id"] = [f"python_mt5_{idx:04d}" for idx in range(1, len(frame) + 1)]
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["dir_norm"] = frame["dir"].map(norm_dir)
    for col in [
        "entry",
        "stop",
        "stop_pts_spec",
        "balance_before",
        "dynamic_total_lot",
        "stage1_lot",
        "stage2_lot",
        "stage3_lot",
        "dynamic_total_$",
        "balance_after",
    ]:
        if col in frame.columns:
            frame[col] = as_float(frame[col])
    frame["entry_key"] = frame["entry"].round(5).astype(str)
    frame["core_key"] = (
        frame["date"].dt.strftime("%Y-%m-%d %H:%M:%S")
        + "|"
        + frame["dir_norm"].astype(str)
        + "|"
        + frame["trigger_family"].astype(str)
        + "|"
        + frame["mode"].astype(str)
        + "|"
        + frame["variant"].astype(str)
        + "|"
        + frame["entry_key"]
    )
    frame["loose_key"] = (
        frame["date"].dt.strftime("%Y-%m-%d %H:%M:%S")
        + "|"
        + frame["dir_norm"].astype(str)
        + "|"
        + frame["trigger_family"].astype(str)
        + "|"
        + frame["mode"].astype(str)
        + "|"
        + frame["variant"].astype(str)
    )
    return frame


def load_mapping_status(mapping_dir: Path) -> pd.DataFrame:
    matched = read_csv(mapping_dir / "python_mt5_mt5_unique_matches.csv")
    unmatched = read_csv(mapping_dir / "python_mt5_unmatched_python_trades.csv")

    matched_cols = [
        "py_trade_id",
        "mt5_trade_id",
        "match_tier",
        "tier_rank",
        "is_reliable_tier",
        "py_profit",
        "mt5_profit",
        "profit_diff",
        "profit_abs_diff",
    ]
    matched = matched[[c for c in matched_cols if c in matched.columns]].copy()
    matched["mapping_status"] = "matched"

    unmatched_cols = ["py_trade_id"]
    unmatched = unmatched[[c for c in unmatched_cols if c in unmatched.columns]].copy()
    unmatched["mapping_status"] = "python_unmatched"
    unmatched["mt5_trade_id"] = ""
    unmatched["match_tier"] = ""
    unmatched["tier_rank"] = ""
    unmatched["is_reliable_tier"] = ""
    unmatched["py_profit"] = ""
    unmatched["mt5_profit"] = ""
    unmatched["profit_diff"] = ""
    unmatched["profit_abs_diff"] = ""

    out = pd.concat([matched, unmatched], ignore_index=True, sort=False)
    return out


def attach_mapping(dynamic: pd.DataFrame, mapping_dir: Path, suffix: str) -> pd.DataFrame:
    status = load_mapping_status(mapping_dir)
    merged = dynamic.merge(status, on="py_trade_id", how="left")
    merged["mapping_status"] = merged["mapping_status"].fillna("unknown")
    rename = {
        "py_trade_id": f"py_trade_id_{suffix}",
        "mapping_status": f"mapping_status_{suffix}",
        "mt5_trade_id": f"mt5_trade_id_{suffix}",
        "match_tier": f"match_tier_{suffix}",
        "tier_rank": f"tier_rank_{suffix}",
        "is_reliable_tier": f"is_reliable_tier_{suffix}",
        "profit_diff": f"profit_diff_{suffix}",
    }
    return merged.rename(columns=rename)


def load_mt5_ledger() -> pd.DataFrame:
    mt5 = read_csv(CURRENT_DYNAMIC_DIR / "mt5_ledger_unique_signals.csv")
    mt5 = mt5.copy()
    mt5["signal_anchor_time"] = pd.to_datetime(mt5["signal_anchor_time"], errors="coerce")
    mt5["aligned_time"] = mt5["signal_anchor_time"] + pd.Timedelta(minutes=90)
    mt5["dir_norm"] = mt5["dir"].map(norm_dir)
    mt5["net_profit"] = as_float(mt5["net_profit"])
    mt5["stop_pts_spec"] = as_float(mt5["stop_pts_spec"])
    mt5["mt5_trade_id"] = [f"mt5_{idx:04d}" for idx in range(1, len(mt5) + 1)]
    return mt5


def compare_variant(run: str) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    current = attach_mapping(load_dynamic(CURRENT_DYNAMIC_DIR, "current_metadatafix"), CURRENT_MAPPING_DIR, "current")
    variant_dynamic_dir = PROTO_DYNAMIC_ROOT / run
    variant_mapping_dir = PROTO_MAPPING_ROOT / run
    variant = attach_mapping(load_dynamic(variant_dynamic_dir, run), variant_mapping_dir, "variant")

    current_keys = set(current["core_key"])
    variant_keys = set(variant["core_key"])

    removed = current[~current["core_key"].isin(variant_keys)].copy()
    added = variant[~variant["core_key"].isin(current_keys)].copy()

    common = current.merge(
        variant,
        on="core_key",
        how="inner",
        suffixes=("_current", "_variant"),
    )
    common["dynamic_total_delta"] = common["dynamic_total_$_variant"] - common["dynamic_total_$_current"]
    common["balance_before_delta"] = common["balance_before_variant"] - common["balance_before_current"]
    common["balance_after_delta"] = common["balance_after_variant"] - common["balance_after_current"]
    common["stop_delta"] = common["stop_variant"] - common["stop_current"]
    common["stop_pts_spec_delta"] = common["stop_pts_spec_variant"] - common["stop_pts_spec_current"]
    common["total_lot_delta"] = common["dynamic_total_lot_variant"] - common["dynamic_total_lot_current"]
    changed = common[
        (common["dynamic_total_delta"].abs() > 1e-6)
        | (common["stop_delta"].abs() > 1e-9)
        | (common["total_lot_delta"].abs() > 1e-9)
        | (common["mapping_status_current"] != common["mapping_status_variant"])
        | (common["mt5_trade_id_current"].astype(str) != common["mt5_trade_id_variant"].astype(str))
    ].copy()

    removed["delta_contribution"] = -removed["dynamic_total_$"]
    removed["impact_type"] = "removed"
    added["delta_contribution"] = added["dynamic_total_$"]
    added["impact_type"] = "added"
    changed["delta_contribution"] = changed["dynamic_total_delta"]
    changed["impact_type"] = "common_changed"

    current_total = float(current["dynamic_total_$"].sum())
    variant_total = float(variant["dynamic_total_$"].sum())
    removed_sum = float(removed["dynamic_total_$"].sum())
    added_sum = float(added["dynamic_total_$"].sum())
    common_delta_sum = float(changed["dynamic_total_delta"].sum())

    current_target_removed_sum = float(
        removed[
            removed["date"].isin(
                [pd.Timestamp("2025-10-17 11:00:00"), pd.Timestamp("2025-10-21 10:00:00")]
            )
        ]["dynamic_total_$"].sum()
    )

    summary = pd.DataFrame(
        [
            {
                "run": run,
                "current_trades": len(current),
                "variant_trades": len(variant),
                "trade_count_delta": len(variant) - len(current),
                "removed_count": len(removed),
                "added_count": len(added),
                "common_count": len(common),
                "changed_common_count": len(changed),
                "current_total_profit": round(current_total, 6),
                "variant_total_profit": round(variant_total, 6),
                "total_profit_delta": round(variant_total - current_total, 6),
                "removed_profit_sum": round(removed_sum, 6),
                "added_profit_sum": round(added_sum, 6),
                "common_profit_delta_sum": round(common_delta_sum, 6),
                "reconstructed_delta": round(-removed_sum + added_sum + common_delta_sum, 6),
                "target_20251017_20251021_removed_profit_sum": round(current_target_removed_sum, 6),
                "non_target_removed_profit_sum": round(removed_sum - current_target_removed_sum, 6),
            }
        ]
    )

    return summary, {
        "removed": removed,
        "added": added,
        "common_changed": changed,
        "current": current,
        "variant": variant,
    }


def build_top_contributors(parts: dict[str, pd.DataFrame], run: str) -> pd.DataFrame:
    rows = []
    removed_cols = [
        "impact_type",
        "date",
        "dir_norm",
        "trigger_family",
        "mode",
        "variant",
        "entry",
        "stop",
        "stop_pts_spec",
        "dynamic_total_$",
        "delta_contribution",
        "mapping_status_current",
        "mt5_trade_id_current",
        "match_tier_current",
    ]
    for _, row in parts["removed"].iterrows():
        rows.append({col: row.get(col, "") for col in removed_cols})
    added_cols = [
        "impact_type",
        "date",
        "dir_norm",
        "trigger_family",
        "mode",
        "variant",
        "entry",
        "stop",
        "stop_pts_spec",
        "dynamic_total_$",
        "delta_contribution",
        "mapping_status_variant",
        "mt5_trade_id_variant",
        "match_tier_variant",
    ]
    for _, row in parts["added"].iterrows():
        item = {col: row.get(col, "") for col in added_cols}
        item["mapping_status_current"] = ""
        item["mt5_trade_id_current"] = ""
        item["match_tier_current"] = ""
        rows.append(item)
    for _, row in parts["common_changed"].iterrows():
        rows.append(
            {
                "impact_type": "common_changed",
                "date": row.get("date_current", ""),
                "dir_norm": row.get("dir_norm_current", ""),
                "trigger_family": row.get("trigger_family_current", ""),
                "mode": row.get("mode_current", ""),
                "variant": row.get("variant_current", ""),
                "entry": row.get("entry_current", ""),
                "stop": row.get("stop_current", ""),
                "stop_variant": row.get("stop_variant", ""),
                "stop_pts_spec": row.get("stop_pts_spec_current", ""),
                "stop_pts_spec_variant": row.get("stop_pts_spec_variant", ""),
                "dynamic_total_$": row.get("dynamic_total_$_current", ""),
                "dynamic_total_$_variant": row.get("dynamic_total_$_variant", ""),
                "delta_contribution": row.get("delta_contribution", ""),
                "balance_before_delta": row.get("balance_before_delta", ""),
                "total_lot_delta": row.get("total_lot_delta", ""),
                "mapping_status_current": row.get("mapping_status_current", ""),
                "mapping_status_variant": row.get("mapping_status_variant", ""),
                "mt5_trade_id_current": row.get("mt5_trade_id_current", ""),
                "mt5_trade_id_variant": row.get("mt5_trade_id_variant", ""),
                "match_tier_current": row.get("match_tier_current", ""),
                "match_tier_variant": row.get("match_tier_variant", ""),
            }
        )
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["run"] = run
    out["abs_delta_contribution"] = as_float(out["delta_contribution"]).abs()
    return out.sort_values("abs_delta_contribution", ascending=False).reset_index(drop=True)


def find_nearby_mt5_candidates(removed: pd.DataFrame, mt5: pd.DataFrame, run: str, window_minutes: int = 240) -> pd.DataFrame:
    rows = []
    if removed.empty:
        return pd.DataFrame()
    for _, rem in removed.iterrows():
        same_dir = mt5[mt5["dir_norm"] == rem["dir_norm"]].copy()
        same_dir["time_diff_minutes"] = (same_dir["aligned_time"] - rem["date"]).dt.total_seconds() / 60.0
        cand = same_dir[same_dir["time_diff_minutes"].abs() <= window_minutes].copy()
        cand["abs_time_diff_minutes"] = cand["time_diff_minutes"].abs()
        cand["trigger_same"] = cand["trigger_family"].astype(str) == str(rem["trigger_family"])
        cand["mode_same"] = cand["mode_family"].astype(str) == str(rem.get("mode_family", ""))
        cand = cand.sort_values(["abs_time_diff_minutes", "trigger_same", "mode_same"], ascending=[True, False, False]).head(5)
        if cand.empty:
            rows.append(
                {
                    "run": run,
                    "removed_date": rem["date"],
                    "removed_dir": rem["dir_norm"],
                    "removed_trigger": rem["trigger_family"],
                    "removed_mode": rem["mode"],
                    "removed_variant": rem["variant"],
                    "removed_profit": rem["dynamic_total_$"],
                    "removed_mapping_status": rem.get("mapping_status_current", ""),
                    "candidate_rank": "",
                    "mt5_trade_id": "",
                    "mt5_aligned_time": "",
                    "time_diff_minutes": "",
                    "mt5_trigger": "",
                    "mt5_mode": "",
                    "mt5_profit": "",
                    "note": "no_same_dir_mt5_within_240m",
                }
            )
            continue
        for rank, (_, mrow) in enumerate(cand.iterrows(), start=1):
            rows.append(
                {
                    "run": run,
                    "removed_date": rem["date"],
                    "removed_dir": rem["dir_norm"],
                    "removed_trigger": rem["trigger_family"],
                    "removed_mode": rem["mode"],
                    "removed_variant": rem["variant"],
                    "removed_profit": rem["dynamic_total_$"],
                    "removed_mapping_status": rem.get("mapping_status_current", ""),
                    "candidate_rank": rank,
                    "mt5_trade_id": mrow["mt5_trade_id"],
                    "mt5_anchor_time": mrow["signal_anchor_time"],
                    "mt5_aligned_time": mrow["aligned_time"],
                    "time_diff_minutes": round(float(mrow["time_diff_minutes"]), 3),
                    "mt5_trigger": mrow["trigger_family"],
                    "mt5_mode": mrow["mode_family"],
                    "mt5_signal_src": mrow["signal_src"],
                    "mt5_stop_pts_spec": mrow["stop_pts_spec"],
                    "mt5_profit": mrow["net_profit"],
                    "trigger_same": mrow["trigger_same"],
                    "mode_same": mrow["mode_same"],
                    "note": "",
                }
            )
    return pd.DataFrame(rows)


def build_gap_delta() -> pd.DataFrame:
    gap = read_csv(PROTO_REVIEW_DIR / "gap_components.csv")
    current = gap[gap["run"] == "current_metadatafix"].iloc[0]
    rows = []
    metrics = [
        "python_mt5_total_profit",
        "mt5_total_profit",
        "direct_dynamic_gap_python_minus_mt5",
        "matched_profit_diff",
        "python_unmatched_gap_effect",
        "mt5_unmatched_gap_effect",
        "signal_set_gap_effect",
    ]
    for _, row in gap[gap["run"] != "current_metadatafix"].iterrows():
        item = {"run": row["run"]}
        for metric in metrics:
            item[f"current_{metric}"] = round(float(current[metric]), 6)
            item[f"variant_{metric}"] = round(float(row[metric]), 6)
            item[f"delta_{metric}"] = round(float(row[metric]) - float(current[metric]), 6)
        rows.append(item)
    return pd.DataFrame(rows)


def build_python_removal_seed(removed: pd.DataFrame) -> pd.DataFrame:
    if removed.empty:
        return pd.DataFrame()
    out = removed.copy()
    target_dates = {pd.Timestamp("2025-10-17 11:00:00"), pd.Timestamp("2025-10-21 10:00:00")}
    priorities = []
    notes = []
    for _, row in out.iterrows():
        date = row["date"]
        status = str(row.get("mapping_status_current", ""))
        profit = float(row.get("dynamic_total_$", 0.0))
        if date in target_dates:
            priorities.append("P0_remove_high_conf_ea_diag_false_positive")
            notes.append("Target case already backed by EA M15 diag review.")
        elif status == "python_unmatched" and profit > 0:
            priorities.append("P1_review_positive_python_unmatched_before_remove")
            notes.append("Removal worsens Python-MT5 profit; require EA diag or raw-parent evidence before merging.")
        elif status == "matched":
            priorities.append("P2_do_not_remove_without_replacement")
            notes.append("Current row has an MT5 mapping; deleting it needs a paired replacement or remap.")
        elif profit < 0:
            priorities.append("P3_profit_beneficial_but_alignment_unproven")
            notes.append("Removal improves raw profit but still needs signal-layer justification.")
        else:
            priorities.append("P3_review_low_impact")
            notes.append("Low-impact row; review after P0/P1 candidates.")
    out["two_sided_priority"] = priorities
    out["two_sided_note"] = notes
    cols = [
        "two_sided_priority",
        "two_sided_note",
        "date",
        "dir_norm",
        "trigger_family",
        "mode",
        "variant",
        "dynamic_total_$",
        "mapping_status_current",
        "mt5_trade_id_current",
        "match_tier_current",
        "entry",
        "stop",
        "stop_pts_spec",
    ]
    return out[[c for c in cols if c in out.columns]].sort_values(
        ["two_sided_priority", "dynamic_total_$"], ascending=[True, False]
    )


def build_mt5_recovery_seed() -> pd.DataFrame:
    unmatched = read_csv(CURRENT_MAPPING_DIR / "python_mt5_unmatched_mt5_trades.csv")
    unmatched = unmatched.copy()
    unmatched["net_profit"] = as_float(unmatched["net_profit"])
    signal_cases_path = VALIDATION_DIR / "post_bridge_remaining_p1_review_20260714" / "post_bridge_signal_set_cases.csv"
    if signal_cases_path.exists():
        cases = read_csv(signal_cases_path)
        cases = cases.rename(columns={"trade_id": "mt5_trade_id"})
        keep = [
            "mt5_trade_id",
            "effective_cause_bucket",
            "post_bridge_action_bucket",
            "post_bridge_action_note",
            "bridge_reclass_applied_bool",
            "bridge_raw_anchor",
            "bridge_log_time",
            "bridge_ledger_signal_entry",
            "bridge_ledger_signal_stop",
            "bridge_ledger_stop_pts_spec",
        ]
        unmatched = unmatched.merge(cases[[c for c in keep if c in cases.columns]], on="mt5_trade_id", how="left")
    priorities = []
    notes = []
    for _, row in unmatched.iterrows():
        profit = float(row.get("net_profit", 0.0))
        cause = str(row.get("effective_cause_bucket", ""))
        action = str(row.get("post_bridge_action_bucket", ""))
        if profit > 0 and cause == "time_axis_bridge_candidate":
            priorities.append("P0_recover_time_axis_positive_mt5_only")
            notes.append("Positive MT5-only signal already classified as time-axis bridge candidate.")
        elif profit > 0 and row.get("trigger_family", "") == "M15 SLOT1":
            priorities.append("P1_recover_positive_m15_slot1_mt5_only")
            notes.append("Positive MT5-only M15 SLOT1 signal; require raw parent/EA diag support.")
        elif profit > 0:
            priorities.append("P2_recover_positive_m30_mt5_only")
            notes.append("Positive MT5-only M30 signal; review after M15 time-axis candidates.")
        else:
            priorities.append("P3_skip_loss_or_low_priority")
            notes.append("Non-positive MT5-only signal is not useful for closing the current negative gap first.")
        if action:
            notes[-1] = notes[-1] + f" Post-bridge action: {action}."
    unmatched["two_sided_priority"] = priorities
    unmatched["two_sided_note"] = notes
    cols = [
        "two_sided_priority",
        "two_sided_note",
        "mt5_trade_id",
        "signal_anchor_time",
        "aligned_time",
        "dir_norm",
        "trigger_family",
        "mode_family",
        "signal_src",
        "net_profit",
        "effective_cause_bucket",
        "post_bridge_action_bucket",
        "bridge_reclass_applied_bool",
        "bridge_raw_anchor",
        "bridge_log_time",
        "bridge_ledger_signal_entry",
        "bridge_ledger_signal_stop",
        "bridge_ledger_stop_pts_spec",
    ]
    return unmatched[[c for c in cols if c in unmatched.columns]].sort_values(
        ["two_sided_priority", "net_profit"], ascending=[True, False]
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mt5 = load_mt5_ledger()

    summaries = []
    all_nearby = []
    focus_top_tables = {}
    focus_removed_tables = {}
    targeted_split_strict_removed = pd.DataFrame()

    for run in VARIANTS:
        summary, parts = compare_variant(run)
        summaries.append(summary)

        prefix = short_name(run)
        export_csv(parts["removed"], OUT_DIR / f"{prefix}_removed_trades.csv")
        export_csv(parts["added"], OUT_DIR / f"{prefix}_added_trades.csv")
        export_csv(parts["common_changed"], OUT_DIR / f"{prefix}_common_changed_trades.csv")

        top = build_top_contributors(parts, run)
        export_csv(top, OUT_DIR / f"{prefix}_top_delta_contributors.csv")
        nearby = find_nearby_mt5_candidates(parts["removed"], mt5, run)
        export_csv(nearby, OUT_DIR / f"{prefix}_nearby_mt5_candidates_for_removed.csv")
        if not nearby.empty:
            all_nearby.append(nearby)

        if run in FOCUS_VARIANTS:
            focus_top_tables[run] = top
            focus_removed_tables[run] = parts["removed"].sort_values("dynamic_total_$", ascending=False)
        if run == "python_h2_context_q2early_targeted_split_strict":
            targeted_split_strict_removed = parts["removed"].copy()

    summary_df = pd.concat(summaries, ignore_index=True)
    gap_delta = build_gap_delta()
    nearby_all = pd.concat(all_nearby, ignore_index=True, sort=False) if all_nearby else pd.DataFrame()
    python_removal_seed = build_python_removal_seed(targeted_split_strict_removed)
    mt5_recovery_seed = build_mt5_recovery_seed()

    export_csv(summary_df, OUT_DIR / "variant_trade_diff_summary.csv")
    export_csv(gap_delta, OUT_DIR / "variant_gap_delta_decomposition.csv")
    export_csv(nearby_all, OUT_DIR / "all_nearby_mt5_candidates_for_removed.csv")
    export_csv(python_removal_seed, OUT_DIR / "two_sided_seed_python_removals.csv")
    export_csv(mt5_recovery_seed, OUT_DIR / "two_sided_seed_mt5_recoveries.csv")

    report = [
        "# Row-level split/spread impact review",
        "",
        "## Summary",
        markdown_table(
            summary_df[
                [
                    "run",
                    "trade_count_delta",
                    "removed_count",
                    "added_count",
                    "changed_common_count",
                    "total_profit_delta",
                    "removed_profit_sum",
                    "added_profit_sum",
                    "common_profit_delta_sum",
                    "target_20251017_20251021_removed_profit_sum",
                    "non_target_removed_profit_sum",
                ]
            ],
            max_rows=20,
        ),
        "",
        "## Gap Delta",
        markdown_table(
            gap_delta[
                [
                    "run",
                    "delta_direct_dynamic_gap_python_minus_mt5",
                    "delta_matched_profit_diff",
                    "delta_python_unmatched_gap_effect",
                    "delta_mt5_unmatched_gap_effect",
                    "delta_signal_set_gap_effect",
                ]
            ],
            max_rows=20,
        ),
        "",
        "## Focus Top Contributors",
    ]

    for run in FOCUS_VARIANTS:
        top = focus_top_tables.get(run, pd.DataFrame())
        report.extend(
            [
                "",
                f"### {run}",
                markdown_table(
                    top[
                        [
                            "impact_type",
                            "date",
                            "dir_norm",
                            "trigger_family",
                            "mode",
                            "variant",
                            "dynamic_total_$",
                            "dynamic_total_$_variant",
                            "delta_contribution",
                            "mapping_status_current",
                            "mapping_status_variant",
                            "mt5_trade_id_current",
                            "mt5_trade_id_variant",
                        ]
                    ]
                    if not top.empty
                    else top,
                    max_rows=15,
                ),
            ]
        )

    report.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Spread-only keeps the signal set mostly unchanged, so the loss comes from changed stop distance, lot sizing and stage PnL on common trades; it does not remove the two target false positives.",
            "- Targeted split removes the target false positives, but the removed-profit sum is larger than those two targets alone and the common-trade PnL also shifts after balance/lots change.",
            "- The decomposition confirms that a one-sided deletion rule is not enough; the next prototype must pair high-confidence Python false-positive removal with MT5-only/time-axis candidate recovery.",
            "",
            "## Two-sided Seed Lists",
            "",
            "### Python removal seed",
            markdown_table(
                python_removal_seed[
                    [
                        "two_sided_priority",
                        "date",
                        "dir_norm",
                        "trigger_family",
                        "mode",
                        "variant",
                        "dynamic_total_$",
                        "mapping_status_current",
                        "mt5_trade_id_current",
                    ]
                ]
                if not python_removal_seed.empty
                else python_removal_seed,
                max_rows=12,
            ),
            "",
            "### MT5 recovery seed",
            markdown_table(
                mt5_recovery_seed[
                    [
                        "two_sided_priority",
                        "mt5_trade_id",
                        "aligned_time",
                        "dir_norm",
                        "trigger_family",
                        "mode_family",
                        "net_profit",
                        "effective_cause_bucket",
                        "post_bridge_action_bucket",
                    ]
                ]
                if not mt5_recovery_seed.empty
                else mt5_recovery_seed,
                max_rows=12,
            ),
        ]
    )

    write_text(OUT_DIR / "row_level_split_spread_impact_review.md", "\n".join(report))
    write_text(
        OUT_DIR / "README.md",
        "Row-level impact decomposition for targeted split runtime_rescue and spread-stop prototypes.\n",
    )


if __name__ == "__main__":
    main()
