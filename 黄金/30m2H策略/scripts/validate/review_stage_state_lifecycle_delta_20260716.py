# -*- coding: utf-8 -*-
"""Localize lifecycle/profit deltas caused by the stage-state EA fix.

The previous gates proved the deinit artifact is gone, but the full MT5 result
regressed. This diagnostic decomposes close-retry -> stage-state ledger delta
without changing EA or Python strategy logic.
"""
from __future__ import annotations


from pathlib import Path

import pandas as pd


STRATEGY_DIR = Path(__file__).resolve().parents[2]
VALIDATION_DIR = STRATEGY_DIR / "data" / "validation"

BASELINE_DIR = VALIDATION_DIR / "mt5_full_close_retry_fix_20260714"
STAGE_STATE_DIR = VALIDATION_DIR / "mt5_stage_state_full_2018_20260707_20260716"
REMAP_REVIEW_DIR = VALIDATION_DIR / "stage_state_full_remap_residual_review_20260716"
RESIDUAL_DIR = VALIDATION_DIR / "exec_model_residual_stage_state_20260716"
MAPPING_DIR = VALIDATION_DIR / "mapped_trade_alignment_exec_model_stage_state_metadatafix_20260716"
OUT_DIR = VALIDATION_DIR / "stage_state_lifecycle_delta_localization_20260716"

START_CAPITAL = 500.0
TARGET_DEINIT_ANCHOR = "2022-11-08 16:30:00"


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


def to_dt(value: object) -> pd.Timestamp:
    text = str(value).strip()
    if not text:
        return pd.NaT
    return pd.to_datetime(text.replace(".", "-"), errors="coerce")


