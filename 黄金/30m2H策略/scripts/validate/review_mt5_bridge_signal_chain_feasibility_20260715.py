# -*- coding: utf-8 -*-
"""Signal-chain feasibility review for P0/P1 MT5 bridge candidates."""
from __future__ import annotations


from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
STRATEGY_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = STRATEGY_DIR / "data"
VALIDATION_DIR = DATA_DIR / "validation"

SIGNAL_DIR = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "python_h2_context_q2early"
M30_SHIFT90 = DATA_DIR / "signals_mt5_shift90_metadatafix_20260714" / "m30_prepared_with_mt5_shift90.csv"
M15_CONTEXT = DATA_DIR / "processed" / "m15_context_bars.csv"

ROW_IMPACT_DIR = VALIDATION_DIR / "row_level_split_spread_impact_20260715"
BRIDGE_DIR = VALIDATION_DIR / "m15_slot1_time_axis_bridge_20260714"
POST_BRIDGE_DIR = VALIDATION_DIR / "post_bridge_remaining_p1_review_20260714"
TWO_SIDED_DIR = VALIDATION_DIR / "two_sided_correction_prototype_20260715"

OUT_DIR = VALIDATION_DIR / "mt5_bridge_signal_chain_feasibility_20260715"

WINDOWS = [0, 60, 180, 24 * 60, 7 * 24 * 60]


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
    if any(token in text for token in ["slot1", "replace", "rescue"]):
        return "M15 SLOT1"
    return "M30 CLOSE"


def parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def markdown_table(frame: pd.DataFrame, max_rows: int = 20) -> str:
    if frame.empty:
        return "_No rows._"
    return frame.head(max_rows).to_markdown(index=False)