def iso(value: object) -> str:
    dt = to_dt(value)
    if pd.isna(dt):
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def prep_ledger(frame: pd.DataFrame, snapshot: str) -> pd.DataFrame:
    out = frame.copy()
    out["snapshot"] = snapshot
    out["anchor_iso"] = out["signal_anchor_time"].map(iso)
    out["open_dt"] = out["open_time"].map(to_dt)
    out["exit_dt"] = out["exit_time"].map(to_dt)
    out["stage"] = pd.to_numeric(out["stage"], errors="coerce").astype("Int64")
    for col in ["profit", "swap", "commission", "net_profit", "lots", "fill_price", "exit_price", "actual_stop"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def key_cols(include_stage: bool = False) -> list[str]:
    cols = ["anchor_iso", "trigger_tag", "signal_src", "dir"]
    if include_stage:
        cols.append("stage")
    return cols


def join_values(series: pd.Series) -> str:
    vals = [str(v) for v in series.dropna().astype(str).unique() if str(v).strip()]
    return ";".join(vals)


def group_ledger(frame: pd.DataFrame, prefix: str, include_stage: bool = False) -> pd.DataFrame:
    cols = key_cols(include_stage)
    grouped = (
        frame.groupby(cols, dropna=False)
        .agg(
            **{
                f"{prefix}_rows": ("stage", "count"),
                f"{prefix}_net": ("net_profit", "sum"),
                f"{prefix}_profit": ("profit", "sum"),
                f"{prefix}_swap": ("swap", "sum"),
                f"{prefix}_lots": ("lots", "sum"),
                f"{prefix}_stages": ("stage", join_values),
                f"{prefix}_exit_reasons": ("local_exit_reason", join_values),
                f"{prefix}_deal_reasons": ("deal_reason", join_values),
                f"{prefix}_first_open": ("open_dt", "min"),
                f"{prefix}_last_exit": ("exit_dt", "max"),
            }
        )
        .reset_index()
    )
    return grouped


def build_delta(old: pd.DataFrame, new: pd.DataFrame, include_stage: bool = False) -> pd.DataFrame:
    cols = key_cols(include_stage)
    old_g = group_ledger(old, "old", include_stage)
    new_g = group_ledger(new, "new", include_stage)
    merged = old_g.merge(new_g, on=cols, how="outer")
    fill_zero = {
        "old_rows": 0,
        "old_net": 0.0,
        "old_profit": 0.0,
        "old_swap": 0.0,
        "old_lots": 0.0,
        "new_rows": 0,
        "new_net": 0.0,
        "new_profit": 0.0,
        "new_swap": 0.0,
        "new_lots": 0.0,
    }
    merged = merged.fillna(fill_zero)
    for col in ["old_rows", "new_rows"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0).astype(int)
    for col in ["old_net", "new_net", "old_profit", "new_profit", "old_swap", "new_swap", "old_lots", "new_lots"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0.0)
    merged["net_delta_new_minus_old"] = merged["new_net"] - merged["old_net"]
    merged["row_delta_new_minus_old"] = merged["new_rows"] - merged["old_rows"]
    merged["status"] = "shared"
    merged.loc[(merged["old_rows"] == 0) & (merged["new_rows"] > 0), "status"] = "new_anchor"
    merged.loc[(merged["old_rows"] > 0) & (merged["new_rows"] == 0), "status"] = "lost_anchor"
    return merged.sort_values("net_delta_new_minus_old").reset_index(drop=True)


def classify_stage_delta(row: pd.Series) -> str:
    if row["anchor_iso"] == TARGET_DEINIT_ANCHOR and int(row.get("stage", 0)) == 1:
        return "target_deinit_stage1_correction"
    if row["anchor_iso"] == TARGET_DEINIT_ANCHOR:
        return "target_anchor_other_stages"
    if row["status"] == "new_anchor":
        return "new_anchor_rows"
    if row["status"] == "lost_anchor":
        return "lost_anchor_rows"
    return "shared_anchor_other_lifecycle_delta"


def bucket_summary(stage_delta: pd.DataFrame) -> pd.DataFrame:
    frame = stage_delta.copy()
    frame["bucket"] = frame.apply(classify_stage_delta, axis=1)
    grouped = (
        frame.groupby("bucket", dropna=False)
        .agg(
            rows=("bucket", "count"),
            old_rows=("old_rows", "sum"),
            new_rows=("new_rows", "sum"),
            old_net=("old_net", "sum"),
            new_net=("new_net", "sum"),
            net_delta_new_minus_old=("net_delta_new_minus_old", "sum"),
        )
        .reset_index()
    )
    total = float(stage_delta["net_delta_new_minus_old"].sum())
    grouped["pct_of_total_delta_abs"] = grouped["net_delta_new_minus_old"].abs() / abs(total) * 100.0 if total else 0.0
    total_row = pd.DataFrame(
        [
            {
                "bucket": "total_close_retry_to_stage_state",
                "rows": int(len(stage_delta)),
                "old_rows": int(stage_delta["old_rows"].sum()),
                "new_rows": int(stage_delta["new_rows"].sum()),
                "old_net": float(stage_delta["old_net"].sum()),
                "new_net": float(stage_delta["new_net"].sum()),
                "net_delta_new_minus_old": total,
                "pct_of_total_delta_abs": 100.0,
            }
        ]
    )
    after_target = total - float(
        grouped.loc[grouped["bucket"].eq("target_deinit_stage1_correction"), "net_delta_new_minus_old"].sum()
    )
    extra_row = pd.DataFrame(
        [
            {
                "bucket": "extra_delta_after_target_stage1",
                "rows": "",
                "old_rows": "",
                "new_rows": "",
                "old_net": "",
                "new_net": "",
                "net_delta_new_minus_old": after_target,
                "pct_of_total_delta_abs": abs(after_target) / abs(total) * 100.0 if total else 0.0,
            }
        ]
    )
    out = pd.concat([grouped, extra_row, total_row], ignore_index=True)
    return round_numeric(out)


def active_rows_at(frame: pd.DataFrame, anchor_iso: str, exclude_key: tuple[str, str, str, str] | None = None) -> pd.DataFrame:
    anchor_dt = to_dt(anchor_iso)
    active = frame[(frame["open_dt"] <= anchor_dt) & (frame["exit_dt"] > anchor_dt)].copy()
    if exclude_key is not None:
        a, trig, src, direction = exclude_key
        same_key = (
            active["anchor_iso"].eq(a)
            & active["trigger_tag"].astype(str).eq(str(trig))
            & active["signal_src"].astype(str).eq(str(src))
            & active["dir"].astype(str).eq(str(direction))
        )
        active = active[~same_key].copy()
    return active


def active_description(active: pd.DataFrame, limit: int = 6) -> str:
    if active.empty:
        return ""
    rows = []
    for _, row in active.sort_values(["open_dt", "stage"]).head(limit).iterrows():
        rows.append(
            f"{row['anchor_iso']}|{row['signal_src']}|{row['dir']}|S{row['stage']}|exit={row['exit_dt']}"
        )
    suffix = "" if len(active) <= limit else f";+{len(active) - limit} more"
    return ";".join(rows) + suffix


def load_signals(directory: Path) -> pd.DataFrame:
    path = directory / "30m2H_strategy_signals_export.csv"
    if not path.exists():
        return pd.DataFrame()
    sig = read_csv(path).copy()
    sig["anchor_iso"] = sig["bar_time"].map(iso)
    keep = [
        "anchor_iso",
        "close",
        "m30_cross",
        "h2_dir",
        "h2_cross",
        "stop_pts",
        "decision",
        "skip_reason",
    ]
    return sig[[c for c in keep if c in sig.columns]].drop_duplicates("anchor_iso")


def audit_new_or_lost_anchors(anchor_delta: pd.DataFrame, old: pd.DataFrame, new: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    signals = load_signals(STAGE_STATE_DIR)
    rows = []
    for _, row in anchor_delta[anchor_delta["status"].isin(["new_anchor", "lost_anchor"])].iterrows():
        key = (row["anchor_iso"], row["trigger_tag"], row["signal_src"], row["dir"])
        old_active = active_rows_at(old, row["anchor_iso"], key)
        new_active = active_rows_at(new, row["anchor_iso"], key)
        record = row.to_dict()
        record.update(
            {
                "old_active_stage_rows_at_anchor": int(len(old_active)),
                "new_active_stage_rows_at_anchor": int(len(new_active)),
                "old_active_examples": active_description(old_active),
                "new_active_examples": active_description(new_active),
            }
        )
        if not signals.empty:
            hit = signals[signals["anchor_iso"].eq(row["anchor_iso"])]
            if not hit.empty:
                for col in ["decision", "skip_reason", "m30_cross", "h2_dir", "h2_cross", "stop_pts", "close"]:
                    if col in hit.columns:
                        record[f"signal_{col}"] = hit.iloc[0][col]
        rows.append(record)
    audit = pd.DataFrame(rows)
    new_audit = audit[audit["status"].eq("new_anchor")].copy() if not audit.empty else pd.DataFrame()
    lost_audit = audit[audit["status"].eq("lost_anchor")].copy() if not audit.empty else pd.DataFrame()
    return round_numeric(new_audit), round_numeric(lost_audit)


def top_residual_join(stage_delta: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    top = read_csv(REMAP_REVIEW_DIR / "stage_state_full_top_residual_trades.csv")
    top = top[top["scenario"].eq("stage_state_metadatafix_exec_model")].copy()
    top = top.sort_values("abs_profit_diff", ascending=False).drop_duplicates("mt5_trade_id").head(10)
    matches = read_csv(MAPPING_DIR / "python_mt5_mt5_unique_matches.csv")
    rows: list[dict[str, object]] = []
    for _, residual in top.iterrows():
        match = matches[matches["mt5_trade_id"].astype(str).eq(str(residual["mt5_trade_id"]))]
        match_row = match.iloc[0] if not match.empty else pd.Series(dtype=object)
        anchor = iso(residual["mt5_signal_anchor_time"])
        signal_src = str(match_row.get("mt5_signal_src", ""))
        direction = str(residual["dir_norm"])
        ledger_rows = new[
            new["anchor_iso"].eq(anchor)
            & new["signal_src"].astype(str).eq(signal_src)
            & new["dir"].astype(str).eq(direction)
        ].copy()
        delta_hit = stage_delta[
            stage_delta["anchor_iso"].eq(anchor)
            & stage_delta["signal_src"].astype(str).eq(signal_src)
            & stage_delta["dir"].astype(str).eq(direction)
        ]
        delta_net = float(delta_hit["net_delta_new_minus_old"].sum()) if not delta_hit.empty else 0.0
        delta_status = join_values(delta_hit["status"]) if not delta_hit.empty else ""
        reliable = str(residual["is_reliable_tier"]).lower() in {"true", "1"}
        if not reliable:
            review_priority = "mapping_policy_first"
        elif str(residual["primary_residual_driver"]) == "lot_sizing":
            review_priority = "execution_lot_sizing_or_balance_path"
        elif str(residual["primary_residual_driver"]) == "stage_exit_points":
            review_priority = "stage_exit_path"
        else:
            review_priority = "cost_or_rounding"
        rows.append(
            {
                "mt5_trade_id": residual["mt5_trade_id"],
                "py_trade_id": residual["py_trade_id"],
                "match_tier": residual["match_tier"],
                "is_reliable_tier": reliable,
                "review_priority": review_priority,
                "primary_residual_driver": residual["primary_residual_driver"],
                "anchor_iso": anchor,
                "signal_src": signal_src,
                "dir": direction,
                "py_profit": num(residual["py_profit"]),
                "mt5_profit": num(residual["mt5_profit"]),
                "profit_diff_py_minus_mt5": num(residual["profit_diff_py_minus_mt5"]),
                "abs_profit_diff": num(residual["abs_profit_diff"]),
                "stage_state_anchor_net": float(ledger_rows["net_profit"].sum()) if not ledger_rows.empty else 0.0,
                "stage_state_stage_reasons": join_values(ledger_rows["stage"].astype(str) + ":" + ledger_rows["local_exit_reason"].astype(str)),
                "stage_state_open_min": ledger_rows["open_dt"].min() if not ledger_rows.empty else "",
                "stage_state_exit_max": ledger_rows["exit_dt"].max() if not ledger_rows.empty else "",
                "close_retry_to_stage_state_delta_for_anchor": delta_net,
                "anchor_delta_status": delta_status,
                "lot_sizing_effect_mt5_minus_py": num(residual["lot_sizing_effect_mt5_minus_py"]),
                "stage_exit_points_effect_mt5_minus_py": num(residual["stage_exit_points_effect_mt5_minus_py"]),
                "swap_commission_effect_mt5_minus_py": num(residual["swap_commission_effect_mt5_minus_py"]),
            }
        )
    return round_numeric(pd.DataFrame(rows))


def exit_reason_delta(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    cols = ["local_exit_reason", "deal_reason"]
    old_g = old.groupby(cols, dropna=False).agg(old_rows=("stage", "count"), old_net=("net_profit", "sum")).reset_index()
    new_g = new.groupby(cols, dropna=False).agg(new_rows=("stage", "count"), new_net=("net_profit", "sum")).reset_index()
    merged = old_g.merge(new_g, on=cols, how="outer").fillna({"old_rows": 0, "new_rows": 0, "old_net": 0.0, "new_net": 0.0})
    merged["net_delta_new_minus_old"] = merged["new_net"] - merged["old_net"]
    merged["row_delta_new_minus_old"] = merged["new_rows"] - merged["old_rows"]
    return round_numeric(merged.sort_values("net_delta_new_minus_old"))


def decision_rows(bucket: pd.DataFrame, stage_delta: pd.DataFrame, top_residuals: pd.DataFrame) -> pd.DataFrame:
    total = float(bucket.loc[bucket["bucket"].eq("total_close_retry_to_stage_state"), "net_delta_new_minus_old"].iloc[0])
    target = float(bucket.loc[bucket["bucket"].eq("target_deinit_stage1_correction"), "net_delta_new_minus_old"].sum())
    extra = float(bucket.loc[bucket["bucket"].eq("extra_delta_after_target_stage1"), "net_delta_new_minus_old"].iloc[0])
    top_non_target = bucket[
        bucket["bucket"].isin(["new_anchor_rows", "shared_anchor_other_lifecycle_delta", "target_anchor_other_stages"])
    ].copy()
    non_target_stage = stage_delta[
        ~(
            stage_delta["anchor_iso"].eq(TARGET_DEINIT_ANCHOR)
            & (pd.to_numeric(stage_delta["stage"], errors="coerce") == 1)
        )
    ].copy()
    largest_stage = (
        non_target_stage.sort_values("net_delta_new_minus_old", key=lambda s: s.abs(), ascending=False).iloc[0]
        if not non_target_stage.empty
        else pd.Series(dtype=object)
    )
    mapping_first = int(top_residuals["review_priority"].eq("mapping_policy_first").sum()) if not top_residuals.empty else 0
    reliable_top = int(top_residuals["is_reliable_tier"].astype(bool).sum()) if not top_residuals.empty else 0
    return pd.DataFrame(
        [
            {
                "gate": "stage_state_lifecycle_delta_localization",
                "merge_gate_pass": False,
                "total_delta_new_minus_old": total,
                "target_deinit_stage1_delta": target,
                "extra_delta_after_target_stage1": extra,
                "target_explains_pct_of_abs_total": abs(target) / abs(total) * 100.0 if total else 0.0,
                "largest_non_target_bucket": top_non_target.sort_values(
                    "net_delta_new_minus_old", key=lambda s: s.abs(), ascending=False
                ).iloc[0]["bucket"]
                if not top_non_target.empty
                else "",
                "largest_non_target_stage_anchor": largest_stage.get("anchor_iso", ""),
                "largest_non_target_stage": largest_stage.get("stage", ""),
                "largest_non_target_stage_delta": largest_stage.get("net_delta_new_minus_old", ""),
                "top_residual_mapping_policy_first_count": mapping_first,
                "top_residual_reliable_count": reliable_top,
                "next_action": "audit_2025_09_05_stage3_then_new_anchor_position_gate",
            }
        ]
    )


def round_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    for col in out.select_dtypes(include=["number"]).columns:
        out[col] = out[col].round(6)
    return out


def write_report(
    bucket: pd.DataFrame,
    anchor_delta: pd.DataFrame,
    stage_delta: pd.DataFrame,
    new_anchors: pd.DataFrame,
    lost_anchors: pd.DataFrame,
    top_residuals: pd.DataFrame,
    exits: pd.DataFrame,
    decision: pd.DataFrame,
) -> None:
    largest_non_target = stage_delta[
        ~(
            stage_delta["anchor_iso"].eq(TARGET_DEINIT_ANCHOR)
            & (pd.to_numeric(stage_delta["stage"], errors="coerce") == 1)
        )
    ].copy()
    largest_non_target = largest_non_target.sort_values(
        "net_delta_new_minus_old", key=lambda s: s.abs(), ascending=False
    ).head(20)
    lines = [
        "# Stage-state lifecycle delta localization",
        "",
        "## Scope",
        "",
        f"- Baseline ledger: `{BASELINE_DIR}`.",
        f"- Stage-state ledger: `{STAGE_STATE_DIR}`.",
        "- Compares close-retry baseline to stage-state full at anchor and anchor-stage levels.",
        "- No EA/Python behavior is changed in this diagnostic.",
        "",
        "## Decision",
        "",
        markdown_table(decision),
        "",
        "## Delta Buckets",
        "",
        markdown_table(bucket),
        "",
        "## New Anchors",
        "",
        markdown_table(new_anchors),
        "",
        "## Lost Anchors",
        "",
        markdown_table(lost_anchors),
        "",
        "## Largest Non-target Stage Deltas",
        "",
        markdown_table(largest_non_target),
        "",
        "## Top Residual Ledger Join",
        "",
        markdown_table(top_residuals),
        "",
        "## Exit Reason Delta",
        "",
        markdown_table(exits),
        "",
        "## Interpretation",
        "",
        "- The target `mt5_0031` deinit Stage1 correction is separated from all other lifecycle deltas.",
        "- `extra_delta_after_target_stage1` is the remaining full-run regression after removing the known invalid end-of-test profit.",
        "- New anchors are audited with baseline/stage-state active position context at the anchor time.",
        "- Top residual rows are tagged as mapping-policy-first, execution lot-sizing/balance path, or Stage-exit path to avoid changing the wrong layer.",
        "",
        "## Output Files",
        "",
        "- `stage_state_delta_bucket_summary.csv`",
        "- `stage_state_anchor_delta_summary.csv`",
        "- `stage_state_stage_delta_summary.csv`",
        "- `stage_state_largest_non_target_stage_deltas.csv`",
        "- `stage_state_new_anchor_audit.csv`",
        "- `stage_state_lost_anchor_audit.csv`",
        "- `stage_state_top_residual_ledger_join.csv`",
        "- `stage_state_exit_reason_delta.csv`",
        "- `stage_state_lifecycle_decision.csv`",
    ]
    write_text(OUT_DIR / "stage_state_lifecycle_delta_localization_review.md", "\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    old = prep_ledger(read_csv(BASELINE_DIR / "30m2H_strategy_trade_ledger.csv"), "close_retry")
    new = prep_ledger(read_csv(STAGE_STATE_DIR / "30m2H_strategy_trade_ledger.csv"), "stage_state")

    anchor_delta = round_numeric(build_delta(old, new, include_stage=False))
    stage_delta = build_delta(old, new, include_stage=True)
    stage_delta["bucket"] = stage_delta.apply(classify_stage_delta, axis=1)
    stage_delta = round_numeric(stage_delta)
    buckets = bucket_summary(stage_delta)
    new_anchors, lost_anchors = audit_new_or_lost_anchors(anchor_delta, old, new)
    top_residuals = top_residual_join(stage_delta, new)
    exits = exit_reason_delta(old, new)
    decision = round_numeric(decision_rows(buckets, stage_delta, top_residuals))

    largest_non_target = stage_delta[
        ~(
            stage_delta["anchor_iso"].eq(TARGET_DEINIT_ANCHOR)
            & (pd.to_numeric(stage_delta["stage"], errors="coerce") == 1)
        )
    ].copy()
    largest_non_target = largest_non_target.sort_values(
        "net_delta_new_minus_old", key=lambda s: s.abs(), ascending=False
    ).head(40)

    export_csv(buckets, OUT_DIR / "stage_state_delta_bucket_summary.csv")
    export_csv(anchor_delta, OUT_DIR / "stage_state_anchor_delta_summary.csv")
    export_csv(stage_delta, OUT_DIR / "stage_state_stage_delta_summary.csv")
    export_csv(round_numeric(largest_non_target), OUT_DIR / "stage_state_largest_non_target_stage_deltas.csv")
    export_csv(new_anchors, OUT_DIR / "stage_state_new_anchor_audit.csv")
    export_csv(lost_anchors, OUT_DIR / "stage_state_lost_anchor_audit.csv")
    export_csv(top_residuals, OUT_DIR / "stage_state_top_residual_ledger_join.csv")
    export_csv(exits, OUT_DIR / "stage_state_exit_reason_delta.csv")
    export_csv(decision, OUT_DIR / "stage_state_lifecycle_decision.csv")
    write_report(buckets, anchor_delta, stage_delta, new_anchors, lost_anchors, top_residuals, exits, decision)

    print(buckets.to_string(index=False))
    print()
    print(decision.to_string(index=False))
    print()
    print(new_anchors.to_string(index=False))
    print(f"\nWrote {OUT_DIR}")


if __name__ == "__main__":
    main()