def load_layers() -> dict[str, pd.DataFrame]:
    layers = {
        "raw": read_csv(SIGNAL_DIR / "raw_candidates.csv"),
        "accepted": read_csv(SIGNAL_DIR / "候选信号_Layer1_Layer2通过.csv"),
        "picked": read_csv(SIGNAL_DIR / "最终信号_Layer3入选.csv"),
        "stage": read_csv(SIGNAL_DIR / "执行交易_Stage结果.csv"),
    }
    picked_meta = layers["picked"][
        [
            c
            for c in [
                "date",
                "mode",
                "dir",
                "trigger",
                "variant",
                "entry",
                "stop",
                "sd",
                "spec_pass",
                "spec_reason",
                "layer3_eval_time",
                "Bias_5_ea",
                "layer3_threshold_ea",
                "layer3_pass_ea",
            ]
            if c in layers["picked"].columns
        ]
    ].copy()
    if not picked_meta.empty:
        layers["stage"] = layers["stage"].merge(
            picked_meta,
            on=["date", "mode", "dir"],
            how="left",
            suffixes=("", "_picked"),
        )

    for name, frame in layers.items():
        frame = frame.copy()
        frame["date_dt"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["dir_norm"] = frame["dir"].map(norm_dir)
        frame["mode_family"] = frame["mode"].map(mode_family)
        if "trigger" in frame.columns:
            frame["trigger_family"] = frame["trigger"].astype(str).str.replace("[", "", regex=False).str.replace("]", "", regex=False)
        elif "variant" in frame.columns:
            frame["trigger_family"] = frame["variant"].map(trigger_family_from_variant)
        else:
            frame["trigger_family"] = ""
        for col in ["entry", "stop", "sd", "Bias_5_ea", "layer3_threshold_ea"]:
            if col in frame.columns:
                frame[col] = pd.to_numeric(frame[col], errors="coerce")
        layers[name] = frame
    return layers


def load_seed() -> pd.DataFrame:
    seed = read_csv(ROW_IMPACT_DIR / "two_sided_seed_mt5_recoveries.csv")
    seed = seed[seed["two_sided_priority"].astype(str).str.startswith(("P0_", "P1_"))].copy()
    seed["aligned_time_dt"] = pd.to_datetime(seed["aligned_time"], errors="coerce")
    seed["signal_anchor_time_dt"] = pd.to_datetime(seed["signal_anchor_time"], errors="coerce")
    seed["dir_norm"] = seed["dir_norm"].map(norm_dir)
    return seed


def load_bridge_context() -> tuple[pd.DataFrame, pd.DataFrame]:
    bridge = read_csv(BRIDGE_DIR / "m15_slot1_time_axis_bridge_candidates.csv")
    bridge = bridge.rename(columns={"remaining_trade_id": "mt5_trade_id"})
    post = read_csv(POST_BRIDGE_DIR / "post_bridge_signal_set_cases.csv")
    post = post.rename(columns={"trade_id": "mt5_trade_id"})
    return bridge, post


def processed_coverage() -> tuple[set[pd.Timestamp], set[pd.Timestamp]]:
    m30 = read_csv(M30_SHIFT90)
    m15 = read_csv(M15_CONTEXT)
    m30_dates = set(pd.to_datetime(m30["date"], errors="coerce").dropna())
    m15_dates = set(pd.to_datetime(m15["date"], errors="coerce").dropna())
    return m30_dates, m15_dates


def nearest_rows(layer: str, frame: pd.DataFrame, seed_row: pd.Series, limit: int = 5) -> pd.DataFrame:
    target = seed_row["aligned_time_dt"]
    same_dir = frame[frame["dir_norm"] == seed_row["dir_norm"]].copy()
    if same_dir.empty or pd.isna(target):
        return pd.DataFrame()
    same_dir["abs_minutes"] = (same_dir["date_dt"] - target).dt.total_seconds().abs() / 60.0
    same_dir["signed_minutes"] = (same_dir["date_dt"] - target).dt.total_seconds() / 60.0
    same_dir["same_mode_family"] = same_dir["mode_family"].astype(str) == str(seed_row["mode_family"])
    same_dir["same_trigger_family"] = same_dir["trigger_family"].astype(str) == str(seed_row["trigger_family"])
    same_dir = same_dir.sort_values(
        ["abs_minutes", "same_trigger_family", "same_mode_family"],
        ascending=[True, False, False],
    ).head(limit)
    cols = [
        "date",
        "signed_minutes",
        "abs_minutes",
        "dir_norm",
        "trigger_family",
        "mode",
        "mode_family",
        "variant",
        "entry",
        "stop",
        "sd",
        "spec_pass",
        "spec_reason",
        "Bias_5_ea",
        "layer3_threshold_ea",
        "layer3_pass_ea",
        "total_$",
        "stage1_exit",
        "stage2_exit",
        "stage3_exit",
        "same_trigger_family",
        "same_mode_family",
    ]
    out = same_dir[[c for c in cols if c in same_dir.columns]].copy()
    out.insert(0, "layer", layer)
    out.insert(0, "mt5_trade_id", seed_row["mt5_trade_id"])
    return out


def exact_status(layer_frame: pd.DataFrame, seed_row: pd.Series) -> dict[str, object]:
    target = seed_row["aligned_time_dt"]
    if pd.isna(target):
        return {"count": 0}
    exact = layer_frame[
        (layer_frame["date_dt"] == target)
        & (layer_frame["dir_norm"] == seed_row["dir_norm"])
        & (layer_frame["mode_family"].astype(str) == str(seed_row["mode_family"]))
    ].copy()
    same_trigger = exact[exact["trigger_family"].astype(str) == str(seed_row["trigger_family"])]
    picked = same_trigger if not same_trigger.empty else exact
    row = picked.iloc[0] if not picked.empty else None
    return {
        "count": int(len(exact)),
        "same_trigger_count": int(len(same_trigger)),
        "mode": row.get("mode", "") if row is not None else "",
        "trigger_family": row.get("trigger_family", "") if row is not None else "",
        "variant": row.get("variant", "") if row is not None else "",
        "entry": row.get("entry", "") if row is not None else "",
        "stop": row.get("stop", "") if row is not None else "",
        "sd": row.get("sd", "") if row is not None else "",
        "spec_pass": row.get("spec_pass", "") if row is not None else "",
        "spec_reason": row.get("spec_reason", "") if row is not None else "",
        "layer3_pass_ea": row.get("layer3_pass_ea", "") if row is not None else "",
        "total_$": row.get("total_$", "") if row is not None else "",
    }


def classify_feasibility(seed_row: pd.Series, bridge_row: pd.Series | None, statuses: dict[str, dict[str, object]]) -> dict[str, str]:
    raw = statuses["raw"]
    accepted = statuses["accepted"]
    picked = statuses["picked"]
    stage = statuses["stage"]
    bridge_class = str(bridge_row.get("bridge_class", "")) if bridge_row is not None else ""
    has_gap = parse_bool(bridge_row.get("has_time_axis_gap", "")) if bridge_row is not None else False
    ledger_spec = num(seed_row.get("bridge_ledger_stop_pts_spec"), num(bridge_row.get("ledger_stop_pts_spec", "") if bridge_row is not None else "", 0.0))
    ledger_spec_ok = 5.0 <= ledger_spec <= 35.0

    if int(stage.get("same_trigger_count", 0)) > 0:
        current = "yes_stage_exact"
    elif int(picked.get("same_trigger_count", 0)) > 0:
        current = "no_stage_missing_after_picked"
    elif int(accepted.get("same_trigger_count", 0)) > 0:
        current = "no_layer3_or_stage_missing"
    elif int(raw.get("same_trigger_count", 0)) > 0:
        current = "no_raw_exists_but_rejected_before_accepted"
    elif int(raw.get("count", 0)) > 0:
        current = "no_raw_same_time_mode_but_trigger_diff_or_reject"
    else:
        current = "no_raw_missing"

    if current.startswith("yes"):
        rule = "none_current_chain_already_generates"
        risk = "low"
        bridge_feas = "already_generated"
    elif has_gap and bridge_class == "time_axis_bridge_candidate" and ledger_spec_ok:
        rule = "data_axis_bridge_or_backfill_required"
        risk = "medium"
        bridge_feas = "feasible_if_processed_time_axis_gap_is_restored"
    elif int(raw.get("count", 0)) > 0 and str(raw.get("spec_reason", "")) in {"too_wide", "too_tight"} and ledger_spec_ok:
        rule = "m15_entry_stop_reconstruction_required"
        risk = "high"
        bridge_feas = "possible_but_needs_signal_rule_proof"
    elif "missing_raw_parent" in str(seed_row.get("effective_cause_bucket", "")):
        rule = "raw_parent_construction_required"
        risk = "high"
        bridge_feas = "not_proven"
    else:
        rule = "manual_review_required"
        risk = "high"
        bridge_feas = "not_proven"

    return {
        "current_can_generate": current,
        "bridge_feasibility": bridge_feas,
        "required_rule_change": rule,
        "risk_level": risk,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    layers = load_layers()
    seed = load_seed()
    bridge, post = load_bridge_context()
    m30_dates, m15_dates = processed_coverage()

    seed = seed.merge(
        bridge,
        on="mt5_trade_id",
        how="left",
        suffixes=("", "_bridge"),
    )
    post_cols = [
        "mt5_trade_id",
        "effective_cause_bucket",
        "post_bridge_action_bucket",
        "nearby_status",
        "nearby_abs_minutes",
        "nearby_time",
        "parent_status",
        "picked_status",
        "executed_status",
        "bridge_reclass_applied_bool",
    ]
    seed = seed.merge(post[[c for c in post_cols if c in post.columns]], on="mt5_trade_id", how="left", suffixes=("", "_post"))

    summary_rows: list[dict[str, object]] = []
    nearest_frames: list[pd.DataFrame] = []
    exact_rows: list[dict[str, object]] = []

    for _, row in seed.iterrows():
        statuses = {layer: exact_status(frame, row) for layer, frame in layers.items()}
        bridge_row = row
        feasibility = classify_feasibility(row, bridge_row, statuses)

        for layer, status in statuses.items():
            exact_item = {"mt5_trade_id": row["mt5_trade_id"], "layer": layer}
            exact_item.update(status)
            exact_rows.append(exact_item)
            near = nearest_rows(layer, layers[layer], row)
            if not near.empty:
                nearest_frames.append(near)

        shifted_anchor = pd.to_datetime(row.get("shifted_anchor", row.get("aligned_time")), errors="coerce")
        log_time_plus90 = pd.to_datetime(row.get("log_time_plus90", ""), errors="coerce")
        raw_anchor = pd.to_datetime(row.get("raw_anchor", row.get("signal_anchor_time")), errors="coerce")

        nearest_raw_entry = num(row.get("nearest_raw_entry"), 0.0)
        nearest_raw_stop = num(row.get("nearest_raw_stop"), 0.0)
        ledger_entry = num(row.get("ledger_signal_entry", row.get("bridge_ledger_signal_entry")), 0.0)
        ledger_stop = num(row.get("ledger_signal_stop", row.get("bridge_ledger_signal_stop")), 0.0)

        summary_rows.append(
            {
                "mt5_trade_id": row["mt5_trade_id"],
                "priority": row["two_sided_priority"],
                "aligned_time": row["aligned_time"],
                "signal_anchor_time": row["signal_anchor_time"],
                "raw_anchor": raw_anchor,
                "log_time": row.get("log_time", row.get("bridge_log_time", "")),
                "log_time_plus90": log_time_plus90,
                "dir_norm": row["dir_norm"],
                "trigger_family": row["trigger_family"],
                "mode_family": row["mode_family"],
                "signal_src": row["signal_src"],
                "net_profit": num(row["net_profit"]),
                "effective_cause_bucket": row.get("effective_cause_bucket", row.get("effective_cause_bucket_post", "")),
                "post_bridge_action_bucket": row.get("post_bridge_action_bucket", row.get("post_bridge_action_bucket_post", "")),
                "bridge_class": row.get("bridge_class", ""),
                "has_time_axis_gap": parse_bool(row.get("has_time_axis_gap", "")),
                "processed_m30_has_shifted_anchor": shifted_anchor in m30_dates if pd.notna(shifted_anchor) else False,
                "processed_m15_has_log_plus90": log_time_plus90 in m15_dates if pd.notna(log_time_plus90) else False,
                "current_raw_count": statuses["raw"]["count"],
                "current_raw_same_trigger_count": statuses["raw"]["same_trigger_count"],
                "current_raw_spec_pass": statuses["raw"].get("spec_pass", ""),
                "current_raw_spec_reason": statuses["raw"].get("spec_reason", ""),
                "current_accepted_count": statuses["accepted"]["count"],
                "current_picked_count": statuses["picked"]["count"],
                "current_stage_count": statuses["stage"]["count"],
                "nearest_raw_time": row.get("nearest_raw_time", ""),
                "nearest_raw_abs_minutes": row.get("nearest_raw_abs_minutes", ""),
                "nearest_raw_mode": row.get("nearest_raw_mode", ""),
                "nearest_raw_spec_reason": row.get("nearest_raw_spec_reason", ""),
                "ledger_stop_pts_spec": num(row.get("ledger_stop_pts_spec", row.get("bridge_ledger_stop_pts_spec")), 0.0),
                "ledger_entry": ledger_entry,
                "ledger_stop": ledger_stop,
                "nearest_raw_entry": nearest_raw_entry,
                "nearest_raw_stop": nearest_raw_stop,
                "entry_diff_ledger_minus_nearest_raw": round(ledger_entry - nearest_raw_entry, 6) if nearest_raw_entry else "",
                "stop_diff_ledger_minus_nearest_raw": round(ledger_stop - nearest_raw_stop, 6) if nearest_raw_stop else "",
                **feasibility,
            }
        )

    summary = pd.DataFrame(summary_rows)
    exact = pd.DataFrame(exact_rows)
    nearest = pd.concat(nearest_frames, ignore_index=True, sort=False) if nearest_frames else pd.DataFrame()

    export_csv(summary, OUT_DIR / "bridge_signal_chain_feasibility.csv")
    export_csv(exact, OUT_DIR / "bridge_exact_layer_status.csv")
    export_csv(nearest, OUT_DIR / "bridge_nearest_layer_candidates.csv")

    decision = summary[
        [
            "mt5_trade_id",
            "priority",
            "current_can_generate",
            "bridge_feasibility",
            "required_rule_change",
            "risk_level",
            "has_time_axis_gap",
            "processed_m30_has_shifted_anchor",
            "processed_m15_has_log_plus90",
            "current_raw_count",
            "current_raw_spec_reason",
            "net_profit",
        ]
    ].copy()
    export_csv(decision, OUT_DIR / "bridge_feasibility_decision_matrix.csv")

    p0 = decision[decision["priority"].astype(str).str.startswith("P0_")]
    p1 = decision[decision["priority"].astype(str).str.startswith("P1_")]

    report = [
        "# MT5 bridge signal-chain feasibility review",
        "",
        "## Decision Matrix",
        markdown_table(decision, max_rows=20),
        "",
        "## P0 Summary",
        markdown_table(p0, max_rows=10),
        "",
        "## P1 Summary",
        markdown_table(p1, max_rows=10),
        "",
        "## Interpretation",
        "",
        "- `current_can_generate` checks the current Python-MT5 raw/accepted/picked/stage chain at the MT5 aligned time.",
        "- P0 rows are feasible only as data-axis bridge/backfill candidates when processed M15/M30 coverage is missing but MT5 ledger stop spec is valid.",
        "- P1 rows have normal time-axis availability but current raw entries fail StopSpec; they need a separate M15 entry/stop reconstruction proof before any signal rule can be proposed.",
        "- This review does not modify strategy code and does not treat MT5 ledger injection as a mergeable fix.",
    ]
    write_text(OUT_DIR / "mt5_bridge_signal_chain_feasibility_review.md", "\n".join(report))
    write_text(OUT_DIR / "README.md", "Signal-chain feasibility review for P0/P1 MT5 bridge candidates.\n")


if __name__ == "__main__":
    main()
